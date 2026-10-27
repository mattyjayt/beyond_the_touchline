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

## 11. Demo match `SIM-001` (simulated storyline, sim-v0.4)

> Everything below is **simulated**. The players are real reference names; the match, the duels and the outcome are synthetic.

### Current demo (sim-v0.4, duel-v3, advisor-v2)

Generated by `uv run python -m app.sim.generate` (`SIM_SEED=2026`) after the Phase B calibration (`uv run python -m app.sim.calibrate`; pre-registration, amendments A1/A2 and outcomes at the end of this section).

| | |
|---|---|
| Demo seed | `2055` (`script_boost` 6) |
| Demo event hash | `433dcd7e7ca6f381` |
| Final score | Liverpool 0-1 Manchester City (City score at 80:45) |
| Hot-duel trigger | ≥ 3 beaten possessions, P(win rate < league 0.610) ≥ 0.95 (Beta prior worth 6 duels), flank threat, over 20' |

**What the demo shows** (derived from events):
- Between 50' and 70', Doku beats Frimpong in 6 distinct possessions (8 of 9 take-ons).
- The alert first fires at 3333 s (55.5'), score 0-0: Frimpong beaten in 4 possessions (n=5, 0 won), P(below league) 0.97, no shots from the flank yet but 8 crosses/box entries.
- The advisor (shortlist) at the alert: 1) Gomez for Frimpong; 2) Swap: Leoni to RB, Frimpong to RCB; 3) Bradley for Frimpong; 4) Leoni to RB, Frimpong off, Gomez on at RCB (all four within 0.03: tied); 5) KEEP.
- At 70' (4223 s, the next stoppage) Liverpool make the scripted swap: Szoboszlai to RB, Frimpong to RW. Among the 17 options the advisor scored at the alert, this swap ranked **9th, below KEEP**. The page says so.
- After the swap (KEEP only while Szoboszlai has fewer than 4 duels at RB): Szoboszlai wins 6 of 9 (67%) against Frimpong's 2 of 9 (22%) in the 20' before; duels lost per 10' 2.50 → 1.02; channel shots 1 → 1 (xG 0.05 → 0.09). The after-swap channel shot is City's 80:45 goal (Samba), in a possession where Doku had beaten Szoboszlai in the channel. The 95% intervals overlap.

