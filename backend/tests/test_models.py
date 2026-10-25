import pytest
from pydantic import ValidationError

from app.models import Insight, MatchEvent


def make_event(**overrides):
    base = {
        "event_id": "SIM-001-E0101",
        "match_id": "SIM-001",
        "sequence_no": 101,
        "period": 2,
        "event_sec": 3990,
        "possession_id": "SIM-001-P0042",
        "team_id": "T-ARS",
        "player_id": "P-ARS-07",
        "event_type": "take_on",
        "outcome": "fail",
        "start_x": 78,
        "start_y": 12,
        "opponent_id": "P-MCI-03",
    }
    return MatchEvent(**(base | overrides))


def test_valid_take_on_matches_spec_example():
    ev = make_event()
    assert ev.source_type == "synthetic_simulation"


@pytest.mark.parametrize(
    "overrides",
    [
        {"outcome": "goal"},  # outcome not valid for take_on
        {"opponent_id": None},  # take_on needs a matched opponent
        {"player_id": None},  # actor required
        {"start_x": 101},  # out of pitch bounds
        {"body_part": "head"},  # body_part only on shots
        {"event_type": "substitution", "outcome": "neutral", "recipient_id": None},
    ],
)
def test_invalid_events_rejected(overrides):
    with pytest.raises(ValidationError):
        make_event(**overrides)


def test_period_markers_need_no_actor():
    ev = make_event(event_type="period_start", outcome="neutral", player_id=None, opponent_id=None)
    assert ev.player_id is None


def test_insight_requires_evidence():
    with pytest.raises(ValidationError):
        Insight(
            insight_id="INS-SIM-001-4020-1",
            kind="substitution_opportunity",
            match_id="SIM-001",
            asof_sec=4020,
            audience="fan",
            headline="A change on the right could help",
            explanation="...",
            evidence_event_ids=[],
            uncertainty="Limited matchup sample",
            generator_version="rules-v0",
        )
