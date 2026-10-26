"""Agent tools (spec §8) - defined ONCE, exposed via REST, MCP (/mcp) and the
Claude Agent SDK. Read tools are deterministic; `publish_insight` is the only
write and is grounding-checked. The LLM never computes or alters match facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models import Insight, MatchEvent
from app.replay import ReplayManager
from app.services.advisor import POLICY_WEIGHTS, advisor_input, evaluate, keep_only
from app.services.bench import build_bench_view
from app.services.matchups import duel_ledger, hot_duels
from app.services.performance import (
    METHODOLOGY_VERSION,
    live_rating,
    minutes_played,
    player_metrics,
)
from app.store import Store

CAVEAT = (
    "Scores are policy-weighted model outputs from synthetic priors and an uncalibrated duel "
    "model, not causal effects."
)


@dataclass
class AgentContext:
    store: Store
    replays: ReplayManager


_ctx: AgentContext | None = None


def init(store: Store, replays: ReplayManager) -> None:
    global _ctx
    _ctx = AgentContext(store, replays)


def ctx() -> AgentContext:
    if _ctx is None:
        raise RuntimeError("agent tools not initialised")
    return _ctx


def _asof(match_id: str, asof_sec: int | None) -> int:
    """Agents may look back but never past the live replay clock (no future leakage)."""
    clock = int(ctx().replays.get(match_id).clock)
    return clock if asof_sec is None else min(asof_sec, clock)


def _events(match_id: str, asof: float) -> list[MatchEvent]:
    return [e for e in ctx().store.events(match_id) if e.event_sec <= asof]


def _name(pid: str | None) -> str | None:
    return ctx().store.players[pid].display_name if pid and pid in ctx().store.players else pid


# --------------------------------------------------------------------------- read tools


async def get_match_state(match_id: str, asof_sec: int | None = None) -> dict[str, Any]:
    """Score, formations, on-pitch players (with live ratings) and available bench."""
    store = ctx().store
    session = ctx().replays.get(match_id)
    asof = _asof(match_id, asof_sec)
    state = session.state(asof)
    rosters = store.rosters(match_id)
    events = store.events(match_id)
    on_pitch_ids = {p.player_id for p in state.on_pitch}
    used = {
        e.recipient_id for e in events if e.event_type == "substitution" and e.event_sec <= asof
    }
    match = store.matches[match_id]
    players = []
    for p in state.on_pitch:
        player = store.players[p.player_id]
        mins = minutes_played(p.player_id, rosters, events, asof)
        rating, _, low = live_rating(player, events, asof, mins)
        players.append(
            {"player_id": p.player_id, "name": player.display_name, "team_id": p.team_id,
             "slot": p.formation_slot, "live_rating": rating, "low_confidence": low}
        )  # fmt: skip
    bench = [
        {"player_id": r.player_id, "name": _name(r.player_id), "team_id": r.team_id,
         "position": store.players[r.player_id].primary_position}
        for r in rosters
        if r.roster_status == "bench" and r.player_id not in used and r.player_id not in on_pitch_ids
    ]  # fmt: skip
    return {
        "match_id": match_id,
        "asof_sec": asof,
        "minute": asof // 60 + 1,
        "home": {"team_id": match.home_team_id, "formation": match.home_formation,
                 **state.home.model_dump()},
        "away": {"team_id": match.away_team_id, "formation": match.away_formation,
                 **state.away.model_dump()},
        "momentum_home_minus_away": state.momentum,
        "on_pitch": players,
        "available_bench": bench,
        "subs_used": state.subs_used,
        "synthetic": True,
    }  # fmt: skip


async def get_player_performance(
    match_id: str, player_id: str, asof_sec: int | None = None
) -> dict[str, Any]:
    """Current metrics and live rating, with the source events behind the rating."""
    store = ctx().store
    asof = _asof(match_id, asof_sec)
    events = store.events(match_id)
    player = store.players[player_id]
    mins = minutes_played(player_id, store.rosters(match_id), events, asof)
    rating, contribs, low = live_rating(player, events, asof, mins)
    biggest = sorted(contribs, key=lambda c: abs(c.delta), reverse=True)[:8]
    return {
        "player_id": player_id,
        "name": player.display_name,
        "position": player.primary_position,
        "asof_sec": asof,
        "minutes": round(mins, 1),
        "metrics": player_metrics(player_id, events, asof),
        "live_rating": rating,
        "low_confidence": low,
        "top_rating_contributions": [c.model_dump() for c in biggest],
        "methodology_version": METHODOLOGY_VERSION,
        "synthetic": True,
    }


async def get_player_history(player_id: str, lookback: int = 5) -> dict[str, Any]:
    """Baseline from prior simulated matches only (no current-match leakage)."""
    store = ctx().store
    player = store.players[player_id]
    history = []
    for m in sorted(store.matches.values(), key=lambda m: m.kickoff_at, reverse=True):
        if m.kind != "historical":
            continue
        rosters = store.rosters(m.match_id)
        if not any(r.player_id == player_id for r in rosters):
            continue
        events = store.events(m.match_id)
        end = events[-1].event_sec
        mins = minutes_played(player_id, rosters, events, end)
        if mins < 1:
            continue
        rating, _, _ = live_rating(player, events, end, mins)
        metrics = player_metrics(player_id, events, end)
        history.append({"match_id": m.match_id, "minutes": round(mins), "rating": rating,
                        "take_ons_attempted": metrics["take_ons_attempted"],
                        "take_ons_won": metrics["take_ons_won"],
                        "pass_accuracy": metrics["pass_accuracy"]})  # fmt: skip
        if len(history) >= lookback:
            break
    n = len(history)
    att = sum(h["take_ons_attempted"] for h in history)
    won = sum(h["take_ons_won"] for h in history)
    return {
        "player_id": player_id,
        "name": player.display_name,
        "sample_size": n,
        "expected_rating": round(sum(h["rating"] for h in history) / n, 2) if n else None,
        "take_on_success_pct": round(100 * won / att, 1) if att else None,
        "matches": history,
        "note": "Baseline uses prior simulated matches only." if n >= 3 else "Sparse history.",
        "synthetic": True,
    }


async def get_matchup_analysis(
    match_id: str, player_id: str, opponent_id: str, asof_sec: int | None = None
) -> dict[str, Any]:
    """Observed duels between two players in this match, plus prior meetings."""
    store = ctx().store
    asof = _asof(match_id, asof_sec)

    def duels(mid: str, until: float) -> list[MatchEvent]:
        return [
            e for e in store.events(mid)
            if e.event_sec <= until and {e.player_id, e.opponent_id} == {player_id, opponent_id}
        ]  # fmt: skip

    now = duels(match_id, asof)
    take_ons = [e for e in now if e.event_type == "take_on" and e.player_id == player_id]
    prior = []
    for m in store.matches.values():
        if m.kind == "historical":
            evs = duels(m.match_id, 10**9)
            if evs:
                tk = [e for e in evs if e.event_type == "take_on" and e.player_id == player_id]
                prior.append({"match_id": m.match_id, "take_ons": len(tk),
                              "won": sum(e.outcome == "success" for e in tk)})  # fmt: skip
    return {
        "player": _name(player_id),
        "opponent": _name(opponent_id),
        "asof_sec": asof,
        "take_ons_attempted": len(take_ons),
        "take_ons_won": sum(e.outcome == "success" for e in take_ons),
        "duel_event_ids": [e.event_id for e in now],
        "prior_meetings": prior,
        "synthetic": True,
    }


async def get_duel_ledger(
    match_id: str, attacker_id: str, slot: str, team_id: str, asof_sec: int | None = None
) -> dict[str, Any]:
    """Attacker vs a defending slot (follows whoever holds it) or a defender id: duels,
    outcomes, channel threat, rolling win % and duel points with their stored model terms."""
    store = ctx().store
    asof = _asof(match_id, asof_sec)
    led = duel_ledger(store.events(match_id), attacker_id, slot, team_id,
                      store.rosters(match_id), asof)  # fmt: skip
    return {"asof_sec": asof, "attacker": _name(attacker_id),
            "defenders": [_name(d) for d in led.defender_ids], **led.model_dump()}  # fmt: skip


async def get_bench_view(
    match_id: str, team_id: str, asof_sec: int | None = None
) -> dict[str, Any]:
    """Everything on the assistant-coach page: sticky hot-duel alert, ledger, ranked options,
    radar cards, sprint race, swap impact (after a position change), briefing seed."""
    asof = _asof(match_id, asof_sec)
    view = build_bench_view(ctx().store, ctx().replays, match_id, team_id, asof)
    return view.model_dump()


async def evaluate_substitutions(
    match_id: str, team_id: str, asof_sec: int | None = None
) -> dict[str, Any]:
    """KEEP vs SUB / position SWAP / SUB+SWAP for the team's hottest losing duel, scored on six
    bounded policy dimensions with pros/cons quoting the numbers and evidence ids."""
    store = ctx().store
    asof = _asof(match_id, asof_sec)
    inp = advisor_input(store, match_id, team_id, asof)
    events = _events(match_id, asof)
    subs_used = sum(1 for e in events if e.event_type == "substitution" and e.team_id == team_id)
    if inp is None:
        keep = keep_only(match_id, team_id, asof)
        return {
            "match_id": match_id, "team_id": team_id, "asof_sec": asof,
            "game_state": {"subs_remaining": 5 - subs_used},
            "diagnosis": "No hot duel: no defender is being beaten repeatedly",
            "hot_duel": None, "ledger": None, "head_to_head": {},
            "options": [keep.model_dump() | {"incoming_name": None, "outgoing_name": None}],
            "caveat": CAVEAT, "synthetic": True,
        }  # fmt: skip
    recs = evaluate(inp)
    h = inp.hot
    diagnosis = (
        f"{_name(h.attacker_id)} has beaten {_name(h.defender_id)} ({h.defender_slot}) "
        f"{h.beaten_20m} times in the last 20 min (defender win "
        f"{'n/a' if h.win_pct_20m is None else f'{h.win_pct_20m:.0%}'}, n={h.n_20m})"
    )
    head_to_head = {}
    for pid in {r.incoming_player_id for r in recs if r.incoming_player_id} | {h.defender_id}:
        prior = (await get_matchup_analysis(match_id, h.attacker_id, pid, asof))["prior_meetings"]
        head_to_head[pid] = {"name": _name(pid), "prior_meetings": prior,
                             "n": sum(m["take_ons"] for m in prior)}  # fmt: skip
    return {
        "match_id": match_id, "team_id": team_id, "asof_sec": asof,
        "game_state": {"goal_difference": inp.goal_diff, "subs_remaining": inp.subs_left,
                       "minute": inp.minute},
        "diagnosis": diagnosis,
        "hot_duel": h.model_dump() | {"attacker": _name(h.attacker_id),
                                      "defender": _name(h.defender_id)},
        "ledger": inp.ledger.model_dump(),
        "head_to_head": head_to_head,
        "policy_weights": POLICY_WEIGHTS,
        "options": [
            r.model_dump() | {"incoming_name": _name(r.incoming_player_id),
                              "outgoing_name": _name(r.outgoing_player_id),
                              "moves_named": [m.model_dump() | {"name": _name(m.player_id)}
                                              for m in r.moves]}
            for r in recs
        ],
        "caveat": CAVEAT,
        "synthetic": True,
    }  # fmt: skip


async def get_insight_candidates(
    match_id: str, since_sec: int = 0, asof_sec: int | None = None
) -> dict[str, Any]:
    """Deterministic triggers since `since_sec`: goals, momentum swings, hot (losing) duels."""
    store = ctx().store
    asof = _asof(match_id, asof_sec)
    match = store.matches[match_id]
    evs = [e for e in _events(match_id, asof) if e.event_sec > since_sec]
    cands: list[dict[str, Any]] = []
    for e in evs:
        if e.event_type == "shot" and e.outcome == "goal":
            cands.append({"kind": "key_moment", "key": f"goal-{e.event_id}", "asof_sec": e.event_sec,
                          "facts": {"scorer": _name(e.player_id), "team_id": e.team_id,
                                    "xg": e.qualifiers.get("xg")},
                          "evidence_event_ids": [e.event_id] + ([e.qualifiers["assist_event_id"]]
                                                                 if e.qualifiers.get("assist_event_id") else []),
                          "confidence": "high"})  # fmt: skip
    state = ctx().replays.get(match_id).state(asof)
    if abs(state.momentum) >= 8:
        team = match.home_team_id if state.momentum > 0 else match.away_team_id
        recent = [e for e in _events(match_id, asof) if e.event_sec > asof - 300 and e.team_id == team
                  and (e.event_type == "shot" or (e.event_type == "take_on" and e.outcome == "success"))]  # fmt: skip
        if recent:
            cands.append({"kind": "momentum_shift", "key": f"momentum-{team}-{asof // 600}",
                          "asof_sec": asof, "facts": {"team_id": team, "momentum": state.momentum},
                          "evidence_event_ids": [e.event_id for e in recent[-6:]],
                          "confidence": "medium"})  # fmt: skip
    rosters = store.rosters(match_id)
    events = _events(match_id, asof)
    for team in (match.home_team_id, match.away_team_id):
        for h in hot_duels(events, rosters, team, asof):
            fired = h.first_fired_sec or asof
            if fired <= since_sec:
                continue  # already raised in an earlier check
            led = duel_ledger(events, h.attacker_id, h.defender_slot, team, rosters, fired,
                              since=max(0, fired - 1200))  # fmt: skip
            facts = {**h.model_dump(), "attacker": _name(h.attacker_id),
                     "defender": _name(h.defender_id)}  # fmt: skip
            evidence = [p.event_id for p in led.points][-6:]
            cands.append({"kind": "tactical_alert", "key": f"hot-{team}-{h.defender_slot}-"
                          f"{h.attacker_id}-{fired}", "asof_sec": fired, "facts": facts,
                          "evidence_event_ids": evidence, "confidence": led.confidence})  # fmt: skip
            score = {match.home_team_id: state.home.score, match.away_team_id: state.away.score}
            other = match.away_team_id if team == match.home_team_id else match.home_team_id
            if score[team] <= score[other]:
                cands.append({"kind": "substitution_opportunity",
                              "key": f"sub-{team}-{h.defender_slot}-{fired}", "asof_sec": asof,
                              "facts": facts, "evidence_event_ids": evidence,
                              "confidence": led.confidence})  # fmt: skip
    return {"match_id": match_id, "since_sec": since_sec, "asof_sec": asof, "candidates": cands}


# --------------------------------------------------------------------------- write tool


class GroundingError(ValueError):
    pass


async def publish_insight(insight: dict[str, Any]) -> dict[str, Any]:
    """Validate (schema + evidence exists and is not from the future) then publish to the UI."""
    store = ctx().store
    try:
        model = Insight(**insight)
    except Exception as e:  # pydantic ValidationError -> readable message for the agent
        raise GroundingError(f"insight does not match the contract: {e}") from e
    session = ctx().replays.get(model.match_id)
    known = {e.event_id: e for e in store.events(model.match_id)}
    missing = [i for i in model.evidence_event_ids if i not in known]
    if missing:
        raise GroundingError(f"unknown evidence_event_ids: {missing}")
    future = [i for i in model.evidence_event_ids if known[i].event_sec > session.clock + 1]
    if future:
        raise GroundingError(f"evidence from the future (after replay clock): {future}")
    if any(i.insight_id == model.insight_id for i in store.insights(model.match_id)):
        return {
            "published": False,
            "reason": "duplicate insight_id",
            "insight_id": model.insight_id,
        }
    session.publish_insight(model)
    return {"published": True, "insight_id": model.insight_id}
