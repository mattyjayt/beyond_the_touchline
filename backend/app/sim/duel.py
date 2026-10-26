"""Pure 1v1 duel model (spec 3.2). Simulator model, uncalibrated.

No I/O, no randomness: the caller draws ``stance`` and passes it in. Shared by the engine's
take-on, the study and the substitution advisor. Tech, burst and agility use 0-100 indices;
the recovery roll uses top speed in km/h directly.
"""

import math
from dataclasses import dataclass

from app.models.reference import Player

MODEL_VERSION = "duel-v2"
# Calibration offset on z (pre-registered): the smallest integer that puts league-wide
# simulated take-on success in [0.45, 0.52]. Simulator model, uncalibrated against real data.
DUEL_BASELINE = 12


@dataclass(frozen=True)
class DuelContext:
    isolated: bool  # no defender team-mate slot within 15u
    transition: bool  # attacking/inverted full-back and possession < 8 s old
    defender_on_yellow: bool
    cover_near: bool  # covering team-mate within 10u
    touch: float  # distance of duel point to nearest touchline, 0-50
    att_minutes_on: float
    def_minutes_on: float
    script: float = 0.0  # demo scenario bonus, only while the marker is in the marked slot


@dataclass(frozen=True)
class DuelTerms:
    tech: float
    burst: float
    agil: float
    stance: float
    touch: float
    ctx: float
    script: float
    z: float
    p_beat: float
    p_recover: float

    def as_qualifier(self) -> dict:
        return {
            "tech": self.tech,
            "burst": self.burst,
            "agil": self.agil,
            "stance": self.stance,
            "touch": self.touch,
            "ctx": self.ctx,
            "script": self.script,
            "z": self.z,
            "p_beat": self.p_beat,
            "p_recover": self.p_recover,
        }


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def fatigue(minutes_on: float, stamina_idx: int) -> float:
    """Multiplier on accel and agility indices; flat until minute 55."""
    return 1 - 0.004 * max(0.0, minutes_on - 55) * (100 - stamina_idx) / 20


def p_recover(def_kmh: float, att_kmh: float) -> float:
    """Chance the defender recovers after being beaten (top speeds in km/h)."""
    return _clamp(0.10 + 0.04 * (def_kmh - att_kmh + 2), 0.03, 0.35)


def duel_prob(att: Player, dfn: Player, c: DuelContext, stance: float) -> DuelTerms:
    """Probability the attacker beats the defender, with every term reported."""
    if att.priors is None or att.physical is None or dfn.priors is None or dfn.physical is None:
        raise ValueError("duel_prob needs priors and physical profiles on both players")
    a_phys, d_phys = att.physical, dfn.physical
    fat_a = fatigue(c.att_minutes_on, a_phys.stamina_idx)
    fat_d = fatigue(c.def_minutes_on, d_phys.stamina_idx)
    acc_a, acc_d = a_phys.accel_idx * fat_a, d_phys.accel_idx * fat_d
    agil_a, agil_d = a_phys.agility_idx * fat_a, d_phys.agility_idx * fat_d

    tech = att.priors.dribbling - (0.7 * dfn.priors.defending + 0.3 * agil_d)
    burst = acc_a - acc_d
    agil = agil_a - agil_d

    ctx = 6 * (1 - stance) - 4 * (1 - _clamp(c.touch, 0.0, 50.0) / 50)
    if c.isolated:
        ctx += 8
    if c.transition:
        ctx += 6
    if c.defender_on_yellow:
        ctx += 4
    if c.cover_near:
        ctx -= 6

    z = (0.5 * tech + 0.4 * burst + 0.1 * agil + ctx + c.script - DUEL_BASELINE) / 10
    p_beat = _clamp(0.85 / (1 + math.exp(-z)), 0.05, 0.9)
    p_rec = p_recover(d_phys.top_speed_kmh, a_phys.top_speed_kmh)

    return DuelTerms(
        tech=round(tech, 3),
        burst=round(burst, 3),
        agil=round(agil, 3),
        stance=round(stance, 3),
        touch=round(c.touch, 3),
        ctx=round(ctx, 3),
        script=round(c.script, 3),
        z=round(z, 3),
        p_beat=round(p_beat, 3),
        p_recover=round(p_rec, 3),
    )
