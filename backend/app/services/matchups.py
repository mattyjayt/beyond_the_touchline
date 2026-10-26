"""Matchup services (spec §4): slots, 1v1 duel ledgers, the hot-duel trigger, swap impact.

Pure functions over plain event / roster lists and an as-of second: no Store, no DB, no I/O.
Nothing past ``asof`` is ever read. Everything is derived from simulated events.

Duels are counted from the DEFENDER's side (see ``app.models.advisor``):

- a ``take_on`` by the attacker against the defender is one duel. ``fail`` -> won;
  ``success`` followed at once by the defender's ``recovery`` tackle -> recovered (a win);
  ``success`` followed at once by the defender's foul -> foul; any other ``success`` -> lost.
- a ``foul`` by the defender on the attacker that does not follow a take-on is its own duel.

Duel terms are quoted from the take-on's stored ``qualifiers.duel`` (simulator model,
uncalibrated); they are never recomputed here.
"""

import math
from collections.abc import Iterator
from dataclasses import dataclass, field

from app.models import (
    ROLE_GROUP,
    DuelLedger,
    DuelOutcome,
    DuelPoint,
    HotDuel,
    MatchEvent,
    RollingPoint,
    RosterEntry,
    SwapImpact,
)
from app.models.advisor import Confidence
from app.services.performance import BEATEN_DELTA, CARD_DELTA, WEIGHTS, slot_position
from app.sim.formations import FORMATIONS, formation_slots

ROLLING_WINDOW_SEC = 600
ROLLING_STEP_SEC = 60
HOT_WINDOW_SEC = 1200
HOT_BEATEN = 6  # beaten >= 6 in the last 20 min ...
HOT_WIN_PCT = 0.30  # ... or defender win rate <= 30% ...
HOT_MIN_N = 8  # ... over at least 8 duels
CHANNEL_Y = 67.0  # wide channel: start_y > 67 (or < 33) in the attacker's frame

_WINS: frozenset[str] = frozenset({"won", "recovered"})
# slot name -> y in the team's own frame (slot names mean the same side in every formation)
_SLOT_Y: dict[str, float] = {}
for _slots in FORMATIONS.values():
    for _s in _slots:
        _SLOT_Y.setdefault(_s.slot, _s.y)


# ----------------------------------------------------------------- slots
def _apply_slot_change(slot: dict[str, str | None], e: MatchEvent) -> None:
    """Same rules as the validator / rating: subs, red cards and position changes."""
    if e.event_type == "substitution" and e.player_id and e.recipient_id:
        slot[e.recipient_id] = slot.pop(e.player_id, None)
    elif e.event_type == "card" and e.qualifiers.get("card") in ("red", "second_yellow"):
        slot.pop(e.player_id or "", None)
    elif e.event_type == "position_change" and e.player_id in slot:
        slot[e.player_id] = e.qualifiers.get("to_slot")


def _starting_slots(rosters: list[RosterEntry]) -> dict[str, str | None]:
    return {r.player_id: r.formation_slot for r in rosters if r.roster_status == "starter"}


def _walk(
    rosters: list[RosterEntry], events: list[MatchEvent], asof: int
) -> Iterator[tuple[int, MatchEvent, dict[str, str | None]]]:
    """Yield (index, event, slots BEFORE the event) for every event at or before ``asof``."""
    slot = _starting_slots(rosters)
    for i, e in enumerate(events):
        if e.event_sec > asof:
            return
        yield i, e, slot
        _apply_slot_change(slot, e)


def current_slots(
    rosters: list[RosterEntry], events: list[MatchEvent], asof: int
) -> dict[str, str]:
    """player_id -> slot for everyone on the pitch (both teams) once ``asof`` has applied."""
    slot = _starting_slots(rosters)
    for e in events:
        if e.event_sec > asof:
            break
        _apply_slot_change(slot, e)
    return {pid: s for pid, s in slot.items() if s}


def _engine_dist(dfn_x: float, dfn_y: float, att_x: float, att_y: float) -> float:
    """``nearest()``'s metric: defending slot x scaled, attacker mirrored into its frame."""
    return math.hypot(dfn_x * 0.85 - (100 - att_x), dfn_y - (100 - att_y))


