# Subs Advisor ("Assistant Coach") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace the thin substitution helper with a physical-profile-driven duel model, a real `position_change` event, a KEEP/SUB/SWAP advisor, a 100+ variable catalogue with a ranked top-25 study, and an in-depth interactive `/match/SIM-001/bench` page.

**Architecture:**
- The simulator gains `PhysicalProfile` priors and a pure `duel_prob()` shared by the engine, advisor and study. The demo is rescripted to LIV vs MCI: Doku torments Frimpong, and Szoboszlai ↔ Frimpong are swapped at 70'.
- Pure services (`matchups`, `race`, `advisor`) feed one aggregated `GET /api/matches/{id}/bench` endpoint and the agent tools.
- The Next.js page renders hand-rolled SVG and CSS-3D panels from that one payload.

**Tech Stack:**
- Backend: Python 3.13, FastAPI, Pydantic, pytest, numpy and scikit-learn (study only).
- Frontend: Next.js 16 (App Router, `cacheComponents`), React 19, Tailwind v4 and `motion`, with no new frontend dependencies.

**Spec:** `docs/superpowers/specs/2026-10-26-subs-advisor-design.md`. Real-world ranges are in `reports/Football matchup variables catalogue.md`.

## Global Constraints

- **Synthetic labelling:** everything is simulated. Every new payload carries `synthetic: true`, and the UI shows a SIMULATED badge on the bench page.
- **Arithmetic location:**
  - All arithmetic lives in tested Python. The UI and the LLM only render and narrate.
  - The UI never computes race curves, win % or scores.
- **Events are the source of truth:**
  - Slots, subs and swaps are derived from events plus rosters.
  - Pitch dots are visual-only.
- **Reproducibility:**
  - Same `SIM_SEED` + `GENERATOR_VERSION = "sim-v0.3"` ⇒ identical events (bumped by the Task 5b calibration).
  - `uv run python -m app.sim.generate` must pass validation for all 21 matches.
- **Contracts:**
  - New Pydantic models live in `backend/app/models/`.
  - They are mirrored in `frontend/src/lib/types.ts` in the same task.
- **IDs:**
  - Players: Doku `P-MCI-11`, Frimpong `P-LIV-30`, Szoboszlai `P-LIV-08`, Gomez `P-LIV-02`, Bradley `P-LIV-12`.
  - Teams: `T-LIV` (home) and `T-MCI`.
- **Labels:**
  - Duel model: "simulator model, uncalibrated".
  - Study: "methodology demo: importance mirrors the generator".
  - Advisor weights: "policy weights".
- **Tooling:**
  - Use `uv add` and `bun add` only, and ruff (line length 100). Run `cd frontend && bun run lint` clean.
  - Scripts must stay bash 3.2-compatible.
- **Next.js 16:** before writing any route or page code, read `frontend/node_modules/next/dist/docs/`, especially dynamic route `params` (a Promise in v16) and `cacheComponents`.
- **Commits:** do **not** commit unless the owner asks (CLAUDE.md). Each task ends with a green-suite checkpoint instead.

## Review Focus

1. **Scrubbing to a second before the alert, or before 50'.** `/bench` returns `alert: null`, a KEEP-only option list (or none), and `impact: null`. It must not raise. Test owned by Task 9.
2. **Scrubbing past the swap at 70'.** The ledger keeps attributing Doku's duels to whoever is now at RB (Szoboszlai), not to Frimpong. `current_slots` reflects the swap, and the radar and race default to the new RB. Test owned by Task 6.
3. **`asof_sec` beyond the live replay clock.** It is clamped. No future events, impact or ledger leak. Test owned by Task 9.
4. **Historical matches have no scenario.** `hot_duels` must rarely fire there (no more than 3 of the 20 matches), so the trigger is generic rather than scripted. Test owned by Task 6.
5. **A position swap with a card-dismissed or subbed-off partner.** The advisor must not offer a swap involving a player no longer on the pitch, and the validator must reject a `position_change` for an off-pitch player. Tests owned by Tasks 4 and 8.

---

### Task 1: Physical profile

**Files:**
- Modify: `backend/app/models/reference.py` (add `PhysicalProfile`, `Player.physical`), `backend/app/models/__init__.py` (export)
- Modify: `backend/app/sim/squads.py` (sample physical values)
- Modify: `backend/app/db.py` (`physical TEXT` column on `players`, add to `JSON_COLS`)
- Modify: `frontend/src/lib/types.ts` (mirror)
- Test: `backend/tests/test_physical.py`

**Interfaces:**
- Produces:
  - `PhysicalProfile(top_speed_kmh: float, accel_ms2: float, agility_idx: int, stamina_idx: int, stance_idx: int, height_cm: int)`.
  - Derived properties:
    - `speed_idx` = (kmh−29)/(37−29)·100, clamped 0–100
    - `accel_idx` = (a−6.0)/(7.9−6.0)·100, clamped
    - `time_0_5m_s` = `round(sqrt(10/accel_ms2) + 0.25, 2)`
  - `Player.physical: PhysicalProfile | None = None`.
  - `PINNED_PHYSICAL: dict[str, dict]` in `squads.py`, applied after sampling.

- [x] **Step 1: Write the failing tests.**
  - `test_profile_indices_map_linearly`: `PhysicalProfile(top_speed_kmh=33, accel_ms2=6.95, …).speed_idx == 50` and `.accel_idx == 50`.
  - `test_all_players_have_plausible_physical`: for every player from `load_reference(2026)`, `29.0 <= top_speed_kmh <= 37.4` and `6.0 <= accel_ms2 <= 7.9`.
  - `test_speed_and_accel_correlate`: the Pearson r across outfield players is > 0.3.
  - `test_demo_story_profiles_pinned`. Doku's values are `top_speed_kmh == 35.1` and Doku `accel_idx >= 90`. Frimpong is faster than Szoboszlai:
    `phys(P-LIV-30).top_speed_kmh > phys(P-LIV-08).top_speed_kmh`.
    Szoboszlai out-accelerates Frimpong:
    `phys(P-LIV-08).accel_ms2 > phys(P-LIV-30).accel_ms2`.
    Szoboszlai and Gomez both have better stance than Frimpong:
    `stance_idx(P-LIV-08) > stance_idx(P-LIV-30) < stance_idx(P-LIV-02)`.
  - `test_load_reference_deterministic`: same seed ⇒ equal `physical` for all players.
