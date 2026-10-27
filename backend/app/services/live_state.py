"""Deterministic live match state as of a match second (docs/schema.md §7)."""

import itertools

from app.models import Match, MatchEvent, MatchState, OnPitchPlayer, RosterEntry, TeamLiveStats

MOMENTUM_WINDOW_SEC = 300
ON_BALL = {"pass", "carry", "take_on", "shot", "restart", "interception", "tackle"}


def _team_stats(team_id: str, evs: list[MatchEvent], possession_pct: float) -> TeamLiveStats:
    mine = [e for e in evs if e.team_id == team_id]
    shots = [e for e in mine if e.event_type == "shot"]
    passes = [e for e in mine if e.event_type == "pass"]
    completed = sum(1 for e in passes if e.outcome == "success")
    return TeamLiveStats(
        team_id=team_id,
        score=sum(1 for e in shots if e.outcome == "goal"),
        possession_pct=round(possession_pct, 1),
        shots=len(shots),
        shots_on_target=sum(1 for e in shots if e.outcome in ("goal", "saved")),
        xg=round(sum(float(e.qualifiers.get("xg", 0)) for e in shots), 2),
        passes=len(passes),
        pass_accuracy=round(100 * completed / len(passes), 1) if passes else 0.0,
    )


def _threat(evs: list[MatchEvent], team_id: str) -> float:
    total = 0.0
    for e in evs:
        if e.team_id != team_id:
            continue
        if e.event_type == "shot":
            total += 3
        elif e.event_type == "take_on" and e.outcome == "success":
            total += 1
        elif (
            e.event_type == "pass"
            and e.outcome == "success"
            and (e.start_x or 0) <= 66 < (e.end_x or 0)
        ):
            total += 1  # final-third entry
    return total


def compute_state(
    match: Match, rosters: list[RosterEntry], events: list[MatchEvent], asof_sec: float
) -> MatchState:
    evs = [e for e in events if e.event_sec <= asof_sec]
    home, away = match.home_team_id, match.away_team_id

    # possession share by time between consecutive on-ball events
    owner: dict[str, str] = {}
    poss_time = {home: 0.0, away: 0.0}
    ball = [e for e in evs if e.event_type in ON_BALL and e.possession_id]
    for e in ball:
        owner.setdefault(e.possession_id, e.team_id)
    for cur, nxt in itertools.pairwise(ball):
        poss_time[owner[cur.possession_id]] += max(0, nxt.event_sec - cur.event_sec)
    total = sum(poss_time.values()) or 1.0

    recent = [e for e in evs if e.event_sec > asof_sec - MOMENTUM_WINDOW_SEC]
    momentum = _threat(recent, home) - _threat(recent, away)

    slot_of = {r.player_id: r.formation_slot for r in rosters if r.roster_status == "starter"}
    team_of = {r.player_id: r.team_id for r in rosters}
    subs_used = {home: 0, away: 0}
    for e in evs:
        if e.event_type == "substitution" and e.player_id and e.recipient_id:
            slot_of[e.recipient_id] = slot_of.pop(e.player_id, None)
            subs_used[e.team_id] += 1
        elif e.event_type == "card" and e.qualifiers.get("card") in ("red", "second_yellow"):
            slot_of.pop(e.player_id or "", None)
        elif e.event_type == "position_change" and e.player_id in slot_of:
            slot_of[e.player_id] = e.qualifiers.get("to_slot")

    last_sec = events[-1].event_sec if events else 0
    if asof_sec <= 0:
        status = "scheduled"
    elif asof_sec >= last_sec:
        status = "finished"
    else:
        status = "live"

    return MatchState(
        match_id=match.match_id,
        asof_sec=int(asof_sec),
        period=2 if asof_sec >= 2700 else 1,
        status=status,
        home=_team_stats(home, evs, 100 * poss_time[home] / total),
        away=_team_stats(away, evs, 100 * poss_time[away] / total),
        momentum=momentum,
        on_pitch=[
            OnPitchPlayer(player_id=pid, team_id=team_of[pid], formation_slot=slot)
            for pid, slot in slot_of.items()
            if slot
        ],
        subs_used=subs_used,
    )