def matchup_map(our_formation: str, their_formation: str) -> dict[str, str]:
    """Our (defending) slot -> the opposing slot it is paired with by ``nearest()`` geometry.

    Engine first: for each opposing outfield slot t, the engine's defender is our outfield slot
    nearest to t's mirrored position (strict ``<``, so ties go to our slot order). Our slot s
    maps to the first t (their slot order) the engine sends at it. A slot the engine never
    picks (e.g. a 4-2-3-1 LCB, which loses the tie to RCB) falls back to the attacker nearest
    to it under the same metric. GKs are excluded on both sides.
    """
    _, ours = formation_slots(our_formation)
    _, theirs = formation_slots(their_formation)
    ours = [s for s in ours if s.slot != "GK"]
    theirs = [t for t in theirs if t.slot != "GK"]

    def argmin(cands, dist):
        best, best_d = None, math.inf
        for c in cands:
            if (d := dist(c)) < best_d:
                best, best_d = c, d
        return best

    engine: dict[str, str] = {}  # our slot -> first opposing slot the engine sends at it
    for t in theirs:
        s = argmin(ours, lambda s, t=t: _engine_dist(s.x, s.y, t.x, t.y))
        engine.setdefault(s.slot, t.slot)
    out: dict[str, str] = {}
    for s in ours:
        if s.slot in engine:
            out[s.slot] = engine[s.slot]
        else:
            out[s.slot] = argmin(theirs, lambda t, s=s: _engine_dist(s.x, s.y, t.x, t.y)).slot
    return out


# ----------------------------------------------------------------- duels
@dataclass
class _Duel:
    point: DuelPoint
    slot: str | None  # defender's slot at the time of the duel
    beaten: bool  # take-on lost without recovery: outright, or then fouled (not recovered)
    evidence: list[str] = field(default_factory=list)
    rating_delta: float = 0.0


def _group(slot: str | None) -> str:
    # Rating weights by the role group of the slot held (spec 3.3); DEF if unknown.
    return ROLE_GROUP.get(slot_position(slot), "DEF") if slot else "DEF"


def _card_delta(
    foul: MatchEvent, by_id: dict[str, MatchEvent], asof: int
) -> tuple[list[str], float]:
    card = by_id.get(str(foul.qualifiers.get("card_event_id", "")))
    if card is None or card.event_sec > asof:
        return [], 0.0
    return [card.event_id], CARD_DELTA.get(str(card.qualifiers.get("card")), 0.0)


def _duels(
    events: list[MatchEvent], rosters: list[RosterEntry], def_team: str, asof: int
) -> list[_Duel]:
    """Every duel against ``def_team`` up to ``asof``, with the defender's slot at the time."""
    team_of = {r.player_id: r.team_id for r in rosters}
    by_id = {e.event_id: e for e in events if e.event_sec <= asof}
    out: list[_Duel] = []
    linked: set[str] = set()  # fouls already attached to a take-on
    for i, e, slot in _walk(rosters, events, asof):
        if (
            e.event_type == "take_on"
            and e.team_id != def_team
            and e.opponent_id
            and team_of.get(e.opponent_id) == def_team
            and e.player_id
        ):
            dfn, att = e.opponent_id, e.player_id
            s = slot.get(dfn)
            g = _group(s)
            nxt = events[i + 1] if i + 1 < len(events) else None
            if nxt is not None and (
                nxt.event_sec != e.event_sec or nxt.player_id != dfn or nxt.opponent_id != att
            ):
                nxt = None
            evidence = [e.event_id]
            delta = 0.0
            if e.outcome == "fail":
                outcome: DuelOutcome = "won"
                if nxt is not None and nxt.event_type == "tackle":
                    evidence.append(nxt.event_id)
                    delta += WEIGHTS[("tackle", "success")][g]
            else:
                delta += BEATEN_DELTA
                outcome = "lost"
                if (
                    nxt is not None
                    and nxt.event_type == "tackle"
                    and nxt.qualifiers.get("recovery")
                ):
                    outcome = "recovered"
                    evidence.append(nxt.event_id)
                    delta += WEIGHTS[("tackle", "success")][g]
                elif nxt is not None and nxt.event_type == "foul":
                    outcome = "foul"
                    linked.add(nxt.event_id)
                    card_ids, card_d = _card_delta(nxt, by_id, asof)
                    evidence += [nxt.event_id, *card_ids]
                    delta += WEIGHTS[("foul", "neutral")][g] + card_d
            point = DuelPoint(
                event_id=e.event_id, sec=e.event_sec,
                x=e.start_x if e.start_x is not None else 50.0,
                y=e.start_y if e.start_y is not None else 50.0,
                outcome=outcome, attacker_id=att, defender_id=dfn,
                terms=dict(e.qualifiers.get("duel") or {}),
            )  # fmt: skip
            beaten = outcome in ("lost", "foul")  # beaten and not won straight back
            out.append(_Duel(point, s, beaten, evidence, round(delta, 4)))
        elif (
            e.event_type == "foul"
            and e.team_id == def_team
            and e.event_id not in linked
            and e.player_id
            and e.opponent_id
            and team_of.get(e.opponent_id) not in (None, def_team)
        ):
            s = slot.get(e.player_id)
            card_ids, card_d = _card_delta(e, by_id, asof)
            point = DuelPoint(
                event_id=e.event_id, sec=e.event_sec,
                # the foul is logged in the defender's frame: mirror into the attacker's
                x=100 - e.start_x if e.start_x is not None else 50.0,
                y=100 - e.start_y if e.start_y is not None else 50.0,
                outcome="foul", attacker_id=e.opponent_id, defender_id=e.player_id,
            )  # fmt: skip
            delta = WEIGHTS[("foul", "neutral")][_group(s)] + card_d
            out.append(_Duel(point, s, False, [e.event_id, *card_ids], round(delta, 4)))
    return out


