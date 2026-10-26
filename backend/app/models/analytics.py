"""Derived analytics and agent artefacts (docs/schema.md §7–§8)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.advisor import Move, OptionDims
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
    out_of_position: bool = False  # slot position is neither primary nor secondary (spec 3.3)
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
    option_type: Literal["keep", "substitution", "position_swap", "sub_and_swap"]
    # the player leaving / entering the hot slot (for a swap both stay on the pitch)
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
    moves: list[Move] = []
    dims: OptionDims | None = None
    score: float | None = None  # policy-weighted sum of dims; KEEP = 0
    projected_win_pct: float | None = None  # hot-slot defender vs the tormentor, duel model
    observed_win_pct: float | None = None  # same pairing, this match so far
    n_observed: int = 0
    blended_win_pct: float | None = None  # model prior (k=6 duels) + observed record
    blended_ci: list[float] | None = None  # 90% Beta interval on the blended estimate
    tied: bool = False  # within TIE_BAND of a neighbouring option's score
    out_of_position: bool = False
    model_version: str
    synthetic: Literal[True] = True
