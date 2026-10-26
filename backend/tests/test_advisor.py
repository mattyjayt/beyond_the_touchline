"""Advisor (spec 4): KEEP / SUB / SWAP / SUB+SWAP options on the regenerated demo."""

import dataclasses
from pathlib import Path

import pytest

from app.config import get_settings
from app.services.advisor import POLICY_WEIGHTS, advisor_input, evaluate
from app.store import Store

MATCH, TEAM, ASOF = "SIM-001", "T-LIV", 4080
FRIMPONG, SZOBOSZLAI, GOMEZ, BRADLEY = "P-LIV-30", "P-LIV-08", "P-LIV-02", "P-LIV-12"


@pytest.fixture(scope="module")
def store():
    return Store(Path(get_settings().database_url.removeprefix("sqlite:///")))


@pytest.fixture(scope="module")
def inp(store):
    i = advisor_input(store, MATCH, TEAM, ASOF)
    assert i is not None
    return i


@pytest.fixture(scope="module")
def options(inp):
    return evaluate(inp)


def _moves(rec) -> set[tuple[str, str | None, str | None, str]]:
    return {(m.player_id, m.from_slot, m.to_slot, m.kind) for m in rec.moves}


def _players(rec) -> set[str]:
    return {m.player_id for m in rec.moves}


def test_no_input_before_the_alert(store):
    assert advisor_input(store, MATCH, TEAM, 1200) is None


def test_input_reflects_the_hot_duel(inp):
    assert inp.hot.defender_slot == "RB" and inp.hot.attacker_id == "P-MCI-11"
    assert inp.slots[FRIMPONG] == "RB" and inp.slots[SZOBOSZLAI] == "RW"
    assert GOMEZ in inp.bench and BRADLEY in inp.bench
    assert inp.subs_left == 5 and inp.tormentor.player_id == "P-MCI-11"
    assert FRIMPONG in inp.yellows  # booked at 3725 s


def test_keep_always_present_and_first_class(options):
    keeps = [o for o in options if o.option_type == "keep"]
    assert len(keeps) == 1
    assert keeps[0].dims is not None and keeps[0].supporting_event_ids
    assert sorted(o.option_rank for o in options) == list(range(1, len(options) + 1))
    assert len(options) <= 5


def test_swap_option_szoboszlai_to_rb(options):
    swap = next(o for o in options if o.option_type == "position_swap")
    assert _moves(swap) == {(SZOBOSZLAI, "RW", "RB", "move"), (FRIMPONG, "RB", "RW", "move")}
    assert swap.dims.M > 0
    assert swap.confidence == "low"  # no history at RB (n=0)
    assert swap.incoming_player_id == SZOBOSZLAI and swap.outgoing_player_id == FRIMPONG
    assert swap.projected_win_pct is not None and swap.projected_win_pct > 0.3
    assert swap.out_of_position is False  # RB and RW are listed secondaries


def test_swap_pros_and_cons_quote_numbers(options):
    swap = next(o for o in options if o.option_type == "position_swap")
    text = " ".join(swap.pros + swap.cons)
    assert "to 5 m" in text and "(simulated)" in text
    assert "n=0" in text


def test_sub_options_include_gomez_or_bradley(options):
    subs = [o for o in options if o.option_type == "substitution"]
    assert {o.incoming_player_id for o in subs} & {GOMEZ, BRADLEY}
    for o in subs:
        assert o.outgoing_player_id == FRIMPONG
        assert (FRIMPONG, "RB", None, "off") in _moves(o)


def test_no_swap_with_off_pitch_player(inp):
    slots = {p: s for p, s in inp.slots.items() if p != SZOBOSZLAI}
    out = evaluate(dataclasses.replace(inp, slots=slots))
    assert all(SZOBOSZLAI not in _players(o) for o in out)


def test_dims_bounded_and_score_uses_policy_weights(options):
    assert set(POLICY_WEIGHTS) == {"L", "F", "M", "A", "G", "R"}
    for o in options:
        for v in o.dims.model_dump().values():
            assert -1 <= v <= 1


def test_no_subs_left_hides_sub_options(inp):
    out = evaluate(dataclasses.replace(inp, subs_left=0))
    assert {o.option_type for o in out} <= {"keep", "position_swap"}
    assert any(o.option_type == "position_swap" for o in out)


def test_every_option_cites_evidence_up_to_asof(store, options):
    secs = {e.event_id: e.event_sec for e in store.events(MATCH)}
    for o in options:
        assert o.supporting_event_ids
        assert all(secs[i] <= ASOF for i in o.supporting_event_ids)
        assert o.synthetic is True


def test_acceleration_claim_needs_a_real_gap(options):
    import re

    for o in options:
        for text in o.pros:
            if m := re.search(r"Out-accelerates .*: ([\d.]+) s vs ([\d.]+) s", text):
                assert float(m[2]) - float(m[1]) >= 0.03, text
    swap = next(o for o in options if o.option_type == "position_swap")
    assert any("Level off the mark" in t for t in swap.pros)  # 1.62 s vs 1.64 s


def test_fresh_legs_only_when_the_sub_takes_the_duel(store, options):
    for o in options:
        fresh = any("Fresh legs" in t for t in o.pros)
        assert fresh == (o.option_type == "substitution"), o.option_type
        if o.option_type == "sub_and_swap":
            on = next(m for m in o.moves if m.kind == "on")
            name = store.players[on.player_id].display_name
            assert any(name in t and on.to_slot in t for t in o.pros)


def test_projected_role_is_flagged(inp):
    for o in evaluate(inp):
        if o.dims.F < 0.5 and o.option_type != "keep":
            assert o.out_of_position
            assert any("not a listed position" in t for t in o.cons)