- [x] **Step 2: Run** `cd backend && uv run pytest tests/test_physical.py -v`. Expected: FAIL (no `PhysicalProfile`).
- [x] **Step 3: Implement the model and sampling.**
  - Sample from a separate `random.Random(f"physical-{seed}")`, so the existing priors stream is unchanged.
  - Position means: CB 32.5 km/h, FB 34.0, CM 32.5, W 34.5, ST 33.5, GK 29.5; sd 1.2.
  - Accel = 6.9 + 0.6·z_speed·0.6 + noise·0.8·0.35, clipped.
  - Agility comes from the dribbling prior ± 6, stamina from position (CM 82, FB 80, W 74, CB 72) ± 7, stance from the defending prior ± 8, height by position.
  - Pinned values (fictional):

    | Player | top_speed_kmh | accel_ms2 | agility_idx | stamina_idx | stance_idx |
    |---|---|---|---|---|---|
    | Doku | 35.1 | 7.8 | 95 | 72 | — |
    | Frimpong | 36.4 | 7.0 | 84 | 80 | 38 |
    | Szoboszlai | 32.6 | 7.55 | 80 | 93 | 74 |
    | Gomez | 33.9 | 7.4 | 70 | 76 | 78 |
    | Bradley | 34.6 | 7.2 | 78 | 82 | 60 |

- [x] **Step 4: Run** `uv run pytest -q`. Expected: all PASS (the existing suite still passes, because the priors stream is untouched).
- [x] **Step 5: Mirror types.** Add `PhysicalProfile` and `physical?: PhysicalProfile | null` to `Player` in `types.ts`. Run `bun run lint`.

### Task 2: Pure duel model

**Files:**
- Create: `backend/app/sim/duel.py`
- Test: `backend/tests/test_duel.py`

**Interfaces:**
- Consumes: `Player.priors` and `Player.physical` (Task 1).
- Produces:
  - `DuelContext(isolated: bool, transition: bool, defender_on_yellow: bool, cover_near: bool, touch: float, att_minutes_on: float, def_minutes_on: float, script: float = 0.0)`, a frozen dataclass.
  - `DuelTerms(tech, burst, agil, stance, touch, ctx, script, z, p_beat, p_recover)`, all floats rounded to 3 dp, with `.as_qualifier() -> dict`.
  - `fatigue(minutes_on: float, stamina_idx: int) -> float`
  - `duel_prob(att: Player, dfn: Player, c: DuelContext, stance: float) -> DuelTerms`
  - `p_recover(def_kmh: float, att_kmh: float) -> float`
  - `MODEL_VERSION = "duel-v1"`

- [x] **Step 1: Write the failing tests** (the formula is pinned in spec §3.2).
  - `test_fatigue_flat_before_55`: `fatigue(50, 60) == 1.0`. And `fatigue(85, 60) == 1 - 0.004*30*40/20`, which is 0.76.
  - `test_burst_favours_faster_accelerator`: two copies of one defender that differ only in `accel_ms2` (6.5 vs 7.6) give `p_beat` higher against the 6.5 copy.
  - `test_top_speed_only_affects_recovery`: changing only the defender's `top_speed_kmh` leaves `p_beat` equal and changes `p_recover`.
  - `test_square_stance_concedes`: `duel_prob(..., stance=0.0).p_beat > duel_prob(..., stance=1.0).p_beat`.
  - `test_clamps`: extreme inputs give `0.05 <= p_beat <= 0.9` and `0.03 <= p_recover <= 0.35`.
  - `test_script_term_reported`: `DuelContext(script=8)` ⇒ `terms.script == 8` and `"script" in terms.as_qualifier()`.
  - `test_doku_beats_frimpong_more_than_szoboszlai`: using `load_reference(2026)` with a neutral context and stance set to each player's `stance_idx/100`, `p_beat(Doku vs Frimpong) > p_beat(Doku vs Szoboszlai)`.
- [x] **Step 2: Run** `uv run pytest tests/test_duel.py -v`. Expected: FAIL (module missing).
- [x] **Step 3: Implement exactly the spec §3.2 formula.**
  - Use the indices from Task 1.
  - Fatigue scales the attacker's and the defender's `accel_idx` and `agility_idx` before the terms are computed.
  - `p_recover` uses km/h directly.
- [x] **Step 4: Run** `uv run pytest tests/test_duel.py -v`. Expected: PASS.

### Task 3: Engine uses the duel model (sim-v0.2)

**Files:**
- Modify: `backend/app/sim/engine.py`
  - `GENERATOR_VERSION = "sim-v0.2"`
  - `Scenario`: replace `take_on_success_mult` with `script_boost: float = 0.0`, and add `marker_slot: str | None`
  - `take_on`, plus a new `minutes_on`
- Test: `backend/tests/test_sim.py` (extend)

**Interfaces:**
- Consumes: `duel_prob`, `DuelContext` and `p_recover` (Task 2).
- Produces:
  - Every `take_on` event has `qualifiers["duel"] = DuelTerms.as_qualifier()`.
  - A beaten defender who recovers emits a `tackle` (success, `qualifiers={"recovery": True}`) on the same possession.
  - A beaten, unrecovered last-line defender has a 25% chance of a `foul`.
  - `Scenario.active_against(att_id, dfn_id, dfn_slot, sec) -> bool` is true only when the attacker is the focus player, the defender is the marker, `dfn_slot == marker_slot`, and `sec` is in the window.

