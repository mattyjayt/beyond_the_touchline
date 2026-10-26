"""Subs-advisor contracts (spec §4, §6). Everything here is derived from simulated events.

Duel outcomes are from the DEFENDER's point of view: ``won`` = the attacker's take-on
failed, ``recovered`` = beaten but the defender's recovery tackle won it straight back
(also a defender win), ``lost`` = beaten without recovery, ``foul`` = the defender fouled
the attacker. Win rates are fractions in [0, 1].
"""

from typing import Literal

from pydantic import BaseModel, Field

DuelOutcome = Literal["won", "lost", "recovered", "foul"]
Confidence = Literal["low", "medium", "high"]


class DuelPoint(BaseModel):
    event_id: str
    sec: int
    x: float  # duel location in the ATTACKER's frame (x: towards their goal)
    y: float
    outcome: DuelOutcome
    attacker_id: str
    defender_id: str
    terms: dict = {}  # stored `qualifiers.duel` of the take-on, quoted, never recomputed


class RollingPoint(BaseModel):
    sec: int
    win_pct: float | None = Field(default=None, ge=0, le=1)  # None when n == 0
    n: int


class DuelLedger(BaseModel):
    attacker_id: str
    defender_ids: list[str]
    duels: int
    won: int
    lost: int
    recoveries: int
    fouls: int
    win_pct: float | None = Field(default=None, ge=0, le=1)
    window_sec: int  # asof - since + 1: the span the counts cover
    beaten: int  # lost without recovery (outright or then fouled), as in the hot-duel trigger
    beaten_per_10: float | None = None  # beaten * 600 / window_sec; None if window_sec <= 0
    channel_shots: int
    channel_xg: float
    defender_rating_swing: float | None = None
    confidence: Confidence
    points: list[DuelPoint] = []
    rolling: list[RollingPoint] = []
    evidence_event_ids: list[str] = []
    synthetic: Literal[True] = True


class HotDuel(BaseModel):
    team_id: str  # the defending team
    defender_id: str  # current occupant of the slot
    defender_slot: str
    attacker_id: str
    beaten_20m: int
    win_pct_20m: float | None = Field(default=None, ge=0, le=1)
    n_20m: int
    first_fired_sec: int | None = None
    synthetic: Literal[True] = True


class SwapImpact(BaseModel):
    swap_sec: int
    before: DuelLedger
    after: DuelLedger
    synthetic: Literal[True] = True


class RaceCurve(BaseModel):
    player_id: str
    name: str
    t: list[float]  # seconds from the trigger, 0..horizon
    d: list[float]  # metres covered at each t
    t5m: float  # seconds to 5 m, reaction included
    d1s: float  # metres at 1 s
    d2s: float  # metres at 2 s


class RaceResult(BaseModel):
    curves: list[RaceCurve]
    gap1s: dict[str, float]  # metres vs the first curve (the tormentor) at 1 s
    gap2s: dict[str, float]
    reaction_s: float
    label: str
    synthetic: Literal[True] = True


class Move(BaseModel):
    """One leg of an option: ``on`` (bench -> slot), ``off`` (slot -> bench), ``move``."""

    player_id: str
    from_slot: str | None
    to_slot: str | None
    kind: Literal["on", "off", "move"]


class OptionDims(BaseModel):
    """Option vs KEEP on six policy dimensions, each in [-1, 1] (positive = better).

    L live form vs expected · F fit · M projected duel win vs current · A attacking upside ·
    G game state · R risk (negative = riskier).
    """

    L: float = Field(ge=-1, le=1)
    F: float = Field(ge=-1, le=1)
    M: float = Field(ge=-1, le=1)
    A: float = Field(ge=-1, le=1)
    G: float = Field(ge=-1, le=1)
    R: float = Field(ge=-1, le=1)


class ImportanceItem(BaseModel):
    """One ranked variable from the duel study (methodology demo: mirrors the generator)."""

    var_id: str
    name: str
    family: str
    importance: float
    rank: int
