# Subs Advisor ("Assistant Coach"): design

> Everything here is **simulated**. Club and player names are real reference data; every ability,
> physical value, event, rating and recommendation is fictional and labelled so. Real-world ranges
> come from `reports/Football matchup variables catalogue.md`.

## 1. Intent

Turn the MVP's thin substitution helper into its flagship: a sideline **assistant coach** that spots a
losing individual duel, explains it with evidence, and recommends the best fix. The fix can be a
substitution, a **position swap** between players already on the pitch, or keeping things as they are.
The point is to show what fusing event processing, ratings, history and physical profiles can do.
Everything outside the advisor stays as is until greenlight. **Scope: build all of it** (owner, no
time cap).

**The story (demo `SIM-001`, LIV 4-2-3-1 home vs MCI 4-2-3-1):**
- From about 50', Doku (MCI LW, direct winger) repeatedly beats Jeremie Frimpong (LIV RB, attacking full-back). City's chances come down that flank. Frimpong pushes high and is chasing back in transition.
- The generic hot-duel trigger raises the alert (the seed search makes it fire between 55' and 68').
- It offers:
  - **KEEP**
  - **SUB**: Joe Gomez (CB, RB secondary, stopper) or Conor Bradley (RB) for Frimpong
  - **SWAP, the "Bale move"**: Szoboszlai (CM, starting at RW, RB secondary) drops to RB and Frimpong moves up to RW (a listed secondary). It uses no substitution, rebuilds a midfielder as a defensive full-back, and adds Frimpong's pace in attack.
- The thesis is preventative over reactive. Szoboszlai's acceleration and stance win the first 2 seconds, while Frimpong relies on top speed to recover *after* being beaten. Research supports this: top speed alone does not predict 1v1 wins; acceleration, closing speed, distance and stance do.
- At about 70' the scripted replay **actually performs the swap** (two `position_change` events), so the before and after are real event data.
- This **replaces** the ARS vs MCI Saka/Aït-Nouri storyline. The rules agent, tests and UI copy are updated to match.

## 2. Goals / non-goals / anti-goals

**Goals**
- A physical profile per player, used by a new duel model in the engine (sim-v0.2).
- A `position_change` event, end to end: engine, validator, ratings and pitch dots.
- Deterministic, tested services: matchup map, flank duel ledger, advisor (KEEP / SUB / SWAP / SUB+SWAP), sprint race.
- A catalogue of 100+ variables, plus a simulation study ranking the top 25.
- An in-depth, interactive page at `/match/SIM-001/bench` with ten visual panels.
- An AI briefing through Claude, with a rules fallback.

**Non-goals**
- Formation changes
- Claims that a winger tracks back or presses (no off-ball data)
- WebGL 3D (CSS 3D is used)
- Multi-seed counterfactual distributions
- An away-team advisor UI

**Anti-goals**
- **Planted discoveries.** The scripted boost applies only while Frimpong is the defender in the RB slot. It is stored on every duel event as a visible `script` term. Outcomes after the swap come from priors alone. The seed search never looks at what happens after the swap, and if the swap underdelivers, the page says so.
- **False precision.** Deltas are shown as bands or arrows with their sample size, never as causal claims.
- **LLM arithmetic.** The LLM never does arithmetic and never reorders the ranking.
- **Pitch dots as data.** Nothing is derived from the pitch dots.

## 3. Data model (sim-v0.2)

### 3.1 Physical profile: `Player.physical: PhysicalProfile`

Real units are the source. 0–100 indices are derived for the engine by linear maps.

| field | unit / range (elite PL) | index map | engine use |
|---|---|---|---|
| `top_speed_kmh` | 29.0–37.4 | 29→0, 37→100 | recovery roll (km/h directly) |
| `accel_ms2` | 6.0–7.9 max | 6.0→0, 7.9→100 | `burst` term |
| `time_0_5m_s` | derived: `sqrt(2·5/accel)` + 0.25 reaction | display | race strip |
| `agility_idx` | 0–100 | — | change-of-direction term |
| `stamina_idx` | 0–100 | — | fatigue decay |
| `stance_idx` | 0–100 (tendency to defend side-on) | — | mean of the per-duel stance draw |
| `height_cm` | 165–200 | — | descriptive only |

- **Sampling:** values are drawn from a position × archetype table with speed↔accel ρ≈0.6, seeded through `squads.py`.
- **Pinned demo values** (fictional, but within the research ranges):

| Player | Profile |
|---|---|
| Doku | Top accel; 35.1 km/h; elite agility |
| Frimpong | Very high top speed; accel below Doku's; low stance; modest defending |
| Szoboszlai | Lower top speed, higher accel, high stamina, good stance |
| Gomez | Good accel and stance, stopper |
| Bradley | Balanced |

### 3.2 Duel model: pure `duel_prob()` in `app/sim/duel.py`

It replaces `p_ok` in `engine.take_on` and is shared with the study and the advisor.

