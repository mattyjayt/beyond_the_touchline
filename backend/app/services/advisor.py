"""Subs advisor (spec 4): KEEP / SUB / SWAP / SUB+SWAP for a losing 1v1 duel.

``evaluate`` is pure: it scores options from an ``AdvisorInput`` built at the edge by
``advisor_input`` (Store reads only, nothing past ``asof``). Every option is scored against
KEEP on six bounded dimensions combined with stated POLICY weights - a policy, not a causal
estimate. Projected duel win rates come from the simulator's duel model (uncalibrated) and are
shrunk towards what has been observed. Everything is simulated.
"""

from dataclasses import dataclass
from itertools import product

from app.models import (
    ROLE_GROUP,
    DuelLedger,
    HotDuel,
    MatchEvent,
    Move,
    OptionDims,
    Player,
    Recommendation,
    RosterEntry,
)
from app.services.matchups import HOT_WINDOW_SEC, current_slots, duel_ledger, hot_duels
from app.services.performance import (
    is_out_of_position,
    live_rating,
    minutes_played,
    slot_position,
    slot_timeline,
)
from app.services.race import race
from app.sim.duel import DuelContext, duel_prob
from app.store import Store

ADVISOR_VERSION = "advisor-v1"
POLICY_WEIGHTS = {"L": 0.15, "F": 0.15, "M": 0.35, "A": 0.1, "G": 0.1, "R": 0.15}
SHRINK_K = 6  # pseudo-duels of model prior when blending with the observed rate
M_SCALE = 0.3  # a 30-point gain in duel win rate saturates M
MAX_SUBS = 5
MAX_OPTIONS = 4  # besides KEEP
RACE_GAP_S = 0.03  # smaller 0-5 m gaps are reported as level, not as an edge
_GROUP_STEP = {"DEF": 0, "MID": 1, "ATT": 2}
_ATTACK_W = {"GK": 0.0, "DEF": 0.4, "MID": 0.7, "ATT": 1.0}  # attacking weight of a slot
_CONTEXT_GRID = list(product((True, False), (True, False)))  # isolated x transition
_TOUCH = 15.0  # typical wide-duel distance to the touchline


@dataclass(frozen=True)
class AdvisorInput:
    team_id: str
    players: dict[str, Player]
    slots: dict[str, str]  # our on-pitch players -> slot
    bench: list[str]  # eligible bench players
    formation: str
    hot: HotDuel
    ledger: DuelLedger  # tormentor vs the hot slot, whole match up to asof
    live: dict[str, float]  # live rating of our on-pitch players
    expected: dict[str, float | None]  # baseline rating from prior simulated matches
    history_n_at_slot: dict[tuple[str, str], int]  # prior matches the player held the slot
    goal_diff: int
    minute: int
    subs_left: int
    yellows: set[str]  # our booked players still on the pitch
    tormentor: Player
    asof: int
    match_id: str
    minutes_on: dict[str, float]  # minutes on the pitch (bench = 0), incl. the tormentor
    observed: dict[str, tuple[int, int]]  # player -> (duels won, duels) vs the tormentor


# ------------------------------------------------------------------ helpers
def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def fit(player: Player, slot: str) -> float:
    """1 primary, 0.8 secondary, 0.5 same role group, 0.3 adjacent group (projected), else 0."""
    pos = slot_position(slot)
    if pos == player.primary_position:
        return 1.0
    if pos in player.secondary_positions:
        return 0.8
    have, need = ROLE_GROUP[player.primary_position], ROLE_GROUP.get(pos)
    if need == have:
        return 0.5
    if (
        have in _GROUP_STEP
        and need in _GROUP_STEP
        and abs(_GROUP_STEP[have] - _GROUP_STEP[need]) == 1
    ):
        return 0.3
    return 0.0


def _attack(p: Player) -> float:
    pr = p.priors
    return (pr.dribbling + pr.finishing + pr.passing) / 3 if pr else 50.0


