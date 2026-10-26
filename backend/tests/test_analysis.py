"""Variable catalogue + duel study (Task 10). Methodology demo: importance mirrors the generator."""

import pytest

from app.analysis.catalogue import FAMILIES, STUDY_IDS, VARIABLES, research_rows
from app.analysis.duel_study import build_features, run_study
from app.config import get_settings
from app.sim.duel import DuelContext
from app.sim.squads import load_reference


@pytest.fixture(scope="module")
def small():
    return run_study(2026, 3000)


def test_catalogue_has_100_plus_unique_ids():
    ids = [v.id for v in VARIABLES]
    assert len(ids) >= 100
    assert len(ids) == len(set(ids))


def test_every_family_present():
    assert {v.family for v in VARIABLES} == set(FAMILIES)


def test_research_rows_come_from_the_report():
    rows = research_rows()
    assert len(rows) == 108
    assert rows[1]["name"] == "Season-peak top speed"
    assert "29–37.4" in rows[1]["range"]
    # our own variables cite report rows for their real-world range
    top = next(v for v in VARIABLES if v.id == "phy.def_top_speed_kmh")
    assert top.real_range and top.ref


def test_build_features_keys_are_study_variable_ids():
    _, players = load_reference(get_settings().sim_seed)
    by_id = {p.player_id: p for p in players}
    ctx = DuelContext(True, False, False, False, 12.0, 70, 70)
    feats = build_features(by_id["P-MCI-11"], by_id["P-LIV-30"], ctx, 0.4)
    assert set(feats) == set(STUDY_IDS)
    assert feats["phy.accel_idx_diff"] > 0  # Doku out-accelerates Frimpong


def test_ranked_vars_are_causal(small):
    causal = {v.id for v in VARIABLES if v.engine_causal}
    assert {r.var_id for r in small.ranked} <= causal
    assert [r.rank for r in small.ranked] == list(range(1, len(small.ranked) + 1))


def test_study_small_run(small):
    assert small.auc > 0.6
    assert len(small.ranked) >= 20
    top5 = {r.var_id for r in small.ranked[:5]}
    assert {"phy.accel_idx_diff", "duel.burst"} & top5


def test_top_speed_ranks_below_acceleration(small):
    # the generator's thesis: top speed only drives recovery, not who wins the first step
    rank = {r.var_id: r.rank for r in small.ranked}
    assert rank["duel.burst"] < rank["phy.speed_kmh_diff"]


def test_study_deterministic(small):
    again = run_study(2026, 3000)
    assert [r.var_id for r in again.ranked] == [r.var_id for r in small.ranked]
    assert again.auc == small.auc