- [x] **Step 1: Write the failing tests.**
  - `test_take_on_events_carry_duel_terms`: every `take_on` in `sim(reference)` has the keys `{"tech","burst","agil","stance","touch","ctx","script","p_beat"}` in `qualifiers["duel"]`.
  - `test_historical_has_no_script_term`: every `qualifiers["duel"]["script"] == 0` in historical sims.
  - `test_recovery_tackles_exist`: there is at least one `tackle` with `qualifiers.get("recovery")` in `sim(reference)`.
  - `test_simulated_match_passes_validation` and `test_same_seed_reproduces_identical_events` still pass.
- [x] **Step 2: Run** `uv run pytest tests/test_sim.py -v`. Expected: the new tests FAIL.
- [x] **Step 3: Implement the engine changes.**
  - Build the `DuelContext` from engine state:
    - `isolated`: no other defending outfield slot within 15 units of the mirrored duel point, using the `nearest()` metric.
    - `cover_near`: the same check within 10 units.
    - `transition`: the possession is fewer than 3 events old.
    - `defender_on_yellow`: `dfn.player_id in opp.yellows`.
    - `touch`: `min(y, 100 - y)` of the duel point.
    - `minutes_on`: from a new `Side.entered_at: dict[str, float]`, set at kickoff and on substitution.
  - Draw stance with `self.rng.gauss(stance_idx/100, 0.15)`, clamped to 0–1.
  - Keep the existing `scenario.take_on_freq_mult` for frequency.
- [x] **Step 4: Run** `uv run pytest -q`. Expected: all PASS except `test_demo_storyline_*` and `test_agent.py` storyline tests, which Task 5 rewrites. Mark them `xfail(reason="rescripted in Task 5")` until then.

### Task 4: `position_change` event end to end

**Files:**
- Modify: `backend/app/models/events.py` (add `"position_change"` to `EventType`, `neutral` in `ALLOWED_OUTCOMES`; requires `qualifiers.from_slot` and `to_slot`)
- Modify: `backend/app/sim/engine.py` (`Scenario.forced_swaps: list[tuple[int, str, str, str]]` as (sec, team, a_id, b_id); `MatchSim.swap(side, a_id, b_id)`, called from `process_subs`)
- Modify: `backend/app/sim/validate.py` (slot tracking + swap rules)
- Modify: `backend/app/services/live_state.py:65-92` (apply swaps to `slot_of`)
- Modify: `backend/app/services/performance.py` (slot-aware role group)
- Modify: `backend/app/models/analytics.py` (`Rating.out_of_position: bool = False`)
- Modify: `frontend/src/lib/types.ts`, `frontend/src/components/EventFeed.tsx` and `frontend/src/lib/describe.ts` (render "X moves to RB")
- Test: `backend/tests/test_position_change.py`

**Interfaces:**
- Produces:
  - `MatchSim.swap(side, a_id, b_id) -> None` emits two events, `player_id=a` / `recipient_id=b` and the mirror, each with `{from_slot, to_slot}`.
  - `slot_timeline(player_id: str, rosters: list[RosterEntry], events: list[MatchEvent]) -> list[tuple[int, str | None]]` in `performance.py`.
  - `live_rating(player, events, asof, minutes, rosters=None) -> tuple[float, list[RatingContribution], bool]`. It is **backwards-compatible**: when `rosters` is given, each event's weight uses `ROLE_GROUP[slot position at event_sec]`.
  - `is_out_of_position(player: Player, slot_position: str) -> bool`.

- [x] **Step 1: Write the failing tests.**
  - `test_swap_emits_two_events_and_keeps_bijection`:
    - Run a sim with `Scenario(forced_swaps=[(4200, "T-LIV", "P-LIV-08", "P-LIV-30")], …)`.
    - Assert two `position_change` events at the same second, with `qualifiers == {"from_slot":"RW","to_slot":"RB"}` and `{"from_slot":"RB","to_slot":"RW"}`.
    - `validate_match(...) == []`.
  - `test_validator_rejects_swap_with_off_pitch_player`: inject a `position_change` for a bench player ⇒ an error containing `"not on the pitch"`.
  - `test_validator_rejects_wrong_from_slot`: ⇒ an error containing `"from_slot"`.
  - `test_swap_does_not_count_as_sub`: a match with 5 subs plus 1 swap validates.
  - `test_live_state_reflects_swap`: `state(4300).on_pitch` shows Szoboszlai at `formation_slot == "RB"`.
  - `test_rating_uses_slot_role_after_swap`:
    - Szoboszlai's tackle after the swap contributes `WEIGHTS[("tackle","success")]["DEF"]`.
    - `is_out_of_position(szoboszlai, "RB") is False` (RB is secondary).
    - `is_out_of_position(frimpong, "CM") is True`.
- [x] **Step 2: Run** `uv run pytest tests/test_position_change.py -v`. Expected: FAIL.
- [x] **Step 3: Implement.**
  - The validator keeps a `slot: dict[player_id, slot]` from the starters and updates it on subs (the incoming player takes the slot) and on swaps.
  - After each group of events at the same `event_sec`, it checks that the map is one-to-one.
  - `position_change` does not touch `subs` or possession.
- [x] **Step 4: Run** `uv run pytest -q`. Expected: PASS (except the xfails).
- [x] **Step 5: Mirror the type** (`EventType`, `Rating.out_of_position`), update the describe copy, then run `bun run lint`.

### Task 5: Rescript the demo (LIV vs MCI) and regenerate

