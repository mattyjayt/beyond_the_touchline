"""Derived analytics and agent artefacts (docs/schema.md §7–§8)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.reference import RoleGroup


class RatingContribution(BaseModel):
    event_id: str
    delta: float
    reason: str


class Rating(BaseModel):
    rating_id: str
    match_id: str
    player_id: str
    asof_sec: int
    live_rating: float = Field(ge=0, le=10)
    expected_rating: float | None = Field(default=None, ge=0, le=10)
    form_delta: float | None = None
    role_group: RoleGroup
    contributions: list[RatingContribution] = []
    low_confidence: bool = False
    methodology_version: str


InsightKind = Literal[
    "momentum_shift", "player_form", "tactical_alert", "substitution_opportunity", "key_moment"
]


class Insight(BaseModel):
    insight_id: str
    kind: InsightKind
    match_id: str
    asof_sec: int
    audience: Literal["fan", "analyst"]
    headline: str
    explanation: str
    evidence_event_ids: list[str] = Field(min_length=1)
    recommendation_id: str | None = None
    uncertainty: str
    generator_version: str
    synthetic: Literal[True] = True


class Recommendation(BaseModel):
    rec_id: str
    match_id: str
    team_id: str
    asof_sec: int
    option_rank: int = Field(ge=1)
    option_type: Literal["keep", "substitution"]
    outgoing_player_id: str | None = None
    incoming_player_id: str | None = None
    eligibility_status: Literal["eligible", "ineligible"] = "eligible"
    attack_delta_estimate: float
    control_delta_estimate: float
    defensive_risk_delta: float
    tactical_fit_score: float = Field(ge=0, le=1)
    confidence: Literal["low", "medium", "high"]
    pros: list[str]
    cons: list[str]
    supporting_event_ids: list[str] = []
    model_version: str
    synthetic: Literal[True] = True
