"""Canonical event contract (docs/schema.md §5)."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

EventType = Literal[
    "period_start",
    "period_end",
    "restart",
    "pass",
    "carry",
    "take_on",
    "shot",
    "tackle",
    "interception",
    "foul",
    "card",
    "substitution",
    "position_change",
]
Outcome = Literal["success", "fail", "goal", "saved", "blocked", "off_target", "neutral"]

ALLOWED_OUTCOMES: dict[str, frozenset[str]] = {
    "period_start": frozenset({"neutral"}),
    "period_end": frozenset({"neutral"}),
    "restart": frozenset({"neutral"}),
    "pass": frozenset({"success", "fail"}),
    "carry": frozenset({"success", "fail"}),
    "take_on": frozenset({"success", "fail"}),
    "shot": frozenset({"goal", "saved", "blocked", "off_target"}),
    "tackle": frozenset({"success", "fail"}),
    "interception": frozenset({"success"}),
    "foul": frozenset({"neutral"}),
    "card": frozenset({"neutral"}),
    "substitution": frozenset({"neutral"}),
    "position_change": frozenset({"neutral"}),
}

REQUIRES_OPPONENT = frozenset({"take_on", "tackle", "foul"})
NO_ACTOR = frozenset({"period_start", "period_end"})

Coord = Field(default=None, ge=0, le=100)


class MatchEvent(BaseModel):
    event_id: str
    match_id: str
    sequence_no: int = Field(ge=0)
    period: Literal[1, 2]
    event_sec: int = Field(ge=0)
    possession_id: str | None = None
    team_id: str
    player_id: str | None = None
    event_type: EventType
    outcome: Outcome
    start_x: float | None = Coord
    start_y: float | None = Coord
    end_x: float | None = Coord
    end_y: float | None = Coord
    recipient_id: str | None = None
    opponent_id: str | None = None
    body_part: Literal["right_foot", "left_foot", "head"] | None = None
    qualifiers: dict[str, Any] = {}
    source_type: Literal["synthetic_simulation"] = "synthetic_simulation"

    @model_validator(mode="after")
    def _check_type_rules(self) -> "MatchEvent":
        if self.outcome not in ALLOWED_OUTCOMES[self.event_type]:
            raise ValueError(f"outcome '{self.outcome}' not allowed for {self.event_type}")
        if self.event_type not in NO_ACTOR and self.player_id is None:
            raise ValueError(f"{self.event_type} requires player_id")
        if self.event_type in REQUIRES_OPPONENT and self.opponent_id is None:
            raise ValueError(f"{self.event_type} requires opponent_id")
        if self.event_type == "substitution" and self.recipient_id is None:
            raise ValueError("substitution requires recipient_id (incoming player)")
        if self.event_type == "position_change" and not (
            self.qualifiers.get("from_slot") and self.qualifiers.get("to_slot")
        ):
            raise ValueError("position_change requires qualifiers from_slot and to_slot")
        if self.body_part is not None and self.event_type != "shot":
            raise ValueError("body_part is only valid on shots")
        return self
