import random
from datetime import UTC, datetime

import pytest

from app.sim.engine import MatchSim, pick_lineup
from app.sim.generate import (
    FOCUS_MARKER,
    FOCUS_PLAYER,
    event_hash,
    round_robin,
    simulate_demo,
)
from app.sim.squads import load_reference
from app.sim.validate import validate_match

SEED = 2026


@pytest.fixture(scope="module")
def reference():
    teams, players = load_reference(SEED)
    squads = {t.team_id: [p for p in players if p.team_id == t.team_id] for t in teams}
    return {t.team_id: t for t in teams}, squads


def sim(reference, seed=SEED):
    teams, squads = reference
    rng = random.Random(seed)
    home = pick_lineup(teams["T-LIV"], squads["T-LIV"], rng, 0.25)
    away = pick_lineup(teams["T-CHE"], squads["T-CHE"], rng, 0.25)
    return MatchSim(
        "SIM-T01", "historical", home, away, seed, datetime(2026, 9, 1, tzinfo=UTC)
    ).run()


def test_round_robin_gives_20_unique_fixtures():
    fixtures = round_robin(["A", "B", "C", "D", "E"])
    assert len(fixtures) == 20 and len(set(fixtures)) == 20


def test_simulated_match_passes_validation(reference):
    match, rosters, events = sim(reference)
    assert validate_match(match, rosters, events) == []
    assert 1000 < len(events) < 2500


def test_same_seed_reproduces_identical_events(reference):
    assert event_hash(sim(reference)[2]) == event_hash(sim(reference)[2])
    assert event_hash(sim(reference)[2]) != event_hash(sim(reference, seed=SEED + 1)[2])


def test_validator_catches_score_mismatch(reference):
    match, rosters, events = sim(reference)
    bad = match.model_copy(update={"home_score": match.home_score + 1})
    assert any("score mismatch" in e for e in validate_match(bad, rosters, events))


def test_demo_storyline_focus_player_struggles_in_window(reference):
    teams, squads = reference
    match, rosters, events = simulate_demo(teams, squads, SEED)
    assert validate_match(match, rosters, events) == []
    window = [
        e
        for e in events
        if e.player_id == FOCUS_PLAYER and e.event_type == "take_on" and 2880 <= e.event_sec <= 4140
    ]
    assert len(window) >= 6
    assert sum(e.outcome == "success" for e in window) / len(window) < 0.4
    assert all(e.opponent_id == FOCUS_MARKER for e in window)


def test_api_serves_demo_and_replay_controls(app_client):
    detail = app_client.get("/api/matches/demo").json()
    mid = detail["match"]["match_id"]
    assert detail["match"]["synthetic"] is True
    assert len([r for r in detail["roster"] if r["roster_status"] == "starter"]) == 22
    state = app_client.get(f"/api/matches/{mid}/state", params={"asof_sec": 4020}).json()
    assert state["period"] == 2 and len(state["on_pitch"]) >= 20
    ctrl = app_client.post(f"/api/matches/{mid}/replay", json={"action": "seek", "value": 600})
    assert ctrl.json()["clock_sec"] == 600
    assert (
        app_client.post(f"/api/matches/{mid}/replay", json={"action": "bogus"}).status_code == 422
    )
