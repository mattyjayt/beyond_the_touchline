# Beyond the Touchline: demo guide

This guide covers four things:
1. How to install and run the demo.
2. What every screen shows.
3. Which variables the system uses, and why.
4. A minute-by-minute walkthrough of the demo match, including how to read the assistant coach (the **Bench** page).

> **Everything you will see is simulated.** Club and player names are real reference data (2026–27 squads). Every match, event, rating, physical profile, alert and recommendation is synthetic. The page and the docs say so wherever it matters. Nothing here is a claim about real players.

---

## 1. Setup

### Prerequisites

| Tool | Why | Install |
|---|---|---|
| macOS or Linux | the scripts are bash (macOS's bash 3.2 works) | — |
| [uv](https://docs.astral.sh/uv/) | Python 3.13 backend (FastAPI) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [bun](https://bun.sh) | Next.js 16 frontend | `curl -fsSL https://bun.sh/install \| bash` |
| [Claude Code](https://claude.com/claude-code), logged in (optional) | powers the AI analyst and the coach briefing through your subscription | `claude` then `/login` |

Without Claude Code the app still works. The analyst and the briefing fall back to deterministic, rule-based text, and the page tags it `rules` instead of `claude`.

### Install

```bash
git clone https://github.com/mattyjayt/beyond_the_touchline.git
cd beyond_the_touchline
scripts/install.sh
```

`scripts/install.sh` does five things:
1. Checks for `uv`, `bun` and `curl`.
2. Copies `.env.example` to `.env` if you don't have one.
3. Runs `uv sync` for the backend and `bun install` for the frontend.
4. Generates the synthetic data into `backend/data/` (20 historical matches plus the demo match `SIM-001`). This prints `generator_version sim-v0.4` and the demo line `SIM-001 seed=2055 final 0-1`.
5. Runs the duel study, which writes `backend/data/variable_importance.json` for the importance panel.

### Run

```bash
scripts/run.sh                    # API on http://127.0.0.1:8000, then web on http://localhost:3000
scripts/run.sh --backend-only     # API only
scripts/run.sh --frontend-only    # web only
```

Open:
- **Match centre:** http://localhost:3000
- **Assistant coach (Bench):** http://localhost:3000/match/SIM-001/bench, or use the **Bench · Assistant coach →** button in the match-centre header.
- **API docs:** http://127.0.0.1:8000/docs

Press `Ctrl+C` in the terminal to stop both servers.

### Useful settings (`.env`)

| Variable | Default | What it does |
|---|---|---|
| `REPLAY_SPEED` | `10` | match seconds per real second (you can also change it in the UI) |
| `SIM_SEED` | `2026` | generator seed; same seed + version gives byte-identical data |
| `LOCAL_AGENT_PROVIDER` | `claude_code` | set to `rules` to force the offline analyst |

### Other commands

```bash
cd backend && uv run pytest -q                              # backend tests (192)
cd backend && uv run ruff check . && uv run ruff format .   # lint / format
cd frontend && bun run lint                                 # eslint

cd backend && uv run python -m app.sim.generate             # rebuild the synthetic data (prints the demo hash)
cd backend && uv run python -m app.analysis.duel_study --n 40000   # rebuild the variable-importance study
cd backend && uv run python -m app.analysis.catalogue       # rebuild docs/variable_catalogue.md
cd backend && uv run python -m app.sim.calibrate            # re-run the calibration steps (prints each step's choice)
```

### Running on Windows

The scripts are bash and use POSIX tools (`lsof`, `pkill`, `trap`, sourcing `.env`), so native Windows isn't supported yet. Today:

1. Install **WSL2** with Ubuntu (`wsl --install` in an admin PowerShell, then restart).
2. Inside the Ubuntu shell, install uv and bun (the commands in the table above), clone the repo **inside the Linux file system** (e.g. `~/beyond_the_touchline`, not `/mnt/c/...`, which is much slower), then run `scripts/install.sh` and `scripts/run.sh` as normal.
3. Open http://localhost:3000 in your Windows browser. WSL2 forwards localhost automatically.
4. For the AI analyst, install and log in to Claude Code inside WSL as well, or set `LOCAL_AGENT_PROVIDER=rules`.

Native Windows support would need:
- PowerShell (or cross-platform Python) versions of `install.sh` / `run.sh`, with port checks and process clean-up done without `lsof`/`pkill`;
- `.env` loading through Python rather than `source`;
- a `.gitattributes` keeping `*.sh` as LF;
- a Windows job in CI.

The Python and TypeScript code is already portable: uv, bun, Next.js, FastAPI and SQLite all run on Windows, and every text read and write uses UTF-8 explicitly (a test guards this).

### Running on Azure (planned)

Cloud mode is designed but not built, and the Terraform scripts are deliberately deferred for now. **[docs/azure.md](docs/azure.md)** lists every Azure service that replaces a local component and the code work each needs:
- Static Web Apps, Container Apps, Azure SQL / PostgreSQL, Blob Storage, Key Vault, Entra ID, Application Insights, Web PubSub, GitHub Actions;
- **Microsoft Foundry Agent Service** in place of Claude Code (an Azure OpenAI or Claude model deployed in Foundry, calling the same tools over `/mcp`).

### Optional: let Claude Code act as the live analyst

With the app running, the backend exposes an MCP server at `http://127.0.0.1:8000/mcp/` (registered in `.mcp.json`). Open Claude Code in this folder and it can call:
- the read tools: `get_match_state`, `get_player_performance`, `get_player_history`, `get_matchup_analysis`, `get_duel_ledger`, `evaluate_substitutions`, `get_bench_view` and `get_insight_candidates`;
- one write tool, `publish_insight`, which posts evidence-checked insights to the analyst panel.

Tools never see past the replay clock.

---

## 2. The views

There are two pages. The **Match centre** is a live, broadcast-style view of the whole match. The **Bench** is the assistant coach for the home team (Liverpool), focused on one problem: a one-on-one duel Liverpool are losing.

### 2.1 Match centre (`/`)

| Area | What it shows |
|---|---|
| **Header** | `SIMULATED` badge, stream status, mode, and the **Bench · Assistant coach →** link. A red dot pulses on that link once the hot-duel alert has fired. |
| **Scoreboard** | Teams, formations (both 4-2-3-1), animated score, half and clock. |
| **Pitch** | A 105 × 68 pitch. Liverpool attack left → right and City right → left. The white ball follows each event, and a dashed trail shows the last pass or carry. Each **player dot** sits at its formation slot and drifts with the ball. **Dots are visual only: no statistic is ever computed from them.** After the 70' swap, the Szoboszlai and Frimpong dots trade places. |
| **Replay controls** | Play / Pause / Restart, speeds 1× · 10× · 30× · 60× · 120×, and a timeline. Ticks on the timeline mark goals, cards and substitutions; drag it to jump. |
| **Stats panel** | Possession, shots, shots on target, xG (an illustrative model), passes and pass accuracy, plus a **momentum** bar: a rolling 5-minute threat index. |
| **Event stream** | Every simulated event, newest first. Tick **all events** to include routine passes. Clicking an event highlights it on the pitch. |
| **Match Analyst** | Insights published by the rules agent (and Claude, if connected), in a **Fan** (short, plain) or **Analyst** (metric-led) voice. Each insight cites event IDs as clickable chips. Ask a question at the bottom, e.g. *"Should Liverpool change the right back?"*. The tag shows which agent answered (`claude_code` or `rules`). |

### 2.2 Bench, the assistant coach (`/match/SIM-001/bench`)

The page is built from one backend call (`GET /api/matches/SIM-001/bench`). Every number on it is computed in tested Python; the page and the AI only display and narrate.

**Coach header**
- **Score and clock:** score and the second being viewed.
- **Alert pill:** for example *"Doku vs RB: beaten 4 in 20' · win 0% (n=5) · since 55'"*. Red and pulsing means the alert is firing now; grey means it fired earlier and is quiet.
- **Scrubber:** drag it to view the bench as of any second. **● Live** follows the replay clock. You can't scrub past the replay clock, because nothing in the future is ever shown.
- **Disclosure (amber):** what is pinned or scripted in this demo.

**Briefing**
- A 3–4 sentence assistant-coach briefing for the second you are viewing, written by Claude (tag `claude`) or by the deterministic template (tag `rules`).
- It names the losing duel, cites evidence chips, keeps the advisor's ranking order, and always ends with the KEEP alternative.
- Clicking an evidence chip highlights that duel on the flank pitch.

**Where the duels happen (3D flank pitch)**
- Every one-on-one between the attacker (Doku) and whoever holds the alerted slot (RB), at its real coordinates, on a tilted pitch.
- **Green dots:** the defender won the duel or recovered the ball straight away.
- **Red dots:** he was beaten or fouled.
- **Dot size:** the duel model's chance that the attacker would win (`p_beat`).
- **Red columns:** duels lost per zone along the flank.
- **Before swap / After swap / All:** filters around the 70' change.
- **Click a dot:** shows that duel's stored model terms (tech, burst, stance, ctx, script, p_beat).
- **Threat line underneath:** shots, xG and crosses/box entries from this flank in the last 20'.

**Duel win rate**
- The defender's rolling 10-minute win rate against the attacker.
- **Dashed line:** the league-average defender win rate (61%).
- **Vertical markers:** the alert and the swap.
- **Gaps:** no duels in that window.
- Hover for the exact win % and n; click to jump the scrubber to that second.

**Options**
One card per option: **KEEP**, **SUB** (a substitution), **SWAP** (two players already on the pitch trade positions) and **SUB + SWAP**. They are ranked by a policy score; the KEEP card is the baseline and scores 0.

| Element on a card | Meaning |
|---|---|
| `#rank` and score | Policy score as a change against KEEP. Positive means better than keeping things as they are. |
| `≈ tied` | Within 0.03 of a neighbouring option: treat them as level, not as a strict order. |
| confidence chip | `low` / `medium` / `high`: the weakest of three things — how much evidence there is, how often the incoming player has played that slot before, and how well he fits it. |
| `Out of position` | The option puts someone in a position that isn't one of his listed positions. |
| Moves | e.g. *"Jeremie Frimpong off (RB) · Joe Gomez on → RB"* |
| Six bars (−1 … +1) | **Live form, Fit, Duel win, Attack, Game state\*, Risk** (explained in §3.6). Green is better than KEEP, red worse. \*Game state re-weights Attack and Duel win; it isn't independent. |
| 1v1 win (blended) | The duel model's projection blended with what has actually happened, with a 90% interval. |
| Model only / Observed | The model projection alone, and the record against this attacker in this match (with n). |
| Pros (+) / cons (−) | Each one quotes its numbers, e.g. *"Level off the mark with Jeremie Frimpong: 1.73 vs 1.67 m after 1 s (max accel 7.40 vs 7.00 m/s²)"*. |
| Choose | Marks your pick (stored in your browser only) and re-asks the briefing with it in mind. |

**Profile vs the tormentor (radar)**
- Seven axes on 0–100: pace, acceleration, agility, stamina, defending, stance (side-on tendency) and 1v1 win %.
- **Blue:** the attacker (Doku). **Red:** the selected option's incoming defender. **Dashed:** the current defender.
- Hover an axis to see the real units (km/h, m/s²) and to highlight the matching group in the importance panel.

**First steps: 0–3 s sprint**
- A race from a standing start for the attacker, the current defender and the candidate, using the sprint model.
- Each row shows time to 5 m, metres covered at 1 s and 2 s, and the gap to the attacker. **▶ Play** animates the race; the slider scrubs time.

**Swap impact** (unlocks after the 70' change)
- Compares the 20 minutes **before** the swap with the time **since**:
  - duels lost per 10', channel xG and channel shots;
  - defender win % with 95% intervals;
  - a trajectory table at 5', 10' and 20' after the change.
- It only says "up" or "down" if the intervals don't overlap.
- It says where the swap Liverpool actually made ranked when the alert fired. In this demo: *9th of 17, below KEEP*.

**Shape after the change**
- A mini-pitch with Liverpool's formation. Selecting an option card animates the moving players to their new slots.
- Ringed dots are the players that option moves; amber means out of position. Visual only.

**What drives a 1v1 here (variable importance)**
- The duel study: which groups of inputs drive the simulator's duel outcomes, with each group's rank range across five seeds.
- It is a **methodology demo**: the importance mirrors how the generator is built, not football truth (§3.8).

---

## 3. Variables, assumptions and reasoning

The design rests on six principles:
- **Events are the source of truth.** Every number is derived from the simulated event stream plus the rosters.
- **All arithmetic lives in tested Python**, never in the UI or the AI. The AI cannot reorder the advisor's options.
- **Same seed + same version gives identical data.**
- **Honesty over flattery.** Everything shows its sample size and uncertainty, and scripted or pinned parts are disclosed on the page.
- **Pre-registration.** Calibration targets and selection rules were written down before any run, and every later change is recorded in `docs/schema.md` §11.
- **Real-world ranges** come from `reports/Football matchup variables catalogue.md`, a 108-variable research summary.

### 3.1 The physical profile (per player)

| Field | Unit / range | Why it matters |
|---|---|---|
| `top_speed_kmh` | 29–37.4 | Mainly decides whether a beaten defender **recovers**; it barely affects the first two steps |
| `accel_ms2` (A0) | 6.0–7.9 m/s² | Maximal starting acceleration: who wins the **first step** |
| `agility_idx` | 0–100 | Change of direction |
| `stamina_idx` | 0–100 | How fast acceleration and agility fade late in the match |
| `stance_idx` | 0–100 | Tendency to defend **side-on**, the best-supported defending technique in the research |
| `height_cm` | 165–200 | Descriptive only |

**How the values are sampled:**
- Top speed is drawn by position (CB 32.5, FB 34.0, CM 32.5, W 34.5, ST 33.5 km/h; σ 1.2).
- A0 means come from published LaLiga data: CB 6.79, FB 6.70, CM 6.44, W and ST 6.40 m/s² (σ 0.35, correlation with speed ρ = 0.6).
- Agility, stamina and stance come from the player's ability priors plus noise.

**Pinned demo profiles (fictional, chosen for the storyline):**

| Player | Top speed | A0 | Agility | Stamina | Stance | Note |
|---|---|---|---|---|---|---|
| Doku (MCI LW) | 35.1 | 7.80 | 95 | 72 | sampled | elite first step and agility |
| Frimpong (LIV RB) | 36.4 | 7.00 | 84 | 80 | 38 | very fast, but square-on; defending prior pinned to 68 ("modest") |
| Szoboszlai (LIV RW/CM) | 32.6 | 7.55 | 80 | 93 | 74 | slower, quicker off the mark, side-on |
| Gomez (LIV bench, CB/RB) | 33.9 | 7.40 | 70 | 76 | 78 | stopper |
| Bradley (LIV bench, RB) | 34.6 | 7.20 | 78 | 82 | 60 | balanced natural right-back |

### 3.2 The duel model (`duel-v3`, one formula used everywhere)

Every take-on is decided by one function, which the simulator, the advisor and the study all share:

```
tech   = dribbling(att) − defending(def)                       # ability priors
burst  = d_att(1 s) − d_def(1 s)                               # metres gained in the first second (sprint model)
agil   = agility(att) − agility(def)
ctx    = +8 isolated (no team-mate within reach)
         −6 a covering team-mate within 10 units
         +6·(1 − stance)          # square-on concedes
         −4·(1 − touch/50)        # the touchline acts as an extra defender
         +6 transition (attacking full-back, possession < 8 s old)
         +4 defender already on a yellow
z      = (0.5·tech + 0.1·agil + ctx + script − 16) / 10  +  4.22 · burst
p_beat = 0.85 · logistic(z)
```

- **Burst is in metres, from the same sprint model as the race panel.** Its weight (4.22 per metre) is derived rather than tuned: half a m/s² of extra acceleration at equal top speed is worth 1.5× the odds of winning the duel.
- **Fatigue** reduces A0 and agility after 55 minutes, faster for low-stamina players.
- **Recovery:** if the defender is beaten, he wins the ball straight back with probability 0.10 + 0.04 × (his top speed − the attacker's + 2), clamped to 3–35%. This is where top speed matters.
- **Last-man fouls:** a beaten last defender fouls 25% of the time. That is a yellow 80% of the time, and a red 10% of the time when the attacker is central and within about 25 m of goal.
- **`script`:** the demo's handicap, +6 (so +0.6 on z) applied **only** while Frimpong holds RB between 50' and 70'. It is stored on every duel and visible when you click a dot.
- The model is labelled **"simulator model, uncalibrated"** wherever it appears.

### 3.3 Calibration (the simulated league looks like a real one)

| Target (pre-registered) | Result |
|---|---|
| League take-on success 34–40% averaged over seeds 1–5, each seed 30–44% (real PL ≈ 36.7%) | 39.0% (baseline offset 16) |
| Sendings-off ≤ 0.2 per match | 0.17 (a booked player is 95% less likely to get another card: cautious) |
| The scripted attacker's volume ≤ 18 take-ons per 90 on average | 13.1 per 90 on the pre-registered check (seeds 1–5). Over 50 seeds it is 18.6, slightly above the cap. The real Doku manages about 10. |
| Hot-duel alert fires in ≤ 5% of non-demo matches | 2 of 100 |

### 3.4 The hot-duel alert (when does the coach get interrupted?)

The alert fires for a defending slot (here RB) and an attacker when **all three** hold over the **last 20 minutes**:
1. The **current** holder of the slot has been beaten in **≥ 3 separate possessions**. Three beats in one dribbling run count once.
2. He is confidently **worse than a league-average defender**: the probability that his true win rate is below the league's 61% is at least 95%. The estimate starts from the league average as if he had already played 6 average duels, which stops a couple of losses from causing panic.
3. **The flank is dangerous:** at least 1 shot, or at least 2 completed crosses or box entries, from that channel.

The alert is **sticky**. Once it has fired, that attacker and that slot stay the subject of the page as the duel cools down, heats up again, or the slot changes hands:
- **active:** firing now;
- **cooling:** fired earlier, quiet now;
- **monitoring:** a new player has taken the slot and has had fewer than 4 duels. The advisor offers KEEP only, because there's no record to judge him on yet, and it never shows the previous player's numbers under his name.

### 3.5 How options are generated

- **KEEP:** always present; the baseline everything is compared against.
- **SUB:** a bench player whose fit for the slot is at least 0.5.
- **SWAP:** two players already on the pitch trade positions. Both must fit their new slots at least 0.3, their main roles can be at most one step apart (DEF↔MID or MID↔ATT), and no goalkeepers.
- **SUB + SWAP:** a team-mate moves into the hot slot, the struggling defender comes off, and the best-fitting sub fills the gap.
- **The shortlist** always shows the best option of each type and the best natural-position sub, up to four plus KEEP.
- **Fit:** 1.0 for his main position, 0.8 for a listed secondary position, 0.5 for the same role group, 0.3 for an adjacent group (flagged as a projected role), and 0 otherwise.

### 3.6 The six dimensions and the policy score

Each option is scored **as a change against KEEP**, so KEEP is 0 by definition:

| Bar | Meaning | Weight |
|---|---|---|
| **L** Live form | How far the outgoing defender is below his usual rating (half credit for a swap, because he stays on the pitch) | 0.15 |
| **F** Fit | The new player's fit for the slot minus the current holder's | 0.15 |
| **M** Duel win | (incoming defender's blended estimate − current defender's blended estimate) / 0.30 | **0.35** |
| **A** Attack | Attacking quality gained or lost in the slots that change, weighted by how attacking each slot is | 0.10 |
| **G** Game state | Re-weights A (when losing) or M (when winning), stronger later in the match | 0.10 |
| **R** Risk | Defending drop, card risk, poor fit in a vacated slot, a substitution used | 0.15 |

**Adjustments to the score:**
- **Disruption:** −0.05 for every player moved beyond a single sub or swap.
- **Ties:** options within 0.03 of a neighbour are marked tied.

**The blended estimate (the 1v1 win figure on each card):**
- It starts from the duel model's projection against this attacker, averaged over isolated/covered and transition/settled situations, using the defender's own stance and minutes played.
- That projection is treated as if it were 6 duels' worth of evidence, then combined with his actual record against this attacker today.
- Example: a model projection of 39% plus a record of 0 wins in 5 duels gives (0 + 6 × 0.39) / (5 + 6) ≈ 21%.

**Confidence** is the lowest of three bands:
- **Evidence:** the width of the 95% interval on the duel record. High needs a half-width of 0.12 or less; fewer than 5 duels is always low.
- **History at the slot:** 0 prior matches is low, 1–2 medium, 3+ high.
- **Fit:** below 0.5 is low, below 0.8 medium.

These weights are a **policy**, not a causal estimate. The page says so on every view.

### 3.7 Swap impact

- **Before** is the 20 minutes before the swap, the same window the alert uses, so the per-10-minute rates compare like with like.
- **After** is everything since the swap.
- Rates are hidden for windows shorter than 5 minutes, and intervals for fewer than 5 duels.
- A direction is only drawn when the 95% intervals don't overlap.
- The page also states where the actual swap ranked at the alert, among every option the advisor scored.

### 3.8 The variable catalogue and the duel study

- **`docs/variable_catalogue.md`** lists 171 variables: our own physical, ability, context, duel-term, history, event and rating variables, plus the research report's 108 rows. Each row carries its real-world range and source.
- **The duel study** samples 40,000 simulated duels per seed across five seeds and fits a logistic regression on the primitive inputs only (derived terms are excluded). It measures how much each **group** of inputs matters by shuffling the group's columns together.
- **Result:**
  1. dribbling vs defending priors
  2. isolation and cover
  3. acceleration
  4. stamina and minutes
  5. transition exposure
  6. defender on a yellow
  7. agility
  8. stance
  9. touchline
  10. top speed (last on every seed)
- **Fit:** model AUC 0.744 against an oracle (scoring with the true probabilities) of 0.752. The model has learned almost everything the generator contains, so the ranking describes the simulator. That is why the page calls it a **methodology demo**.

### 3.9 What we deliberately did not do

- **No formation changes, no pressing or tracking-back claims.** There is no off-ball data. Even "ask a team-mate to double up" appears only as an unscored note on KEEP.
- **No WebGL and no chart library:** CSS 3D and hand-drawn SVG.
- **No causal claims:** deltas are shown with their sample sizes and intervals, never as "this would have saved a goal".
- **No AI arithmetic:** Claude narrates the numbers the tools return and must cite event IDs. `publish_insight` rejects unknown or future evidence.

### 3.10 Disclosures specific to this demo

- **Pinned:** the demo players' profiles above are pinned for the storyline.
- **Scripted:** from 50', Doku gets more of the ball and keeps meeting whoever holds Liverpool's RB slot. The +0.6 z handicap applies only while Frimpong is there.
- **Forced:** the 70' swap (Szoboszlai to RB, Frimpong to RW) happens **whatever the advisor says**. Everything after it comes from the model alone, but Doku's volume and his pairing with the RB holder stay scripted.
- **Busy match:** in this demo Doku makes about 43 take-ons per 90 in the scripted window, against about 19 on average for the scenario (18.6 over 50 seeds, slightly above the pre-registered cap of 18, which was checked on seeds 1–5 only). The demo seed search needs repeated beats, so it favours busy matches.
- **Seed history:** the demo seed changed four times (2029 → 2027 → 2036 → 2055). The trigger's definition changed twice after it was first written down. The full history, including the version where the swap failed, is in `docs/schema.md` §11.

---

## 4. The story: what happens when you run the demo

**SIM-001 · Liverpool (home, 4-2-3-1) v Manchester City (4-2-3-1) · simulated.** The demo is about one matchup on Liverpool's right: **Jérémy Doku** (City LW, the most direct dribbler in the league) against **Jeremie Frimpong** (Liverpool RB, an attacking full-back who is very fast but defends square-on). On Liverpool's right wing is **Dominik Szoboszlai**, a midfielder who can also play RB.

### Before you start

1. Run `scripts/run.sh` and open **http://localhost:3000**.
2. Open the Bench in a second tab: **http://localhost:3000/match/SIM-001/bench**. Leave it on **● Live**.
3. In the match centre, press **Play** and set the speed to **30×**. A full match then takes about 3 minutes. To skip the quiet first half, drag the timeline to about **48'**.

### 0'–50': a normal match

Nothing is scripted yet. On the Bench:
- the alert pill says *"No hot duel yet"*;
- the only option is **KEEP**;
- the briefing says no defender is being beaten repeatedly.

That is the system being quiet when it should be. In 98 of 100 simulated non-demo matches it never fires.

Meanwhile, in the match centre:
- Haaland is booked at **53:29** (watch the timeline tick and the event stream);
- the score stays 0-0.

### 50'–55': the pressure builds

The scripted spell starts at 50'. City feed Doku, and every first take-on in a possession meets the RB.

On the **Bench**, watch two panels:
- **Where the duels happen:** red dots start clustering on Liverpool's right flank, bottom left of the tilted pitch, and red columns rise along the touchline.
- **Duel win rate:** the red line drops well below the dashed league-average line (61%).

### 55:33: the alert fires (score 0-0)

- **The alert pill turns red and pulses:** *"Doku vs RB: beaten 4 in 20' · win 0% (n=5) · since 55'"*.
- **In the match centre,** the Bench link gets a red dot and the analyst publishes a *"Hot duel"* insight.
- **The flank panel** reads *"0 shot(s) · 8 cross(es)/box entries · no shots conceded from this flank yet"*. The danger is real, but it hasn't cost a shot yet; the assistant says so rather than exaggerating.
- **Read the briefing.** It names the duel, cites evidence chips (click one and the duel lights up on the pitch), and lists the advisor's options in order, ending with KEEP. Claude's exact wording varies run to run; the `rules` version is fixed.

**How to read the options at this moment:**
1. **Joe Gomez for Frimpong** — score about +0.25, *tied*.
2. **Swap: Leoni to RB, Frimpong to RCB** — tied, flagged **Out of position** (Frimpong at centre-back is a projected role).
3. **Conor Bradley for Frimpong** — the like-for-like RB, tied.
4. **Leoni to RB, Frimpong off, Gomez on at RCB** — tied.
5. **KEEP** — the baseline.

The four changes are within 0.03 of each other, so the honest message is *"make a defensive change at RB; which one is close"*, not "Gomez, definitely". Open the Gomez card:
- **Bars:** *Duel win* is strongly green (Gomez projects much better against Doku). *Fit* is slightly red (RB is his secondary position; Frimpong is a natural RB). *Risk* is slightly red (it uses a substitution).
- **Stats:** the blended estimate is about 66% with a wide 90% interval, the model alone says something similar, and *Observed* is n/a (n=0): Gomez hasn't faced Doku yet.
- **Pros and cons quote numbers:**
  - *"Level off the mark… 1.73 vs 1.67 m after 1 s"*: the gain is not raw speed.
  - *"Defends side-on more often: stance 78 vs 38"*: this is the real driver.
  - *"Lower top speed… fewer recoveries once beaten"*: an honest con.

**Select a card** and three panels respond:
- **Radar:** the red shape morphs to the candidate, with Frimpong as a dashed ghost. Notice Frimpong's big *pace* spike and his collapsed *stance* axis.
- **Sprint race:** press **▶ Play** and the three runners are almost level after 1 s. That is why the copy says "level off the mark" rather than "faster".
- **Shape after the change:** the moving players glide to their new slots.

**Hover an axis on the radar** (e.g. *Stance*) to highlight the matching group in the importance panel. The study ranks *Dribbling vs defending* and *Isolation and cover* highest and *Top speed* last: the generator's version of "pace isn't what wins one-on-ones".

### 57'–68': the alert breathes

- Around **57:30** the pill turns grey (*cooling*): Frimpong won a duel.
- Around **59:00** it turns red again, and it cools again around **60:30**.
- Around **67:30** it is back on, with Frimpong now beaten in 6 possessions (n=10). **Bradley for Frimpong** briefly becomes #1, because the natural RB's fit outweighs Gomez's.
- At **68:14** Doku gets his own shot off from the flank (off target).

This back-and-forth is the alert reacting honestly to a short, noisy window. The options don't flicker away when it cools, because the alert is sticky.

### 70:23: the swap

- At the first stoppage after 70', Liverpool move **Szoboszlai to RB and Frimpong to RW**, recorded as two `position_change` events.
- In the **match centre**, their dots trade places.
- On the **Bench**:
  - **The pill keeps the RB slot but now names Szoboszlai,** and the state is **monitoring**: *"has only 0 duel(s) … monitoring until 4"*.
  - **The advisor offers KEEP only.** It refuses to judge him on Frimpong's numbers.
  - **The Swap impact panel unlocks.**

Read the honesty line at the bottom of Swap impact: *"The swap Liverpool made ranked #9 of 17 options the advisor scored at the alert, below KEEP. It is scripted at 70' whatever the advisor says."* The advisor would not have made this move, because the model rates Szoboszlai's defending (62) as a real cost. The demo shows you what happens anyway.

### 74:30–90': after the swap

- At about **74:30** Szoboszlai has 4 duels of his own and monitoring ends (state *cooling*). From here the advisor judges him on his own record.
- **Swap impact** fills in as the minutes pass:
  - **Before (Frimpong, 20'):** 2 wins in 9 duels (22%), 2.50 duels lost per 10'.
  - **After (Szoboszlai):** 6 wins in 9 (67%), 1.02 lost per 10'.
  - **The trajectory table:** 3 wins of 4 at 5', then 5 of 6 at 10'.
  - **The verdict:** *"No clear change in win rate yet: the 95% intervals overlap"* (22% [6–55%] vs 67% [35–88%]). The swap looks good, but nine duels each way can't prove it, and the page won't pretend otherwise.
- **The duel win-rate line** climbs back above the league average after the swap marker.
- **Elsewhere in the match:**
  - **76:05:** Endo off, Mac Allister on.
  - **78:36:** Frimpong (now at RW) is substituted for Chiesa.
  - **80:45: City score (0-1)** through Samba, in a possession where Doku had beaten Szoboszlai in the channel. It is the one channel shot since the swap (the panel's *Channel shots* "after" row). Even with a better duel record, one beat at the wrong moment costs a goal, which is why the page won't call the swap a success.
  - **81:24:** Gomez comes on for Leoni at RCB. Around **81:30** the advisor's top option becomes *"Swap: Gomez to RB, Szoboszlai to RCB"*. With Liverpool behind and Gomez on the pitch, it suggests putting the stopper on Doku with no substitution needed. At 90' that swap is still #1, with Bradley-for-Szoboszlai and KEEP close behind (tied).
- **Full time: Liverpool 0-1 Manchester City (simulated).**

### How to use the bench assistant: a checklist

1. **Start with the pill.** Is the alert *active*, *cooling* or *monitoring*? Monitoring means "too early to judge the new player"; act on nothing yet.
2. **Read the threat line.** Beaten duels that don't produce shots or entries are a nuisance, not an emergency. This demo's alert fired with **0 shots** but 8 entries.
3. **Treat tied options as level.** The rank matters less than the shared message (e.g. "change the RB").
4. **Read the Duel win bar first.** It carries the biggest weight (0.35). Then check *Fit* and *Risk* for the cost.
5. **Check n and the intervals.** A blended 66% with a 90% interval of 33–92% and n=0 observed is a model-based bet, not evidence.
6. **Trust the pros and cons, not the vibe.** They state the mechanism: here stance and transition exposure, not top speed.
7. **Use the sprint race and radar** to sanity-check the physical story.
8. **Scrub back** to see what the assistant knew at any moment. It never knows the future.
9. **Choose** an option to log your pick (it stays in your browser) and get a briefing written around it.
10. **Remember the label:** simulated, policy weights, not causal. The assistant structures the decision; the coach makes it.
