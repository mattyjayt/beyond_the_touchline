# Backend: Inside the Game API

FastAPI service with the seeded match simulator, replay clock (SSE), deterministic analytics and the agent tool layer. See the [root README](../README.md) and [docs/](../docs).

```bash
uv sync
uv run python -m app.sim.generate                 # writes backend/data/inside_the_game.db
uv run uvicorn app.main:app --reload              # http://127.0.0.1:8000/docs
uv run pytest -q && uv run ruff check .
```

| Endpoint | Purpose |
|---|---|
| `GET /health` | mode, agent provider |
| `GET /api/matches/demo` · `/api/matches/{id}` | match, teams, roster, players |
| `GET /api/matches/{id}/events?until_sec=` | event ledger |
| `GET /api/matches/{id}/state?asof_sec=` | live state as of a second |
| `POST /api/matches/{id}/replay` | `{action: play|pause|speed|seek|restart, value}` |
| `GET /api/matches/{id}/stream` | SSE: snapshot, event, state, insight, recommendation, control |
| `POST /api/agent/ask` | question → Claude (Agent SDK) or rules fallback |
| `/mcp/` | MCP gateway (streamable HTTP) exposing the agent tools |
