"""duel-v3 (Phase B pre-registration items 2-4): burst in metres, one agility term, fatigue on A0."""

import math

import pytest

from app.models import PhysicalProfile, Player, PlayerPriors
from app.sim import sprint
from app.sim.duel import BURST_BETA, MODEL_VERSION, DuelContext, duel_prob, fatigue

NEUTRAL = DuelContext(False, False, False, False, 25.0, 30, 30)


def player(pid: str, a0: float = 7.0, kmh: float = 33.0, agility: int = 70, stamina: int = 75):
    return Player(
        player_id=pid, team_id="T-X", display_name=pid, shirt_number=1, primary_position="RB",
        secondary_positions=[], foot="right", archetype="balanced",
        priors=PlayerPriors(passing=60, dribbling=70, finishing=60, defending=70, physical=60,
                            goalkeeping=20),
        physical=PhysicalProfile(top_speed_kmh=kmh, accel_ms2=a0, agility_idx=agility,
                                 stamina_idx=stamina, stance_idx=50, height_cm=180),
    )  # fmt: skip


def test_version_bumped():
    assert MODEL_VERSION == "duel-v3"


def test_half_a_metre_per_second_squared_is_worth_odds_x_1_5():
    dfn = player("D")
    fast, slow = player("A1", a0=7.4), player("A2", a0=6.9)
    dz = duel_prob(fast, dfn, NEUTRAL, 0.5).z - duel_prob(slow, dfn, NEUTRAL, 0.5).z
    assert math.exp(dz) == pytest.approx(1.5, abs=0.05)


def test_beta_is_derived_not_tuned():
    gap = sprint.distance(1.0, 33.0, 7.4) - sprint.distance(1.0, 33.0, 6.9)
    assert BURST_BETA == pytest.approx(math.log(1.5) / gap, rel=1e-6)


def test_burst_is_the_one_second_gap_in_metres():
    att, dfn = player("A", a0=7.6, kmh=34.0), player("D", a0=7.0, kmh=36.0)
    t = duel_prob(att, dfn, NEUTRAL, 0.5)
    expected = sprint.distance(1.0, 34.0, 7.6) - sprint.distance(1.0, 36.0, 7.0)
    assert t.burst == pytest.approx(expected, abs=1e-3)


def test_defender_agility_enters_once():
    att = player("A")
    t1 = duel_prob(att, player("D1", agility=50), NEUTRAL, 0.5)
    t2 = duel_prob(att, player("D2", agility=90), NEUTRAL, 0.5)
    assert t1.tech == t2.tech  # no agility share inside the technique term
    assert t1.agil - t2.agil == pytest.approx(40)


def test_fatigue_costs_even_a_slow_starter():
    att = player("A")
    fresh = DuelContext(False, False, False, False, 25.0, 30, 30)
    tired = DuelContext(False, False, False, False, 25.0, 30, 90)
    slow_def = player("D", a0=6.0, stamina=50)
    assert duel_prob(att, slow_def, tired, 0.5).burst > duel_prob(att, slow_def, fresh, 0.5).burst
    assert fatigue(90, 50) < 1


def test_time_to_5m_uses_the_sprint_model():
    p = PhysicalProfile(top_speed_kmh=33.0, accel_ms2=7.0, agility_idx=70, stamina_idx=75,
                        stance_idx=50, height_cm=180)  # fmt: skip
    assert p.time_0_5m_s == pytest.approx(sprint.time_to(5.0, 33.0, 7.0), abs=0.005)