def _band(n: int, cuts: tuple[int, int]) -> int:
    return 0 if n < cuts[0] else 1 if n < cuts[1] else 2


_BANDS = ("low", "medium", "high")


def t5m(p: Player) -> float:
    return race([p]).curves[0].t5m


@dataclass
class _Option:
    kind: str
    moves: list[Move]
    new_def: str  # who holds the hot slot afterwards
    vacated_fit: float | None  # fit in the slot left by the swap partner, if any
    subs: int


class _Scorer:
    def __init__(self, inp: AdvisorInput) -> None:
        self.inp = inp
        self.slot = inp.hot.defender_slot
        self.old_def = inp.hot.defender_id
        self._proj: dict[str, float] = {}

    def projected(self, pid: str) -> float:
        """1 - mean p_beat of the tormentor vs ``pid`` over a fixed context grid."""
        if pid not in self._proj:
            inp, d = self.inp, self.inp.players[pid]
            vals = [
                duel_prob(
                    inp.tormentor, d,
                    DuelContext(iso, tr, pid in inp.yellows, False, _TOUCH,
                                inp.minutes_on.get(inp.tormentor.player_id, 0.0),
                                inp.minutes_on.get(pid, 0.0)),
                    d.physical.stance_idx / 100,
                ).p_beat
                for iso, tr in _CONTEXT_GRID
            ]  # fmt: skip
            self._proj[pid] = round(1 - sum(vals) / len(vals), 3)
        return self._proj[pid]

    def shrunk(self, pid: str) -> float:
        won, n = self.inp.observed.get(pid, (0, 0))
        return (won + SHRINK_K * self.projected(pid)) / (n + SHRINK_K)

    def current(self) -> float:
        w = self.inp.hot.win_pct_20m
        return w if w is not None else self.shrunk(self.old_def)

    def dims(self, o: _Option) -> tuple[OptionDims, float]:
        inp, P = self.inp, self.inp.players
        new, old = P[o.new_def], P[self.old_def]
        exp, live = inp.expected.get(self.old_def), inp.live.get(self.old_def)
        L = _clamp(exp - live) if exp is not None and live is not None else 0.0
        F = min(fit(new, self.slot), o.vacated_fit if o.vacated_fit is not None else 1.0)
        M = _clamp((self.shrunk(o.new_def) - self.current()) / M_SCALE)
        # attacking change of every slot the option touches, weighted by the slot's role
        before = {s: p for p, s in inp.slots.items()}
        after = dict(before)
        for m in o.moves:
            if m.from_slot and after.get(m.from_slot) == m.player_id:
                after.pop(m.from_slot)
        for m in o.moves:
            if m.to_slot:
                after[m.to_slot] = m.player_id
        delta = sum(
            _ATTACK_W[ROLE_GROUP[slot_position(s)]] * (_attack(P[after[s]]) - _attack(P[before[s]]))
            for s in set(before) & set(after)
            if after[s] != before[s]
        )
        A = _clamp(delta / 25)
        urgency = _clamp((inp.minute - 45) / 45, 0.0, 1.0)
        if inp.goal_diff < 0:
            G = _clamp(urgency * A)
        elif inp.goal_diff > 0:
            G = _clamp(urgency * M)
        else:
            G = _clamp(urgency * (A + M) / 2)
        risk = max(0, old.priors.defending - new.priors.defending) / 40
        risk += 0.25 if o.new_def in inp.yellows else 0.0
        risk -= 0.25 if self.old_def in inp.yellows else 0.0  # booked defender leaves the duel
        risk += (1 - o.vacated_fit) * 0.5 if o.vacated_fit is not None else 0.0
        risk += 0.15 * o.subs
        R = _clamp(-risk)
        dims = OptionDims(**{k: round(v, 3) for k, v in zip("LFMAGR", (L, F, M, A, G, R))})
        score = sum(POLICY_WEIGHTS[k] * getattr(dims, k) for k in POLICY_WEIGHTS)
        return dims, round(score, 4)

    def confidence(self, new_def: str, f: float) -> str:
        n_slot = self.inp.history_n_at_slot.get((new_def, self.slot), 0)
        bands = [
            _BANDS.index(self.inp.ledger.confidence),
            _band(n_slot, (1, 3)),
            0 if f < 0.5 else 1 if f < 0.8 else 2,
        ]
        return _BANDS[min(bands)]


