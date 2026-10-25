#!/usr/bin/env bash
# Install backend + frontend dependencies and prepare local data.
#
#   scripts/install.sh                 # install, keep current APP_MODE
#   scripts/install.sh --mode cloud    # install and persist APP_MODE=cloud in .env
set -euo pipefail
. "$(dirname "$0")/_common.sh"

usage() {
  cat <<EOF
Usage: scripts/install.sh [--mode local|cloud]

  --mode MODE   Persist APP_MODE=MODE in .env (default: leave as is)
  -h, --help    Show this help
EOF
}

MODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --mode=*) MODE="${1#*=}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage; die "unknown argument: $1" ;;
  esac
done

log "checking prerequisites"
require uv   "curl -LsSf https://astral.sh/uv/install.sh | sh"
require bun  "curl -fsSL https://bun.sh/install | bash"
require curl "brew install curl"
ok "uv $(uv --version | awk '{print $2}'), bun $(bun --version)"

ensure_env_file
if [ -n "$MODE" ]; then
  validate_mode "$MODE"
  persist_mode "$MODE"
  ok "APP_MODE=$MODE saved to .env"
fi
load_env
validate_mode "$APP_MODE"

log "backend: uv sync"
(cd "$BACKEND_DIR" && uv sync)
ok "backend dependencies installed"

log "frontend: bun install"
(cd "$FRONTEND_DIR" && bun install)
ok "frontend dependencies installed"

# Synthetic data is generated from a fixed seed, so re-running is idempotent.
if [ -f "$BACKEND_DIR/app/sim/generate.py" ]; then
  log "generating synthetic match data (seed $SIM_SEED)"
  (cd "$BACKEND_DIR" && uv run python -m app.sim.generate)
  ok "synthetic data ready in ${LOCAL_DATA_DIR:-backend/data}"
fi

if [ "$APP_MODE" = "cloud" ]; then
  # Future: infra/provision.sh (terraform apply -> read outputs -> write CLOUD_* into .env).
  warn "cloud provisioning is not implemented yet - fill the CLOUD_* values in .env manually"
fi

ok "install complete (mode: $APP_MODE). Next: scripts/run.sh"
