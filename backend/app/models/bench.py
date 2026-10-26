"""Assistant-coach page payload (spec §6): one aggregated view, clamped to the replay clock."""

from typing import Literal

from pydantic import BaseModel

from app.models.advisor import DuelLedger, HotDuel, ImportanceItem, RaceResult, SwapImpact
from app.models.analytics import Recommendation
from app.models.reference import PhysicalProfile, PlayerPriors

RADAR_AXES = ("pace", "acceleration", "agility", "stamina", "defending", "stance", "duel_win")


class PlayerCard(BaseModel):
    player_id: str
    name: str
    slot: str | None  # current slot, None on the bench
    position: str
    physical: PhysicalProfile
    priors: PlayerPriors
    # radar axes on 0-100 (RADAR_AXES). duel_win: projected % of 1v1s won against the
    # tormentor (for the tormentor himself: projected % he wins against the current defender)
    profile: dict[str, float]


class FlankThreat(BaseModel):
    """What the alerted flank produced in the last 20 minutes (consequence, not just duels)."""

    shots: int
    xg: float
    entries: int  # completed crosses / box entries
    threatening: bool  # >= 1 shot or >= 2 entries


class BenchView(BaseModel):
    match_id: str
    team_id: str
    asof_sec: int
    minute: int
    score: dict[str, int]  # team_id -> goals
    alert: HotDuel | None  # sticky: the first hot duel up to asof, with current stats
    alert_active: bool  # whether that duel is firing right now
    # none: no alert yet · active: firing · monitoring: a new holder with < 4 duels of his own
    # (KEEP only until he has a record) · cooling: fired earlier, not firing now
    alert_state: Literal["none", "active", "monitoring", "cooling"]
    tormentor: PlayerCard | None
    defender: PlayerCard | None  # current holder of the alerted slot
    ledger: DuelLedger | None
    threat: FlankThreat | None
    options: list[Recommendation]
    cards: dict[str, PlayerCard]
    race: RaceResult | None
    impact: SwapImpact | None
    executed_option_rank_at_alert: int | None  # rank of the swap Liverpool made, at the alert
    importance: list[ImportanceItem]
    importance_note: str  # method, n, AUC and the methodology-demo caveat ("" if no study)
    slots: dict[str, str]  # our on-pitch players -> slot at asof (formation preview)
    disclosure: str  # what is pinned / scripted in this simulated demo (docs/schema.md §11)
    briefing_seed: str
    briefing_evidence_ids: list[str]
    synthetic: Literal[True] = True
