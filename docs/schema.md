# MVP Data Schema

Narrowed from the spec (`Inside_the_Game_Synthetic_Data_and_Schema_Specification.pdf`, §3–§7). Canonical contracts are the Pydantic models in `backend/app/models/`; `frontend/src/lib/types.ts` mirrors them.

> **Synthetic data.** Club and player names come from `backend/app/seed/premier_league_squads.json` (real reference data). Every match, event, rating, insight and recommendation is simulated and carries `synthetic: true` / `source_type: "synthetic_simulation"`.

## 1. Scope decisions

| Spec item | MVP decision | Why |
|---|---|---|
| 4 fictional clubs, ~100 players | **5 real PL clubs** (ARS, MCI, LIV, CHE, MUN), 20–25 real squad players each | Owner decision; abilities stay synthetic |
| 20 historical fixtures + 1 demo | **20 historical** (double round robin, 8 per club) + **1 demo** (`SIM-001`, LIV vs MCI; storyline in §11) | Gives last-5 baselines; same generator |
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

**players** — `player_id` PK · `team_id` FK · `display_name` · `shirt_number` · `primary_position` · `secondary_positions` JSON · `foot` · `archetype` · `priors` JSON (synthetic 0–100: `passing`, `dribbling`, `finishing`, `defending`, `physical`, `goalkeeping`) · `physical` JSON (synthetic, real units: `top_speed_kmh` 29–37.4, `accel_ms2` 6.0–7.9, `agility_idx`, `stamina_idx`, `stance_idx` (side-on tendency), `height_cm`; derived `speed_idx`, `accel_idx`, `time_0_5m_s`). Demo players' values are pinned (`squads.py`: `PINNED_PHYSICAL`, `PINNED_PRIORS`).

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

### Event types (13) and allowed outcomes

| Type | Outcomes | Qualifiers |
|---|---|---|
| `period_start` / `period_end` | `neutral` | — |
| `restart` | `neutral` | `restart_type`: `kickoff`, `goal_kick`, `corner`, `free_kick`, `throw_in` |
| `pass` | `success`, `fail` | `cross`, `through_ball` (bool) |
| `carry` | `success`, `fail` | — |
| `take_on` | `success`, `fail` | `duel`: `{tech, burst, agil, stance, touch, ctx, script, z, p_beat, p_recover}` (duel model `duel-v2`, uncalibrated; `script` ≠ 0 only in the demo window) (requires `opponent_id`) |
| `shot` | `goal`, `saved`, `blocked`, `off_target` | `xg` (illustrative), `assist_event_id`? |
| `tackle` | `success`, `fail` | `recovery` (bool: the beaten defender won it straight back) (requires `opponent_id`) |
| `interception` | `success` | — |
| `foul` | `neutral` | `card_event_id`? |
| `card` | `neutral` | `card`: `yellow`, `second_yellow`, `red` |
| `substitution` | `neutral` | — (`player_id` out, `recipient_id` in) |
| `position_change` | `neutral` | `from_slot`, `to_slot` (`player_id` moves; `recipient_id` = swap partner). A swap is two events at the same second. Both players on the pitch; one player per slot after the second; not a substitution; no possession change. |

**Derived tags, never separate events** (spec modelling rule): `key_pass` = successful pass whose recipient's next action in the same possession is a shot; `assist` = key pass on a `goal`; `progressive` = pass/carry that moves the ball ≥ 25 units closer to the opponent goal (threshold versioned).

## 6. Pitch coordinates

0–100 on both axes, **relative to the actor's attacking direction**: `x = 0` own goal line, `x = 100` opponent goal line; `y = 0` actor's right touchline, `y = 100` left. The UI converts to absolute coordinates with home attacking left→right: away events map to `(100 − x, 100 − y)`. Ends don't swap at half-time in the UI (display simplification).

## 7. Derived analytics (computed, as-of `asof_sec`)

