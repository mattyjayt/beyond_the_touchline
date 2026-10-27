# Frontend: Beyond the Touchline match centre

Next.js 16 (App Router), Tailwind v4 and Motion. The page is a static shell around a client-side match centre that reads the backend over REST and SSE. Run it through `scripts/run.sh` from the repo root, which sets `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_MODE`.

```bash
bun install
bun run dev        # http://localhost:3000 (expects the API on :8000)
bun run lint && bunx tsc --noEmit
```

- `src/components/`: `MatchCenter` (layout), `Pitch`, `Scoreboard`, `ReplayControls`, `StatsPanel`, `EventFeed`, `AgentPanel`
- `src/hooks/useMatchStream.ts`: SSE reducer
- `src/lib/types.ts`: mirror of the backend Pydantic contracts (keep in sync)
- `src/lib/pitch.ts`: coordinate transforms; player dots are visual only
