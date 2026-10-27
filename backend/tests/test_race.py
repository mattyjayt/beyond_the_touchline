"""Sprint race (spec 4, services/race.py): simulated 0-3 s acceleration curves."""

import pytest

from app.config import get_settings
from app.services.race import race
from app.sim.squads import load_reference

DOKU, FRIMPONG, SZOBOSZLAI = "P-MCI-11", "P-LIV-30", "P-LIV-08"


@pytest.fixture(scope="module")
def players():
    _, ps = load_reference(get_settings().sim_seed)
    return {p.player_id: p for p in ps}


def test_zero_before_reaction(players):
    res = race([players[DOKU], players[FRIMPONG]])
    for c in res.curves:
        assert all(d == 0 for t, d in zip(c.t, c.d, strict=True) if t <= 0.25)
        assert c.d[-1] > 0
        assert c.t[0] == 0 and c.t[-1] == pytest.approx(3.0)


def test_higher_accel_leads_at_1s_lower_top_speed(players):
    res = race([players[DOKU], players[FRIMPONG], players[SZOBOSZLAI]])
    by_id = {c.player_id: c for c in res.curves}
    assert by_id[SZOBOSZLAI].d1s > by_id[FRIMPONG].d1s
    # gaps are relative to the first player (the tormentor)
    assert res.gap1s[DOKU] == 0
    assert res.gap1s[FRIMPONG] == pytest.approx(
        round(by_id[FRIMPONG].d1s - by_id[DOKU].d1s, 2), abs=0.011
    )


def test_t5m_monotonic_in_accel(players):
    base = players[FRIMPONG]
    times = []
    for accel in (6.4, 7.0, 7.6):
        p = base.model_copy(
            update={"physical": base.physical.model_copy(update={"accel_ms2": accel})}
        )
        times.append(race([p]).curves[0].t5m)
    assert times[0] > times[1] > times[2]


def test_distance_monotonic(players):
    for c in race([players[DOKU]]).curves:
        assert all(b >= a for a, b in zip(c.d, c.d[1:], strict=False))


def test_label_mentions_model(players):
    res = race([players[DOKU]])
    assert "simulated" in res.label.lower()
    assert res.reaction_s == 0.25 and res.synthetic is True
