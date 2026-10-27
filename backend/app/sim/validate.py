"""Generator gate: spec §9 validation checks. Returns a list of human-readable errors."""

from collections import Counter

from app.models import Match, MatchEvent, RosterEntry
from app.sim.formations import formation_slots

HALF_SEC = 2700
ON_BALL = {"pass", "carry", "take_on", "shot", "restart", "interception", "tackle"}
MAX_SUBS = 5


def validate_match(match: Match, rosters: list[RosterEntry], events: list[MatchEvent]) -> list[str]:
    errors: list[str] = []
    teams = {match.home_team_id, match.away_team_id}
    roster = {r.player_id: r for r in rosters if r.match_id == match.match_id}
    on_pitch = {pid for pid, r in roster.items() if r.roster_status == "starter"}
    # player_id -> formation slot for everyone on the pitch (subs and swaps move it)
    slot = {pid: r.formation_slot for pid, r in roster.items() if r.roster_status == "starter"}
    formation_of = {
        match.home_team_id: match.home_formation,
        match.away_team_id: match.away_formation,
    }
    slot_names = {team: {s.slot for s in formation_slots(f)[1]} for team, f in formation_of.items()}
    used_bench: set[str] = set()
    reported_clashes: set[tuple[str, str]] = set()  # report each slot clash once
    subs = dict.fromkeys(teams, 0)
    goals = dict.fromkeys(teams, 0)
    possession_team: dict[str, str] = {}
    seen_ids: set[str] = set()
    prev: MatchEvent | None = None
    in_period = False

    for r in rosters:
        if r.team_id not in teams:
            errors.append(f"roster {r.player_id}: team {r.team_id} not in match")
    for team in teams:
        starters = [
            r for r in roster.values() if r.team_id == team and r.roster_status == "starter"
        ]
        if len(starters) != 11:
            errors.append(f"{team}: {len(starters)} starters (expected 11)")

    for i, ev in enumerate(events):
        tag = ev.event_id
        if ev.event_id in seen_ids:
            errors.append(f"{tag}: duplicate event_id")
        seen_ids.add(ev.event_id)
        if ev.match_id != match.match_id:
            errors.append(f"{tag}: wrong match_id")
        if ev.team_id not in teams:
            errors.append(f"{tag}: team {ev.team_id} not in match")

        # chronology
        if prev:
            if ev.sequence_no <= prev.sequence_no:
                errors.append(f"{tag}: sequence_no not increasing")
            if ev.event_sec < prev.event_sec:
                errors.append(f"{tag}: event_sec went backwards")
        if ev.period == 1 and ev.event_sec > HALF_SEC:
            errors.append(f"{tag}: period 1 event after {HALF_SEC}s")
        if ev.period == 2 and ev.event_sec < HALF_SEC:
            errors.append(f"{tag}: period 2 event before {HALF_SEC}s")
        if ev.event_type == "period_start":
            in_period = True
        elif not in_period:
            errors.append(f"{tag}: event outside a period")
        if ev.event_type == "period_end":
            in_period = False

        # relational integrity + presence
        for field in ("player_id", "recipient_id", "opponent_id"):
            pid = getattr(ev, field)
            if pid is not None and pid not in roster:
                errors.append(f"{tag}: {field} {pid} not on match roster")
        if ev.player_id and ev.player_id in roster:
            if roster[ev.player_id].team_id != ev.team_id:
                errors.append(f"{tag}: actor {ev.player_id} not on team {ev.team_id}")
            if ev.event_type != "substitution" and ev.player_id not in on_pitch:
                errors.append(f"{tag}: actor {ev.player_id} not on the pitch")
        if ev.opponent_id and ev.opponent_id in roster:
            if roster[ev.opponent_id].team_id == ev.team_id:
                errors.append(f"{tag}: opponent {ev.opponent_id} is a teammate")
            elif ev.opponent_id not in on_pitch:
                errors.append(f"{tag}: opponent {ev.opponent_id} not on the pitch")
        recipient = roster.get(ev.recipient_id or "")
        if ev.event_type == "pass" and recipient and recipient.team_id != ev.team_id:
            errors.append(f"{tag}: pass recipient on other team")

        # substitutions
        if ev.event_type == "substitution":
            out_id, in_id = ev.player_id, ev.recipient_id
            if out_id not in on_pitch:
                errors.append(f"{tag}: outgoing {out_id} not on pitch")
            r_in = roster.get(in_id or "")
            if r_in is None or r_in.roster_status != "bench" or in_id in used_bench:
                errors.append(f"{tag}: incoming {in_id} not an unused bench player")
            subs[ev.team_id] += 1
            if subs[ev.team_id] > MAX_SUBS:
                errors.append(f"{tag}: more than {MAX_SUBS} substitutions")
            on_pitch.discard(out_id)
            out_slot = slot.pop(out_id or "", None)
            if in_id:
                on_pitch.add(in_id)
                used_bench.add(in_id)
                slot[in_id] = out_slot
        if ev.event_type == "card" and ev.qualifiers.get("card") in ("red", "second_yellow"):
            on_pitch.discard(ev.player_id)
            slot.pop(ev.player_id or "", None)

        # position changes (spec 3.3): never a sub, never touch possession
        if ev.event_type == "position_change":
            src, dst = ev.qualifiers.get("from_slot"), ev.qualifiers.get("to_slot")
            partner = roster.get(ev.recipient_id or "")
            if ev.recipient_id and ev.recipient_id not in on_pitch:
                errors.append(f"{tag}: partner {ev.recipient_id} not on the pitch")
            elif partner and partner.team_id != ev.team_id:
                errors.append(f"{tag}: partner {ev.recipient_id} is not a teammate")
            if ev.player_id in on_pitch and slot.get(ev.player_id) != src:
                errors.append(
                    f"{tag}: from_slot {src} is not {ev.player_id}'s slot "
                    f"({slot.get(ev.player_id)})"
                )
            if dst not in slot_names.get(ev.team_id, set()):
                errors.append(f"{tag}: to_slot {dst} not in {formation_of.get(ev.team_id)}")
            if ev.player_id in on_pitch:
                slot[ev.player_id] = dst

        # possessions
        if ev.event_type in ON_BALL:
            if ev.possession_id is None:
                errors.append(f"{tag}: on-ball event without possession_id")
            else:
                owner = possession_team.setdefault(ev.possession_id, ev.team_id)
                if owner != ev.team_id:
                    errors.append(f"{tag}: possession {ev.possession_id} switched team")

        if ev.event_type == "shot" and ev.outcome == "goal":
            goals[ev.team_id] += 1

        # one player per slot once every event at this second has applied
        nxt = events[i + 1] if i + 1 < len(events) else None
        if nxt is None or nxt.event_sec != ev.event_sec:
            taken = Counter(
                (roster[pid].team_id, s) for pid, s in slot.items() if s and pid in roster
            )
            clashes = {k for k, n in taken.items() if n > 1}
            for team, s in sorted(clashes - reported_clashes):
                errors.append(f"{tag}: slot map not one-to-one ({team} {s} x{taken[team, s]})")
            reported_clashes = clashes
        prev = ev

    if (
        goals[match.home_team_id] != match.home_score
        or goals[match.away_team_id] != match.away_score
    ):
        errors.append(
            f"score mismatch: events {goals} vs match {match.home_score}-{match.away_score}"
        )
    if events and events[-1].event_type != "period_end":
        errors.append("match does not end with period_end")
    return errors
