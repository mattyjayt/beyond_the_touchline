"""Pure duel model (spec 3.2): simulator model, uncalibrated."""

import pytest

from app.models.reference import Player
from app.sim.duel import (
    MODEL_VERSION,
    DuelContext,
    DuelTerms,
    duel_prob,
    fatigue,
    p_recover,
)
from app.sim.squads import load_reference


def _ctx(**kw) -> DuelContext:
    base = {
        "isolated": False,
        "transition": False,
        "defender_on_yellow": False,
        "cover_near": False,
        "touch": 25.0,
        "att_minutes_on": 30.0,
        "def_minutes_on": 30.0,
    }
    return DuelContext(**(base | kw))


def _player(pid: str, **phys) -> Player:
    physical = {
        "top_speed_kmh": 33.0,
        "accel_ms2": 7.0,
        "agility_idx": 70,
        "stamina_idx": 70,
        "stance_idx": 50,
        "height_cm": 180,
    }
    return Player(
        player_id=pid,
        team_id="T-X",
        display_name=pid,
        shirt_number=1,
        primary_position="RW",
        archetype="test",
        priors={
            "passing": 70,
            "dribbling": 75,
            "finishing": 70,
            "defending": 70,
            "physical": 70,
            "goalkeeping": 10,
        },
        physical=physical | phys,
    )


def test_model_version():
    assert MODEL_VERSION == "duel-v2"


def test_fatigue_flat_before_55():
    assert fatigue(50, 60) == 1.0
    assert fatigue(85, 60) == pytest.approx(1 - 0.004 * 30 * 40 / 20)
    assert fatigue(85, 60) == pytest.approx(0.76)


def test_burst_favours_faster_accelerator():
    att = _player("A")
    slow = _player("D1", accel_ms2=6.5)
    fast = _player("D2", accel_ms2=7.6)
    c = _ctx()
    assert duel_prob(att, slow, c, 0.5).p_beat > duel_prob(att, fast, c, 0.5).p_beat


def test_top_speed_only_affects_recovery():
    att = _player("A")
    d1 = _player("D1", top_speed_kmh=31.0)
    d2 = _player("D2", top_speed_kmh=36.0)
    c = _ctx()
    t1, t2 = duel_prob(att, d1, c, 0.5), duel_prob(att, d2, c, 0.5)
    assert t1.p_beat == t2.p_beat
    assert t1.p_recover != t2.p_recover
    assert t2.p_recover > t1.p_recover


def test_square_stance_concedes():
    att, dfn, c = _player("A"), _player("D"), _ctx()
    assert duel_prob(att, dfn, c, 0.0).p_beat > duel_prob(att, dfn, c, 1.0).p_beat


def test_clamps():
    # Extreme attacker-favoured duel, slow defender: p_beat at its ceiling, recovery at floor.
    strong = _player("A", accel_ms2=7.9, agility_idx=100, top_speed_kmh=45.0)
    strong.priors.dribbling = 100
    weak = _player("D", accel_ms2=6.0, agility_idx=0, top_speed_kmh=20.0)
    weak.priors.defending = 0
    hi = duel_prob(
        strong, weak, _ctx(isolated=True, transition=True, defender_on_yellow=True, script=50), 0.0
    )
    assert 0.05 <= hi.p_beat <= 0.9
    assert hi.p_beat > 0.8
    assert hi.p_recover == 0.03
    # Extreme defender-favoured duel, fast defender: p_beat at its floor, recovery at ceiling.
    lo = duel_prob(weak, strong, _ctx(cover_near=True, script=-50), 1.0)
    assert lo.p_beat == 0.05
    assert lo.p_recover == 0.35


def test_p_recover_formula():
    assert p_recover(33.0, 33.0) == pytest.approx(0.18)
    assert p_recover(100.0, 0.0) == 0.35
    assert p_recover(0.0, 100.0) == 0.03


def test_script_term_reported():
    att, dfn = _player("A"), _player("D")
    base = duel_prob(att, dfn, _ctx(), 0.5)
    scripted = duel_prob(att, dfn, _ctx(script=8), 0.5)
    assert scripted.script == 8
    assert "script" in scripted.as_qualifier()
    assert scripted.p_beat > base.p_beat
    assert scripted.z > base.z


def test_context_terms_direction():
    att, dfn = _player("A"), _player("D")
    base = duel_prob(att, dfn, _ctx(), 0.5).ctx
    assert duel_prob(att, dfn, _ctx(isolated=True), 0.5).ctx == pytest.approx(base + 8, abs=1e-3)
    assert duel_prob(att, dfn, _ctx(transition=True), 0.5).ctx == pytest.approx(base + 6, abs=1e-3)
    assert duel_prob(att, dfn, _ctx(defender_on_yellow=True), 0.5).ctx == pytest.approx(
        base + 4, abs=1e-3
    )
    assert duel_prob(att, dfn, _ctx(cover_near=True), 0.5).ctx == pytest.approx(base - 6, abs=1e-3)
    # touchline helps the defender: touch 0 gives -4, touch 50 gives 0
    near = duel_prob(att, dfn, _ctx(touch=0.0), 0.5).ctx
    far = duel_prob(att, dfn, _ctx(touch=50.0), 0.5).ctx
    assert far - near == pytest.approx(4.0, abs=1e-3)


def test_fatigue_hurts_defender():
    att = _player("A")
    dfn = _player("D", stamina_idx=40)
    fresh = duel_prob(att, dfn, _ctx(def_minutes_on=30), 0.5)
    tired = duel_prob(att, dfn, _ctx(def_minutes_on=90), 0.5)
    assert tired.p_beat > fresh.p_beat


def test_terms_rounded_and_qualifier():
    t = duel_prob(_player("A"), _player("D"), _ctx(), 0.4321)
    assert isinstance(t, DuelTerms)
    q = t.as_qualifier()
    assert set(q) == {
        "tech", "burst", "agil", "stance", "touch", "ctx", "script", "z", "p_beat", "p_recover",
    }  # fmt: skip
    for v in q.values():
        assert v == round(v, 3)


def test_deterministic():
    a = duel_prob(_player("A"), _player("D"), _ctx(), 0.5)
    b = duel_prob(_player("A"), _player("D"), _ctx(), 0.5)
    assert a == b


def test_doku_beats_frimpong_more_than_szoboszlai():
    _, players = load_reference(2026)
    by_id = {p.player_id: p for p in players}
    doku, frimpong, szob = by_id["P-MCI-11"], by_id["P-LIV-30"], by_id["P-LIV-08"]
    c = _ctx(att_minutes_on=0, def_minutes_on=0)

    def p(d: Player) -> float:
        return duel_prob(doku, d, c, d.physical.stance_idx / 100).p_beat

    assert p(frimpong) > p(szob)