**Files:**
- Modify: `backend/app/sim/generate.py`
  - Constants and docstring. Remove `FOCUS_PLAYER`, `FOCUS_MARKER`, `SUB_INCOMING`, `ALT_INCOMING`, `ALERT_SEC` and `SUB_SEC`. Add `DEMO_HOME, DEMO_AWAY = "T-LIV", "T-MCI"`, `TORMENTOR = "P-MCI-11"`, `VICTIM = "P-LIV-30"`, `SWAP_IN = "P-LIV-08"`, `BENCH_OPTIONS = ["P-LIV-02", "P-LIV-12"]`, `BOOST_FROM_SEC = 3000` and `SWAP_SEC = 4200`.
  - `demo_scenario()` and `simulate_demo()`.
- Modify: `backend/tests/test_sim.py`, `backend/tests/test_agent.py` (remove the xfails; rewrite the storyline tests)
- Modify: `backend/app/agent/rules.py` and `backend/app/agent/ask.py` (any ARS/Saka copy or examples)
- Modify: `README.md` and `docs/schema.md` (storyline description)

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces:
  - Demo `SIM-001`: LIV home, MCI away.
  - Forced lineup: LIV `{"RB": VICTIM, "RW": SWAP_IN}`, MCI `{"LW": TORMENTOR}`.
  - `bench_must = BENCH_OPTIONS`.
  - `forced_swaps = [(SWAP_SEC, "T-LIV", SWAP_IN, VICTIM)]`.
  - `no_auto_subs_before = {"T-LIV": SWAP_SEC + 300}`.
  - `script_boost` is set by the seed search, from the candidates [6, 8, 10, 12], lowest that passes first.
  - `hot_duels` is imported from Task 6, so implement Task 6 before this task's Step 3. The two tasks are ordered 6 → 5 in execution.

- [x] **Step 1: Write the failing tests.**
  - `test_demo_storyline_doku_beats_frimpong`: in the demo, successful take-ons by `P-MCI-11` with `opponent_id == "P-LIV-30"` between 3000 and 4200 s number at least 6.
  - `test_demo_trigger_fires_before_swap`: `hot_duels(...)` for `T-LIV` first fires at some `asof` in [3300, 4080].
  - `test_demo_liverpool_not_ahead_at_trigger`.
  - `test_demo_swap_happens_at_70`: `position_change` events occur at `event_sec >= 4200`, the first of them within 60 s.
  - `test_script_term_zero_after_swap`: every `take_on` after the swap has `qualifiers.duel.script == 0`.
  - `test_agent.py::test_substitution_evaluation_has_keep_swap_and_sub` (asserted fully in Task 8).
- [x] **Step 2: Run** `uv run pytest tests/test_sim.py -v`. Expected: FAIL.
- [x] **Step 3: Implement the seed search.**
  - Loop over the `script_boost` candidates outermost and the seeds `seed..seed+499` inside.
  - Accept only if all the spec §3.4 criteria hold. **Never inspect events after `SWAP_SEC`** (add a code comment stating this; it is disclosed in docs).
- [x] **Step 4: Regenerate.**
  - Run `uv run python -m app.sim.generate`. Expected: it prints `generator_version sim-v0.2`, `matches 21` and a `demo` line `SIM-001 seed=… final x-y`.
  - Record the demo hash in `docs/schema.md`.
- [x] **Step 5: Run** `uv run pytest -q && uv run ruff check .`. Expected: PASS and clean.

### Task 6: Matchup services

**Files:**
- Create: `backend/app/services/matchups.py`
- Create: `backend/app/models/advisor.py` (all new advisor contracts; export from `app/models/__init__.py`)
- Test: `backend/tests/test_matchups.py`

**Interfaces:**
- Produces, in `models/advisor.py`:
  - `DuelPoint(event_id: str, sec: int, x: float, y: float, outcome: Literal["won","lost","recovered","foul"], attacker_id: str, defender_id: str, terms: dict)`
  - `RollingPoint(sec: int, win_pct: float | None, n: int)`
  - `DuelLedger(attacker_id, defender_ids: list[str], duels: int, won: int, lost: int, recoveries: int, fouls: int, win_pct: float | None, channel_shots: int, channel_xg: float, defender_rating_swing: float | None, confidence: Literal["low","medium","high"], points: list[DuelPoint], rolling: list[RollingPoint], evidence_event_ids: list[str])`
  - `HotDuel(team_id, defender_id, defender_slot, attacker_id, beaten_20m: int, win_pct_20m: float | None, n_20m: int, first_fired_sec: int | None)`
  - `SwapImpact(swap_sec: int, before: DuelLedger, after: DuelLedger)`
- Produces, in `services/matchups.py`:
  - `current_slots(rosters, events, asof) -> dict[str, str]`: player_id → slot, applying subs, swaps and red cards.
  - `matchup_map(our_formation: str, their_formation: str) -> dict[str, str]`: our slot → the opposing slot that the engine's `nearest()` geometry pairs with it (mirrored coords, `x*0.85` metric, ties by slot order).
  - `duel_ledger(events, attacker_id, slot_or_defender: str, team_id: str, rosters, asof: int, since: int = 0) -> DuelLedger`. When given a slot, it follows whoever occupied it over time, so after the swap it covers Szoboszlai.
  - `hot_duels(events, rosters, team_id, asof) -> list[HotDuel]`: the trigger is beaten ≥6 in the last 20 min, or win % ≤30% with n≥8 (calibrated in Task 5b).
  - `swap_impact(events, rosters, team_id, attacker_id, slot: str, asof) -> SwapImpact | None`.
- Confidence bands by n: fewer than 4 low, 4–9 medium, 10+ high.
- Channel threat: shots and xG in possessions that contain the attacker's successful take-on or carry with `start_y > 67` in the attacker frame.

