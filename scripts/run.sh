#!/usr/bin/env bash
# Run the app. Local mode starts the API, waits for it to be healthy, then
# starts the web UI. Cloud mode runs only the UI against the deployed API.
#
#   scripts/run.sh                      # use APP_MODE from .env
#   scripts/run.sh --mode cloud         # override for this run only
#   scripts/run.sh --backend-only       # API only (local mode)
set -euo pipefail
. "$(dirname "$0")/_common.sh"

usage() {
  cat <<EOF
Usage: scripts/run.sh [--mode local|cloud] [--backend-only | --frontend-only]

  --mode MODE       Override APP_MODE from .env for this run
  --backend-only    Start only the API (local mode)
  --frontend-only   Start only the web UI
  -h, --help        Show this help
EOF
}

MODE_FLAG=""; RUN_API=1; RUN_WEB=1
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE_FLAG="${2:-}"; shift 2 ;;
    --mode=*) MODE_FLAG="${1#*=}"; shift ;;
    --backend-only) RUN_WEB=0; shift ;;
    --frontend-only) RUN_API=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage; die "unknown argument: $1" ;;
  esac
done

load_env
APP_MODE="${MODE_FLAG:-${APP_MODE:-local}}"
validate_mode "$APP_MODE"
export APP_MODE

[ -d "$BACKEND_DIR/.venv" ]          || die "backend not installed - run scripts/install.sh"
[ -d "$FRONTEND_DIR/node_modules" ]  || die "frontend not installed - run scripts/install.sh"

API_HOST="${LOCAL_API_HOST:-127.0.0.1}"
API_PORT="${LOCAL_API_PORT:-8000}"
WEB_PORT="${LOCAL_WEB_PORT:-3000}"

if [ "$APP_MODE" = "cloud" ]; then
  RUN_API=0
  API_BASE_URL="${CLOUD_API_BASE_URL:-}"
  [ -n "$API_BASE_URL" ] || die "CLOUD_API_BASE_URL is empty - provision cloud resources or use --mode local"
else
  API_BASE_URL="${LOCAL_API_BASE_URL:-http://$API_HOST:$API_PORT}"
fi

port_in_use() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

PIDS=""
cleanup() {
  trap - INT TERM EXIT
  if [ -n "$PIDS" ]; then
    log "stopping"
    for pid in $PIDS; do
      pkill -TERM -P "$pid" 2>/dev/null || true
      kill -TERM "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
  fi
}
trap cleanup INT TERM EXIT

wait_for_health() {
  local url="$1/health" tries=60
  while [ $tries -gt 0 ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then return 0; fi
    sleep 0.5; tries=$((tries - 1))
  done
  return 1
}

log "mode: ${C_MAGENTA}$APP_MODE${C_RESET}  api: $API_BASE_URL"

if [ $RUN_API -eq 1 ]; then
  port_in_use "$API_PORT" && die "port $API_PORT is already in use (set LOCAL_API_PORT in .env)"
  log "starting API on $API_HOST:$API_PORT"
  (cd "$BACKEND_DIR" && exec uv run uvicorn app.main:app --host "$API_HOST" --port "$API_PORT" --reload) \
    > >(prefix "${C_DIM}[api]${C_RESET} ") 2>&1 &
  PIDS="$PIDS $!"
fi

if [ $RUN_WEB -eq 1 ]; then
  log "waiting for API health"
  wait_for_health "$API_BASE_URL" || die "API did not become healthy at $API_BASE_URL/health"
  ok "API healthy"
  port_in_use "$WEB_PORT" && die "port $WEB_PORT is already in use (set LOCAL_WEB_PORT in .env)"
  log "starting web on http://localhost:$WEB_PORT"
  (cd "$FRONTEND_DIR" && \
    NEXT_PUBLIC_API_BASE_URL="$API_BASE_URL" NEXT_PUBLIC_APP_MODE="$APP_MODE" \
    exec bun run dev --port "$WEB_PORT") \
    > >(prefix "${C_DIM}[web]${C_RESET} ") 2>&1 &
  PIDS="$PIDS $!"
fi

ok "running - press Ctrl+C to stop"
wait
