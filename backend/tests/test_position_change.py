"""Task 4: `position_change` event end to end (spec 3.3)."""

import random
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import MatchEvent
from app.services.live_state import compute_state
from app.services.performance import (
    WEIGHTS,
    is_out_of_position,
    live_rating,
    slot_timeline,
)
from app.sim.engine import MatchSim, Scenario, pick_lineup
from app.sim.squads import load_reference
from app.sim.validate import validate_match

SEED = 2026
HOME, AWAY = "T-LIV", "T-MCI"
SZOBOSZLAI, FRIMPONG, GOMEZ, BRADLEY, DOKU = (
    "P-LIV-08",
    "P-LIV-30",
    "P-LIV-02",
    "P-LIV-12",
    "P-MCI-11",
)
SWAP_SEC = 4200


@pytest.fixture(scope="module")
def reference():
    teams, players = load_reference(SEED)
    squads = {t.team_id: [p for p in players if p.team_id == t.team_id] for t in teams}
    return {t.team_id: t for t in teams}, squads, {p.player_id: p for p in players}


def run_swap_match(reference, extra_subs: int = 0):
    """LIV (Szoboszlai RW, Frimpong RB) vs MCI with a forced 70' swap; optional forced subs."""
    teams, squads, _ = reference
    rng = random.Random(SEED)
    lineup = {"RW": SZOBOSZLAI, "RB": FRIMPONG}
    home = pick_lineup(teams[HOME], squads[HOME], rng, 0.0, lineup, [GOMEZ, BRADLEY])
    away = pick_lineup(teams[AWAY], squads[AWAY], rng, 0.0)
    subs = []
    if extra_subs:
        bench = [p.player_id for p in home.bench if p.primary_position != "GK"]
        outs = [p.player_id for s, p in home.players() if s.slot not in ("GK", "RB", "RW")]
        subs = [
            (SWAP_SEC + 300 + 60 * i, HOME, out, inc)
            for i, (out, inc) in enumerate(zip(outs, bench, strict=False))
        ][:extra_subs]
    scenario = Scenario(
        focus_player_id=DOKU,
        window=(0, 0),
        forced_swaps=[(SWAP_SEC, HOME, SZOBOSZLAI, FRIMPONG)],
        forced_subs=subs,
        no_auto_subs_before={HOME: 88 * 60, AWAY: 88 * 60},  # auto subs only at 88'+
    )
    return MatchSim(
        "SIM-T04", "demo", home, away, SEED, datetime(2026, 9, 1, tzinfo=UTC), scenario
    ).run()


@pytest.fixture(scope="module")
def swap_match(reference):
    return run_swap_match(reference)


def swap_events(events):
    return [e for e in events if e.event_type == "position_change"]


def test_swap_emits_two_events_and_keeps_bijection(swap_match):
    match, rosters, events = swap_match
    a, b = swap_events(events)
    assert a.event_sec == b.event_sec >= SWAP_SEC
    assert b.sequence_no == a.sequence_no + 1
    assert (a.player_id, a.recipient_id) == (SZOBOSZLAI, FRIMPONG)
    assert (b.player_id, b.recipient_id) == (FRIMPONG, SZOBOSZLAI)
    assert a.qualifiers == {"from_slot": "RW", "to_slot": "RB"}
    assert b.qualifiers == {"from_slot": "RB", "to_slot": "RW"}
    assert a.outcome == b.outcome == "neutral" and a.possession_id is None
    assert validate_match(match, rosters, events) == []


def test_position_change_requires_slots():
    with pytest.raises(ValidationError):
        MatchEvent(
            event_id="X-E0001", match_id="X", sequence_no=1, period=2, event_sec=4200,
            team_id=HOME, player_id=SZOBOSZLAI, event_type="position_change",
            outcome="neutral", qualifiers={"from_slot": "RW"},
        )  # fmt: skip


def test_validator_rejects_swap_with_off_pitch_player(swap_match):
    match, rosters, events = swap_match
    a = swap_events(events)[0]
    bad = [e.model_copy(update={"player_id": GOMEZ}) if e is a else e for e in events]
    assert any("not on the pitch" in err for err in validate_match(match, rosters, bad))