# ------------------------------------------------------------------ options
def _candidates(inp: AdvisorInput) -> list[_Option]:
    P, slot, old = inp.players, inp.hot.defender_slot, inp.hot.defender_id
    if old not in inp.slots:
        return []
    subs = [b for b in inp.bench if fit(P[b], slot) >= 0.5] if inp.subs_left > 0 else []
    out = [
        _Option("substitution", [Move(player_id=old, from_slot=slot, to_slot=None, kind="off"),
                                 Move(player_id=b, from_slot=None, to_slot=slot, kind="on")],
                b, None, 1)
        for b in subs
    ]  # fmt: skip
    g_old = _GROUP_STEP.get(ROLE_GROUP[P[old].primary_position])
    for x, sx in inp.slots.items():
        g_x = _GROUP_STEP.get(ROLE_GROUP[P[x].primary_position])
        if x == old or sx == "GK" or g_x is None or g_old is None or abs(g_x - g_old) > 1:
            continue
        if fit(P[x], slot) < 0.3:
            continue
        into = Move(player_id=x, from_slot=sx, to_slot=slot, kind="move")
        back = fit(P[old], sx)
        if back >= 0.3:
            out.append(
                _Option("position_swap",
                        [into, Move(player_id=old, from_slot=slot, to_slot=sx, kind="move")],
                        x, back, 0)
            )  # fmt: skip
        if inp.subs_left > 0:
            fills = [b for b in inp.bench if fit(P[b], sx) >= 0.5]
            if fills:
                b = max(fills, key=lambda b: (fit(P[b], sx), _attack(P[b]), b))
                out.append(
                    _Option("sub_and_swap",
                            [into, Move(player_id=old, from_slot=slot, to_slot=None, kind="off"),
                             Move(player_id=b, from_slot=None, to_slot=sx, kind="on")],
                            x, fit(P[b], sx), 1)
                )  # fmt: skip
    return out


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.0%}"


