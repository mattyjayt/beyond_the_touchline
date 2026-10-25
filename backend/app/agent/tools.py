"""Agent tools (spec §8) - defined ONCE, exposed via REST, MCP (/mcp) and the
Claude Agent SDK. Read tools are deterministic; `publish_insight` is the only
write and is grounding-checked. The LLM never computes or alters match facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models import ROLE_GROUP, Insight, MatchEvent, Recommendation
from app.replay import ReplayManager
from app.services.performance import (
    METHODOLOGY_VERSION,
    live_rating,
    minutes_played,
    player_metrics,
)
from app.store import Store

RECOMMENDER_VERSION = "subs-v0"
STRUGGLE_WINDOW_SEC = 20 * 60


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


def _struggles(match_id: str, team_id: str | None, asof: int) -> list[dict[str, Any]]:
    """Players with >=5 take-ons in the window and <=30% success."""
    evs = [e for e in _events(match_id, asof) if e.event_sec > asof - STRUGGLE_WINDOW_SEC]
    by_player: dict[str, list[MatchEvent]] = {}
    for e in evs:
        if e.event_type == "take_on" and (team_id is None or e.team_id == team_id):
            by_player.setdefault(e.player_id or "", []).append(e)
    out = []
    for pid, tks in by_player.items():
        won = sum(e.outcome == "success" for e in tks)
        if len(tks) >= 5 and won / len(tks) <= 0.3:
            opps = [e.opponent_id for e in tks]
            marker = max(set(opps), key=opps.count)
            out.append({"player_id": pid, "team_id": tks[0].team_id, "attempts": len(tks),
                        "won": won, "main_opponent": marker,
                        "failed_event_ids": [e.event_id for e in tks if e.outcome == "fail"]})  # fmt: skip
    return out


async def evaluate_substitutions(
    match_id: str, team_id: str, asof_sec: int | None = None
) -> dict[str, Any]:
    """KEEP plus eligible substitution options with bounded scores, pros/cons and evidence."""
    store = ctx().store
    asof = _asof(match_id, asof_sec)
    state = await get_match_state(match_id, asof)
    match = store.matches[match_id]
    side = "home" if team_id == match.home_team_id else "away"
    goal_diff = state[side]["score"] - state["away" if side == "home" else "home"]["score"]
    subs_left = 5 - state["subs_used"].get(team_id, 0)

    struggles = _struggles(match_id, team_id, asof)
    if struggles:
        problem = max(struggles, key=lambda s: s["attempts"] - s["won"])
        out_id, evidence = problem["player_id"], problem["failed_event_ids"]
        diagnosis = (f"{_name(out_id)}: {problem['won']}/{problem['attempts']} take-ons in the "
                     f"last 20 min, mostly against {_name(problem['main_opponent'])}")  # fmt: skip
    else:
        mine = [p for p in state["on_pitch"] if p["team_id"] == team_id and p["slot"] != "GK"]
        worst = min(mine, key=lambda p: p["live_rating"])
        out_id, evidence = worst["player_id"], []
        diagnosis = f"{worst['name']} has the lowest live rating ({worst['live_rating']})"

    outgoing = store.players[out_id]
    perf = await get_player_performance(match_id, out_id, asof)
    hist = await get_player_history(out_id)
    form = perf["live_rating"] / (hist["expected_rating"] or perf["live_rating"] or 6.0)
    slot = next((p["slot"] for p in state["on_pitch"] if p["player_id"] == out_id), None)
    slot_pos = outgoing.primary_position

    attack_w = 1.5 if goal_diff < 0 else 0.7 if goal_diff > 0 else 1.0
    pri = outgoing.priors
    cur_attack = (pri.dribbling + pri.finishing) / 2 * form

    def fit(pos: str, secondary: list[str]) -> float:
        if pos == slot_pos:
            return 1.0
        if slot_pos in secondary:
            return 0.8
        return 0.5 if ROLE_GROUP[pos] == ROLE_GROUP[slot_pos] else 0.0

    options = []
    for b in state["available_bench"] if subs_left > 0 else []:
        if b["team_id"] != team_id:
            continue
        cand = store.players[b["player_id"]]
        f = fit(cand.primary_position, cand.secondary_positions)
        if f < 0.5:
            continue
        cp = cand.priors
        attack = round(((cp.dribbling + cp.finishing) / 2 * 1.03 - cur_attack) / 100, 3)
        control = round((cp.passing - pri.passing) / 100, 3)
        risk = round((pri.defending - cp.defending) / 100, 3)
        score = attack_w * attack + 0.5 * control - 0.5 * risk + 0.05 * f
        options.append((score, cand, f, attack, control, risk))
    options.sort(key=lambda o: o[0], reverse=True)

    n_evidence = len(evidence)
    confidence = "medium" if n_evidence >= 4 and hist["sample_size"] >= 3 else "low"
    recs: list[Recommendation] = []
    keep_score = 0.02 if goal_diff >= 0 else -0.02
    ranked = sorted(
        [("keep", keep_score, None, 1.0, 0.0, 0.0, 0.0)]
        + [("substitution", s, c, f, a, ctl, r) for s, c, f, a, ctl, r in options[:3]],
        key=lambda o: o[1],
        reverse=True,
    )
    for rank, (kind, _, cand, f, a, ctl, r) in enumerate(ranked, start=1):
        rec_id = f"REC-{match_id}-{asof}-{rank}"
        if kind == "keep":
            pros = [
                "Keeps defensive structure and continuity",
                f"Preserves {subs_left} substitution(s)",
            ]
            cons = [diagnosis]
            recs.append(Recommendation(
                rec_id=rec_id, match_id=match_id, team_id=team_id, asof_sec=asof,
                option_rank=rank, option_type="keep", attack_delta_estimate=0,
                control_delta_estimate=0, defensive_risk_delta=0, tactical_fit_score=1.0,
                confidence=confidence, pros=pros, cons=cons,
                supporting_event_ids=evidence[:6], model_version=RECOMMENDER_VERSION,
            ))  # fmt: skip
        else:
            pros = [f"Fresh {cand.archetype.replace('_', ' ')} for the {slot or slot_pos} role"]
            if a > 0:
                pros.append(f"Higher simulated attacking profile (+{a:.2f})")
            if ctl > 0:
                pros.append("Better ball retention profile")
            cons = []
            if r > 0:
                cons.append(f"Less defensive cover (risk +{r:.2f})")
            if f < 1:
                cons.append(f"Not a natural {slot_pos} (fit {f:.1f})")
            cons.append("Uses a substitution window")
            recs.append(Recommendation(
                rec_id=rec_id, match_id=match_id, team_id=team_id, asof_sec=asof,
                option_rank=rank, option_type="substitution", outgoing_player_id=out_id,
                incoming_player_id=cand.player_id, attack_delta_estimate=a,
                control_delta_estimate=ctl, defensive_risk_delta=r, tactical_fit_score=f,
                confidence=confidence, pros=pros, cons=cons,
                supporting_event_ids=evidence[:6], model_version=RECOMMENDER_VERSION,
            ))  # fmt: skip
    return {
        "match_id": match_id,
        "team_id": team_id,
        "asof_sec": asof,
        "game_state": {"goal_difference": goal_diff, "subs_remaining": subs_left},
        "diagnosis": diagnosis,
        "outgoing_candidate": {"player_id": out_id, "name": outgoing.display_name,
                               "live_rating": perf["live_rating"],
                               "expected_rating": hist["expected_rating"],
                               "baseline_sample_size": hist["sample_size"]},
        "options": [
            r.model_dump() | {"incoming_name": _name(r.incoming_player_id),
                              "outgoing_name": _name(r.outgoing_player_id)}
            for r in recs
        ],
        "caveat": "Deltas are hypothetical model outputs from synthetic priors, not causal effects.",
        "synthetic": True,
    }  # fmt: skip


async def get_insight_candidates(
    match_id: str, since_sec: int = 0, asof_sec: int | None = None
) -> dict[str, Any]:
    """Deterministic triggers since `since_sec`: goals, momentum swings, player struggles."""
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
    for s in _struggles(match_id, None, asof):
        cands.append({"kind": "player_form", "key": f"struggle-{s['player_id']}", "asof_sec": asof,
                      "facts": {**s, "player": _name(s["player_id"]),
                                "opponent": _name(s["main_opponent"])},
                      "evidence_event_ids": s["failed_event_ids"][-6:],
                      "confidence": "medium" if s["attempts"] >= 8 else "low"})  # fmt: skip
        team_score = state.home.score if s["team_id"] == match.home_team_id else state.away.score
        opp_score = state.away.score if s["team_id"] == match.home_team_id else state.home.score
        if asof >= 3600 and team_score <= opp_score:
            cands.append({"kind": "substitution_opportunity", "key": f"sub-{s['player_id']}",
                          "asof_sec": asof, "facts": {**s, "player": _name(s["player_id"])},
                          "evidence_event_ids": s["failed_event_ids"][-6:],
                          "confidence": "medium"})  # fmt: skip
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