def test_validator_rejects_wrong_from_slot(swap_match):
    match, rosters, events = swap_match
    a = swap_events(events)[0]
    quals = {"from_slot": "LW", "to_slot": "RB"}
    bad = [e.model_copy(update={"qualifiers": quals}) if e is a else e for e in events]
    assert any("from_slot" in err for err in validate_match(match, rosters, bad))


def test_validator_rejects_unpaired_move(swap_match):
    match, rosters, events = swap_match
    b = swap_events(events)[1]
    bad = [e for e in events if e is not b]
    assert any("one-to-one" in err for err in validate_match(match, rosters, bad))


def test_validator_rejects_to_slot_outside_formation(swap_match):
    match, rosters, events = swap_match
    a = swap_events(events)[0]
    quals = {"from_slot": "RW", "to_slot": "RWB"}
    bad = [e.model_copy(update={"qualifiers": quals}) if e is a else e for e in events]
    assert any("to_slot" in err for err in validate_match(match, rosters, bad))


def test_swap_does_not_count_as_sub(reference):
    match, rosters, events = run_swap_match(reference, extra_subs=5)
    subs = [e for e in events if e.event_type == "substitution" and e.team_id == HOME]
    assert len(subs) == 5
    assert len(swap_events(events)) == 2
    assert validate_match(match, rosters, events) == []


def test_live_state_reflects_swap(swap_match):
    match, rosters, events = swap_match
    slots = {
        p.player_id: p.formation_slot for p in compute_state(match, rosters, events, 4300).on_pitch
    }
    assert slots[SZOBOSZLAI] == "RB"
    assert slots[FRIMPONG] == "RW"
    before = compute_state(match, rosters, events, SWAP_SEC - 60).on_pitch
    assert {p.player_id: p.formation_slot for p in before}[SZOBOSZLAI] == "RW"


def test_slot_timeline_follows_swap(swap_match):
    _, rosters, events = swap_match
    sec = swap_events(events)[0].event_sec
    for pid, before, after in ((SZOBOSZLAI, "RW", "RB"), (FRIMPONG, "RB", "RW")):
        timeline = slot_timeline(pid, rosters, events)
        assert timeline[:2] == [(0, before), (sec, after)]
        # auto subs are allowed from 88': the only later change is leaving the pitch
        assert all(s is None and t >= 88 * 60 for t, s in timeline[2:])


def test_rating_uses_slot_role_after_swap(reference, swap_match):
    _, _, players = reference
    match, rosters, events = swap_match
    sec = swap_events(events)[0].event_sec
    szob, frim = players[SZOBOSZLAI], players[FRIMPONG]

    def tackle(eid: str, at: int) -> MatchEvent:
        return MatchEvent(
            event_id=eid, match_id=match.match_id, sequence_no=0, period=2, event_sec=at,
            possession_id="P-X", team_id=HOME, player_id=SZOBOSZLAI, event_type="tackle",
            outcome="success", opponent_id=DOKU,
        )  # fmt: skip

    pre, post = tackle("T-PRE", sec - 100), tackle("T-POST", sec + 50)
    evs = sorted([*events, pre, post], key=lambda e: e.event_sec)
    _, contribs, _ = live_rating(szob, evs, sec + 60, 75, rosters=rosters)
    delta = {c.event_id: c.delta for c in contribs}
    assert delta["T-POST"] == WEIGHTS[("tackle", "success")]["DEF"]
    assert delta["T-PRE"] == WEIGHTS[("tackle", "success")]["ATT"]  # RW slot before the swap

    # backwards compatible: without rosters the primary position's group is used
    _, legacy, _ = live_rating(szob, evs, sec + 60, 75)
    assert {c.event_id: c.delta for c in legacy}["T-POST"] == WEIGHTS[("tackle", "success")]["MID"]

    assert is_out_of_position(szob, "RB") is False
    assert is_out_of_position(frim, "CM") is True