def _pros_cons(inp: AdvisorInput, sc: _Scorer, o: _Option) -> tuple[list[str], list[str]]:
    P, slot = inp.players, sc.slot
    new, old, torm = P[o.new_def], P[sc.old_def], inp.tormentor
    pros = [
        (
            f"Projected duel win vs {torm.display_name}: {_pct(sc.projected(o.new_def))} "
            f"vs {_pct(sc.current())} now (simulated)"
        )
    ]
    cons: list[str] = []
    tn, to = t5m(new), t5m(old)
    race_txt = f"{old.display_name}: {tn:.2f} s vs {to:.2f} s to 5 m (simulated)"
    if to - tn >= RACE_GAP_S:
        pros.append(f"Out-accelerates {race_txt}")
    elif tn - to >= RACE_GAP_S:
        cons.append(f"Slower off the mark than {race_txt}")
    else:
        pros.append(f"Level off the mark with {race_txt}")
    sn, so = new.physical.stance_idx, old.physical.stance_idx
    if sn > so:
        pros.append(f"Defends side-on more often: stance {sn} vs {so} (simulated index)")
    if new.physical.top_speed_kmh < old.physical.top_speed_kmh:
        cons.append(
            f"Lower top speed: {new.physical.top_speed_kmh:.1f} vs "
            f"{old.physical.top_speed_kmh:.1f} km/h, fewer recoveries once beaten"
        )
    if sc.old_def in inp.yellows:
        pros.append(f"Takes booked {old.display_name} out of the duel")
    won, n = inp.observed.get(o.new_def, (0, 0))
    if n:
        pros.append(f"Already {won}/{n} in duels with {torm.display_name} this match")
    n_slot = inp.history_n_at_slot.get((o.new_def, slot), 0)
    if n_slot == 0:
        cons.append(f"No history at {slot} (n=0): experimental role")
    else:
        pros.append(f"Has played {slot} in {n_slot} prior simulated match(es)")
    if o.kind == "position_swap":
        pros.append("Uses no substitution")
        partner = next(m for m in o.moves if m.player_id == sc.old_def)
        cons.append(f"{old.display_name} moves to {partner.to_slot} (fit {o.vacated_fit:.1f})")
    if o.subs:
        cons.append(f"Uses a substitution window ({inp.subs_left - o.subs} left)")
    if o.kind == "substitution":
        pros.append(f"Fresh legs: 0 minutes vs {inp.minutes_on.get(sc.old_def, 0):.0f} for "
                    f"{old.display_name}")  # fmt: skip
    if o.kind == "sub_and_swap":
        on = next(m for m in o.moves if m.kind == "on")
        pros.append(
            f"{P[on.player_id].display_name} comes on at {on.to_slot} (fit {o.vacated_fit:.1f})"
        )
    f_new = fit(new, slot)
    if f_new < 0.5:
        cons.append(
            f"{slot_position(slot)} is not a listed position for {new.display_name} "
            f"(fit {f_new:.1f}): projected role"
        )
    if new.priors.defending < old.priors.defending:
        cons.append(f"Lower defending prior: {new.priors.defending} vs {old.priors.defending}")
    return pros, cons


def option_label(rec: Recommendation, names: dict[str, str]) -> str:
    """Short human label: KEEP, "X for Y", "Swap: X to RB, Y to RW", "X to RB, Y off, Z on at RW"."""

    def n(pid: str | None) -> str:
        return names.get(pid or "", pid or "?")

    if rec.option_type == "keep":
        return "KEEP"
    into, out = rec.incoming_player_id, rec.outgoing_player_id
    if rec.option_type == "substitution":
        return f"{n(into)} for {n(out)}"
    to = {m.player_id: m.to_slot for m in rec.moves}
    if rec.option_type == "position_swap":
        return f"Swap: {n(into)} to {to.get(into or '')}, {n(out)} to {to.get(out or '')}"
    on = next((m for m in rec.moves if m.kind == "on"), None)
    extra = f", {n(on.player_id)} on at {on.to_slot}" if on else ""
    return f"{n(into)} to {to.get(into or '')}, {n(out)} off{extra}"


def projected_win(inp: AdvisorInput, player_id: str) -> float:
    """Duel-model projected win rate of ``player_id`` defending against the tormentor."""
    return _Scorer(inp).projected(player_id)


def keep_only(match_id: str, team_id: str, asof: int) -> Recommendation:
    """The lone KEEP option shown while no duel is being lost."""
    return Recommendation(
        rec_id=f"REC-{match_id}-{asof}-1", match_id=match_id, team_id=team_id, asof_sec=asof,
        option_rank=1, option_type="keep", attack_delta_estimate=0, control_delta_estimate=0,
        defensive_risk_delta=0, tactical_fit_score=1.0, confidence="low",
        pros=["No individual duel is being lost: no trigger fired"],
        cons=["Nothing specific to fix yet"], model_version=ADVISOR_VERSION,
        dims=OptionDims(L=0, F=0, M=0, A=0, G=0, R=0), score=0.0,
    )  # fmt: skip