**Player metrics** — `touches`, `passes_attempted`, `passes_completed`, `pass_accuracy`, `progressive_actions`, `take_ons_attempted`, `take_ons_won`, `shots`, `shots_on_target`, `goals`, `xg`, `key_passes`, `assists`, `tackles_won`, `interceptions`, `fouls`, `cards`, `minutes`.

**Team metrics** — `possession_pct` (by possession duration), `shots`, `shots_on_target`, `xg`, `passes`, `pass_accuracy`, `momentum` (rolling 5-min threat index: shots ×3 + final-third entries + successful take-ons, home minus away).

**ratings** (snapshots) — `rating_id` · `match_id` · `player_id` · `asof_sec` · `live_rating` (0–10) · `expected_rating`? (recency-weighted last-5 baseline at same role; prior matches only) · `form_delta` · `role_group` · `contributions` JSON (`[{event_id, delta, reason}]` — makes every rating explainable) · `low_confidence` (minutes < 15 or actions < 5) · `out_of_position` (slot is neither primary nor secondary) · `methodology_version`. Weights use the role group of the slot held at each event's time.

**Duel ledger** (`services/matchups.py`, as of `asof`) — one attacker vs a defending slot (follows whoever holds it) or a defender: `duels`, `won` (fails + recoveries), `lost`, `recoveries`, `fouls`, `win_pct`, `beaten`, `beaten_per_10`, `channel_shots`/`channel_xg` (possessions with the attacker's successful take-on/carry in the guarded channel), `defender_rating_swing`, `confidence` (n < 4 low, 4–9 medium, 10+ high), `points` (with stored duel terms), `rolling` (10-min win %, every 60 s). **Hot duel** trigger: beaten ≥ 6 in 20 min, or win % ≤ 30% with n ≥ 8.

Rating v0 (illustrative, *not* Opta/Sofascore): base 6.0 + Σ bounded role-weighted event contributions, clipped to [0, 10]. Weights live in a versioned config.

## 8. Agent artefacts

**insights** — spec §8 contract: `insight_id`, `kind` (`momentum_shift`, `player_form`, `tactical_alert`, `substitution_opportunity`, `key_moment`), `match_id`, `asof_sec`, `audience` (`fan`|`analyst`), `headline`, `explanation`, `evidence_event_ids` (non-empty, must exist), `recommendation_id`?, `uncertainty`, `generator_version` (`rules-v0`, `claude-code`, `foundry-…`), `synthetic: true`.

**recommendations** — spec §7 option fields: `rec_id`, `match_id`, `team_id`, `asof_sec`, `option_rank`, `option_type` (`keep`|`substitution`|`position_swap`|`sub_and_swap`), `outgoing_player_id`?/`incoming_player_id`? (leaving/entering the hot slot), `eligibility_status`, `attack_delta_estimate`, `control_delta_estimate`, `defensive_risk_delta`, `tactical_fit_score`, `confidence` (`low`|`medium`|`high`: lowest of evidence, slot-history and fit bands; heuristic, not a probability), `pros`, `cons` (quote numbers), `supporting_event_ids`, `moves` (`[{player_id, from_slot, to_slot, kind: on|off|move}]`), `dims` (`L F M A G R` in [−1, 1], vs KEEP), `score` (policy-weighted sum; KEEP = 0), `projected_win_pct` (duel model vs the tormentor, k=6 shrinkage to observed), `observed_win_pct`, `n_observed`, `out_of_position`, `model_version` (`advisor-v1`). A KEEP option is always present; KEEP + up to 4 others.

**Bench view** (`GET /api/matches/{id}/bench?team_id=&asof_sec=`, clamped to the replay clock) — `alert` (sticky: the first hot duel, tracked as the slot changes hands) + `alert_active`, `tormentor`/`defender`/`cards` (radar profiles, 7 axes 0–100), `ledger`, `options`, `race` (0–3 s sprint curves), `impact` (20′ before vs since the latest `position_change` of the slot), `executed_option_rank_at_alert`, `importance` + `importance_note` (duel study, methodology demo), `slots`, `briefing_seed`, `briefing_evidence_ids`, `synthetic: true`.

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

## 11. Demo match `SIM-001` (simulated storyline, sim-v0.3)

> Everything below is **simulated**. The players are real reference names; the match, the duels and the outcome are synthetic.

**Recorded generation** (`uv run python -m app.sim.generate`, `SIM_SEED=2026`, `generator_version sim-v0.3`, duel model `duel-v2`):

| | |
|---|---|
| Demo seed | `2036` (search started at `SIM_SEED`; first seed that passed) |
| `script_boost` | `6` (lowest of the candidates 6, 8, 10, 12) |
| Demo event hash | `43aa8e2470adea9e` |
| Final score | Liverpool 1-0 Manchester City |

**Setup** (`app/sim/generate.py::demo_scenario`): Liverpool are at home. Frimpong (`P-LIV-30`) is forced to RB, Szoboszlai (`P-LIV-08`) to RW and Doku (`P-MCI-11`) to LW. Gomez (`P-LIV-02`) and Bradley (`P-LIV-12`) are forced onto the bench.

**What is scripted:**
- From 50' (3000 s) to full time, Doku is the focus player. He gets more of the ball and attempts more take-ons, and he always meets whoever holds Liverpool's RB slot.
- The duel `script` term (+6 to the logit numerator, so +0.6 to z) applies **only** while Frimpong holds RB. It is stored on every take-on as `qualifiers.duel.script`.
- Spec 3.4 follow-up: after a scripted take-on win in the RB channel, Doku's next action has its shot weight doubled and gains a cross option.
- At 70' (4200 s) Liverpool swap Szoboszlai and Frimpong (two `position_change` events at 4200 s). This happens whatever the advisor ranks. Liverpool make no substitutions before 75'; normal auto-subs follow.
- **After the swap, the pairing is still forced but the outcomes are not scripted.** Doku still meets the RB holder (now Szoboszlai) at the same rate, but `script` is 0. Every post-swap duel is decided by the duel model alone.

**How the seed was chosen.** The search loops over `script_boost` (outermost) and then seeds `SIM_SEED..SIM_SEED+499`. It keeps the first demo that meets all of these:
- Doku beats Frimpong at least 6 times between 50' and 70'.
- The generic `hot_duels` trigger for Liverpool first fires between 55' and 68' (3300–4080 s), on (RB, Doku).
- Liverpool are level or exactly one goal behind when it fires.
- Neither team has had a player sent off before 70', so it is 11 v 11 at the alert.

Before the search it also checks, once, that Szoboszlai and Gomez match or beat Frimpong on accel and stance (the defensive physical index). This is reference data, so it does not depend on the seed.

**Disclosure: the seed search never inspects post-swap events.** Every criterion is evaluated on the events before 4200 s (`generate.py::storyline`), so what happens after the swap cannot influence which seed is chosen. The search only fails loudly if the forced swap did not happen (for example after a red card); it never moves on to another seed for that reason.

**What the recorded demo shows** (derived from events):
- Between 50' and 70', Doku took on Frimpong 11 times and won 10.
- The trigger first fired at 3714 s (61.9'): (RB Frimpong vs Doku), beaten 5 of 8 in 20 minutes, defender win rate 25%. The score was 0-0. Frimpong was booked at 3725 s.
- After the swap, Szoboszlai's duels against Doku are unscripted, and the samples are small. The swap-impact panel compares the 20 minutes before the swap with the time since it (equal-footing windows):
  - Defender win rate: Frimpong 21% (n=14) before, Szoboszlai 47% (n=19) after.
  - Duels lost per 10 minutes: 4.0 before, 5.0 after (Doku took him on more often).
  - Channel shots: 0 before, 1 after (xG 0.01).
  - Liverpool scored at 4580 s (76:20) and won 1-0. This is not attributed to the swap.

**Calibration (pre-registered, sim-v0.3).** These settings were fixed using only league-wide data from the 20 historical matches and model projections, never demo outcomes after the swap:
- Frimpong's defending prior is pinned to 68 (spec 3.1: "modest").
- The duel model subtracts a baseline (`DUEL_BASELINE = 12`) inside z. That is the smallest integer that puts historical take-on success in 45–52%; it is now 50.9%, against 64.8% before.
- Cards: a straight red is 0.15% per foul, and a booked player's chance of another card is scaled by 0.1 (`SECOND_YELLOW_FACTOR`). Historical dismissals fell from 0.8 to about 0.05 a match (the target was ≤ 0.2).
- The hot-duel trigger is beaten ≥ 6 in 20 minutes, or a defender win rate ≤ 30% with n ≥ 8. These were the first pre-listed thresholds to pass the rarity test, which checks every second and allows the trigger to fire in no more than 3 of the 20 historical matches. It now fires in none of them.
- The demo seed search was then re-run with two added pre-swap criteria (11 v 11, level or one behind).

**Advisor rankings after the review fixes (advisor-v1, same data).** Every option is scored as a change against KEEP; near-ties (within 0.03) are flagged. A new RB holder is monitored (KEEP only) until he has 4 duels of his own.

| As of | Alert state | Ranking (policy score vs KEEP) |
|---|---|---|
| 3714 s (61') | active | 1) Szoboszlai to RB, Frimpong off, Chiesa on at RW (+0.31); 2) Gomez for Frimpong (+0.25, tied); 3) Swap: Szoboszlai to RB, Frimpong to RW (+0.23, tied); 4) Bradley for Frimpong (+0.14); 5) KEEP |
| 4200 s (70') | monitoring | KEEP only (Szoboszlai has no duels at RB yet) |
| 4800 s (80') | active | 1) Gomez for Szoboszlai (+0.24); 2) Swap: Endo to RB, Szoboszlai to LDM (+0.16); 3) Endo to RB, Szoboszlai off, Mac Allister on at LDM (+0.11); 4) Bradley for Szoboszlai (+0.08); 5) KEEP |
| 5400 s (90') | active | 1) Gomez for Szoboszlai (+0.01, tied); 2) KEEP (tied); 3) Bradley for Szoboszlai; 4) Swap: Leoni to RB, Szoboszlai to RCB; 5) Leoni to RB, Szoboszlai off, Gomez on at RCB |

The swap Liverpool make at 70' was ranked #3 at the alert, level with #2.

**Full chronology of the demo seed (disclosure).** The demo went through three seeds. Every change had a pre-swap reason on record, but every re-run happened after the previous seed's post-swap result had been seen, and each one moved the post-swap result in the story's favour. A reviewer flagged this pattern; it is listed here so readers can judge it.

| Step | Change | Demo seed | Post-swap result (RB win % vs Doku) |
|---|---|---|---|
| 1 | sim-v0.2, first search | 2029 | Szoboszlai 30% (n=10) vs Frimpong 42% (n=19): the swap underdelivered |
| 2 | Owner chose recalibration: Frimpong's defending prior **pinned** from 84 to 68 (spec: "modest"), duel baseline added, hot-duel thresholds tightened | 2027 | 29% → 44% |
| 3 | Seed 2027 had Liverpool down to 9 men by 53'; card rates fixed, baseline re-derived, two pre-swap criteria added (11 v 11, level or one behind) | 2036 | 21% (n=14) → 47% (n=19) |

- The profiles of Doku, Frimpong, Szoboszlai, Gomez and Bradley are **pinned** (fictional values, `squads.py`), chosen for the storyline.
- Doku's take-on volume and his pairing with whoever holds RB stay **scripted** after the swap; only the outcomes are unscripted.
- While Frimpong holds RB in the window, a `script` handicap of +6 on the logit numerator (+0.6 z) applies.

