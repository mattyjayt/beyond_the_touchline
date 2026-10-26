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
    assert "m after 1 s" in text and "simulated" in text
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


def test_acceleration_claim_needs_a_real_race_gap(options):
    """C6: an acceleration edge is only claimed when the sprint race shows >= 0.15 m at 1 s,
    and the copy uses real units (m/s2 and metres)."""
    import re

    for o in options:
        for text in o.pros + o.cons:
            if m := re.search(r"Out-accelerates .*: ([\d.]+) vs ([\d.]+) m after 1 s", text):
                assert float(m[1]) - float(m[2]) >= 0.15, text
    swap = next(o for o in options if o.option_type == "position_swap")
    level = next(t for t in swap.pros if "Level off the mark" in t)
    assert "m/s²" in level and "m after 1 s" in level  # 1.74 vs 1.67 m: a 7 cm gap


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
        if o.tactical_fit_score < 0.5 and o.option_type != "keep":
            assert o.out_of_position
            assert any("not a listed position" in t for t in o.cons)


# ------------------------------------------------ C2: KEEP is scored like any option
def test_keep_wins_when_a_natural_holder_is_not_outmatched(inp):
    """Principle: a primary-position holder with a strong record and normal form stays."""
    holder = inp.hot.defender_id
    calm = dataclasses.replace(
        inp,
        observed={**inp.observed, holder: (12, 14)},  # wins 12 of 14 against the tormentor
        expected={**inp.expected, holder: inp.live[holder]},  # playing to his baseline
    )
    ranked = evaluate(calm)
    assert ranked[0].option_type == "keep", [(o.option_type, o.score) for o in ranked]


def test_m_compares_blended_estimates_on_both_sides(inp):
    from app.services.advisor import M_SCALE, SHRINK_K, projected_win

    swap = next(o for o in evaluate(inp) if o.option_type == "position_swap")

    def shrunk(pid: str) -> float:
        won, n = inp.observed.get(pid, (0, 0))
        return (won + SHRINK_K * projected_win(inp, pid)) / (n + SHRINK_K)

    expected = (shrunk(SZOBOSZLAI) - shrunk(FRIMPONG)) / M_SCALE
    assert swap.dims.M == pytest.approx(max(-1, min(1, expected)), abs=1e-3)


def test_fit_is_relative_to_the_holder(inp):
    # Frimpong is a natural RB (fit 1.0); Szoboszlai's RB is a secondary (0.8)
    swap = next(o for o in evaluate(inp) if o.option_type == "position_swap")
    assert swap.dims.F == pytest.approx(-0.2)


def test_swap_gets_partial_form_credit(inp):
    out = evaluate(inp)
    sub = next(o for o in out if o.option_type == "substitution")
    swap = next(o for o in out if o.option_type == "position_swap")
    if sub.dims.L:
        assert swap.dims.L == pytest.approx(sub.dims.L * 0.5, abs=1e-3)


def test_at_the_alert_a_change_still_outranks_keep(store):
    at_alert = advisor_input(store, MATCH, TEAM, 3714)
    ranked = evaluate(at_alert)
    assert ranked[0].option_type != "keep"


def test_shortlist_shows_every_option_type_and_the_natural_sub(store, options):
    kinds = {o.option_type for o in options}
    assert {"keep", "substitution", "position_swap", "sub_and_swap"} <= kinds
    at_alert = evaluate(advisor_input(store, MATCH, TEAM, 3714))
    assert BRADLEY in {o.incoming_player_id for o in at_alert}  # the like-for-like RB


# --------------------------------- C3: transition term gated like the engine's
def test_projection_gates_transition_by_archetype(inp):
    from itertools import product

    from app.services.advisor import projected_win
    from app.sim.duel import DuelContext, duel_prob
    from app.sim.engine import TRANSITION_ARCHETYPES

    szo = inp.players[SZOBOSZLAI]
    assert szo.archetype not in TRANSITION_ARCHETYPES
    mins = inp.minutes_on
    vals = [
        duel_prob(inp.tormentor, szo,
                  DuelContext(iso, False, SZOBOSZLAI in inp.yellows, False, 15.0,
                              mins.get(inp.tormentor.player_id, 0.0), mins.get(SZOBOSZLAI, 0.0)),
                  szo.physical.stance_idx / 100).p_beat
        for iso, _ in product((True, False), (True, False))
    ]  # fmt: skip
    assert projected_win(inp, SZOBOSZLAI) == pytest.approx(1 - sum(vals) / 4, abs=1e-3)


# ------------------------------------------------- C8: ties, disruption, intervals
def test_near_ties_are_marked(options):
    from app.services.advisor import TIE_BAND

    for i, o in enumerate(options):
        nbrs = [options[j].score for j in (i - 1, i + 1) if 0 <= j < len(options)]
        assert o.tied == any(abs(o.score - n) <= TIE_BAND for n in nbrs), o.option_rank


def test_moving_more_players_costs_more(inp):
    from app.services.advisor import DISRUPTION_PER_PLAYER, POLICY_WEIGHTS

    for o in evaluate(inp):
        if o.option_type == "keep":
            continue
        weighted = sum(POLICY_WEIGHTS[k] * getattr(o.dims, k) for k in POLICY_WEIGHTS)
        extra = max(0, len(o.moves) - 2)
        assert o.score == pytest.approx(weighted - DISRUPTION_PER_PLAYER * extra, abs=2e-4)


def test_blended_estimate_has_an_interval(options):
    for o in options:
        lo, hi = o.blended_ci
        assert 0 <= lo <= o.blended_win_pct <= hi <= 1


def test_keep_mentions_the_untested_cover_instruction(options):
    keep = next(o for o in options if o.option_type == "keep")
    assert any("double up" in t and "not modelled" in t for t in keep.pros)