```
tech   = drib_A − (0.7·def_D + 0.3·agil_D)                 # 0–100 indices
burst  = acc_idx_A − acc_idx_D                             # first-2s separation
agil   = agil_A − agil_D
stance = per-duel draw ~ clamp(N(stance_idx_D/100, 0.15), 0, 1)   # side-on = 1
touch  = distance of duel point to nearest touchline (0–50, from coords)
ctx    = +8 if D isolated (no team-mate slot within 15u)
         +6·(1 − stance)                                   # square-on concedes
         −4·(1 − touch/50)                                 # touchline helps D
         +6 if D is an attacking/inverted full-back and possession < 8 s old (transition)
         +4 if D on a yellow
         −6 if a covering team-mate is within 10u
script = +S only while the Scenario marker is the defender in the marked slot (demo only)
z      = (0.5·tech + 0.4·burst + 0.1·agil + ctx + script) / 10
fat(p) = 1 − 0.004·max(0, mins_on − 55)·(100 − stamina)/20     (scales accel + agility idx)
p_beat = clamp(0.85·σ(z), 0.05, 0.9)
if beaten: p_recover = clamp(0.10 + 0.04·(spd_D_kmh − spd_A_kmh + 2), 0.03, 0.35)
           → recovered: late tackle by D (success)
           → not recovered and D is last line: 25% foul (card risk)
```

- All terms are stored on the take-on event in `qualifiers.duel = {tech, burst, agil, stance, touch, ctx, script, p_beat, p_recover?}`.
- The advisor quotes these stored terms and never recomputes them.
- Labelled "simulator model, uncalibrated".

### 3.3 `position_change` event

- **Contract:**
  - `event_type="position_change"`, `outcome="neutral"`.
  - `player_id` is the mover and `recipient_id` the swap partner (nullable).
  - `qualifiers {from_slot, to_slot, recommendation_id?}`.
  - A swap is two events at the same second, with consecutive `sequence_no`.
- **Validator rules:**
  - Both players are on the pitch.
  - `from_slot` is the player's current slot.
  - `to_slot` is in the formation.
  - The slot map is one player per slot after the group of events at that second.
  - It does not count toward the 5 subs and does not change possession.
- **Ratings:**
  - Weights use the role group of the **slot occupied** at each event's time.
  - `Rating.out_of_position` is true when the slot position is neither the player's primary nor a secondary position.
  - Same-slot history is used, so n=0 means low confidence and an "experimental role" label.
- **Pitch dots:** the UI reads current slots from `position_change` events.

### 3.4 Demo scenario

- **Setup:** LIV is home.
  - Forced lineup: Frimpong at RB, Szoboszlai at RW (LIV); Doku at LW (MCI).
  - `bench_must`: Gomez and Bradley.
- **Scripted boost:** the focus is Doku and the marker is Frimpong (in the RB slot), active from 50'.
  - When Doku succeeds in the channel, the follow-up cross or shot weight goes up.
- **Forced swap:** Szoboszlai ↔ Frimpong at 70'.
  - No forced subs before 75'; auto-subs follow afterwards.
- **Seed search accepts a seed only when:**
  - Doku beats Frimpong 6 or more times in the window.
  - The hot-duel trigger fires between 55' and 68'.
  - Liverpool are level or behind when the trigger fires.
  - Szoboszlai's and Gomez's defending and accel indices are at least Frimpong's.
- It never searches on post-swap outcomes. This is disclosed in the docs.

## 4. Services (pure, tested)

**`services/matchups.py`**
- `matchup_map(side_a, side_b)` uses the engine's `nearest()` geometry. Ties are broken by slot order.
- `current_slots(rosters, events, asof)` applies subs and position changes.
- `duel_ledger(events, def_id, att_id, asof)` returns:
  - duels, won, lost, recoveries and fouls
  - channel threat: shots and xG from possessions containing the attacker's successful take-on or carry in the channel
  - the defender's rating swing
  - a rolling 10-minute win % series and a list of duel points (`event_id, x, y, outcome, sec, terms`)
- Confidence by number of duels: fewer than 4 low, 4–9 medium, 10 or more high.
- `hot_duels(...)` is the generic trigger: beaten 6 or more times in 20 minutes, or win % ≤30% with n≥8 (calibrated, see docs/schema.md §11). A test checks it fires, at any second, in no more than 3 of the 20 historical matches.

**`services/advisor.py`** (replaces the body of `evaluate_substitutions`)

*Options*
- KEEP.
- SUB: an eligible bench player into the hot slot.
- SWAP: on-pitch same-team pairs whose role groups are at most one step apart.
- SUB+SWAP: a sub into the vacated slot plus a swap.
- Every leg is scored.

*Dimensions*, each bounded to [−1, 1] and all shown in the UI:

| Dimension | Meaning |
|---|---|
| L | Live form vs expected |
| F | Fit: 1 primary, 0.8 secondary, 0.5 same group, 0.3 projected adjacent (flagged), 0 otherwise |
| M | Projected duel win % (`duel_prob` against the tormentor, blended with observed via k=6 shrinkage) minus the current rate |
| A | Attacking upside of the move |
| G | Game-state weights |
| R | Risk: back-line defending drop, cards, fit of the vacated slot, a sub window used |

