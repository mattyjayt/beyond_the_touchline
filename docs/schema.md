# MVP Data Schema

Narrowed from the spec (`Inside_the_Game_Synthetic_Data_and_Schema_Specification.pdf`, §3–§7). Canonical contracts are the Pydantic models in `backend/app/models/`; `frontend/src/lib/types.ts` mirrors them.

> **Synthetic data.** Club and player names come from `backend/app/seed/premier_league_squads.json` (real reference data). Every match, event, rating, insight and recommendation is simulated and carries `synthetic: true` / `source_type: "synthetic_simulation"`.

## 1. Scope decisions

| Spec item | MVP decision | Why |
|---|---|---|
| 4 fictional clubs, ~100 players | **5 real PL clubs** (ARS, MCI, LIV, CHE, MUN), 20–25 real squad players each | Owner decision; abilities stay synthetic |
| 20 historical fixtures + 1 demo | **20 historical** (double round robin, 8 per club) + **1 demo** (`SIM-001`, ARS vs MCI) | Gives last-5 baselines; same generator |
| ~30–40k historical events | ~1.5–1.8k events/match → ~30–36k total | Matches spec volume |
| 14+ event types, 6 families | **12 types** (below) | Enough for ratings, alerts and sub advice |
| `possessions` table | `possession_id` column on events | Derivable; no extra writes |
| `match_player_stints` table | Derived from roster + `substitution` events | Avoids double bookkeeping |
| `tactical_states` table | Formation per side on `matches`; changes deferred | One formation per side in MVP |
| `player_match_metrics` table | Computed on demand, as-of any second | Derived, never independent truth |
| xG | Illustrative distance/angle model, labelled | Needed for shot quality |
| xT, pressure, keeper events, clearances/blocks | **Deferred** | Not needed for the demo story |
| Tracking data | **None.** Pitch dots are visual-only | Spec: no tracking-derived claims |

## 2. Identifiers

| Entity | Format | Example |
|---|---|---|
| Team | `T-<CODE>` | `T-ARS` |
| Player | `P-<CODE>-<shirt 2-digit>` | `P-ARS-07` |
| Match | `SIM-001` (demo), `SIM-H01..H20` (historical) | `SIM-001` |
| Event | `<match_id>-E<seq 4-digit>` | `SIM-001-E0101` |
| Possession | `<match_id>-P<seq 4-digit>` | `SIM-001-P0042` |
| Rating / Insight / Recommendation | `RAT-…`, `INS-<match>-<asof>-<n>`, `REC-<match>-<asof>-<rank>` | `REC-SIM-001-4020-1` |

## 3. Reference tables (seeded)

**teams** — `team_id` PK · `code` UNIQUE · `name` · `short_name` · `home_venue` · `primary_color` · `secondary_color` · `manager` · `default_formation` · `strength_index` (synthetic 0–1)

**players** — `player_id` PK · `team_id` FK · `display_name` · `shirt_number` · `primary_position` · `secondary_positions` JSON · `foot` · `archetype` · `priors` JSON (synthetic 0–100: `passing`, `dribbling`, `finishing`, `defending`, `physical`, `goalkeeping`)

Positions: `GK RB CB LB RWB LWB CDM CM CAM RM LM RW LW ST`.
Role groups (for ratings): `GK` · `DEF` (RB CB LB RWB LWB) · `MID` (CDM CM CAM RM LM) · `ATT` (RW LW ST).

## 4. Match tables (generated)

**matches** — `match_id` PK · `kind` (`historical`|`demo`) · `home_team_id` FK · `away_team_id` FK · `kickoff_at` · `status` (`scheduled`|`live`|`finished`) · `home_score` · `away_score` · `home_formation` · `away_formation` · `seed` · `generator_version` · `synthetic` (always true)

**match_rosters** — PK (`match_id`, `player_id`) · `team_id` FK · `roster_status` (`starter`|`bench`|`unavailable`) · `formation_slot` (e.g. `RW`, null on bench) · `shirt_number` · `available` · `reason`

**events** — append-only; see §5.

## 5. Event contract

