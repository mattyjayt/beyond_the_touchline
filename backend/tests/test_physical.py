import hashlib
import json
import statistics

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
    assert prof.time_0_5m_s == round((10 / 6.95) ** 0.5 + 0.25, 2)


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
