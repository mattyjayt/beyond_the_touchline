import random
from datetime import UTC, datetime
from itertools import pairwise

import pytest

from app.services.matchups import hot_duels
from app.sim.engine import MatchSim, Scenario, pick_lineup
from app.sim.generate import (
    BOOST_FROM_SEC,
    DEMO_AWAY,
    DEMO_HOME,
    SWAP_IN,
    SWAP_SEC,
    TORMENTOR,
    VICTIM,
    event_hash,
    first_trigger,
    round_robin,
    score_at,
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


DUEL_KEYS = {"tech", "burst", "agil", "stance", "touch", "ctx", "script", "p_beat"}


def build(reference, seed=SEED, scenario=None):
    teams, squads = reference
    rng = random.Random(seed)
    home = pick_lineup(teams["T-LIV"], squads["T-LIV"], rng, 0.25)
    away = pick_lineup(teams["T-CHE"], squads["T-CHE"], rng, 0.25)
    kind = "demo" if scenario else "historical"
    return MatchSim("SIM-T01", kind, home, away, seed, datetime(2026, 9, 1, tzinfo=UTC), scenario)


def sim(reference, seed=SEED):
    return build(reference, seed).run()


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


def test_take_on_events_carry_duel_terms(reference):
    take_ons = [e for e in sim(reference)[2] if e.event_type == "take_on"]
    assert take_ons
    for e in take_ons:
        assert DUEL_KEYS <= set(e.qualifiers["duel"])
        assert 0.05 <= e.qualifiers["duel"]["p_beat"] <= 0.9


def test_historical_has_no_script_term(reference):
    take_ons = [e for e in sim(reference)[2] if e.event_type == "take_on"]
    assert all(e.qualifiers["duel"]["script"] == 0 for e in take_ons)


def test_recovery_tackles_exist(reference):
    events = sim(reference)[2]
    recoveries = [
        (i, e) for i, e in enumerate(events)
        if e.event_type == "tackle" and e.qualifiers.get("recovery")
    ]  # fmt: skip
    assert recoveries
    for i, e in recoveries:
        prev = events[i - 1]  # the take-on the defender was beaten in
        assert e.outcome == "success"
        assert prev.event_type == "take_on" and prev.outcome == "success"
        assert prev.opponent_id == e.player_id and e.opponent_id == prev.player_id


def test_substitutes_enter_with_their_own_clock(reference):
    ms = build(reference)
    ms.run()
    for side in (ms.home, ms.away):
        for pid in side.subbed_on:
            assert side.entered_at[pid] > 2700
            assert ms.minutes_on(side, pid) < 45
        starters = [r.player_id for r in ms.rosters
                    if r.team_id == side.team_id and r.roster_status == "starter"]  # fmt: skip
        assert all(side.entered_at[pid] == 0.0 for pid in starters)


def test_scenario_active_against_requires_marker_in_marked_slot():
    sc = Scenario(
        focus_player_id="P-A", window=(3000, 4000), marker_id="P-M", marker_slot="RB",
        script_boost=12.0,
    )  # fmt: skip
    assert sc.active_against("P-A", "P-M", "RB", 3500)
    assert not sc.active_against("P-A", "P-M", "RW", 3500)  # marker moved slot
    assert not sc.active_against("P-A", "P-X", "RB", 3500)  # someone else in the slot
    assert not sc.active_against("P-B", "P-M", "RB", 3500)  # not the focus player
    assert not sc.active_against("P-A", "P-M", "RB", 2999)  # before the window
    assert not sc.active_against("P-A", "P-M", "RB", 4001)  # after the window


def test_script_term_only_applies_against_marker(reference):
    probe = build(reference)
    focus = probe.home.on_pitch["LW"].player_id
    marker = probe.away.on_pitch["RB"].player_id
    sc = Scenario(
        focus_player_id=focus, window=(0, 6000), marker_id=marker, marker_slot="RB",
        script_boost=15.0,
    )  # fmt: skip
    match, rosters, events = build(reference, scenario=sc).run()
    assert validate_match(match, rosters, events) == []
    scripted = [
        e for e in events if e.event_type == "take_on" and e.qualifiers["duel"]["script"] != 0
    ]
    assert scripted
    assert all(e.player_id == focus and e.opponent_id == marker for e in scripted)
    assert all(e.qualifiers["duel"]["script"] == 15.0 for e in scripted)


# ------------------------------------------------------------- demo storyline
@pytest.fixture(scope="module")
def demo(reference):
    teams, squads = reference
    return simulate_demo(teams, squads, SEED)


def test_demo_is_liverpool_v_city_and_valid(demo):
    match, rosters, events = demo
    assert (match.home_team_id, match.away_team_id) == ("T-LIV", "T-MCI")
    assert validate_match(match, rosters, events) == []
    slot = {r.player_id: r.formation_slot for r in rosters if r.roster_status == "starter"}
    assert slot[VICTIM] == "RB" and slot[SWAP_IN] == "RW" and slot[TORMENTOR] == "LW"
    bench = {r.player_id for r in rosters if r.roster_status == "bench"}
    assert {"P-LIV-02", "P-LIV-12"} <= bench


def test_demo_eleven_v_eleven_before_swap(demo):
    # pre-swap acceptance criterion (calibration C6b): no dismissal before the 70' swap
    _, _, events = demo
    assert not [
        e.event_id for e in events
        if e.event_type == "card" and e.qualifiers.get("card") in ("red", "second_yellow")
        and e.event_sec < SWAP_SEC
    ]  # fmt: skip


def test_demo_storyline_doku_beats_frimpong(demo):
    _, _, events = demo
    beats = [
        e for e in events
        if e.event_type == "take_on" and e.outcome == "success" and e.player_id == TORMENTOR
        and e.opponent_id == VICTIM and BOOST_FROM_SEC <= e.event_sec < SWAP_SEC
    ]  # fmt: skip
    assert len(beats) >= 6


def test_demo_trigger_fires_before_swap(demo):
    _, rosters, events = demo
    sec, hot = first_trigger(events, rosters, DEMO_HOME, SWAP_SEC - 1)
    assert sec is not None and 3300 <= sec <= 4080
    assert any(h.defender_slot == "RB" and h.attacker_id == TORMENTOR for h in hot)
    # nothing fired for Liverpool earlier: the scan is exact, so one second before is quiet
    assert hot_duels(events, rosters, DEMO_HOME, sec - 1) == []


def test_demo_liverpool_not_ahead_at_trigger(demo):
    _, rosters, events = demo
    sec, _ = first_trigger(events, rosters, DEMO_HOME, SWAP_SEC - 1)
    assert sec is not None
    # level or exactly one behind (calibration C6d)
    assert score_at(events, DEMO_AWAY, sec) - score_at(events, DEMO_HOME, sec) in (0, 1)


def test_demo_swap_happens_at_70(demo):
    _, _, events = demo
    swaps = [e for e in events if e.event_type == "position_change"]
    assert len(swaps) == 2
    assert all(e.event_sec >= SWAP_SEC for e in swaps)
    assert swaps[0].event_sec - SWAP_SEC <= 60
    assert {(e.player_id, e.qualifiers["to_slot"]) for e in swaps} == {
        (SWAP_IN, "RB"),
        (VICTIM, "RW"),
    }


def test_script_term_zero_after_swap(demo):
    _, _, events = demo
    swap_sec = next(e.event_sec for e in events if e.event_type == "position_change")
    after = [e for e in events if e.event_type == "take_on" and e.event_sec >= swap_sec]
    assert after
    assert all(e.qualifiers["duel"]["script"] == 0 for e in after)


def test_demo_script_only_vs_frimpong_at_rb_in_window(demo):
    _, _, events = demo
    scripted = [
        e for e in events if e.event_type == "take_on" and e.qualifiers["duel"]["script"] != 0
    ]
    assert scripted
    assert all(e.player_id == TORMENTOR and e.opponent_id == VICTIM for e in scripted)
    assert all(BOOST_FROM_SEC <= e.event_sec < SWAP_SEC for e in scripted)


def test_followup_boost_raises_cross_or_shot_after_scripted_channel_win(reference):
    """Spec 3.4: after the focus player beats the marker in the channel, the next action
    leans to a cross or shot. Compare the same scripted match with the follow-up on and off."""
    probe = build(reference)
    focus = probe.home.on_pitch["LW"].player_id
    marker = probe.away.on_pitch["RB"].player_id

    def followups(mult: float) -> tuple[int, int]:
        sc = Scenario(
            focus_player_id=focus, window=(0, 6000), marker_id=marker, marker_slot="RB",
            script_boost=10.0, followup_mult=mult,
        )  # fmt: skip
        match, rosters, events = build(reference, scenario=sc).run()
        assert validate_match(match, rosters, events) == []
        n = hits = 0
        for prev, e in pairwise(events):
            if (
                prev.event_type == "take_on" and prev.outcome == "success"
                and prev.player_id == focus and prev.qualifiers["duel"]["script"] != 0
                and e.player_id == focus and e.possession_id == prev.possession_id
            ):  # fmt: skip
                n += 1
                hits += e.event_type == "shot" or bool(e.qualifiers.get("cross"))
        return n, hits

    n_off, hits_off = followups(1.0)
    n_on, hits_on = followups(3.0)
    assert n_off and n_on
    assert hits_on / n_on > hits_off / n_off


def test_failed_forced_swap_is_recorded(reference, caplog):
    probe = build(reference)
    on_pitch = probe.home.on_pitch["RB"].player_id
    sc = Scenario(
        focus_player_id="P-NOBODY", window=(0, 0),
        forced_swaps=[(3000, "T-LIV", on_pitch, "P-NOT-ON-PITCH")],
    )  # fmt: skip
    ms = build(reference, scenario=sc)
    ms.run()
    assert ms.failed_swaps == [(3000, "T-LIV", on_pitch, "P-NOT-ON-PITCH")]
    assert "forced swap" in caplog.text


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