- [x] **Step 1: Write the failing tests.**
  - `test_matchup_map_lw_faces_rb`: `matchup_map("4-2-3-1","4-2-3-1")["RB"] == "LW"`, and `["LB"] == "RW"`.
  - `test_ledger_counts_won_lost_recovered`: a hand-built event list of 3 take-on successes (1 followed by a recovery tackle), 2 fails and 1 foul gives `duels == 6`, `lost == 2`, `recoveries == 1`, `fouls == 1` and `won == 3`. Won counts defender wins = fails + recoveries; lost = beaten without recovery.
  - `test_rolling_window_600s`: points every 60 s; `win_pct` is None when n == 0.
  - `test_ledger_follows_slot_after_swap`: with demo data and `asof=5000`, `slot="RB"` gives `defender_ids == ["P-LIV-30","P-LIV-08"]`.
  - `test_hot_duels_rare_in_history`: across the 20 historical matches at `asof=5400`, no more than 3 matches have any `hot_duels` for either team.
  - `test_swap_impact_none_before_swap`: `swap_impact(..., asof=4000) is None`.
  - `test_swap_impact_after_swap`: at `asof=5400`, `before.defender_ids == ["P-LIV-30"]` and `after.defender_ids == ["P-LIV-08"]`.
- [x] **Step 2: Run** `uv run pytest tests/test_matchups.py -v`. Expected: FAIL.
- [x] **Step 3: Implement** the pure functions with no Store access. Inputs are plain lists.
- [x] **Step 4: Run** `uv run pytest tests/test_matchups.py -v`. Expected: PASS.

### Task 7: Sprint race

**Files:**
- Create: `backend/app/services/race.py`
- Modify: `backend/app/models/advisor.py` (`RaceCurve`, `RaceResult`)
- Test: `backend/tests/test_race.py`

**Interfaces:**
- Produces:
  - `RaceCurve(player_id: str, name: str, t: list[float], d: list[float], t5m: float, d1s: float, d2s: float)`
  - `RaceResult(curves: list[RaceCurve], gap1s: dict[str, float], gap2s: dict[str, float], reaction_s: float, label: str)`. The gaps are relative to the first player, the tormentor.
  - `race(players: list[Player], horizon: float = 3.0, dt: float = 0.05, reaction_s: float = 0.25) -> RaceResult`
- Curve: after the reaction time, `v(t) = vmax·(1 − e^(−t/τ))` with `τ = vmax/accel`, where vmax is in m/s. Distance is the closed-form integral. `t5m` is solved by bisection.

- [x] **Step 1: Write the failing tests.**
  - `test_zero_before_reaction`: `d == 0` for `t <= 0.25`.
  - `test_higher_accel_leads_at_1s_lower_top_speed`: Szoboszlai `d1s` > Frimpong `d1s` (pinned values).
  - `test_t5m_monotonic_in_accel`.
  - `test_label_mentions_model`: `"simulated" in result.label.lower()`.
- [x] **Step 2: Run** `uv run pytest tests/test_race.py -v`. Expected: FAIL.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run.** Expected: PASS.

### Task 8: Advisor and agent tools

**Files:**
- Create: `backend/app/services/advisor.py`
- Modify: `backend/app/models/analytics.py`. `Recommendation.option_type` becomes `Literal["keep","substitution","position_swap","sub_and_swap"]`; add `moves: list[Move] = []`, `dims: OptionDims | None = None`, `projected_win_pct: float | None = None`, `observed_win_pct: float | None = None`, `n_observed: int = 0` and `out_of_position: bool = False`.
- Modify: `backend/app/models/advisor.py` (`Move(player_id: str, from_slot: str | None, to_slot: str | None, kind: Literal["on","off","move"])` and `OptionDims(L: float, F: float, M: float, A: float, G: float, R: float)`, each bounded to [−1, 1])
- Modify: `backend/app/agent/tools.py`
  - `evaluate_substitutions` delegates to the advisor and keeps its return keys plus `hot_duel` and `ledger`.
  - Add `get_duel_ledger(match_id, attacker_id, slot, team_id, asof_sec=None)`.
  - Add `get_bench_view(match_id, team_id, asof_sec=None)`, which calls Task 9's builder.
  - Remove `_struggles` and the take-on-only diagnosis.
- Modify: `backend/app/agent/mcp_server.py` and `backend/app/agent/ask.py::_sdk_tools`, plus the `tool_names` list (expose both new tools)
- Modify: `backend/app/agent/rules.py` and `get_insight_candidates` (the trigger is `hot_duels`; insight kind `tactical_alert` names the duel)
- Test: `backend/tests/test_advisor.py`, `backend/tests/test_agent.py`

**Interfaces:**
- Consumes: Tasks 2, 6 and 7, plus `get_player_history`.
- Produces:
  - `AdvisorInput(team_id, players: dict[str, Player], slots: dict[str, str], bench: list[str], formation: str, hot: HotDuel, ledger: DuelLedger, live: dict[str, float], expected: dict[str, float | None], history_n_at_slot: dict[tuple[str, str], int], goal_diff: int, minute: int, subs_left: int, yellows: set[str], tormentor: Player, asof: int, match_id: str)`, a dataclass.
  - `evaluate(inp: AdvisorInput) -> list[Recommendation]`
  - `POLICY_WEIGHTS = {"L": 0.15, "F": 0.15, "M": 0.35, "A": 0.1, "G": 0.1, "R": 0.15}`
  - `ADVISOR_VERSION = "advisor-v1"`
- Options:
  - KEEP is always present.
  - SUB: bench players with F ≥ 0.5 for the hot slot.
  - SWAP: on-pitch same-team pairs where both legs have F ≥ 0.3 and the role groups are at most one step apart. GK is excluded.
  - SUB+SWAP: the best swap plus the best sub into the vacated slot. Only when subs_left > 0.
  - Return KEEP plus the top 4 others, ranked by score.
