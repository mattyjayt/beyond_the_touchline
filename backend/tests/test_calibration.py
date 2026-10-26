"""Duel-model calibration (pre-registered, see the plan ledger): league-wide targets and model
projections only. Nothing here looks at demo outcomes after the swap."""

from itertools import product

import pytest

from app.config import get_settings
from app.sim.duel import DUEL_BASELINE, DuelContext, duel_prob
from app.sim.engine import GENERATOR_VERSION
from app.sim.generate import first_trigger, simulate_history
from app.sim.squads import load_reference

DOKU, FRIMPONG, SZOBOSZLAI = "P-MCI-11", "P-LIV-30", "P-LIV-08"


@pytest.fixture(scope="module")
def reference():
    teams, players = load_reference(get_settings().sim_seed)
    squads = {t.team_id: [p for p in players if p.team_id == t.team_id] for t in teams}
    return {t.team_id: t for t in teams}, squads, {p.player_id: p for p in players}


@pytest.fixture(scope="module")
def historical(reference):
    teams, squads, _ = reference
    return simulate_history(teams, squads, get_settings().sim_seed)


def test_versions_bumped_for_calibration():
    assert GENERATOR_VERSION == "sim-v0.3"
    assert DUEL_BASELINE > 0


def test_frimpong_defending_is_modest(reference):
    # spec 3.1: "modest defending"
    assert reference[2][FRIMPONG].priors.defending == 68


def test_league_take_on_success_is_realistic(historical):
    take_ons = [e for _, _, events in historical for e in events if e.event_type == "take_on"]
    rate = sum(e.outcome == "success" for e in take_ons) / len(take_ons)
    assert 0.45 <= rate <= 0.52, rate


def _mean_p_beat(att, dfn) -> float:
    vals = [
        duel_prob(att, dfn, DuelContext(iso, tr, False, False, 15, 75, 75),
                  dfn.physical.stance_idx / 100).p_beat
        for iso, tr in product((True, False), (True, False))
    ]  # fmt: skip
    return sum(vals) / len(vals)


def test_projected_swap_is_a_real_difference(reference):
    players = reference[2]
    vs_frimpong = _mean_p_beat(players[DOKU], players[FRIMPONG])
    vs_szoboszlai = _mean_p_beat(players[DOKU], players[SZOBOSZLAI])
    assert vs_frimpong - vs_szoboszlai >= 0.08, (vs_frimpong, vs_szoboszlai)


def test_hot_duels_rare_at_any_second_in_history(historical):
    """Spec 4: the generic trigger rarely fires without a scenario, checked at every second."""
    firing = [
        match.match_id
        for match, rosters, events in historical
        if any(
            first_trigger(events, rosters, team, 5400)[0] is not None
            for team in (match.home_team_id, match.away_team_id)
        )
    ]
    assert len(firing) <= 3, firing


def test_dismissals_are_rare_in_history(historical):
    dismissals = sum(
        1
        for _, _, events in historical
        for e in events
        if e.event_type == "card" and e.qualifiers.get("card") in ("red", "second_yellow")
    )
    assert dismissals / len(historical) <= 0.2, dismissals