def evaluate(inp: AdvisorInput) -> list[Recommendation]:
    """KEEP plus the best (up to 4) other options, ranked by policy score (KEEP scores 0)."""
    sc = _Scorer(inp)
    P, slot, old = inp.players, sc.slot, sc.old_def
    evidence = inp.ledger.evidence_event_ids[-8:]
    scored = []
    for o in _candidates(inp):
        dims, score = sc.dims(o)
        scored.append((score, o, dims))
    scored.sort(key=lambda t: (-t[0], t[1].kind, t[1].new_def))
    scored = scored[:MAX_OPTIONS]

    keep_dims = OptionDims(L=0, F=0, M=0, A=0, G=0, R=0)
    rows = [(0.0, None, keep_dims)] + scored
    rows.sort(key=lambda t: -t[0])  # stable: KEEP stays ahead of a 0-scoring option
    torm = inp.tormentor.display_name
    recs: list[Recommendation] = []
    for rank, (score, o, dims) in enumerate(rows, start=1):
        common = {
            "rec_id": f"REC-{inp.match_id}-{inp.asof}-{rank}", "match_id": inp.match_id,
            "team_id": inp.team_id, "asof_sec": inp.asof, "option_rank": rank,
            "supporting_event_ids": evidence, "dims": dims, "score": score,
            "model_version": ADVISOR_VERSION,
        }  # fmt: skip
        if o is None:
            won, n = inp.observed.get(old, (0, 0))
            pros = [f"Keeps the shape and all {inp.subs_left} substitution(s)"]
            cons = [
                (
                    f"{P[old].display_name} beaten {inp.hot.beaten_20m} times by {torm} in the last "
                    f"20' (win {_pct(inp.hot.win_pct_20m)}, n={inp.hot.n_20m})"
                )
            ]
            if old in inp.yellows:
                cons.append(f"{P[old].display_name} is on a yellow: card risk against {torm}")
            recs.append(Recommendation(
                **common, option_type="keep", attack_delta_estimate=0, control_delta_estimate=0,
                defensive_risk_delta=0, tactical_fit_score=fit(P[old], slot),
                confidence=sc.confidence(old, fit(P[old], slot)), pros=pros, cons=cons,
                projected_win_pct=sc.projected(old),
                observed_win_pct=round(won / n, 3) if n else None, n_observed=n,
            ))  # fmt: skip
            continue
        pros, cons = _pros_cons(inp, sc, o)
        new = P[o.new_def]
        won, n = inp.observed.get(o.new_def, (0, 0))
        oop = any(
            m.to_slot is not None and is_out_of_position(P[m.player_id], m.to_slot) for m in o.moves
        )
        recs.append(Recommendation(
            **common, option_type=o.kind, outgoing_player_id=old, incoming_player_id=o.new_def,
            moves=o.moves, attack_delta_estimate=dims.A,
            control_delta_estimate=round((new.priors.passing - P[old].priors.passing) / 100, 3),
            defensive_risk_delta=round(-dims.R, 3), tactical_fit_score=max(0.0, dims.F),
            confidence=sc.confidence(o.new_def, dims.F), pros=pros, cons=cons,
            projected_win_pct=sc.projected(o.new_def),
            observed_win_pct=round(won / n, 3) if n else None, n_observed=n,
            out_of_position=oop,
        ))  # fmt: skip
    return recs


# --------------------------------------------------------------- edge (I/O)
def player_history(store: Store, player_id: str, lookback: int = 5) -> list[dict]:
    """Last ``lookback`` prior simulated matches the player played in (no current match)."""
    player = store.players[player_id]
    out = []
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
        rating, _, _ = live_rating(player, events, end, mins, rosters)
        slots = {s for _, s in slot_timeline(player_id, rosters, events) if s}
        out.append({"match_id": m.match_id, "minutes": round(mins), "rating": rating,
                    "slots": sorted(slots)})  # fmt: skip
        if len(out) >= lookback:
            break
    return out


