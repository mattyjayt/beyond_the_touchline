"""Variable catalogue + duel study (Task 10). Methodology demo: importance mirrors the generator."""

import pytest

from app.analysis.catalogue import FAMILIES, STUDY_IDS, VARIABLES, research_rows
from app.analysis.duel_study import GROUPS, build_features, run_study
from app.config import get_settings
from app.sim.duel import DuelContext
from app.sim.squads import load_reference


@pytest.fixture(scope="module")
def small():
    return run_study(2026, 2000, seeds=3)


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


def test_ranked_items_are_groups_of_causal_primitives(small):
    causal = {v.id for v in VARIABLES if v.engine_causal}
    for r in small.ranked:
        assert r.var_id in GROUPS
        assert set(GROUPS[r.var_id]["vars"]) <= causal
    assert [r.rank for r in small.ranked] == list(range(1, len(small.ranked) + 1))


def test_attacker_and_defender_acceleration_share_one_group():
    acc = GROUPS["group.acceleration"]["vars"]
    assert "phy.att_accel_ms2" in acc and "phy.def_accel_ms2" in acc
    members = [v for g in GROUPS.values() for v in g["vars"]]
    assert len(members) == len(set(members))  # each primitive in exactly one group


def test_derived_terms_are_not_fitted():
    fitted = {v for g in GROUPS.values() for v in g["vars"]}
    assert not any(v.startswith("duel.") for v in fitted)
    assert "phy.def_time_0_5m_s" not in fitted and "phy.accel_idx_diff" not in fitted
    by_id = {v.id: v for v in VARIABLES}
    assert not by_id["phy.def_time_0_5m_s"].engine_causal  # derived from accel, never read


def test_ranks_carry_intervals_over_seeds(small):
    assert small.seeds == [2026, 2027, 2028]
    for r in small.ranked:
        assert r.rank_lo <= r.rank <= r.rank_hi


def test_model_auc_is_reported_against_the_oracle(small):
    assert 0.6 < small.auc <= small.oracle_auc + 0.02


def test_acceleration_outranks_pace(small):
    rank = {r.var_id: r.rank for r in small.ranked}
    assert rank["group.acceleration"] < rank["group.pace"]


def test_study_deterministic(small):
    again = run_study(2026, 2000, seeds=3)
    assert [r.var_id for r in again.ranked] == [r.var_id for r in small.ranked]
    assert again.auc == small.auc
