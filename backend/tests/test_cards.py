"""Phase B item 6: card probabilities by foul context (pure decision function)."""

import pytest

from app.sim.engine import (
    DOGSO_RED_P,
    SECOND_YELLOW_FACTOR,
    SPA_YELLOW_P,
    STRAIGHT_RED_P,
    card_for_foul,
    foul_context,
)


def rates(context: str, booked: bool, n: int = 20000) -> dict[str, float]:
    out: dict[str, int] = {}
    for i in range(n):
        c = card_for_foul((i + 0.5) / n, booked, context)
        out[c or "none"] = out.get(c or "none", 0) + 1
    return {k: v / n for k, v in out.items()}


def test_general_foul_rates_unchanged():
    r = rates("general", booked=False)
    assert r["red"] == pytest.approx(STRAIGHT_RED_P, abs=1e-3)
    assert r["yellow"] == pytest.approx(0.165, abs=1e-3)


def test_spa_foul_is_usually_booked():
    assert rates("spa", booked=False)["yellow"] == pytest.approx(SPA_YELLOW_P, abs=1e-3)
    booked = rates("spa", booked=True)
    assert booked["second_yellow"] == pytest.approx(SPA_YELLOW_P * SECOND_YELLOW_FACTOR, abs=1e-3)


def test_dogso_foul_can_be_a_red():
    r = rates("dogso", booked=False)
    assert r["red"] == pytest.approx(DOGSO_RED_P, abs=1e-3)
    assert r["yellow"] == pytest.approx(SPA_YELLOW_P * (1 - DOGSO_RED_P), abs=2e-3)


@pytest.mark.parametrize(("attacker_xy", "expected"), [
    ((80.0, 50.0), "dogso"),   # central, ~21 m out
    ((80.0, 85.0), "spa"),     # wide
    ((60.0, 50.0), "spa"),     # central but ~42 m out
])  # fmt: skip
def test_foul_context_from_the_duel_point(attacker_xy, expected):
    assert foul_context(attacker_xy) == expected