- Confidence is the lowest of the evidence, history and fit bands.
- Weights are **policy** weights, stated as such. M's internals come from the fitted study model when it is available (§5).
- Head-to-head is reported separately, with its n.

**`services/race.py`**
- `race(players, horizon=3.0, dt=0.05)` computes `v(t) = vmax·(1 − e^(−t/τ))`, with τ = vmax/accel, starting after a 0.25 s reaction time.
- Returns distance curves, the time to 5 m, and the gaps at 1 s and 2 s.

**`analysis/duel_study.py`** (CLI)
- Samples about 40k duels across squads and contexts, with fatigue minute, cards, isolation, stance and touchline.
- Builds about 110 features from the catalogue: physical, priors, last-5 history, ratings and context.
- Fits a standardised logistic regression with permutation importance, plus mutual information as a cross-check, using numpy and scikit-learn.
- Writes `backend/data/variable_importance.json` and `docs/variable_importance.md` (method, seed, n, AUC).
- Framed as a **methodology demo**: importance mirrors the generator.

## 5. Variable catalogue

- `app/analysis/catalogue.py` is machine-readable, and `docs/variable_catalogue.md` is generated from it.
- **Row:** `id · family · name · unit · source · window · engine_causal · advisor_uses · real_range · ref`.
- **Families:** `PHY` · `PRI` · `EVT` · `HIS` · `RAT` · `CTX` · `DUEL` (interaction and geometry).
- **Size:** 100+ rows, from base metrics × window (match, 20m, l5, l10) × side, plus the research's 108 list.
- **Ranking:** variables without an engine hook are flagged descriptive-only and are never ranked.

## 6. API and contracts

`GET /api/matches/{id}/bench?team_id=&asof=` is one call, clamped to the replay clock:

```
{ asof_sec, alert|null, tormentor{profile}, defender{profile},
  matchup{ledger, rolling[], duels[]}, options[] (Recommendation + moves[], dims{L,F,M,A,G,R},
  profile, projected_win_pct, observed_win_pct, n), race{curves, t5m, gap1s, gap2s},
  impact{swap_sec, before, after}|null, importance[], synthetic: true }
```

- `Recommendation.option_type` gains `position_swap` and `sub_and_swap`, plus `moves[]` and `dims`.
- `EventType` gains `position_change`.
- These are mirrored in `frontend/src/lib/types.ts`.
- Agent tools: upgraded `evaluate_substitutions`, and new `get_duel_ledger` and `get_bench_view`. They are exposed in `mcp_server.py` and `ask.py::_sdk_tools`.

## 7. Page `/match/SIM-001/bench` (top to bottom)

1. **`CoachHeader`**: clock, score and SIMULATED badge, plus an alert pill. A scrubber re-queries as of the chosen second.
2. **`CoachBriefing`**: Claude or the rules template, with evidence chips that flash events on the map and chart. A provider tag shows which one wrote it.
3. **`FlankPitch`** (CSS-3D tilt)
   - Duel markers sit at their real coordinates, with heat columns raised by `translateZ`.
   - Labels sit in a flat overlay.
   - A toggle switches between before and after the swap.
4. **`DuelWinRate`**: the rolling win % line, with threshold, alert and swap markers.
5. **`SprintRace`**: an animated 0–3 s strip of Doku against Frimpong and the selected candidate, with a t-slider.
6. **`RadarCompare`**: fixed 0–100 axes (pace, acceleration, agility, stamina, defending, stance, 1v1 win %). The candidate is drawn against Doku, with Frimpong as a ghost.
7. **`OptionCards`**
   - Each card has dimension bars, bands, confidence, pros and cons, and the knock-on hole.
   - Select drives the radar, race and preview.
   - Choose logs the pick client-side.
8. **`SwapImpact`**
   - Before and after the real `position_change`: Doku's win %, flank shots conceded, ratings, and n.
   - Locked until the clock passes it.
   - States honestly if the swap was not ranked first.
9. **`VariableImportance`**: the top 25, coloured by family. Hovering links to the radar axis.
10. **`FormationPreview`**: a mini-pitch where the swapped dots trade slots (Motion), labelled visual-only.

- Charts are hand-rolled SVG with `lib/chart.ts`, and there are **no new frontend dependencies**.
- Colours are Liverpool red for us and City sky blue for Doku.
- A link is added from the match centre header.

## 8. Calls made by Claude (check these)

- Szoboszlai starts at RW, so both swap legs are listed positions.
- Physical data uses real units as the source, with derived indices for the engine.
- Stance and touchline distance are added because they rank in the research top 10.
- CSS 3D instead of three.js, and hand-rolled SVG instead of a chart library.
- One aggregated `/bench` endpoint, and a home-team advisor only.
- The swap is scripted at 70' regardless of the advisor's ranking.
- The coach's decision is logged client-side only.
- scikit-learn is added to the backend for the study.
