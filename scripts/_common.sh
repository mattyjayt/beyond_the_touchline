#!/usr/bin/env bash
# Shared helpers for install.sh / run.sh. Sourced, not executed.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/.env.example"

if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_DIM=$'\033[2m'; C_RED=$'\033[31m'
  C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'; C_MAGENTA=$'\033[35m'
else
  C_RESET=""; C_DIM=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_MAGENTA=""
fi

log()  { printf '%s==>%s %s\n' "$C_BLUE" "$C_RESET" "$*"; }
ok()   { printf '%s ok%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '%s !!%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
die()  { printf '%sERR%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }

require() {
  # require <cmd> <install hint>
  command -v "$1" >/dev/null 2>&1 || die "'$1' not found. Install it: $2"
}

ensure_env_file() {
  if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    ok "created .env from .env.example"
  fi
}

load_env() {
  [ -f "$ENV_FILE" ] || die ".env missing - run scripts/install.sh first"
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
}

validate_mode() {
  case "$1" in
    local|cloud) ;;
    *) die "invalid mode '$1' (expected: local | cloud)" ;;
  esac
}

# Persist APP_MODE into .env, keeping any trailing comment on the line.
persist_mode() {
  local tmp="$ENV_FILE.tmp"
  sed "s/^APP_MODE=[a-z]*/APP_MODE=$1/" "$ENV_FILE" > "$tmp" && mv "$tmp" "$ENV_FILE"
}

# Prefix every line of a stream, flushing per line (portable across BSD/GNU).
prefix() {
  awk -v p="$1" '{ print p $0; fflush() }'
}
