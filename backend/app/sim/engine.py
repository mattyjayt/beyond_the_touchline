"""Possession state-machine match simulator.

Every event follows from the previous ball state, so goals, passes, duels and
turnovers reconcile by construction (spec §1). Coordinates are in the actor's
attacking frame (docs/schema.md §6). Deterministic for a given seed.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime

from app.models import ROLE_GROUP, Match, MatchEvent, Player, RosterEntry, Team
from app.sim.formations import Slot, formation_slots

GENERATOR_VERSION = "sim-v0.1"
HALF_SEC = 2700
MAX_SUBS = 5
WIDE_ARCHETYPES = {"direct_winger", "inside_forward", "ball_carrier", "attacking_fullback"}


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def mirror(x: float, y: float) -> tuple[float, float]:
    return 100 - x, 100 - y


def illustrative_xg(x: float, y: float, header: bool = False) -> float:
    """Distance/angle logistic model. Illustrative only - not calibrated."""
    dx = (100 - x) * 1.05  # metres on a 105 x 68 pitch
    dy = (50 - y) * 0.68
    dist = max(math.hypot(dx, dy), 0.5)
    half_goal = 3.66
    angle = abs(math.atan2(half_goal - dy, dx) - math.atan2(-half_goal - dy, dx))
    logit = -1.4 - 0.15 * dist + 1.0 * angle - (0.6 if header else 0.0)
    return round(1 / (1 + math.exp(-logit)), 3)


def overall(p: Player) -> float:
    pr = p.priors
    assert pr is not None
    group = ROLE_GROUP[p.primary_position]
    if group == "GK":
        return pr.goalkeeping
    if group == "DEF":
        return (pr.defending * 2 + pr.physical + pr.passing) / 4
    if group == "MID":
        return (pr.passing * 2 + pr.dribbling + pr.defending) / 4
    return (pr.finishing * 2 + pr.dribbling) / 3


@dataclass
class Scenario:
    """Scripted storyline layered on top of the simulation (demo match only)."""

    focus_player_id: str
    window: tuple[int, int]
    take_on_success_mult: float = 0.25
    take_on_freq_mult: float = 3.5
    pass_to_focus_mult: float = 4.0
    marker_id: str | None = None  # opponent the focus player keeps meeting
    forced_lineup: dict[str, dict[str, str]] = field(default_factory=dict)  # team -> slot -> pid
    bench_must: dict[str, list[str]] = field(default_factory=dict)
    forced_subs: list[tuple[int, str, str, str]] = field(default_factory=list)  # sec, team, out, in
    no_auto_subs_before: dict[str, int] = field(default_factory=dict)

    def active(self, player_id: str | None, sec: float) -> bool:
        return player_id == self.focus_player_id and self.window[0] <= sec <= self.window[1]


@dataclass
class Side:
    team: Team
    formation: str
    slots: list[Slot]
    on_pitch: dict[str, Player | None]
    bench: list[Player]
    subs_used: int = 0
    yellows: set[str] = field(default_factory=set)
    planned_subs: list[int] = field(default_factory=list)
    subbed_on: set[str] = field(default_factory=set)

    @property
    def team_id(self) -> str:
        return self.team.team_id

    def players(self) -> list[tuple[Slot, Player]]:
        return [(s, p) for s in self.slots if (p := self.on_pitch[s.slot]) is not None]

    def slot_of(self, player_id: str) -> Slot | None:
        for s, p in self.players():
            if p.player_id == player_id:
                return s
        return None

    def by_slot(self, *names: str) -> Player | None:
        for n in names:
            if (p := self.on_pitch.get(n)) is not None:
                return p
        return None

    def gk(self) -> Player | None:
        return self.by_slot("GK")

    def avg_defending(self) -> float:
        ps = [p.priors.defending for _, p in self.players() if p.priors]
        return sum(ps) / max(len(ps), 1)


def pick_lineup(
    team: Team,
    squad: list[Player],
    rng: random.Random,
    noise: float,
    forced: dict[str, str] | None = None,
    bench_must: list[str] | None = None,
) -> Side:
    formation, slots = formation_slots(team.default_formation)
    forced = forced or {}
    by_id = {p.player_id: p for p in squad}
    used: set[str] = set()
    on_pitch: dict[str, Player | None] = {}
    reserved = set(bench_must or [])

    def fit(p: Player, slot: Slot) -> float:
        is_gk = p.primary_position == "GK"
        if (slot.position == "GK") != is_gk:
            return -100
        if p.primary_position == slot.position:
            base = 3.0
        elif slot.position in p.secondary_positions:
            base = 2.0
        elif ROLE_GROUP[p.primary_position] == ROLE_GROUP[slot.position]:
            base = 1.0
        else:
            base = -2.0
        return base + overall(p) / 100 + rng.gauss(0, noise)

    for slot in slots:
        if slot.slot in forced:
            p = by_id[forced[slot.slot]]
        else:
            pool = [p for p in squad if p.player_id not in used | reserved]
            p = max(pool, key=lambda c: fit(c, slot))
        used.add(p.player_id)
        on_pitch[slot.slot] = p

    rest = [p for p in squad if p.player_id not in used]
    bench = [by_id[pid] for pid in (bench_must or [])]
    gks = sorted((p for p in rest if p.primary_position == "GK"), key=overall, reverse=True)
    if gks and gks[0] not in bench:
        bench.append(gks[0])
    outfield = sorted(
        (p for p in rest if p.primary_position != "GK" and p not in bench),
        key=lambda p: overall(p) + rng.gauss(0, noise * 30),
        reverse=True,
    )
    bench.extend(outfield[: max(0, 9 - len(bench))])
    return Side(team=team, formation=formation, slots=slots, on_pitch=on_pitch, bench=bench)


class MatchSim:
    def __init__(
        self,
        match_id: str,
        kind: str,
        home: Side,
        away: Side,
        seed: int,
        kickoff_at: datetime,
        scenario: Scenario | None = None,
    ) -> None:
        self.match_id = match_id
        self.kind = kind
        self.home, self.away = home, away
        self.seed = seed
        self.kickoff_at = kickoff_at
        self.scenario = scenario
        self.rng = random.Random(f"match-{match_id}-{seed}")
        self.events: list[MatchEvent] = []
        self.rosters: list[RosterEntry] = self._rosters()
        self.score = {home.team_id: 0, away.team_id: 0}
        self.clock = 0.0
        self.period = 1
        self.poss_seq = 0
        self.possession_id: str | None = None
        self.att: Side = home
        self.carrier: Player | None = None
        self.ball = (50.0, 50.0)
        self.force_cross = False
        self.force_header: Player | None = None
        self._plan_subs()

    # ------------------------------------------------------------------ setup
    def _rosters(self) -> list[RosterEntry]:
        out = []
        for side in (self.home, self.away):
            for s, p in side.players():
                out.append(self._roster(side, p, "starter", s.slot))
            for p in side.bench:
                out.append(self._roster(side, p, "bench", None))
        return out

    def _roster(self, side: Side, p: Player, status: str, slot: str | None) -> RosterEntry:
        return RosterEntry(
            match_id=self.match_id,
            player_id=p.player_id,
            team_id=side.team_id,
            roster_status=status,
            formation_slot=slot,
            shirt_number=p.shirt_number,
        )

    def _plan_subs(self) -> None:
        for side in (self.home, self.away):
            n = self.rng.choice([2, 3, 3, 4, 5])
            earliest = 55 * 60
            if self.scenario:
                earliest = max(earliest, self.scenario.no_auto_subs_before.get(side.team_id, 0))
                n -= sum(1 for f in self.scenario.forced_subs if f[1] == side.team_id)
            side.planned_subs = sorted(
                self.rng.randint(earliest, 88 * 60) for _ in range(max(n, 0))
            )

    # ---------------------------------------------------------------- helpers
    def other(self, side: Side) -> Side:
        return self.away if side is self.home else self.home

    def side_of(self, team_id: str) -> Side:
        return self.home if team_id == self.home.team_id else self.away

    def new_possession(self, side: Side) -> None:
        self.poss_seq += 1
        self.possession_id = f"{self.match_id}-P{self.poss_seq:04d}"
        self.att = side

    def nearest(self, side: Side, pt: tuple[float, float], allow_gk: bool = False) -> Player:
        best, best_d = None, 1e9
        for s, p in side.players():
            if s.slot == "GK" and not allow_gk:
                continue
            d = math.hypot(s.x * 0.85 - pt[0], s.y - pt[1])
            if d < best_d:
                best, best_d = p, d
        assert best is not None
        return best

    def emit(
        self,
        side: Side,
        event_type: str,
        outcome: str,
        player: Player | None = None,
        start: tuple[float, float] | None = None,
        end: tuple[float, float] | None = None,
        recipient: Player | None = None,
        opponent: Player | None = None,
        body_part: str | None = None,
        qualifiers: dict | None = None,
        in_possession: bool = True,
    ) -> MatchEvent:
        ev = MatchEvent(
            event_id=f"{self.match_id}-E{len(self.events) + 1:04d}",
            match_id=self.match_id,
            sequence_no=len(self.events) + 1,
            period=self.period,
            event_sec=int(self.clock),
            possession_id=self.possession_id if in_possession else None,
            team_id=side.team_id,
            player_id=player.player_id if player else None,
            event_type=event_type,
            outcome=outcome,
            start_x=round(start[0], 1) if start else None,
            start_y=round(start[1], 1) if start else None,
            end_x=round(end[0], 1) if end else None,
            end_y=round(end[1], 1) if end else None,
            recipient_id=recipient.player_id if recipient else None,
            opponent_id=opponent.player_id if opponent else None,
            body_part=body_part,
            qualifiers=qualifiers or {},
        )
        self.events.append(ev)
        return ev

    def tick(self, lo: float, hi: float) -> None:
        self.clock += self.rng.uniform(lo, hi)

    # ------------------------------------------------------------------- run
    def run(self) -> tuple[Match, list[RosterEntry], list[MatchEvent]]:
        for period in (1, 2):
            self.period = period
            start = 0 if period == 1 else HALF_SEC
            # P1 stops early enough that the longest step (goal + kickoff, ~70s) stays < 45:00.
            end = HALF_SEC - 75 if period == 1 else 2 * HALF_SEC + self.rng.randint(60, 240)
            self.clock = start
            self.emit(self.home, "period_start", "neutral", in_possession=False)
            self.kickoff(self.home if period == 1 else self.away)
            while self.clock < end:
                if period == 2:
                    self.process_subs()
                self.step()
            self.clock = min(self.clock, HALF_SEC) if period == 1 else self.clock
            self.emit(self.home, "period_end", "neutral", in_possession=False)
        match = Match(
            match_id=self.match_id,
            kind=self.kind,
            home_team_id=self.home.team_id,
            away_team_id=self.away.team_id,
            kickoff_at=self.kickoff_at,
            status="finished" if self.kind == "historical" else "scheduled",
            home_score=self.score[self.home.team_id],
            away_score=self.score[self.away.team_id],
            home_formation=self.home.formation,
            away_formation=self.away.formation,
            seed=self.seed,
            generator_version=GENERATOR_VERSION,
        )
        return match, self.rosters, self.events

    # ------------------------------------------------------------ set pieces
    def kickoff(self, side: Side) -> None:
        self.new_possession(side)
        taker = side.by_slot("ST", "CAM", "LCM", "RCM") or self.nearest(side, (50, 50))
        self.emit(
            side,
            "restart",
            "neutral",
            taker,
            start=(50, 50),
            qualifiers={"restart_type": "kickoff"},
        )
        self.carrier, self.ball = taker, (50.0, 50.0)
        self.tick(1, 2)

    def goal_kick(self, side: Side) -> None:
        self.new_possession(side)
        gk = side.gk() or self.nearest(side, (6, 50))
        self.tick(12, 25)
        self.emit(
            side, "restart", "neutral", gk, start=(6, 50), qualifiers={"restart_type": "goal_kick"}
        )
        self.carrier, self.ball = gk, (6.0, 50.0)

    def corner(self, side: Side) -> None:
        if side is not self.att:
            self.new_possession(side)
        y = 1.0 if self.rng.random() < 0.5 else 99.0
        takers = [p for s, p in side.players() if ROLE_GROUP[s.position] in ("MID", "ATT")]
        taker = max(takers, key=lambda p: p.priors.passing)
        self.tick(15, 30)
        self.emit(
            side, "restart", "neutral", taker, start=(99, y), qualifiers={"restart_type": "corner"}
        )
        self.carrier, self.ball = taker, (99.0, y)
        self.force_cross = True

    def throw_in(self, side: Side, x: float, y: float) -> None:
        self.new_possession(side)
        ty = 0.0 if y < 50 else 100.0
        taker = self.nearest(side, (x, ty))
        self.tick(6, 15)
        self.emit(
            side, "restart", "neutral", taker, start=(x, ty),
            qualifiers={"restart_type": "throw_in"},
        )  # fmt: skip
        self.carrier, self.ball = taker, (x, clamp(ty, 2, 98))

    def turnover_to(
        self, side: Side, pt: tuple[float, float], winner: Player | None = None
    ) -> None:
        self.new_possession(side)
        self.carrier = winner or self.nearest(side, pt)
        self.ball = pt

    # ---------------------------------------------------------- substitutions
    def process_subs(self) -> None:
        if self.scenario:
            for f in list(self.scenario.forced_subs):
                sec, team_id, out_id, in_id = f
                if self.clock >= sec:
                    self.scenario.forced_subs.remove(f)
                    self.substitute(self.side_of(team_id), out_id, in_id)
        for side in (self.home, self.away):
            while side.planned_subs and self.clock >= side.planned_subs[0]:
                side.planned_subs.pop(0)
                self.auto_sub(side)

    def auto_sub(self, side: Side) -> None:
        if side.subs_used >= MAX_SUBS:
            return
        weights = {"ATT": 3, "MID": 2, "DEF": 1, "GK": 0}
        cands = [
            (s, p) for s, p in side.players()
            if s.slot != "GK" and p.player_id not in side.subbed_on
        ]  # fmt: skip
        if not cands:
            return
        slot, out = self.rng.choices(cands, [weights[ROLE_GROUP[s.position]] for s, _ in cands])[0]
        bench = [p for p in side.bench if p.primary_position != "GK"]
        if not bench:
            return

        def fit(p: Player) -> float:
            if p.primary_position == slot.position:
                return 3 + overall(p) / 100
            if slot.position in p.secondary_positions:
                return 2 + overall(p) / 100
            same = ROLE_GROUP[p.primary_position] == ROLE_GROUP[slot.position]
            return (1 if same else 0) + overall(p) / 100

        self.substitute(side, out.player_id, max(bench, key=fit).player_id)

    def substitute(self, side: Side, out_id: str, in_id: str) -> None:
        slot = side.slot_of(out_id)
        incoming = next((p for p in side.bench if p.player_id == in_id), None)
        if slot is None or incoming is None or side.subs_used >= MAX_SUBS:
            return
        outgoing = side.on_pitch[slot.slot]
        side.on_pitch[slot.slot] = incoming
        side.bench.remove(incoming)
        side.subs_used += 1
        side.subbed_on.add(in_id)
        self.emit(
            side, "substitution", "neutral", outgoing, recipient=incoming, in_possession=False
        )
        if self.carrier and self.carrier.player_id == out_id:
            self.carrier = incoming

    # ------------------------------------------------------------------ step
    def step(self) -> None:
        side, opp = self.att, self.other(self.att)
        if self.carrier is None or side.slot_of(self.carrier.player_id) is None:
            self.carrier = self.nearest(side, self.ball, allow_gk=self.ball[0] < 15)
        p = self.carrier
        x, y = self.ball
        self.tick(1.5, 4.5)

        if self.force_header is not None:
            shooter, self.force_header = self.force_header, None
            if side.slot_of(shooter.player_id):
                return self.shot(side, opp, shooter, header=True)
        if self.force_cross:
            self.force_cross = False
            return self.cross(side, opp, p)

        is_gk = side.slot_of(p.player_id).slot == "GK"
        if not is_gk and self.rng.random() < 0.02 + (0.01 if x > 60 else 0):
            return self.foul(side, opp, p)

        pr = p.priors
        shot_w = 0.0
        if not is_gk and x >= 68:
            shot_w = ((x - 68) / 32) ** 1.5 * 0.36 * (0.6 + pr.finishing / 125)
            shot_w *= 1 - abs(y - 50) / 70
        take_on_w = 0.01
        if not is_gk and x > 35:
            take_on_w = 0.03 + 0.12 * pr.dribbling / 100
            if p.archetype in WIDE_ARCHETYPES:
                take_on_w *= 1.6
            if self.scenario and self.scenario.active(p.player_id, self.clock):
                take_on_w *= self.scenario.take_on_freq_mult
        carry_w = 0.0 if is_gk else 0.2
        actions = [self.pass_, self.carry, self.take_on, self.shot]
        action = self.rng.choices(actions, [1.0, carry_w, take_on_w, shot_w])[0]
        action(side, opp, p)

    # --------------------------------------------------------------- actions
    def pass_(self, side: Side, opp: Side, p: Player, cross: bool = False) -> None:
        x, y = self.ball
        shift = (x - 50) * 0.5
        options = []
        for s, mate in side.players():
            if mate.player_id == p.player_id or (s.slot == "GK" and x > 40):
                continue
            if cross:
                tx, ty = self.rng.uniform(86, 96), self.rng.uniform(35, 65)
                if ROLE_GROUP[s.position] not in ("ATT", "MID", "DEF") or s.slot == "GK":
                    continue
                w = 3.0 if ROLE_GROUP[s.position] == "ATT" else 1.0
            else:
                tx = clamp(s.x + shift + self.rng.gauss(0, 7), 2, 98)
                ty = clamp(s.y + self.rng.gauss(0, 7), 2, 98)
                d = math.hypot(tx - x, ty - y)
                w = math.exp(-d / 22) * (1 + max(0.0, tx - x) / 25) * (0.2 if d < 4 else 1)
                if self.scenario and self.scenario.active(mate.player_id, self.clock):
                    w *= self.scenario.pass_to_focus_mult
            options.append((mate, tx, ty, w))
        mate, tx, ty, _ = self.rng.choices(options, [o[3] for o in options])[0]
        d = math.hypot(tx - x, ty - y)
        if cross:
            p_ok = 0.3 + p.priors.passing / 400
        else:
            p_ok = 1.0 - d / 160 + (p.priors.passing - 70) / 250
            p_ok -= (0.10 if tx > 83 else 0) + (opp.avg_defending() - 70) / 300
        p_ok = clamp(p_ok, 0.25, 0.97)
        quals = {}
        if cross or (x > 75 and (y < 20 or y > 80) and tx > 83):
            quals["cross"] = True
        if tx - x > 25:
            quals["through_ball"] = True
        ok = self.rng.random() < p_ok
        self.emit(
            side, "pass", "success" if ok else "fail", p, start=(x, y), end=(tx, ty),
            recipient=mate, qualifiers=quals,
        )  # fmt: skip
        if ok:
            self.carrier, self.ball = mate, (tx, ty)
            if quals.get("cross") and tx > 85 and self.rng.random() < 0.55:
                self.force_header = mate
            return
        mx, my = mirror(tx, ty)
        r = self.rng.random()
        if r < 0.5:
            interceptor = self.nearest(opp, (mx, my))
            self.turnover_to(opp, (mx, my), interceptor)
            self.tick(0, 1)
            self.emit(opp, "interception", "success", interceptor, start=(mx, my))
        elif r < 0.75:
            self.throw_in(opp, mx, my)
        else:
            self.turnover_to(opp, (mx, my))

    def cross(self, side: Side, opp: Side, p: Player) -> None:
        self.pass_(side, opp, p, cross=True)

    def carry(self, side: Side, opp: Side, p: Player) -> None:
        x, y = self.ball
        end = (clamp(x + self.rng.uniform(3, 12), 0, 99), clamp(y + self.rng.gauss(0, 4), 1, 99))
        ok = self.rng.random() < clamp(0.93 + (p.priors.dribbling - 70) / 300, 0.8, 0.98)
        self.emit(side, "carry", "success" if ok else "fail", p, start=(x, y), end=end)
        if ok:
            self.ball = end
            return
        self.win_ball_by_tackle(opp, p, end)

    def take_on(self, side: Side, opp: Side, p: Player) -> None:
        x, y = self.ball
        defender = self.nearest(opp, mirror(x, y))
        if self.scenario and self.scenario.active(p.player_id, self.clock):
            marker = self.scenario.marker_id
            if marker and opp.slot_of(marker) is not None:
                defender = next(q for _, q in opp.players() if q.player_id == marker)
        diff = p.priors.dribbling - defender.priors.defending
        p_ok = 0.85 / (1 + math.exp(-diff / 12))
        if self.scenario and self.scenario.active(p.player_id, self.clock):
            p_ok *= self.scenario.take_on_success_mult
        ok = self.rng.random() < p_ok
        end = (clamp(x + self.rng.uniform(4, 10), 0, 99), clamp(y + self.rng.gauss(0, 5), 1, 99))
        self.emit(
            side, "take_on", "success" if ok else "fail", p, start=(x, y),
            end=end if ok else None, opponent=defender,
        )  # fmt: skip
        if ok:
            self.ball = end
            return
        self.win_ball_by_tackle(opp, p, (x, y), defender)

    def win_ball_by_tackle(
        self, opp: Side, loser: Player, pt: tuple[float, float], tackler: Player | None = None
    ) -> None:
        mpt = mirror(*pt)
        tackler = tackler or self.nearest(opp, mpt)
        self.turnover_to(opp, mpt, tackler)
        self.emit(opp, "tackle", "success", tackler, start=mpt, opponent=loser)

    def shot(self, side: Side, opp: Side, p: Player, header: bool = False) -> None:
        x, y = self.ball
        if header:
            body = "head"
        elif p.foot == "both":
            body = self.rng.choice(["right_foot", "left_foot"])
        else:
            body = f"{p.foot}_foot"
        xg = illustrative_xg(x, y, header)
        gk = opp.gk()
        gk_factor = 1.15 - (gk.priors.goalkeeping / 100 * 0.3 if gk else 0)
        p_goal = clamp(xg * (0.7 + p.priors.finishing / 100 * 0.6) * gk_factor, 0, 0.95)
        r = self.rng.random()
        if r < p_goal:
            outcome = "goal"
        else:
            outcome = self.rng.choices(["blocked", "saved", "off_target"], [0.28, 0.33, 0.39])[0]
        quals = {"xg": xg}
        prev = self.events[-1] if self.events else None
        if (
            prev
            and prev.event_type == "pass"
            and prev.outcome == "success"
            and prev.recipient_id == p.player_id
            and prev.possession_id == self.possession_id
        ):
            quals["assist_event_id"] = prev.event_id
        self.emit(side, "shot", outcome, p, start=(x, y), end=(100, 50), body_part=body,
                  qualifiers=quals)  # fmt: skip
        if outcome == "goal":
            self.score[side.team_id] += 1
            self.tick(35, 60)
            self.kickoff(opp)
        elif outcome == "saved":
            if self.rng.random() < 0.35:
                self.corner(side)
            else:
                keeper = opp.gk() or self.nearest(opp, (6, 50))
                self.turnover_to(opp, (6.0, 50.0), keeper)
        elif outcome == "off_target":
            self.goal_kick(opp)
        else:  # blocked
            if self.rng.random() < 0.5:
                self.corner(side)
            else:
                self.turnover_to(opp, mirror(x, y))

    def foul(self, side: Side, opp: Side, victim: Player) -> None:
        x, y = self.ball
        offender = self.nearest(opp, mirror(x, y))
        foul_ev = self.emit(opp, "foul", "neutral", offender, start=mirror(x, y), opponent=victim)
        r = self.rng.random()
        card = None
        if r < 0.005:
            card = "red"
        elif r < 0.17:
            card = "second_yellow" if offender.player_id in opp.yellows else "yellow"
        if card:
            self.tick(5, 15)
            card_ev = self.emit(opp, "card", "neutral", offender, qualifiers={"card": card})
            foul_ev.qualifiers["card_event_id"] = card_ev.event_id
            if card == "yellow":
                opp.yellows.add(offender.player_id)
            else:
                slot = opp.slot_of(offender.player_id)
                if slot is not None:
                    opp.on_pitch[slot.slot] = None
        self.tick(10, 30)
        self.emit(
            side, "restart", "neutral", victim, start=(x, y),
            qualifiers={"restart_type": "free_kick"},
        )  # fmt: skip
        self.carrier = victim
