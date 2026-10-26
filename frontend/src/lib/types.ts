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

export interface PhysicalProfile {
  top_speed_kmh: number;
  accel_ms2: number;
  agility_idx: number;
  stamina_idx: number;
  stance_idx: number;
  height_cm: number;
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
  physical?: PhysicalProfile | null;
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
  | "shot" | "tackle" | "interception" | "foul" | "card" | "substitution"
  | "position_change";
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
  out_of_position: boolean;
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
  option_type: "keep" | "substitution" | "position_swap" | "sub_and_swap";
  // the player leaving / entering the hot slot (for a swap both stay on the pitch)
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
  moves: Move[];
  dims: OptionDims | null;
  score: number | null; // policy-weighted sum of dims; KEEP = 0
  projected_win_pct: number | null; // hot-slot defender vs the tormentor, duel model
  observed_win_pct: number | null; // same pairing, this match so far
  n_observed: number;
  blended_win_pct: number | null; // model prior (k=6 duels) + observed record
  blended_ci: [number, number] | null; // 90% Beta interval on the blended estimate
  tied: boolean; // within 0.03 of a neighbouring option's score
  out_of_position: boolean;
  model_version: string;
  synthetic: true;
  // added by the agent tools when options are broadcast
  incoming_name?: string | null;
  outgoing_name?: string | null;
  moves_named?: (Move & { name: string | null })[];
}

/** One leg of an option: on (bench -> slot), off (slot -> bench), move. */
export interface Move {
  player_id: string;
  from_slot: string | null;
  to_slot: string | null;
  kind: "on" | "off" | "move";
}

/** Option vs KEEP on six policy dimensions, each in [-1, 1] (positive = better). */
export interface OptionDims {
  L: number; // live form vs expected
  F: number; // fit
  M: number; // projected duel win vs current
  A: number; // attacking upside
  G: number; // game state
  R: number; // risk (negative = riskier)
}

// ---- subs advisor: matchups (backend/app/models/advisor.py) ---------------
// Duel outcomes are from the defender's side; win rates are fractions in [0, 1].

export type DuelOutcome = "won" | "lost" | "recovered" | "foul";
export type Confidence = "low" | "medium" | "high";

export interface DuelPoint {
  event_id: string;
  sec: number;
  x: number; // attacker's frame
  y: number;
  outcome: DuelOutcome;
  attacker_id: string;
  defender_id: string;
  terms: Record<string, number>; // stored qualifiers.duel (simulator model, uncalibrated)
}

export interface RollingPoint {
  sec: number;
  win_pct: number | null; // null when n == 0
  n: number;
}

export interface DuelLedger {
  attacker_id: string;
  defender_ids: string[];
  duels: number;
  won: number;
  lost: number;
  recoveries: number;
  fouls: number;
  win_pct: number | null;
  win_ci: [number, number] | null; // 95% Wilson interval; null below 5 duels
  window_sec: number; // asof - since + 1
  beaten: number; // lost without recovery (outright or then fouled)
  beaten_per_10: number | null; // null when the window is under 5 minutes
  channel_shots: number;
  channel_entries: number; // completed crosses / box entries from the channel
  channel_xg: number;
  defender_rating_swing: number | null;
  confidence: Confidence;
  points: DuelPoint[];
  rolling: RollingPoint[];
  evidence_event_ids: string[];
  synthetic: true;
}

export interface HotDuel {
  team_id: string;
  defender_id: string;
  defender_slot: string;
  attacker_id: string;
  beaten_20m: number;
  win_pct_20m: number | null;
  n_20m: number;
  first_fired_sec: number | null;
  // the slot's last 20' across every holder; the fields above are the CURRENT holder's own
  slot_beaten_20m: number;
  slot_n_20m: number;
  slot_win_pct_20m: number | null;
  synthetic: true;
}

export interface ImpactPoint {
  minutes: number;
  n: number;
  win_pct: number | null;
  beaten_per_10: number | null;
}

export interface SwapImpact {
  swap_sec: number;
  before: DuelLedger; // the 20 minutes before the swap
  after: DuelLedger; // since the swap
  win_separated: boolean; // the 95% intervals don't overlap: only then show a direction
  trajectory: ImpactPoint[]; // after-window at 5, 10, 20 minutes, once reached
  synthetic: true;
}

export interface RaceCurve {
  player_id: string;
  name: string;
  t: number[]; // seconds, 0..horizon
  d: number[]; // metres at each t (backend samples; the UI only interpolates)
  t5m: number;
  d1s: number;
  d2s: number;
}

export interface RaceResult {
  curves: RaceCurve[];
  gap1s: Record<string, number>; // metres vs the first curve (the tormentor)
  gap2s: Record<string, number>;
  reaction_s: number;
  label: string;
  synthetic: true;
}

export interface ImportanceItem {
  var_id: string;
  name: string;
  family: string;
  importance: number;
  rank: number;
  rank_lo: number | null; // best rank across the study's seeds
  rank_hi: number | null; // worst rank across the study's seeds
}

export type RadarAxis =
  | "pace" | "acceleration" | "agility" | "stamina" | "defending" | "stance" | "duel_win";
export const RADAR_AXES: RadarAxis[] = [
  "pace", "acceleration", "agility", "stamina", "defending", "stance", "duel_win",
];

export interface PlayerCard {
  player_id: string;
  name: string;
  slot: string | null; // current slot, null on the bench
  position: string;
  physical: PhysicalProfile;
  priors: PlayerPriors;
  // radar axes on 0-100. duel_win: projected % of 1v1s won vs the tormentor
  // (for the tormentor: projected % he wins vs the current defender)
  profile: Record<RadarAxis, number>;
}

/** GET /api/matches/{id}/bench: the assistant-coach page, clamped to the replay clock. */
/** What the alerted flank produced in the last 20 minutes. */
export interface FlankThreat {
  shots: number;
  xg: number;
  entries: number; // completed crosses / box entries
  threatening: boolean; // >= 1 shot or >= 2 entries
}

export interface BenchView {
  match_id: string;
  team_id: string;
  asof_sec: number;
  minute: number;
  score: Record<string, number>;
  alert: HotDuel | null; // sticky: the first hot duel up to asof, with current stats
  alert_active: boolean; // whether that duel is firing right now
  // none: no alert yet · active: firing · monitoring: new holder with < 4 own duels (KEEP only)
  // · cooling: fired earlier, not firing now
  alert_state: "none" | "active" | "monitoring" | "cooling";
  tormentor: PlayerCard | null;
  defender: PlayerCard | null; // current holder of the alerted slot
  ledger: DuelLedger | null;
  threat: FlankThreat | null;
  options: Recommendation[];
  cards: Record<string, PlayerCard>;
  race: RaceResult | null;
  impact: SwapImpact | null;
  executed_option_rank_at_alert: number | null;
  importance: ImportanceItem[];
  importance_note: string; // method, n, AUC and the methodology-demo caveat ("" if no study)
  slots: Record<string, string>; // our on-pitch players -> slot at asof (formation preview)
  disclosure: string; // what is pinned / scripted in this simulated demo (docs/schema.md §11)
  briefing_seed: string;
  briefing_evidence_ids: string[];
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
