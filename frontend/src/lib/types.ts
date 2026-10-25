// Mirrors backend/app/models (canonical). Keep in sync in the same change.
// All match data is synthetic: club/player names are real reference data only.

export type Position =
  | "GK" | "RB" | "CB" | "LB" | "RWB" | "LWB" | "CDM" | "CM" | "CAM"
  | "RM" | "LM" | "RW" | "LW" | "ST";
export type RoleGroup = "GK" | "DEF" | "MID" | "ATT";
export type Foot = "left" | "right" | "both";

// ---- reference ------------------------------------------------------------

export interface PlayerPriors {
  passing: number;
  dribbling: number;
  finishing: number;
  defending: number;
  physical: number;
  goalkeeping: number;
}

export interface Team {
  team_id: string;
  code: string;
  name: string;
  short_name: string;
  home_venue: string | null;
  primary_color: string;
  secondary_color: string;
  manager: string | null;
  default_formation: string;
  strength_index: number;
}

export interface Player {
  player_id: string;
  team_id: string;
  display_name: string;
  shirt_number: number;
  primary_position: Position;
  secondary_positions: Position[];
  foot: Foot;
  archetype: string;
  priors: PlayerPriors | null;
}

export interface Match {
  match_id: string;
  kind: "historical" | "demo";
  home_team_id: string;
  away_team_id: string;
  kickoff_at: string;
  status: "scheduled" | "live" | "finished";
  home_score: number;
  away_score: number;
  home_formation: string;
  away_formation: string;
  seed: number;
  generator_version: string;
  synthetic: true;
}

export interface RosterEntry {
  match_id: string;
  player_id: string;
  team_id: string;
  roster_status: "starter" | "bench" | "unavailable";
  formation_slot: string | null;
  shirt_number: number | null;
  available: boolean;
  reason: string | null;
}

// ---- events ---------------------------------------------------------------

export type EventType =
  | "period_start" | "period_end" | "restart" | "pass" | "carry" | "take_on"
  | "shot" | "tackle" | "interception" | "foul" | "card" | "substitution";
export type Outcome =
  | "success" | "fail" | "goal" | "saved" | "blocked" | "off_target" | "neutral";

export interface MatchEvent {
  event_id: string;
  match_id: string;
  sequence_no: number;
  period: 1 | 2;
  event_sec: number;
  possession_id: string | null;
  team_id: string;
  player_id: string | null;
  event_type: EventType;
  outcome: Outcome;
  start_x: number | null;
  start_y: number | null;
  end_x: number | null;
  end_y: number | null;
  recipient_id: string | null;
  opponent_id: string | null;
  body_part: "right_foot" | "left_foot" | "head" | null;
  qualifiers: Record<string, unknown>;
  source_type: "synthetic_simulation";
}

// ---- analytics + agent artefacts ------------------------------------------

export interface RatingContribution {
  event_id: string;
  delta: number;
  reason: string;
}

export interface Rating {
  rating_id: string;
  match_id: string;
  player_id: string;
  asof_sec: number;
  live_rating: number;
  expected_rating: number | null;
  form_delta: number | null;
  role_group: RoleGroup;
  contributions: RatingContribution[];
  low_confidence: boolean;
  methodology_version: string;
}

export type InsightKind =
  | "momentum_shift" | "player_form" | "tactical_alert"
  | "substitution_opportunity" | "key_moment";

export interface Insight {
  insight_id: string;
  kind: InsightKind;
  match_id: string;
  asof_sec: number;
  audience: "fan" | "analyst";
  headline: string;
  explanation: string;
  evidence_event_ids: string[];
  recommendation_id: string | null;
  uncertainty: string;
  generator_version: string;
  synthetic: true;
}

export interface Recommendation {
  rec_id: string;
  match_id: string;
  team_id: string;
  asof_sec: number;
  option_rank: number;
  option_type: "keep" | "substitution";
  outgoing_player_id: string | null;
  incoming_player_id: string | null;
  eligibility_status: "eligible" | "ineligible";
  attack_delta_estimate: number;
  control_delta_estimate: number;
  defensive_risk_delta: number;
  tactical_fit_score: number;
  confidence: "low" | "medium" | "high";
  pros: string[];
  cons: string[];
  supporting_event_ids: string[];
  model_version: string;
  synthetic: true;
}

// ---- live state + stream --------------------------------------------------

export interface TeamLiveStats {
  team_id: string;
  score: number;
  possession_pct: number;
  shots: number;
  shots_on_target: number;
  xg: number;
  passes: number;
  pass_accuracy: number;
}

export interface OnPitchPlayer {
  player_id: string;
  team_id: string;
  formation_slot: string;
  live_rating: number | null;
}

export interface MatchState {
  match_id: string;
  asof_sec: number;
  period: 1 | 2;
  status: "scheduled" | "live" | "finished";
  home: TeamLiveStats;
  away: TeamLiveStats;
  momentum: number;
  on_pitch: OnPitchPlayer[];
  subs_used: Record<string, number>;
  synthetic: true;
}

export interface ReplayControl {
  status: "playing" | "paused" | "finished";
  speed: number;
  clock_sec: number;
}

export interface Snapshot {
  control: ReplayControl;
  events: MatchEvent[];
  state: MatchState;
  insights: Insight[];
}

export interface MatchDetail {
  match: Match;
  home: Team;
  away: Team;
  roster: RosterEntry[];
  players: Record<string, Player>;
  duration_sec: number;
}

export type StreamMessage =
  | { type: "event"; data: MatchEvent }
  | { type: "state"; data: MatchState }
  | { type: "insight"; data: Insight }
  | { type: "recommendation"; data: Recommendation[] }
  | { type: "control"; data: ReplayControl }
  | { type: "snapshot"; data: Snapshot };
