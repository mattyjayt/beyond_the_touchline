"""Assistant-coach page view (spec §6-§7): assembles one ``BenchView`` from Store data.

I/O at the edge only (Store reads, the importance JSON). Every number comes from the tested
services - matchups, advisor, race - and nothing past the replay clock is read. The alert is
sticky: once the hot-duel trigger has fired, its (slot, attacker) pair stays the page's subject
and is tracked as the slot changes hands, so the swap's before and after stay on screen.
"""

import json
from pathlib import Path

from app.models import (
    BenchView,
    ImportanceItem,
    MatchEvent,
    PlayerCard,
    Recommendation,
    SwapImpact,
)
from app.replay import ReplayManager
from app.services.advisor import (
    AdvisorInput,
    advisor_input,
    evaluate,
    keep_only,
    option_label,
    projected_win,
)
from app.services.matchups import (
    current_slots,
    duel_ledger,
    first_trigger,
    hot_duels,
    hot_pair,
    swap_impact,
)
from app.services.race import race
from app.store import Store

IMPORTANCE_PATH = Path(__file__).resolve().parents[2] / "data" / "variable_importance.json"


def load_importance(path: Path = IMPORTANCE_PATH) -> tuple[list[ImportanceItem], str]:
    """The duel study's ranked variables and a one-line note; empty until the study ran."""
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return [], ""
    note = f"{data['method']} · n={data['n']} · test AUC {data['auc']} · {data['caveat']}"
    return [ImportanceItem(**i) for i in data["ranked"]], note


def _card(store: Store, pid: str, slots: dict[str, str], duel_win: float) -> PlayerCard:
    p = store.players[pid]
    ph, pr = p.physical, p.priors
    profile = {
        "pace": ph.speed_idx,
        "acceleration": ph.accel_idx,
        "agility": ph.agility_idx,
        "stamina": ph.stamina_idx,
        "defending": pr.defending,
        "stance": ph.stance_idx,
        "duel_win": duel_win * 100,
    }
    return PlayerCard(
        player_id=pid, name=p.display_name, slot=slots.get(pid), position=p.primary_position,
        physical=ph, priors=pr,
        profile={k: round(max(0.0, min(100.0, float(v))), 1) for k, v in profile.items()},
    )  # fmt: skip


def _executed_rank(
    store: Store, match_id: str, team_id: str, impact: SwapImpact, alert_options: list
) -> int | None:
    """Rank, at the alert, of the option matching the position change actually made."""
    made = {
        (e.player_id, e.qualifiers.get("from_slot"), e.qualifiers.get("to_slot"))
        for e in store.events(match_id)
        if e.event_type == "position_change" and e.team_id == team_id
        and e.event_sec == impact.swap_sec
    }  # fmt: skip
    for o in alert_options:
        if (
            o.option_type == "position_swap"
            and {(m.player_id, m.from_slot, m.to_slot) for m in o.moves} == made
        ):
            return o.option_rank
    return None


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.0%}"


def _briefing(
    store: Store,
    head: str,
    inp: AdvisorInput | None,
    options: list[Recommendation],
    impact: SwapImpact | None,
) -> str:
    """Deterministic assistant-coach text (the rules fallback for the briefing)."""
    if inp is None:
        return f"{head} No defender is being beaten repeatedly yet. KEEP: nothing to fix."
    names = {pid: p.display_name for pid, p in store.players.items()}
    h = inp.hot
    parts = [
        head,
        (
            f"{names[h.attacker_id]} vs {h.defender_slot} {names[h.defender_id]}: beaten "
            f"{h.beaten_20m} in the last 20' (defender win {_pct(h.win_pct_20m)}, n={h.n_20m})."
        ),
    ]
    if impact is not None:
        a = impact.after
        parts.append(
            f"Since the {impact.swap_sec // 60}' change the {h.defender_slot} has won "
            f"{_pct(a.win_pct)} (n={a.duels}) against {_pct(impact.before.win_pct)} "
            f"(n={impact.before.duels}) in the 20' before."
        )
    ranking = "; ".join(f"{o.option_rank}) {option_label(o, names)}" for o in options)
    parts.append(f"Advisor ranking (policy weights): {ranking}.")
    top = next((o for o in options if o.option_type != "keep"), None)
    if top is not None:
        parts.append(f"Top change: {top.pros[0]}.")
    keep = next(o for o in options if o.option_type == "keep")
    parts.append(f"KEEP is still an option: {keep.pros[0].lower()}.")
    return " ".join(parts)


