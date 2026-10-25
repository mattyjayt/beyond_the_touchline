"""Live state + SSE stream contract (docs/schema.md §9)."""

from typing import Literal

from pydantic import BaseModel

from app.models.analytics import Insight, Recommendation
from app.models.events import MatchEvent


class TeamLiveStats(BaseModel):
    team_id: str
    score: int
    possession_pct: float
    shots: int
    shots_on_target: int
    xg: float
    passes: int
    pass_accuracy: float


class OnPitchPlayer(BaseModel):
    player_id: str
    team_id: str
    formation_slot: str
    live_rating: float | None = None


class MatchState(BaseModel):
    match_id: str
    asof_sec: int
    period: Literal[1, 2]
    status: Literal["scheduled", "live", "finished"]
    home: TeamLiveStats
    away: TeamLiveStats
    momentum: float  # home minus away rolling threat index
    on_pitch: list[OnPitchPlayer]
    subs_used: dict[str, int]  # team_id -> count
    synthetic: Literal[True] = True


class ReplayControl(BaseModel):
    status: Literal["playing", "paused", "finished"]
    speed: float
    clock_sec: float


class EventMessage(BaseModel):
    type: Literal["event"] = "event"
    data: MatchEvent


class StateMessage(BaseModel):
    type: Literal["state"] = "state"
    data: MatchState


class InsightMessage(BaseModel):
    type: Literal["insight"] = "insight"
    data: Insight


class RecommendationMessage(BaseModel):
    type: Literal["recommendation"] = "recommendation"
    data: list[Recommendation]


class Snapshot(BaseModel):
    """Full replay history up to the clock; sent on connect and after a seek."""

    control: ReplayControl
    events: list[MatchEvent]
    state: MatchState
    insights: list[Insight]


class SnapshotMessage(BaseModel):
    type: Literal["snapshot"] = "snapshot"
    data: Snapshot


class ControlMessage(BaseModel):
    type: Literal["control"] = "control"
    data: ReplayControl


StreamMessage = (
    EventMessage
    | StateMessage
    | InsightMessage
    | RecommendationMessage
    | ControlMessage
    | SnapshotMessage
)
