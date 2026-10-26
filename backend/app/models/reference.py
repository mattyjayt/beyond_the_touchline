"""Reference and match-level entities (docs/schema.md §3–§4)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Position = Literal[
    "GK", "RB", "CB", "LB", "RWB", "LWB", "CDM", "CM", "CAM", "RM", "LM", "RW", "LW", "ST"
]
RoleGroup = Literal["GK", "DEF", "MID", "ATT"]
Foot = Literal["left", "right", "both"]

ROLE_GROUP: dict[str, RoleGroup] = {
    "GK": "GK",
    **dict.fromkeys(["RB", "CB", "LB", "RWB", "LWB"], "DEF"),
    **dict.fromkeys(["CDM", "CM", "CAM", "RM", "LM"], "MID"),
    **dict.fromkeys(["RW", "LW", "ST"], "ATT"),
}


class PlayerPriors(BaseModel):
    """Synthetic ability priors (0-100). Generated, never real ratings."""

    passing: int = Field(ge=0, le=100)
    dribbling: int = Field(ge=0, le=100)
    finishing: int = Field(ge=0, le=100)
    defending: int = Field(ge=0, le=100)
    physical: int = Field(ge=0, le=100)
    goalkeeping: int = Field(ge=0, le=100)


def _clamp_idx(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


class PhysicalProfile(BaseModel):
    """Synthetic physical attributes. Generated, never real measurements."""

    top_speed_kmh: float = Field(ge=20, le=45)
    accel_ms2: float = Field(ge=3, le=10)
    agility_idx: int = Field(ge=0, le=100)
    stamina_idx: int = Field(ge=0, le=100)
    stance_idx: int = Field(ge=0, le=100)
    height_cm: int = Field(ge=140, le=220)

    @property
    def speed_idx(self) -> float:
        """Top speed mapped linearly 29-37 km/h onto 0-100, clamped."""
        return _clamp_idx((self.top_speed_kmh - 29.0) / (37.0 - 29.0) * 100)

    @property
    def accel_idx(self) -> float:
        """Acceleration mapped linearly 6.0-7.9 m/s2 onto 0-100, clamped."""
        return _clamp_idx((self.accel_ms2 - 6.0) / (7.9 - 6.0) * 100)

    @property
    def time_0_5m_s(self) -> float:
        """Approximate time to cover 5 m from a standing start (constant accel + reaction)."""
        return round((10 / self.accel_ms2) ** 0.5 + 0.25, 2)


class Team(BaseModel):
    team_id: str
    code: str
    name: str
    short_name: str
    home_venue: str | None = None
    primary_color: str
    secondary_color: str
    manager: str | None = None
    default_formation: str = "4-3-3"
    strength_index: float = Field(default=0.5, ge=0, le=1)


class Player(BaseModel):
    player_id: str
    team_id: str
    display_name: str
    shirt_number: int
    primary_position: Position
    secondary_positions: list[Position] = []
    foot: Foot = "right"
    archetype: str
    priors: PlayerPriors | None = None
    physical: PhysicalProfile | None = None

    @property
    def role_group(self) -> RoleGroup:
        return ROLE_GROUP[self.primary_position]


class Match(BaseModel):
    match_id: str
    kind: Literal["historical", "demo"]
    home_team_id: str
    away_team_id: str
    kickoff_at: datetime
    status: Literal["scheduled", "live", "finished"]
    home_score: int = 0
    away_score: int = 0
    home_formation: str
    away_formation: str
    seed: int
    generator_version: str
    synthetic: Literal[True] = True


class RosterEntry(BaseModel):
    match_id: str
    player_id: str
    team_id: str
    roster_status: Literal["starter", "bench", "unavailable"]
    formation_slot: str | None = None
    shirt_number: int | None = None
    available: bool = True
    reason: str | None = None
