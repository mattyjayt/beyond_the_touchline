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
from functools import cache

from scipy.stats import beta as beta_dist

from app.models import (
    ROLE_GROUP,
    DuelLedger,
    DuelOutcome,
    DuelPoint,
    HotDuel,
    ImpactPoint,
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
HOT_WINDOW_SEC = 1200  # trigger window W (Phase B amendment A2 selects 20' or 30')

MIN_CI_N = 5  # duels needed before a win-rate interval is shown
MIN_RATE_WINDOW_SEC = 300  # per-10' rates are hidden for shorter windows
TRAJECTORY_MIN = (5, 10, 20)  # swap-impact checkpoints after the change
HOT_BEATEN_POSS = 3  # beaten in >= 3 distinct possessions in the last 20 min ...
LEAGUE_DEF_WIN = 0.610  # league defender win rate at DUEL_BASELINE 16 (Phase B item 7)
PRIOR_K = 6  # ... with P(win rate < league) >= HOT_Q under a Beta prior worth 6 duels ...
HOT_Q = 0.95  # (amendment A2 grid: W=20', q=0.95 selected) ... and flank threat
BOX_X = 83.0  # end x beyond this (attacker frame) counts as a box entry
CHANNEL_Y = 67.0  # wide channel: start_y > 67 (or < 33) in the attacker's frame


def window_label() -> str:
    """The trigger window as copy, e.g. "20'" (texts follow W)."""
    return f"{HOT_WINDOW_SEC // 60}'"


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
    possession: str | None = None  # the take-on's possession (one beaten per possession)


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
            out.append(_Duel(point, s, beaten, evidence, round(delta, 4), e.possession_id))
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


def wilson(won: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson score interval for a win rate; None below MIN_CI_N duels."""
    if n < MIN_CI_N:
        return None
    p = won / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z / (1 + z * z / n) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)


def _beaten(duels: list[_Duel]) -> int:
    """Beaten count with at most one per possession (a beaten defender re-engaging in the same
    run is one failure, not several; Phase B item 9)."""
    seen: set[str] = set()
    n = 0
    for d in duels:
        if not d.beaten:
            continue
        if d.possession is None:
            n += 1
        elif d.possession not in seen:
            seen.add(d.possession)
            n += 1
    return n


def _confidence(won: int, n: int) -> Confidence:
    """Bands by interval width, not n alone (C4): high only when the 95% half-width <= 0.12."""
    ci = wilson(won, n)
    if ci is None:
        return "low"
    half = (ci[1] - ci[0]) / 2
    return "low" if half > 0.25 else "medium" if half > 0.12 else "high"


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
    in_window = [
        e for e in events
        if since <= e.event_sec <= asof and e.team_id == att_team
        and e.possession_id in channel_poss
    ]  # fmt: skip
    shots = [e for e in in_window if e.event_type == "shot"]
    # completed crosses, or passes/carries ending in the box, from the channel's possessions
    entries = [
        e for e in in_window
        if e.outcome == "success" and e.event_type in ("pass", "carry")
        and (e.qualifiers.get("cross") or (e.end_x or 0) > BOX_X)
    ]  # fmt: skip

    rolling: list[RollingPoint] = []
    first = -(-since // ROLLING_STEP_SEC) * ROLLING_STEP_SEC
    for sec in range(first, asof + 1, ROLLING_STEP_SEC):
        win = [d for d in duels if sec - ROLLING_WINDOW_SEC < d.point.sec <= sec]
        rolling.append(RollingPoint(sec=sec, win_pct=_win_pct(win), n=len(win)))

    outcomes = [d.point.outcome for d in duels]
    won = sum(o in _WINS for o in outcomes)
    ci = wilson(won, len(duels))
    window_sec = asof - since + 1
    beaten = _beaten(duels)
    evidence = [i for d in duels for i in d.evidence]
    evidence += list(channel_poss.values()) + [e.event_id for e in shots]
    return DuelLedger(
        attacker_id=attacker_id,
        defender_ids=defender_ids,
        duels=len(duels),
        won=won,
        lost=outcomes.count("lost"),
        recoveries=outcomes.count("recovered"),
        fouls=outcomes.count("foul"),
        win_pct=_win_pct(duels),
        win_ci=list(ci) if ci else None,
        window_sec=window_sec,
        beaten=beaten,
        beaten_per_10=(
            round(beaten * 600 / window_sec, 2) if window_sec >= MIN_RATE_WINDOW_SEC else None
        ),
        channel_shots=len(shots),
        channel_entries=len(entries),
        channel_xg=round(sum(float(e.qualifiers.get("xg", 0)) for e in shots), 3),
        defender_rating_swing=round(sum(d.rating_delta for d in duels), 3) if duels else None,
        confidence=_confidence(won, len(duels)),
        points=[d.point for d in duels],
        rolling=rolling,
        evidence_event_ids=_unique(evidence),
    )


def records_vs(
    events: list[MatchEvent], rosters: list[RosterEntry], team_id: str, attacker_id: str, asof: int
) -> dict[str, tuple[int, int]]:
    """defender -> (duels won, duels) against ``attacker_id`` up to ``asof``, in one pass.
    Same counting as ``duel_ledger(..., defender_id, ...)``."""
    out: dict[str, tuple[int, int]] = {}
    for d in _duels(events, rosters, team_id, asof):
        if d.point.attacker_id != attacker_id:
            continue
        won, n = out.get(d.point.defender_id, (0, 0))
        out[d.point.defender_id] = (won + (d.point.outcome in _WINS), n + 1)
    return out


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
# Trigger (Phase B, amendment A1): over the last 20 min, for the CURRENT holder of a slot,
#   beaten in >= HOT_BEATEN_POSS distinct possessions, AND
#   posterior P(win rate < league average) >= HOT_Q (Beta prior worth PRIOR_K duels at the
#   league defender win rate), AND
#   channel threat: >= 1 shot or >= 2 completed crosses / box entries from that flank.


@dataclass
class _Pair:
    slot: str
    attacker: str
    duels: list[_Duel]
    threat: list[tuple[int, str, float]]  # (sec, "shot" | "entry", xg) from the channel


@dataclass
class _Timeline:
    """Who holds which slot (and who is on the pitch) over time, from one pass."""

    changes: dict[str, list[tuple[int, str | None]]]  # player -> [(sec, slot)] from kickoff

    def slot_of(self, pid: str, sec: int) -> str | None:
        current = None
        for s, slot in self.changes.get(pid, []):
            if s > sec:
                break
            current = slot
        return current

    def holder(self, slot: str, sec: int, team_of: dict[str, str], team: str) -> str | None:
        return next(
            (p for p in self.changes if team_of.get(p) == team and self.slot_of(p, sec) == slot),
            None,
        )


def _timeline(rosters: list[RosterEntry], events: list[MatchEvent], until: int) -> _Timeline:
    slot = _starting_slots(rosters)
    changes: dict[str, list[tuple[int, str | None]]] = {p: [(0, s)] for p, s in slot.items()}
    for e in events:
        if e.event_sec > until:
            break
        before = dict(slot)
        _apply_slot_change(slot, e)
        for pid in set(before) | set(slot):
            if before.get(pid) != slot.get(pid):
                changes.setdefault(pid, []).append((e.event_sec, slot.get(pid)))
    return _Timeline(changes)


def _pairs(
    events: list[MatchEvent], rosters: list[RosterEntry], team_id: str, until: int
) -> list[_Pair]:
    """Duels against ``team_id`` grouped by (slot at the time, attacker), with the threat each
    attacker created from that slot's channel."""
    groups: dict[tuple[str, str], list[_Duel]] = {}
    for d in _duels(events, rosters, team_id, until):
        if d.slot:
            groups.setdefault((d.slot, d.point.attacker_id), []).append(d)
    team_of = {r.player_id: r.team_id for r in rosters}
    out = []
    for (slot, att), duels in groups.items():
        poss = {
            e.possession_id for e in events
            if e.event_sec <= until and e.player_id == att and e.possession_id
            and e.event_type in ("take_on", "carry") and e.outcome == "success"
            and _in_channel(slot, e.start_y)
        }  # fmt: skip
        threat = []
        for e in events:
            if e.event_sec > until or e.possession_id not in poss:
                continue
            if e.team_id != team_of.get(att):
                continue
            if e.event_type == "shot":
                threat.append((e.event_sec, "shot", float(e.qualifiers.get("xg", 0))))
            elif (
                e.outcome == "success" and e.event_type in ("pass", "carry")
                and (e.qualifiers.get("cross") or (e.end_x or 0) > BOX_X)
            ):  # fmt: skip
                threat.append((e.event_sec, "entry", 0.0))
        out.append(_Pair(slot, att, duels, threat))
    return out


@dataclass
class _State:
    beaten: int  # distinct possessions in which the holder was beaten
    n: int
    won: int
    pct: float | None
    p_below: float | None  # posterior P(win rate < league average)
    shots: int
    entries: int
    fires: bool


@cache
def p_below_league(won: int, n: int) -> float:
    """Posterior P(defender win rate < LEAGUE_DEF_WIN), Beta prior worth PRIOR_K duels."""
    a = PRIOR_K * LEAGUE_DEF_WIN + won
    b = PRIOR_K * (1 - LEAGUE_DEF_WIN) + (n - won)
    return float(beta_dist.cdf(LEAGUE_DEF_WIN, a, b))


def _state(duels: list[_Duel], threat: list[tuple[int, str, float]], end: int) -> _State:
    win = [d for d in duels if end - HOT_WINDOW_SEC < d.point.sec <= end]
    th = [t for t in threat if end - HOT_WINDOW_SEC < t[0] <= end]
    won = sum(d.point.outcome in _WINS for d in win)
    beaten = _beaten(win)
    p_below = p_below_league(won, len(win)) if win else None
    shots = sum(k == "shot" for _, k, _ in th)
    entries = sum(k == "entry" for _, k, _ in th)
    fires = (
        beaten >= HOT_BEATEN_POSS
        and p_below is not None and p_below >= HOT_Q
        and (shots >= 1 or entries >= 2)
    )  # fmt: skip
    return _State(beaten, len(win), won, _win_pct(win), p_below, shots, entries, fires)


def _candidates(pair: _Pair, until: int) -> list[int]:
    """Seconds at which the 20-minute state can change: an input enters or leaves."""
    secs = {d.point.sec for d in pair.duels} | {t[0] for t in pair.threat}
    secs |= {s + HOT_WINDOW_SEC for s in secs}
    return sorted(x for x in secs | {until} if x <= until)


def _fires_at(pair: _Pair, tl: _Timeline, team_of, team_id: str, sec: int) -> _State | None:
    holder = tl.holder(pair.slot, sec, team_of, team_id)
    if holder is None or tl.slot_of(pair.attacker, sec) is None:
        return None  # nobody to defend, or nobody to stop
    own = [d for d in pair.duels if d.point.defender_id == holder]
    recent = [d for d in own if sec - HOT_WINDOW_SEC < d.point.sec <= sec]
    if _beaten(recent) < HOT_BEATEN_POSS:
        return None  # cheap test first: the posterior can't matter without enough beats
    st = _state(own, pair.threat, sec)
    return st if st.fires else None


def _hot(pair: _Pair, holder: str, team_id: str, st: _State, first: int | None) -> HotDuel:
    """The holder's own record; ``_with_slot_history`` adds the slot_* fields."""
    return HotDuel(
        team_id=team_id, defender_id=holder, defender_slot=pair.slot, attacker_id=pair.attacker,
        beaten_20m=st.beaten, win_pct_20m=st.pct, n_20m=st.n, first_fired_sec=first,
        p_below_league=None if st.p_below is None else round(st.p_below, 3),
        threat_shots_20m=st.shots, threat_entries_20m=st.entries,
    )  # fmt: skip


def hot_duels(
    events: list[MatchEvent], rosters: list[RosterEntry], team_id: str, asof: int
) -> list[HotDuel]:
    """Pairs (slot, attacker) firing for ``team_id`` defending at ``asof`` (see the trigger
    above). ``first_fired_sec`` is the first second <= asof at which the pair ever fired."""
    team_of = {r.player_id: r.team_id for r in rosters}
    tl = _timeline(rosters, events, asof)
    out: list[HotDuel] = []
    for pair in _pairs(events, rosters, team_id, asof):
        st = _fires_at(pair, tl, team_of, team_id, asof)
        if st is None:
            continue
        holder = tl.holder(pair.slot, asof, team_of, team_id)
        first = next(s for s in _candidates(pair, asof) if _fires_at(pair, tl, team_of, team_id, s))
        out.append(_with_slot_history(_hot(pair, holder, team_id, st, first), pair, asof))
    out.sort(key=lambda h: (-(h.p_below_league or 0), -h.beaten_20m, h.defender_slot))
    return out


def _with_slot_history(h: HotDuel, pair: _Pair, asof: int) -> HotDuel:
    s = _state(pair.duels, pair.threat, asof)
    return h.model_copy(update={"slot_beaten_20m": s.beaten, "slot_n_20m": s.n,
                                "slot_win_pct_20m": s.pct})  # fmt: skip


def first_trigger(
    events: list[MatchEvent], rosters: list[RosterEntry], team_id: str, until: int
) -> tuple[int | None, list[HotDuel]]:
    """First second <= ``until`` at which ``hot_duels`` fires for ``team_id`` defending.

    Exact: the state only changes when a duel or a threat event enters the 20-minute window
    (its second) or leaves it (second + W), so only those seconds are checked. Reads no
    event after ``until``.
    """
    team_of = {r.player_id: r.team_id for r in rosters}
    tl = _timeline(rosters, events, until)
    pairs = _pairs(events, rosters, team_id, until)
    secs = sorted({s for pair in pairs for s in _candidates(pair, until)})
    for sec in secs:
        if any(_fires_at(pair, tl, team_of, team_id, sec) for pair in pairs):
            return sec, hot_duels([e for e in events if e.event_sec <= sec], rosters, team_id, sec)
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
    that has fired once (``first_fired_sec``) tracked as the slot changes hands. The main
    fields are the current holder's own record; ``slot_*`` cover every holder. None when
    nobody holds the slot any more."""
    team_of = {r.player_id: r.team_id for r in rosters}
    tl = _timeline(rosters, events, asof)
    holder = tl.holder(slot, asof, team_of, team_id)
    if holder is None:
        return None
    pair = next(
        (p for p in _pairs(events, rosters, team_id, asof)
         if p.slot == slot and p.attacker == attacker_id),
        _Pair(slot, attacker_id, [], []),
    )  # fmt: skip
    st = _state([d for d in pair.duels if d.point.defender_id == holder], pair.threat, asof)
    return _with_slot_history(_hot(pair, holder, team_id, st, first_fired_sec), pair, asof)


def sticky_alert(
    events: list[MatchEvent], rosters: list[RosterEntry], team_id: str, asof: int
) -> tuple[int | None, HotDuel | None, bool]:
    """(first fired second, the alerted pair's CURRENT stats, firing now?) up to ``asof``.

    Once the trigger has fired, its (slot, attacker) pair stays the subject - the page, the
    chat and the agent all follow it as it cools down or the slot changes hands."""
    evs = [e for e in events if e.event_sec <= asof]
    fired_sec, fired = first_trigger(evs, rosters, team_id, asof)
    if fired_sec is None:
        return None, None, False
    first = fired[0]
    hot = hot_pair(evs, rosters, team_id, first.defender_slot, first.attacker_id, asof, fired_sec)
    active = any(
        h.defender_slot == first.defender_slot and h.attacker_id == first.attacker_id
        for h in hot_duels(evs, rosters, team_id, asof)
    )
    return fired_sec, hot, active


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
    [swap_sec - W, swap_sec - 1]; ``after`` covers [swap_sec, asof]. Equal-footing windows
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
    trajectory = []
    for minutes in TRAJECTORY_MIN:
        end = swap_sec + minutes * 60 - 1
        if end > asof:
            break
        led = duel_ledger(events, attacker_id, slot, team_id, rosters, asof=end, since=swap_sec)
        trajectory.append(ImpactPoint(minutes=minutes, n=led.duels, win_pct=led.win_pct,
                                      beaten_per_10=led.beaten_per_10))  # fmt: skip
    b, a = before.win_ci, after.win_ci
    separated = b is not None and a is not None and (b[1] < a[0] or a[1] < b[0])
    return SwapImpact(swap_sec=swap_sec, before=before, after=after, win_separated=separated,
                      trajectory=trajectory)  # fmt: skip