def _slot_counts(store: Store, player_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for m in store.matches.values():
        if m.kind != "historical":
            continue
        rosters = store.rosters(m.match_id)
        if not any(r.player_id == player_id for r in rosters):
            continue
        for s in {s for _, s in slot_timeline(player_id, rosters, store.events(m.match_id)) if s}:
            counts[s] = counts.get(s, 0) + 1
    return counts


def _subs_made(events: list[MatchEvent], team_id: str, asof: int) -> int:
    return sum(
        1 for e in events
        if e.event_type == "substitution" and e.team_id == team_id and e.event_sec <= asof
    )  # fmt: skip


def advisor_input(
    store: Store, match_id: str, team_id: str, asof: int, hot: HotDuel | None = None
) -> AdvisorInput | None:
    """Everything ``evaluate`` needs as of ``asof``. Without ``hot`` it uses the duel firing
    now and returns None while none is; pass ``hot`` to keep evaluating an earlier alert."""
    events = [e for e in store.events(match_id) if e.event_sec <= asof]
    rosters: list[RosterEntry] = store.rosters(match_id)
    if hot is None:
        firing = hot_duels(events, rosters, team_id, asof)
        if not firing:
            return None
        hot = firing[0]
    h = hot
    match = store.matches[match_id]
    team_of = {r.player_id: r.team_id for r in rosters}
    slots = {p: s for p, s in current_slots(rosters, events, asof).items() if team_of[p] == team_id}
    came_on = {e.recipient_id for e in events if e.event_type == "substitution"}
    bench = [
        r.player_id for r in rosters
        if r.team_id == team_id and r.roster_status == "bench"
        and r.player_id not in slots and r.player_id not in came_on
    ]  # fmt: skip
    players = store.players
    minutes_on = {p: minutes_played(p, rosters, events, asof) for p in [*slots, h.attacker_id]} | {
        b: 0.0 for b in bench
    }
    live = {p: live_rating(players[p], events, asof, minutes_on[p], rosters)[0] for p in slots}
    expected: dict[str, float | None] = {}
    n_at: dict[tuple[str, str], int] = {}
    for p in [*slots, *bench]:
        hist = player_history(store, p)
        expected[p] = round(sum(x["rating"] for x in hist) / len(hist), 2) if hist else None
        for s, n in _slot_counts(store, p).items():
            n_at[(p, s)] = n
    observed = {}
    for p in [*slots, *bench]:
        led = duel_ledger(events, h.attacker_id, p, team_id, rosters, asof)
        observed[p] = (led.won, led.duels)
    home = team_id == match.home_team_id
    goals = {
        t: sum(
            1 for e in events if e.event_type == "shot" and e.outcome == "goal" and e.team_id == t
        )
        for t in (match.home_team_id, match.away_team_id)
    }
    opp = match.away_team_id if home else match.home_team_id
    yellows = {
        e.player_id for e in events
        if e.event_type == "card" and e.qualifiers.get("card") == "yellow" and e.player_id in slots
    }  # fmt: skip
    return AdvisorInput(
        team_id=team_id, players=players, slots=slots, bench=bench,
        formation=match.home_formation if home else match.away_formation, hot=h,
        ledger=duel_ledger(events, h.attacker_id, h.defender_slot, team_id, rosters, asof),
        live=live, expected=expected, history_n_at_slot=n_at,
        goal_diff=goals[team_id] - goals[opp], minute=asof // 60 + 1,
        subs_left=MAX_SUBS - _subs_made(events, team_id, asof), yellows=yellows,
        tormentor=players[h.attacker_id], asof=asof, match_id=match_id,
        minutes_on=minutes_on, observed=observed,
    )  # fmt: skip


__all__ = [
    "ADVISOR_VERSION",
    "HOT_WINDOW_SEC",
    "POLICY_WEIGHTS",
    "AdvisorInput",
    "advisor_input",
    "evaluate",
    "fit",
    "keep_only",
    "option_label",
    "player_history",
    "projected_win",
]
