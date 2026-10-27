import hashlib
import json
import statistics

import pytest

from app.models import PhysicalProfile
from app.sim import squads
from app.sim.squads import load_reference

SEED = 2026


def _players(seed: int = SEED) -> dict:
    _, players = load_reference(seed)
    return {p.player_id: p for p in players}


def test_profile_indices_map_linearly():
    prof = PhysicalProfile(
        top_speed_kmh=33,
        accel_ms2=6.95,
        agility_idx=50,
        stamina_idx=50,
        stance_idx=50,
        height_cm=180,
    )
    assert prof.speed_idx == 50
    assert prof.accel_idx == 50
    from app.sim.sprint import time_to

    assert prof.time_0_5m_s == round(time_to(5.0, 33.0, 6.95), 2)  # one model: the sprint race


def test_indices_clamped():
    fast = PhysicalProfile(
        top_speed_kmh=40,
        accel_ms2=9.0,
        agility_idx=50,
        stamina_idx=50,
        stance_idx=50,
        height_cm=180,
    )
    slow = fast.model_copy(update={"top_speed_kmh": 25.0, "accel_ms2": 5.0})
    assert fast.speed_idx == 100 and fast.accel_idx == 100
    assert slow.speed_idx == 0 and slow.accel_idx == 0


def test_all_players_have_plausible_physical():
    players = _players()
    assert players
    for p in players.values():
        assert p.physical is not None, p.player_id
        assert 29.0 <= p.physical.top_speed_kmh <= 37.4, p.player_id
        assert 6.0 <= p.physical.accel_ms2 <= 7.9, p.player_id


def test_speed_and_accel_correlate():
    outfield = [p.physical for p in _players().values() if p.primary_position != "GK"]
    speeds = [x.top_speed_kmh for x in outfield]
    accels = [x.accel_ms2 for x in outfield]
    ms, ma = statistics.fmean(speeds), statistics.fmean(accels)
    cov = sum((s - ms) * (a - ma) for s, a in zip(speeds, accels, strict=True))
    var_s = sum((s - ms) ** 2 for s in speeds)
    var_a = sum((a - ma) ** 2 for a in accels)
    r = cov / (var_s * var_a) ** 0.5
    assert r > 0.3


def test_demo_story_profiles_pinned():
    players = _players()

    def phys(pid: str) -> PhysicalProfile:
        p = players[pid].physical
        assert p is not None
        return p

    doku = phys("P-MCI-11")
    assert doku.top_speed_kmh == 35.1
    assert doku.accel_idx >= 90
    assert phys("P-LIV-30").top_speed_kmh > phys("P-LIV-08").top_speed_kmh
    assert phys("P-LIV-08").accel_ms2 > phys("P-LIV-30").accel_ms2
    assert phys("P-LIV-08").stance_idx > phys("P-LIV-30").stance_idx < phys("P-LIV-02").stance_idx
    bradley = phys("P-LIV-12")
    assert (bradley.top_speed_kmh, bradley.accel_ms2, bradley.stamina_idx) == (34.6, 7.2, 82)


def test_load_reference_deterministic():
    a, b = _players(SEED), _players(SEED)
    assert a.keys() == b.keys()
    assert all(a[k].physical == b[k].physical for k in a)


def test_priors_stream_unchanged_by_physical(monkeypatch):
    # priors/strength use their own RNG stream; adding physical must not shift them.
    # Hash captured before the physical profile was introduced. Demo prior pins are applied
    # after sampling, so switching them off must give back the original stream.
    monkeypatch.setattr(squads, "PINNED_PRIORS", {})
    teams, players = load_reference(SEED)
    payload = [p.priors.model_dump() for p in players if p.priors] + [
        t.strength_index for t in teams
    ]
    digest = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
    assert digest == "0751e900dbc6c4e1bb8f2bbbf693e8c56c408e6dfd11d833e0b1d81d13bb52f6"


def test_physical_roundtrips_through_db(tmp_path):
    from app import db

    teams, players = load_reference(SEED)
    conn = db.connect(tmp_path / "t.db")
    db.write_reference(conn, teams, players)
    conn.commit()
    back = {p.player_id: p for p in db.read_players(conn)}
    assert back["P-MCI-11"].physical == _players()["P-MCI-11"].physical
    assert all(p.physical is not None for p in back.values())


# ------------------------------------------- Phase B item 5: sampling hygiene
def test_accel_means_follow_the_research_by_position():
    from app.sim.squads import A0_MEAN_MS2, PINNED_PHYSICAL

    _, players = load_reference(SEED)
    by_bucket: dict[str, list[float]] = {}
    for p in players:
        if p.player_id in PINNED_PHYSICAL:
            continue
        b = squads.PHYS_BUCKET[p.primary_position]
        by_bucket.setdefault(b, []).append(p.physical.accel_ms2)
    for b, vals in by_bucket.items():
        if len(vals) >= 15:
            assert statistics.mean(vals) == pytest.approx(A0_MEAN_MS2[b], abs=0.15), b


def test_pinned_values_are_validated():
    import pydantic

    from app.models import PhysicalProfile as PP

    good = PP(top_speed_kmh=33, accel_ms2=7, agility_idx=50, stamina_idx=50, stance_idx=50,
              height_cm=180)  # fmt: skip
    with pytest.raises(pydantic.ValidationError):
        squads.apply_pin(good, {"accel_ms2": 99})