| Field | Type | Rule |
|---|---|---|
| `event_id` | text PK | `SIM-001-E0101`; immutable |
| `match_id` | FK | existing match |
| `sequence_no` | int | unique, strictly increasing within match |
| `period` | int | 1 or 2 |
| `event_sec` | int | match clock seconds (P1 0–2700+, P2 2700–5400+); non-decreasing with `sequence_no` |
| `possession_id` | text? | null for period markers |
| `team_id` | FK | actor's team |
| `player_id` | FK? | actor; must be on the pitch at `event_sec` |
| `event_type` | enum | see below |
| `outcome` | enum | validated per type (below) |
| `start_x, start_y, end_x, end_y` | 0–100? | see §6 |
| `recipient_id` | FK? | pass target; incoming player for substitutions |
| `opponent_id` | FK? | matched opponent (spec's `defender_id`, generalised: defender on a take-on, attacker on a tackle, fouled player on a foul) |
| `body_part` | text? | shots only: `right_foot`, `left_foot`, `head` |
| `qualifiers` | JSON | typed per event type (below), versioned by `generator_version` |
| `source_type` | enum | always `synthetic_simulation` |

### Event types (12) and allowed outcomes

| Type | Outcomes | Qualifiers |
|---|---|---|
| `period_start` / `period_end` | `neutral` | — |
| `restart` | `neutral` | `restart_type`: `kickoff`, `goal_kick`, `corner`, `free_kick`, `throw_in` |
| `pass` | `success`, `fail` | `cross`, `through_ball` (bool) |
| `carry` | `success`, `fail` | — |
| `take_on` | `success`, `fail` | — (requires `opponent_id`) |
| `shot` | `goal`, `saved`, `blocked`, `off_target` | `xg` (illustrative), `assist_event_id`? |
| `tackle` | `success`, `fail` | — (requires `opponent_id`) |
| `interception` | `success` | — |
| `foul` | `neutral` | `card_event_id`? |
| `card` | `neutral` | `card`: `yellow`, `second_yellow`, `red` |
| `substitution` | `neutral` | — (`player_id` out, `recipient_id` in) |

**Derived tags, never separate events** (spec modelling rule): `key_pass` = successful pass whose recipient's next action in the same possession is a shot; `assist` = key pass on a `goal`; `progressive` = pass/carry that moves the ball ≥ 25 units closer to the opponent goal (threshold versioned).

## 6. Pitch coordinates

0–100 on both axes, **relative to the actor's attacking direction**: `x = 0` own goal line, `x = 100` opponent goal line; `y = 0` actor's right touchline, `y = 100` left. The UI converts to absolute coordinates with home attacking left→right: away events map to `(100 − x, 100 − y)`. Ends don't swap at half-time in the UI (display simplification).

## 7. Derived analytics (computed, as-of `asof_sec`)

**Player metrics** — `touches`, `passes_attempted`, `passes_completed`, `pass_accuracy`, `progressive_actions`, `take_ons_attempted`, `take_ons_won`, `shots`, `shots_on_target`, `goals`, `xg`, `key_passes`, `assists`, `tackles_won`, `interceptions`, `fouls`, `cards`, `minutes`.

**Team metrics** — `possession_pct` (by possession duration), `shots`, `shots_on_target`, `xg`, `passes`, `pass_accuracy`, `momentum` (rolling 5-min threat index: shots ×3 + final-third entries + successful take-ons, home minus away).

**ratings** (snapshots) — `rating_id` · `match_id` · `player_id` · `asof_sec` · `live_rating` (0–10) · `expected_rating`? (recency-weighted last-5 baseline at same role; prior matches only) · `form_delta` · `role_group` · `contributions` JSON (`[{event_id, delta, reason}]` — makes every rating explainable) · `low_confidence` (minutes < 15 or actions < 5) · `methodology_version`.

Rating v0 (illustrative, *not* Opta/Sofascore): base 6.0 + Σ bounded role-weighted event contributions, clipped to [0, 10]. Weights live in a versioned config.

## 8. Agent artefacts

**insights** — spec §8 contract: `insight_id`, `kind` (`momentum_shift`, `player_form`, `tactical_alert`, `substitution_opportunity`, `key_moment`), `match_id`, `asof_sec`, `audience` (`fan`|`analyst`), `headline`, `explanation`, `evidence_event_ids` (non-empty, must exist), `recommendation_id`?, `uncertainty`, `generator_version` (`rules-v0`, `claude-code`, `foundry-…`), `synthetic: true`.

**recommendations** — spec §7 option fields: `rec_id`, `match_id`, `team_id`, `asof_sec`, `option_rank`, `option_type` (`keep`|`substitution`), `outgoing_player_id`?, `incoming_player_id`?, `eligibility_status`, `attack_delta_estimate`, `control_delta_estimate`, `defensive_risk_delta`, `tactical_fit_score`, `confidence` (`low`|`medium`|`high`, heuristic not probability), `pros`, `cons`, `supporting_event_ids`, `model_version`. A KEEP option is always present.

## 9. Stream contract (SSE `GET /api/matches/{id}/stream`)

Each message is `{"type": ..., "data": ...}`:

| `type` | `data` | When |
|---|---|---|
| `event` | `MatchEvent` | each replayed event |
| `state` | `MatchState` (clock, score, team metrics, on-pitch players, ratings) | every 30 match-seconds and after material events |
| `insight` | `Insight` | when an agent publishes |
| `recommendation` | `Recommendation[]` (+ `incoming_name`/`outgoing_name`) | after a substitution evaluation |
| `control` | `{status: playing|paused|finished, speed, clock_sec}` | replay control changes |
| `snapshot` | `{control, events[], state, insights[]}` (history up to the clock) | on connect and after a seek |

## 10. Validation (generator gate)

Mirrors spec §9: FK integrity · chronology (sequence/clock monotonic, no events after `period_end`) · presence (actor on pitch; subs from bench, ≤ 5 subs, no re-entry) · possession changes only on failed pass/carry/take-on, successful tackle/interception, shots, restarts · scoring (`goal` count = match score) · per-type outcome validity · coordinates in [0, 100] · reproducibility (same seed ⇒ same event hash).