- M: `projected = 1 − mean p_beat` from `duel_prob` over a fixed context grid (isolated ∈ {T,F} × transition ∈ {T,F}, stance = `stance_idx/100`, current minutes). This is shrunk with the candidate's observed rate against the tormentor at k=6. `M = clamp((projected − ledger.win_pct_or_projected_current)/0.3, −1, 1)`.
- Head-to-head: `evaluate_substitutions` returns `head_to_head` for each candidate vs the tormentor, taken from `get_matchup_analysis` prior meetings with n. It is reported separately and never blended into M.
- Pros and cons must quote the numbers, e.g. "Out-accelerates Frimpong: 1.52 s vs 1.62 s to 5 m (simulated)" and "No history at RB (n=0): experimental role".

- [x] **Step 1: Write the failing tests.**
  - `test_keep_always_present_and_first_class`: exactly one `option_type == "keep"`.
  - `test_swap_option_szoboszlai_to_rb`, on demo data at `asof=4080`:
    - an option `position_swap` with moves `{P-LIV-08: RW→RB, P-LIV-30: RB→RW}` exists
    - its `dims.M > 0`
    - `confidence == "low"` (n=0 at RB)
  - `test_sub_options_include_gomez_or_bradley`.
  - `test_no_swap_with_off_pitch_player`: if a player is removed from `slots`, no option references them.
  - `test_dims_bounded`: every dim is in [−1, 1].
  - `test_no_subs_left_hides_sub_options`: with `subs_left=0`, only keep and position_swap remain.
  - `test_agent.py::test_substitution_evaluation_has_keep_swap_and_sub`, through `tools.evaluate_substitutions("SIM-001","T-LIV", 4080)`.
  - `test_get_duel_ledger_tool_clamped_to_clock`.
- [x] **Step 2: Run** `uv run pytest tests/test_advisor.py tests/test_agent.py -v`. Expected: FAIL.
- [x] **Step 3: Implement** `advisor.evaluate`, then wire the tools.
- [x] **Step 4: Run** `uv run pytest -q && uv run ruff check .`. Expected: PASS.

### Task 9: Bench view endpoint

**Files:**
- Create: `backend/app/services/bench.py` (assembles the view from Store data; I/O at the edge)
- Modify: `backend/app/models/advisor.py` (`ImportanceItem(var_id: str, name: str, family: str, importance: float, rank: int)` and `PlayerCard(player_id, name, slot: str | None, position, physical: PhysicalProfile, priors: PlayerPriors, profile: dict[str, float])`)
- Add `BenchView(match_id, team_id, asof_sec, minute, score: dict[str, int], alert: HotDuel | None, tormentor: PlayerCard | None, defender: PlayerCard | None, ledger: DuelLedger | None, options: list[Recommendation], cards: dict[str, PlayerCard], race: RaceResult | None, impact: SwapImpact | None, importance: list[ImportanceItem], briefing_seed: str, synthetic: Literal[True] = True)`.
  - `profile` holds the 7 radar axes, all on 0–100: `pace`, `acceleration`, `agility`, `stamina`, `defending`, `stance` and `duel_win`, where `duel_win` is the projected % vs the tormentor.
- Modify: `backend/app/api.py` (`GET /api/matches/{match_id}/bench?team_id=T-LIV&asof_sec=`)
- Modify: `frontend/src/lib/types.ts` (all advisor models) and `frontend/src/lib/api.ts` (`fetchBench(matchId, teamId, asofSec?)`)
- Test: `backend/tests/test_bench.py`

**Interfaces:**
- Consumes: Tasks 6, 7 and 8, plus `backend/data/variable_importance.json` (Task 10; an empty list if absent).
- Produces:
  - `build_bench_view(store, replays, match_id, team_id, asof_sec) -> BenchView`.
  - The race uses the tormentor, the current defender at the hot slot, and every option's incoming defender.
  - `briefing_seed` is the deterministic rules text that Task 15 renders.

- [x] **Step 1: Write the failing tests.**
  - `test_bench_before_alert`: `asof_sec=1200` gives 200, `alert is None`, `impact is None`, and `options` is `[]` or KEEP only.
  - `test_bench_clamped_to_clock`: set the replay clock to 3000 and request 9999; `asof_sec == 3000` and no `ledger.points` have `sec > 3000`.
  - `test_bench_at_alert_has_everything`: at the first-fired second, `alert`, `ledger.points`, `race.curves` (at least 3) and `options` (at least 3) are present; `synthetic is True`.
  - `test_bench_after_swap_has_impact`.
- [x] **Step 2: Run** `uv run pytest tests/test_bench.py -v`. Expected: FAIL.
- [x] **Step 3: Implement** the builder and the route. Mirror every model in `types.ts` with the same field names.
- [x] **Step 4: Run** `uv run pytest -q`, then `cd ../frontend && bun run lint`. Expected: PASS and clean.

### Task 10: Variable catalogue and duel study

**Files:**
- Create: `backend/app/analysis/__init__.py`, `backend/app/analysis/catalogue.py` and `backend/app/analysis/duel_study.py`
- Create (generated): `docs/variable_catalogue.md`, `docs/variable_importance.md` and `backend/data/variable_importance.json`
- Modify: `backend/pyproject.toml` via `uv add scikit-learn numpy`
- Modify: `scripts/install.sh` (run the study after generate)
- Test: `backend/tests/test_analysis.py`

**Interfaces:**
- Produces:
  - `Variable(id: str, family: Literal["PHY","PRI","EVT","HIS","RAT","CTX","DUEL"], name: str, unit: str, source: Literal["physical_synthetic","prior","event","historical","rating","context"], window: str, engine_causal: bool, advisor_uses: bool, real_range: str, ref: str)`
  - `VARIABLES: list[Variable]`
  - `python -m app.analysis.catalogue` writes the md file.
  - `build_features(att, dfn, ctx, stance, history) -> dict[str, float]` (keys equal Variable ids).
  - `run_study(seed: int, n: int) -> StudyResult(n, auc, method, ranked: list[ImportanceItem])`.
  - `python -m app.analysis.duel_study --n 40000` writes the JSON and the md file.
