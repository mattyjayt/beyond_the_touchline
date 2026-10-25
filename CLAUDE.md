# CLAUDE.md

Guidance for Claude Code in this repository. The project owner edits this file as the project evolves — treat it as the source of truth for conventions and your role.

## Project

**Inside the Game** — an AI-assisted football intelligence MVP. A seeded simulator produces a synthetic Premier League-style match as an event stream; deterministic services turn events into ratings, alerts and substitution options; an AI analyst narrates them with evidence. The product spec is `docs/Inside_the_Game_Synthetic_Data_and_Schema_Specification.pdf`; the MVP narrowing lives in `docs/schema.md` and `docs/architecture.md`.

Hackathon timeline: favour working, demoable increments over completeness.

## Your role

1. **Co-developer.** Build backend, frontend, scripts and docs with the owner. Propose, then implement; keep changes small and verifiable.
2. **Live analyst agent (MVP).** While the app runs, you act as the match agent through the backend's MCP gateway (`/mcp`, registered in `.mcp.json`). Read state with the read-only tools, then publish insights with `publish_insight`. Rules for that role:
   - Never compute football facts yourself — use tool outputs. Never alter match facts or ratings.
   - Every claim cites `evidence_event_ids` that exist. State uncertainty. Substitution advice always includes a KEEP option.
   - Everything is synthetic: say so; never present output as a real match fact.

## Non-negotiables (from the spec)

- Events are the single source of truth; every stat, score and rating must be derivable from them.
- Arithmetic lives in tested Python services, not in the LLM or the UI.
- Reproducibility: same `SIM_SEED` + generator version ⇒ identical events and metrics.
- Label all matches, ratings and recommendations as **simulated**. Club/player names are real reference data only.
- Pitch player dots are visual-only (formation slot + ball position); never derive metrics from them.

## Agent gateway (how you act as the analyst)

- With the app running, the `inside-the-game` MCP server (`.mcp.json` → `http://127.0.0.1:8000/mcp/`) exposes `get_match_state`, `get_player_performance`, `get_player_history`, `get_matchup_analysis`, `evaluate_substitutions`, `get_insight_candidates` and `publish_insight`.
- Tools never return data past the live replay clock. `publish_insight` rejects unknown or future evidence IDs and duplicate insight IDs. Use `generator_version` `claude-code-mcp` (set automatically).
- UI chat goes to `POST /api/agent/ask`, which runs Claude through the Agent SDK (`app/agent/ask.py`, subscription login) and falls back to `rules`. The always-on rules agent is in `app/agent/rules.py`.
- To add a tool: implement it once in `app/agent/tools.py`, then expose it in `mcp_server.py` and `ask.py::_sdk_tools`.

## Repo layout

```
backend/          FastAPI + uv (Python 3.13). App package: backend/app
  app/config.py   Settings; resolves LOCAL_*/CLOUD_* via APP_MODE
  app/main.py     FastAPI app: lifespan, routers, /mcp mount, rules agent
  app/api.py      REST + SSE routes
  app/sim/        Simulator (engine), validator, generator
  app/services/   live_state (stats/momentum), performance (metrics, rating v0)
  app/agent/      tools (single definition), rules, ask (Agent SDK), mcp_server
  app/replay.py   Shared replay clock + SSE fan-out
  app/seed/       Real reference data (PL clubs/squads JSON)
  data/           Generated synthetic data + SQLite (gitignored)
  tests/          pytest
frontend/         Next.js 16 (App Router, src/), bun, Tailwind v4, Motion
docs/             Spec PDF, schema.md, architecture.md
scripts/          install.sh, run.sh, _common.sh
.env.example      Two-section env template (copied to .env on install)
```

## Commands

```bash
scripts/install.sh [--mode local|cloud]    # deps (uv sync, bun install) + .env + synthetic data
scripts/run.sh [--mode local|cloud] [--backend-only|--frontend-only]

cd backend && uv run pytest -q             # backend tests
cd backend && uv run python -m app.sim.generate   # rebuild synthetic data (prints demo hash)
cd backend && uv run ruff check . && uv run ruff format .
cd backend && uv add <pkg>                 # never pip install
cd frontend && bun run lint                # eslint
cd frontend && bun add <pkg>               # never npm/yarn
```

API: http://127.0.0.1:8000 (`/health`, `/docs`). Web: http://localhost:3000.

## Environment model

One root `.env` with sections SWITCH (`APP_MODE`), SHARED, `LOCAL_*`, `CLOUD_*`. Backend code reads only resolved properties on `Settings` (`settings.database_url`, `settings.agent_provider`, …) — never `LOCAL_`/`CLOUD_` keys directly. The frontend receives `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_MODE` from `run.sh`. Cloud values will be written by future Terraform provisioning (`infra/`); until then, design locally and document the Azure equivalent in `docs/architecture.md`.

## Conventions

- **Python:** type hints, Pydantic models for every API/agent contract, ruff (line length 100). Keep services pure and testable; I/O at the edges.
- **Contracts:** backend Pydantic models in `backend/app/models/` are canonical; mirror them in `frontend/src/lib/types.ts` and keep both in sync in the same change.
- **IDs:** `T-ARS`, `P-ARS-07` (club code + shirt number), `SIM-001`, `SIM-001-E0001`.
- **Frontend:** Next.js 16 has breaking changes vs. older versions — read the relevant guide in `frontend/node_modules/next/dist/docs/` before writing Next-specific code. `cacheComponents` is enabled. Animations use `motion` (`motion/react`).
- **Scripts:** bash 3.2-compatible (macOS default) — no associative arrays or `${x,,}`.
- Don't commit unless asked. Never commit `.env`.

## Frontend agent rules

@frontend/AGENTS.md