def _confidence(n: int) -> Confidence:
    return "low" if n < 4 else "medium" if n < 10 else "high"


def _win_pct(duels: list[_Duel]) -> float | None:
    if not duels:
        return None
    return round(sum(d.point.outcome in _WINS for d in duels) / len(duels), 3)


def _in_channel(slot: str | None, y: float | None) -> bool:
    """The wide channel the defender's slot guards, in the attacker's frame."""
    if slot is None or y is None or slot not in _SLOT_Y:
        return False
    side = _SLOT_Y[slot]
    if side < 50:  # right-sided defender (team frame) -> attacker's left: high y
        return y > CHANNEL_Y
    if side > 50:
        return y < 100 - CHANNEL_Y
    return 100 - CHANNEL_Y <= y <= CHANNEL_Y


def _unique(ids: list[str]) -> list[str]:
    return list(dict.fromkeys(ids))


def duel_ledger(
    events: list[MatchEvent],
    attacker_id: str,
    slot_or_defender: str,
    team_id: str,
    rosters: list[RosterEntry],
    asof: int,
    since: int = 0,
) -> DuelLedger:
    """Attacker vs a defender (player id) or a slot of ``team_id`` over [since, asof].

    Given a slot, it follows whoever occupied it over time, so a swap or sub hands the
    ledger to the new occupant.
    """
    is_slot = slot_or_defender not in {r.player_id for r in rosters}
    key = slot_or_defender

    def ours(d: _Duel) -> bool:
        return (
            d.point.attacker_id == attacker_id
            and since <= d.point.sec <= asof
            and (d.slot == key if is_slot else d.point.defender_id == key)
        )

    duels = [d for d in _duels(events, rosters, team_id, asof) if ours(d)]

    team_of = {r.player_id: r.team_id for r in rosters}
    defender_ids = (
        _occupants(rosters, events, team_of, key, team_id, since, asof) if is_slot else [key]
    )

    # possessions holding the attacker's successful take-on / carry in the guarded channel
    channel_poss: dict[str, str] = {}  # possession_id -> first channel action id
    for _, e, slot in _walk(rosters, events, asof):
        if (
            e.player_id == attacker_id
            and e.event_sec >= since
            and e.event_type in ("take_on", "carry")
            and e.outcome == "success"
            and e.possession_id
            and _in_channel(key if is_slot else slot.get(key), e.start_y)
        ):
            channel_poss.setdefault(e.possession_id, e.event_id)

    att_team = team_of.get(attacker_id)
    shots = [
        e for e in events
        if e.event_sec <= asof and e.event_type == "shot" and e.team_id == att_team
        and e.possession_id in channel_poss
    ]  # fmt: skip

    rolling: list[RollingPoint] = []
    first = -(-since // ROLLING_STEP_SEC) * ROLLING_STEP_SEC
    for sec in range(first, asof + 1, ROLLING_STEP_SEC):
        win = [d for d in duels if sec - ROLLING_WINDOW_SEC < d.point.sec <= sec]
        rolling.append(RollingPoint(sec=sec, win_pct=_win_pct(win), n=len(win)))

    outcomes = [d.point.outcome for d in duels]
    window_sec = asof - since + 1
    beaten = sum(d.beaten for d in duels)
    evidence = [i for d in duels for i in d.evidence]
    evidence += list(channel_poss.values()) + [e.event_id for e in shots]
    return DuelLedger(
        attacker_id=attacker_id,
        defender_ids=defender_ids,
        duels=len(duels),
        won=sum(o in _WINS for o in outcomes),
        lost=outcomes.count("lost"),
        recoveries=outcomes.count("recovered"),
        fouls=outcomes.count("foul"),
        win_pct=_win_pct(duels),
        window_sec=window_sec,
        beaten=beaten,
        beaten_per_10=round(beaten * 600 / window_sec, 2) if window_sec > 0 else None,
        channel_shots=len(shots),
        channel_xg=round(sum(float(e.qualifiers.get("xg", 0)) for e in shots), 3),
        defender_rating_swing=round(sum(d.rating_delta for d in duels), 3) if duels else None,
        confidence=_confidence(len(duels)),
        points=[d.point for d in duels],
        rolling=rolling,
        evidence_event_ids=_unique(evidence),
    )


def _occupants(
    rosters: list[RosterEntry],
    events: list[MatchEvent],
    team_of: dict[str, str],
    slot_name: str,
    team_id: str,
    since: int,
    asof: int,
) -> list[str]:
    """Who held ``slot_name`` for ``team_id`` over [since, asof], in order (no repeats)."""

    def holder(slot: dict[str, str | None]) -> str | None:
        return next(
            (p for p, s in slot.items() if s == slot_name and team_of.get(p) == team_id), None
        )

    slot = _starting_slots(rosters)
    out: list[str] = []
    for e in events:
        if e.event_sec > asof:
            break
        if e.event_sec > since and (h := holder(slot)) and h not in out:
            out.append(h)  # holder at the start of `since` + 1 (and after each change)
        _apply_slot_change(slot, e)
    if (h := holder(slot)) and h not in out:
        out.append(h)
    return out


# ------------------------------------------------------------- hot duels
def _hot_stats(duels: list[_Duel], end: int) -> tuple[int, int, float | None, bool]:
    win = [d for d in duels if end - HOT_WINDOW_SEC < d.point.sec <= end]
    beaten = sum(d.beaten for d in win)
    pct = _win_pct(win)
    fires = beaten >= HOT_BEATEN or (
        len(win) >= HOT_MIN_N and pct is not None and pct <= HOT_WIN_PCT
    )
    return beaten, len(win), pct, fires


def hot_duels(
    events: list[MatchEvent], rosters: list[RosterEntry], team_id: str, asof: int
) -> list[HotDuel]:
    """Generic trigger for ``team_id`` defending, per (slot, attacker), firing at ``asof``:
    beaten >= 6 in the last 20 min, or a defender win rate <= 30% with n >= 8.

    ``first_fired_sec`` is the first duel second (<= asof) at which the pair ever fired.
    """
    groups: dict[tuple[str, str], list[_Duel]] = {}
    for d in _duels(events, rosters, team_id, asof):
        if d.slot:
            groups.setdefault((d.slot, d.point.attacker_id), []).append(d)
    team_of = {r.player_id: r.team_id for r in rosters}
    holders = {
        s: p for p, s in current_slots(rosters, events, asof).items() if team_of.get(p) == team_id
    }
    out: list[HotDuel] = []
    for (slot, att), duels in groups.items():
        beaten, n, pct, fires = _hot_stats(duels, asof)
        if not fires or slot not in holders:
            continue
        # The window state only changes when a duel enters (its second) or leaves
        # (second + 1200); asof itself fires, so the scan always finds a second.
        candidates = sorted(
            {d.point.sec for d in duels}
            | {min(d.point.sec + HOT_WINDOW_SEC, asof) for d in duels}
            | {asof}
        )
        first = next(sec for sec in candidates if _hot_stats(duels, sec)[3])
        out.append(
            HotDuel(
                team_id=team_id,
                defender_id=holders[slot],
                defender_slot=slot,
                attacker_id=att,
                beaten_20m=beaten,
                win_pct_20m=pct,
                n_20m=n,
                first_fired_sec=first,
            )
        )
    out.sort(key=lambda h: (-h.beaten_20m, h.win_pct_20m or 0.0, h.defender_slot))
    return out


def first_trigger(
    events: list[MatchEvent], rosters: list[RosterEntry], team_id: str, until: int
) -> tuple[int | None, list[HotDuel]]:
    """First second <= ``until`` at which ``hot_duels`` fires for ``team_id`` defending.

    Exact: the trigger state only changes when a duel against ``team_id`` enters the
    20-minute window (its second) or leaves it (second + 1200), so only those seconds
    are checked. Reads no event after ``until``.
    """
    team_of = {r.player_id: r.team_id for r in rosters}
    secs: set[int] = set()
    for e in events:
        if e.event_sec > until:
            break
        duel = (e.event_type == "take_on" and team_of.get(e.opponent_id or "") == team_id) or (
            e.event_type == "foul" and e.team_id == team_id
        )
        if duel:
            secs |= {e.event_sec, e.event_sec + 1200}
    for sec in sorted(s for s in secs if s <= until):
        if hot := hot_duels(events, rosters, team_id, sec):
            return sec, hot
    return None, []


def hot_pair(
    events: list[MatchEvent],
    rosters: list[RosterEntry],
    team_id: str,
    slot: str,
    attacker_id: str,
    asof: int,
    first_fired_sec: int | None,
) -> HotDuel | None:
    """Current 20-minute stats for one (slot, attacker) pair, firing or not: keeps an alert
    that has fired once (``first_fired_sec``) tracked as the slot changes hands. None when
    nobody holds the slot any more."""
    team_of = {r.player_id: r.team_id for r in rosters}
    holder = next(
        (p for p, s in current_slots(rosters, events, asof).items()
         if s == slot and team_of.get(p) == team_id),
        None,
    )  # fmt: skip
    if holder is None:
        return None
    duels = [
        d for d in _duels(events, rosters, team_id, asof)
        if d.slot == slot and d.point.attacker_id == attacker_id
    ]  # fmt: skip
    beaten, n, pct, _ = _hot_stats(duels, asof)
    return HotDuel(
        team_id=team_id, defender_id=holder, defender_slot=slot, attacker_id=attacker_id,
        beaten_20m=beaten, win_pct_20m=pct, n_20m=n, first_fired_sec=first_fired_sec,
    )  # fmt: skip


# ----------------------------------------------------------- swap impact
def swap_impact(
    events: list[MatchEvent],
    rosters: list[RosterEntry],
    team_id: str,
    attacker_id: str,
    slot: str,
    asof: int,
) -> SwapImpact | None:
    """Before vs after the latest position change into or out of ``slot`` (<= asof).

    ``before`` covers the trigger's 20-minute window ahead of the swap,
    [swap_sec - 1200, swap_sec - 1]; ``after`` covers [swap_sec, asof]. Equal-footing windows
    keep per-10 rates comparable. None until a position change has touched the slot.
    """
    swaps = [
        e.event_sec for e in events
        if e.event_sec <= asof and e.event_type == "position_change" and e.team_id == team_id
        and slot in (e.qualifiers.get("from_slot"), e.qualifiers.get("to_slot"))
    ]  # fmt: skip
    if not swaps:
        return None
    swap_sec = swaps[-1]
    before = duel_ledger(
        events, attacker_id, slot, team_id, rosters,
        asof=max(swap_sec - 1, 0), since=max(swap_sec - HOT_WINDOW_SEC, 0),
    )  # fmt: skip
    after = duel_ledger(events, attacker_id, slot, team_id, rosters, asof=asof, since=swap_sec)
    return SwapImpact(swap_sec=swap_sec, before=before, after=after)