| As of | Alert state | Advisor ranking (policy score vs KEEP) |
|---|---|---|
| 3333 s (55') | active | 1) Gomez for Frimpong (+0.25); 2) Swap: Leoni to RB, Frimpong to RCB (+0.22); 3) Bradley for Frimpong (+0.17); 4) Leoni to RB, Frimpong off, Gomez on at RCB (+0.15), all tied; 5) KEEP |
| 4223 s (70') | monitoring | KEEP only |
| 4800 s (80') | cooling | 1) Gomez for Szoboszlai (+0.03); 2) KEEP (tied); 3) Swap: Leoni to RB, Szoboszlai to RCB (tied); 4) Bradley for Szoboszlai (tied); 5) Leoni to RB, Szoboszlai off, Gomez on at RCB |
| 5400 s (90') | cooling | 1) Swap: Gomez to RB, Szoboszlai to RCB (+0.08); 2) Bradley for Szoboszlai (tied); 3) KEEP (tied); 4) Gomez to RB, Szoboszlai off, Bradley on at RCB; 5) Swap: Mac Allister to RB, Szoboszlai to LDM |

**Disclosures for this demo:**
- **Pinned profiles:** Doku, Frimpong, Szoboszlai, Gomez and Bradley have pinned (fictional) profiles, and Frimpong's defending prior is pinned to 68.
- **Scripted:** from 50', Doku's take-on volume and his pairing with the RB holder are scripted. The +0.6 z handicap applies while Frimpong holds RB.
- **Doku's volume is a busy draw.** In this demo he makes 42.8 take-ons per 90 in the scripted window. With the final settings, the scenario averages 18.6 over 50 ordinary seeds (median 18.5, 90th percentile 31.8, max 55.6). That is slightly above the pre-registered cap of 18, which was checked on seeds 1–5 only (13.1 there). The real Doku manages about 10. The seed search favours busy matches, because its pre-swap criteria need repeated beats.
- **The demo seed changed four times:** 2029 → 2027 → 2036 → 2055 (chronology below).
- **The trigger form changed twice** after its pre-registration: A1 by arithmetic before any run; A2 at the owner's request after A1 failed.

*The sim-v0.3 material below is kept as history.*

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

**Phase B pre-registration (written before any Phase B run, 2026-10-26).** Source: review consensus §2. Everything below is fixed before the first simulation; nothing is loosened after seeing results.

1. **Versions.** `GENERATOR_VERSION` sim-v0.4, duel `MODEL_VERSION` duel-v3, `ADVISOR_VERSION` advisor-v2.
2. **Burst in metres.** `burst = d_att(1 s) − d_def(1 s)` from the sprint model (reaction 0.25 s), with fatigue applied to A0 (m/s²). Its z coefficient β = ln(1.5) / Δd, where Δd is the 1 s gap between A0 7.4 and 6.9 m/s² at 33 km/h: an A0 edge of 0.5 m/s² at equal top speed is worth odds × 1.5. β is computed once from this formula, not tuned.
3. **One agility term.** The technique term drops the defender-agility share (agility only enters through `agil`). Fatigue scales A0 in m/s² and the agility index.
4. **One time-to-5 m model.** `PhysicalProfile.time_0_5m_s` uses the sprint model.
5. **Sampling.** A0 means by position from the research report (CB 6.79, FB 6.70, CM/DM/AM 6.44, W/ST 6.40, GK 6.0), σ 0.35 m/s², speed↔A0 ρ = 0.6, clipped to [6.0, 7.9]; pinned values are validated.
6. **Cards.** A last-line foul after the defender is beaten is a stop-a-promising-attack foul: yellow p = 0.8 (scaled by `SECOND_YELLOW_FACTOR` for an already-booked offender). If the duel point is central (attacker-frame y 30–70) and within about 25 m of goal (x ≥ 76), it is a red with p = 0.1 instead (DOGSO). Check: historical dismissals ≤ 0.2 per match pooled over SIM_SEED 1–5; if not, `SECOND_YELLOW_FACTOR` is the first of [0.1, 0.05] that passes.
7. **League calibration.** `DUEL_BASELINE` is the smallest integer giving mean historical take-on success over SIM_SEED 1–5 in [0.34, 0.40] (real league 36.7%) with each seed in [0.30, 0.44]. The league defender win rate m is then measured at that baseline over the same seeds and fixed as a constant.
8. **Volume.** Measured on the demo scenario's line-ups simulated with SIM_SEED 1–5 (not the chosen demo seed): Doku's take-on attempts per 90 while the scenario is active. Scan `pass_to_focus_mult` in [4.0, 3.0, 2.0, 1.5, 1.0] (outer) and `take_on_freq_mult` in [2.5, 2.0, 1.5, 1.0] (inner); the first pair with mean ≤ 18 per 90 wins. (The consensus named only `take_on_freq_mult`; the engine also scales passes to Doku, so both levers are pre-registered here, in this order.)
9. **Counting.** At most one "beaten" per possession in the ledger and the trigger. In the engine, a follow-up take-on by the focus player in the same possession meets `nearest()`, not the scripted marker.
10. **Trigger.** Over the last 20' for the current holder, all of:
    - beaten in ≥ 3 distinct possessions;
    - posterior P(defender win rate < 0.30) ≥ q, Beta prior with k = 6 centred on m;
    - channel threat: ≥ 1 shot or ≥ 2 completed crosses / box entries from that flank.

    q is the first of [0.80, 0.85, 0.90] that keeps the firing rate ≤ 5% of historical matches pooled over SIM_SEED 1–5 (100 matches). If none passes, report it and keep sim-v0.3.
11. **Demo seed search** (pre-swap events only): Doku beats the RB holder in ≥ 3 distinct possessions between 50' and 70'; the trigger first fires 55'–68' on (RB, Doku); 11 v 11 at the alert; level or one behind; `script_boost` from [6, 8, 10, 12], seeds SIM_SEED..+499. The post-swap result is reported as it comes out.
12. **If no seed passes:** report it and keep sim-v0.3 (owner decision 3a). No criterion is loosened after seeing results.

**Amendment A1 to item 10 (owner decision, 2026-10-27, written before any trigger code or match run).** Arithmetic on the rules alone showed item 10 could not fire under item 8: at the calibrated volume (12.7 take-ons per 90, about 2.8 duels per 20') the posterior P(win rate < 0.30) needs 11–14 straight losses. Calibration results already fixed before this amendment: `SECOND_YELLOW_FACTOR` 0.1, `DUEL_BASELINE` 16, league defender win rate m = 0.608, `DEMO_PASS_MULT` 4.0, `DEMO_TAKE_ON_MULT` 1.5. The trigger is now "worse than a league-average defender": over the last 20' for the current holder, all of
- beaten in ≥ 3 distinct possessions;
- posterior P(defender win rate < m = 0.608) ≥ q, Beta prior with k = 6 centred on m;
- channel threat: ≥ 1 shot or ≥ 2 completed crosses / box entries from that flank.

q is the first of [0.80, 0.85, 0.90] that keeps the firing rate ≤ 5% of historical matches pooled over SIM_SEED 1–5 (100 matches). Items 11–12 are unchanged.

**Phase B outcome (2026-10-27): stopped by the pre-registered rule; sim-v0.3 stays.** Calibration ran in the pre-registered order (`uv run python -m app.sim.calibrate`):
- item 6: `SECOND_YELLOW_FACTOR` 0.1 kept (0.19 dismissals a match, limit 0.2);
- item 7: `DUEL_BASELINE` 16 (take-on success 39.2% mean over SIM_SEED 1–5, every seed in band), league defender win rate m = 0.608;
- item 8: `DEMO_PASS_MULT` 4.0, `DEMO_TAKE_ON_MULT` 1.5 (12.7 take-ons per 90);
- item 10 (amendment A1): the trigger fires in 32, 25 and 8 of 100 historical matches for q = 0.80, 0.85 and 0.90. None meets the 5% limit.

No q passed, so by items 10 and 12 no demo seed search was run and the demo stays at sim-v0.3. No criterion was loosened after seeing these results. The finding: with real-world volume (about 3 duels per 20'), a "worse than an average defender" signal with flank threat is either too slow to be sure or fires too often by chance; three straight beats happen to ordinary defenders too.

**Amendment A2 (owner request after A1 failed, 2026-10-27, written before any further run).** The owner asked for Phases A and B in a demo state. A2 is decided after seeing A1's result, so it is disclosed as such. It keeps A1's trigger form (≥ 3 beaten possessions, posterior P(win rate < m = 0.608) ≥ q with k = 6, and flank threat) and all of items 6–8 as already calibrated. Only the trigger window W and q come from a fixed grid, tried in this order:

| Order | W | q |
|---|---|---|
| 1 | 20' | 0.90 |
| 2 | 20' | 0.95 |
| 3 | 30' | 0.90 |
| 4 | 30' | 0.95 |

- A grid point is eligible only if the trigger fires in ≤ 5% of historical matches pooled over SIM_SEED 1–5.
- The first eligible point for which item 11's demo seed search (pre-swap criteria only, unchanged apart from "beats" meaning ≥ 3 distinct possessions) finds a seed is used.
- If none does, Phase B stays shelved and sim-v0.3 stays.
- The post-swap result is reported as it comes out.
- Texts that say "20'" follow W.

**A2 outcome (2026-10-27).** The grid ran in order.
- W = 20', q = 0.90 fired in 7 of 100 historical matches, so it was not eligible.
- W = 20', q = 0.95 fired in 2 of 100 and the demo search found seed 2055, so that point was used.
- Before the final run, item 6's dismissal check was re-applied to the final configuration: 0.21 per match exceeded 0.2, so `SECOND_YELLOW_FACTOR` became 0.05 (0.17 per match).
- Items 7, 8 and A2 were then re-run in order with unchanged rules: the same baseline (16), the same volume levers (13.1 per 90), m = 0.610, and the same selection.

The post-swap result is reported above as it came out.