- Catalogue rules:
  - Ids follow `family.metric[_window]`, e.g. `phy.accel_ms2`, `evt.take_on_won_20m` and `his.duel_win_pct_l5`.
  - The `real_range` and `ref` columns come from `reports/Football matchup variables catalogue.md`.
- Study:
  - Sample attacker/defender pairs from all squads (attackers ATT/MID, defenders DEF/MID), and contexts uniform over the `DuelContext` fields.
  - Draw the outcome as Bernoulli(`p_beat`).
  - Standardise the features and fit `LogisticRegression(max_iter=1000)` on a 75/25 split.
  - Use `permutation_importance` on the test split (`n_repeats=5`), with `mutual_info_classif` as a cross-check column.
  - Rank only `engine_causal` variables. Descriptive-only variables are listed and marked "not ranked".

- [x] **Step 1: Write the failing tests.**
  - `test_catalogue_has_100_plus_unique_ids`.
  - `test_every_family_present`.
  - `test_ranked_vars_are_causal`.
  - `test_study_small_run`: `run_study(2026, 3000)` gives `auc > 0.6`, `len(ranked) >= 20`, and `phy.accel_idx_diff` or `duel.burst` is in the top 5.
  - `test_study_deterministic`: two runs with the same seed give identical rankings.
- [x] **Step 2: Run** `uv run pytest tests/test_analysis.py -v`. Expected: FAIL.
- [x] **Step 3: Implement.**
  - The md header must state: "methodology demo: importance mirrors the generator (`duel-v1`); not football truth".
  - Write method, seed, n and AUC into the header.
- [x] **Step 4: Run** `uv run python -m app.analysis.catalogue && uv run python -m app.analysis.duel_study --n 40000`. Expected: it prints the AUC and the top 25, and creates all three files.
- [x] **Step 5: Run** `uv run pytest -q`. Expected: PASS.

### Task 11: Bench page shell, header and option cards

**Files:**
- Create: `frontend/src/app/match/[id]/bench/page.tsx` (server wrapper; awaits `params` per the v16 docs) and `frontend/src/components/bench/BenchPage.tsx` (`"use client"`)
- Create: `frontend/src/hooks/useBenchView.ts`
- Create: `frontend/src/lib/chart.ts`
- Create: `frontend/src/components/bench/CoachHeader.tsx` and `OptionCards.tsx`
- Modify: `frontend/src/components/Scoreboard.tsx` or `MatchCenter.tsx` (add a "Bench / Assistant coach" link, with an alert dot when `alert` is set)

**Interfaces:**
- Consumes: `fetchBench` and the `BenchView` types (Task 9), plus `useMatchStream` for the live clock.
- Produces:
  - `useBenchView(matchId, teamId) -> { view: BenchView | null, asof: number, setAsof(sec|null), selected: string | null, select(rec_id), chosen: string | null, choose(rec_id) }`.
    - It refetches on a stream `state` tick (throttled to ≥ 2 s) or when the scrubber changes.
    - `null` asof means follow live.
    - `chosen` is persisted in `localStorage` key `itg-bench-choice-{matchId}`, wrapped in try/catch.
  - `chart.ts`: `linear(domain: [number, number], range: [number, number]) => (v: number) => number`, `polar(cx, cy, r, angleRad) => [x, y]`, `linePath(points: [number, number][]) => string`, `areaPath(points, baseline) => string`, and `PALETTE = { us: "#C8102E", them: "#6CABDD", ghost: "…", grid: "…" }`. The colours come from CSS variables in `globals.css`.

- [x] **Step 1: Read** `frontend/node_modules/next/dist/docs/` for dynamic segments, `params` and client components under `cacheComponents`. Note the exact pattern in a code comment.
- [x] **Step 2: Implement the page shell.**
  - It has a 12-column grid layout and works at 360 px width.
  - `CoachHeader`: clock, score, SIMULATED badge, an alert pill ("Doku vs RB: beaten 6 in 20'", from `alert`), and a range scrubber 0–5400 with a "Live" button.
  - `OptionCards`:
    - One card per option: type chip, moves list, six dimension bars (−1…1, centred), projected vs observed win % with n, a confidence chip, pros and cons, and an "Out of position" badge when flagged.
    - Select sets `selected`; Choose sets `chosen`.
    - Text "Policy weights · simulated · not causal".
- [x] **Step 3: Verify.** Run `bun run lint`. Then run `scripts/run.sh` and open `http://localhost:3000/match/SIM-001/bench`. Seek the replay to 4080 s: the alert pill shows, and at least 3 cards render with KEEP present.

### Task 12: Flank pitch (CSS 3D) and duel win-rate chart

**Files:**
- Create: `frontend/src/components/bench/FlankPitch.tsx` and `DuelWinRate.tsx`

**Interfaces:**
- Consumes: `view.ledger.points`, `view.ledger.rolling`, `view.alert.first_fired_sec` and `view.impact?.swap_sec`, plus `toSvg` from `lib/pitch.ts`. Points are in the attacker (MCI) frame, so pass `isHome=false`.
- Produces: shared hover state `highlight: string[]` (event ids) on `BenchPage`. Panels accept `highlight` and `onHighlight`.

- [x] **Step 1: Build `FlankPitch`.**
  - The full pitch SVG goes inside a wrapper with `perspective: 1000px`, and the inner element uses `rotateX(50deg)`. Motion animates from 0deg to 50deg on mount.
  - Markers: green when the defender won or recovered, red when lost or a foul. Size encodes `p_beat` from the terms.
  - Heat columns:
    - Bin our right flank into 6 x-zones.
    - Each zone gets a div with `translateZ` and a height proportional to duels lost.
  - Labels and tooltips sit in a flat overlay, never in the tilted plane.
  - A "Before swap / After swap / All" toggle filters by `impact.swap_sec`.
  - Clicking a marker shows the event id and its terms (tech, burst, stance, ctx, script).