def build_bench_view(
    store: Store, replays: ReplayManager, match_id: str, team_id: str, asof_sec: int | None
) -> BenchView:
    clock = int(replays.get(match_id).clock)
    asof = clock if asof_sec is None else max(0, min(asof_sec, clock))
    events: list[MatchEvent] = [e for e in store.events(match_id) if e.event_sec <= asof]
    rosters = store.rosters(match_id)
    match = store.matches[match_id]
    score = {
        t: sum(
            1 for e in events if e.event_type == "shot" and e.outcome == "goal" and e.team_id == t
        )
        for t in (match.home_team_id, match.away_team_id)
    }
    minute = asof // 60 + 1
    teams = store.teams
    head = (
        f"{minute}' · {teams[match.home_team_id].name} {score[match.home_team_id]}-"
        f"{score[match.away_team_id]} {teams[match.away_team_id].name} (simulated)."
    )
    importance, importance_note = load_importance()
    team_of = {r.player_id: r.team_id for r in rosters}
    ours = {p: s for p, s in current_slots(rosters, events, asof).items() if team_of[p] == team_id}
    fired_sec, fired = first_trigger(events, rosters, team_id, asof)
    if fired_sec is None:
        return BenchView(
            match_id=match_id, team_id=team_id, asof_sec=asof, minute=minute, score=score,
            alert=None, alert_active=False, tormentor=None, defender=None, ledger=None,
            options=[keep_only(match_id, team_id, asof)], cards={}, race=None, impact=None,
            executed_option_rank_at_alert=None, importance=importance,
            importance_note=importance_note, slots=ours,
            briefing_seed=_briefing(store, head, None, [], None), briefing_evidence_ids=[],
        )  # fmt: skip

    first = fired[0]
    slot, att = first.defender_slot, first.attacker_id
    hot = hot_pair(events, rosters, team_id, slot, att, asof, fired_sec)
    active = any(
        h.defender_slot == slot and h.attacker_id == att
        for h in hot_duels(events, rosters, team_id, asof)
    )
    inp = advisor_input(store, match_id, team_id, asof, hot=hot) if hot else None
    options = evaluate(inp) if inp else [keep_only(match_id, team_id, asof)]
    ledger = duel_ledger(events, att, slot, team_id, rosters, asof)
    impact = swap_impact(events, rosters, team_id, att, slot, asof)
    executed = None
    if impact is not None:
        at_alert = advisor_input(store, match_id, team_id, fired_sec, hot=first)
        if at_alert is not None:
            executed = _executed_rank(store, match_id, team_id, impact, evaluate(at_alert))

    slots = current_slots(rosters, events, asof)
    cards: dict[str, PlayerCard] = {}
    tormentor = defender = None
    race_ids: list[str] = []
    if inp is not None:
        dfn = inp.hot.defender_id
        tormentor = _card(store, att, slots, 1 - projected_win(inp, dfn))
        defender = _card(store, dfn, slots, projected_win(inp, dfn))
        cards = {att: tormentor, dfn: defender}
        for o in options:
            for m in o.moves:
                if m.player_id not in cards:
                    cards[m.player_id] = _card(store, m.player_id, slots,
                                               projected_win(inp, m.player_id))  # fmt: skip
        race_ids = [att, dfn] + [
            o.incoming_player_id for o in options
            if o.incoming_player_id and o.incoming_player_id not in (att, dfn)
        ]  # fmt: skip
    race_res = race([store.players[p] for p in dict.fromkeys(race_ids)]) if race_ids else None

    evidence = [p.event_id for p in ledger.points if p.sec > asof - 1200][-6:]
    return BenchView(
        match_id=match_id, team_id=team_id, asof_sec=asof, minute=minute, score=score,
        alert=hot, alert_active=active, tormentor=tormentor, defender=defender, ledger=ledger,
        options=options, cards=cards, race=race_res, impact=impact,
        executed_option_rank_at_alert=executed, importance=importance,
        importance_note=importance_note, slots=ours,
        briefing_seed=_briefing(store, head, inp, options, impact),
        briefing_evidence_ids=evidence or ledger.evidence_event_ids[-6:],
    )  # fmt: skip