- [x] **Step 2: Build `DuelWinRate`.**
  - An SVG line of `rolling.win_pct`, with gaps where null and a 30% threshold dashed line (`HOT_WIN_PCT`).
  - Vertical markers at the alert and the swap, and a crosshair tooltip showing win % and n.
  - Clicking sets the scrubber asof.
- [x] **Step 3: Verify** with `bun run lint`. In the browser at asof 4080, there are red markers clustered on LIV's right flank and the line has dipped below 30% before the alert marker.

### Task 13: Radar and sprint race

**Files:**
- Create: `frontend/src/components/bench/RadarCompare.tsx` and `SprintRace.tsx`

**Interfaces:**
- Consumes: `view.cards[pid].profile` (7 axes, 0–100), `view.tormentor`, `view.defender` and `view.race`. The selected option's incoming defender comes from `moves` (the player whose `to_slot` is the hot slot).

- [x] **Step 1: Build `RadarCompare`.**
  - 7 fixed axes on 0–100, with grid rings at 25, 50, 75 and 100.
  - Polygons: the tormentor (City blue), the selected candidate (Liverpool red, filled), and the current defender (ghost outline).
  - Motion morphs the polygon `d` when the selection changes. Axis hover highlights the matching `VariableImportance` row (Task 14) through the shared `highlightVar`.
- [x] **Step 2: Build `SprintRace`.**
  - Horizontal lanes, one per curve, over a 0–3 s range.
  - Play/Replay animates with Motion: each runner dot follows `d(t)`, interpolating between the backend samples only.
  - It has a t-slider, labels for `t5m`, `d1s` and `d2s`, and the gap vs Doku at 1 s and 2 s.
  - Caption from `race.label`.
- [x] **Step 3: Verify** with `bun run lint`. Selecting the SWAP card morphs the radar to Szoboszlai, and the race shows Szoboszlai ahead of Frimpong at 1 s.

### Task 14: Swap impact, variable importance and formation preview

**Files:**
- Create: `frontend/src/components/bench/SwapImpact.tsx`, `VariableImportance.tsx` and `FormationPreview.tsx`

**Interfaces:**
- Consumes: `view.impact`, `view.importance`, the selected option's `moves`, and the formation from `MatchDetail`.

- [x] **Step 1: Build `SwapImpact`.**
  - Before the swap it shows a locked placeholder: "Unlocks after the 70' change".
  - After it:
    - Paired bars for before vs after: win %, duels lost per 10 min, channel shots and channel xG, each with n.
    - The defenders' names.
    - A line saying whether the executed swap was the advisor's #1 option at the alert. If not, it states it honestly.
- [x] **Step 2: Build `VariableImportance`.**
  - Top 25 horizontal bars, coloured by family, with a family filter chips row.
  - The header shows the method and AUC with the "methodology demo" caveat.
  - Hovering sets `highlightVar`.
- [x] **Step 3: Build `FormationPreview`.**
  - A small pitch of our formation using `slotPosition`.
  - On selecting an option, Motion animates the dots in `moves` to their `to_slot` (layout animation), and the out-of-position player glows.
  - Caption "Visual only, not data".
- [x] **Step 4: Verify** with `bun run lint`. Scrubbing to 5400 unlocks the impact panel, and hovering the "acceleration" radar axis highlights the importance row.

### Task 15: Coach briefing, pitch dots after swaps, and final docs

**Files:**
- Create: `frontend/src/components/bench/CoachBriefing.tsx`
- Modify: `backend/app/agent/ask.py`. `AskRequest` gains `mode: Literal["chat","briefing"] = "chat"`. The briefing prompt asks for a 3–4 sentence assistant-coach briefing that cites evidence ids, never reorders the options, and ends with the KEEP alternative. The rules fallback returns `view.briefing_seed`.
- Modify: `frontend/src/components/Pitch.tsx` and `frontend/src/hooks/useMatchStream.ts` (dots read slots from the stream `state.on_pitch`, which already reflects swaps after Task 4; check the swap animates)
- Modify: `docs/schema.md` (§5 event types 13 with `position_change`; §7 physical profile; §8 recommendation fields), `docs/architecture.md` (advisor pipeline + new tools) and `CLAUDE.md` (tool list)
- Test: `backend/tests/test_agent.py::test_briefing_rules_fallback_cites_evidence`

- [x] **Step 1: Write the failing test.**
  - `test_briefing_rules_fallback_cites_evidence`:
    - Force the provider to `rules`.
    - `POST /api/agent/ask {"mode":"briefing", …}` returns `provider == "rules"`.
    - The answer contains "KEEP".
    - Every id in `evidence_event_ids` exists.
- [x] **Step 2: Run** `uv run pytest tests/test_agent.py -v`. Expected: FAIL.
- [x] **Step 3: Implement** the briefing mode and `CoachBriefing`.
  - The text has evidence chips that set `highlight`.
  - The provider tag reads "claude" or "rules".
  - It refetches only when `alert.first_fired_sec` or the chosen option changes, not every tick.
- [x] **Step 4: Update the docs** listed above.
- [x] **Step 5: Full verification.**
  - Run `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .`, then `cd ../frontend && bun run lint`. Expected: all green.
  - Run `scripts/run.sh` and walk the demo. Play from 45' at speed. The alert fires between 55' and 68'. The briefing shows. Select SWAP, and the radar, race and preview update. At 70' the pitch dots trade places. After the swap the impact panel unlocks.

## Execution order

1 → 2 → 3 → 4 → **6 → 5** → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15.
- Task 5's seed search needs Task 6's `hot_duels`.
- Tasks 11–14 can run in parallel once Task 9 is merged.
