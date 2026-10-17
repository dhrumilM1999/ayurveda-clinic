#!/usr/bin/env bash
# Shared helpers for the deploy scripts (they "source" this file). ASK FIRST before editing.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE_FILE_PROD="${COMPOSE_FILE_PROD:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"

# Run docker compose for the live stack
dc() { docker compose -f "$COMPOSE_FILE_PROD" "$@"; }

say()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
fail() { say "ERROR: $*" >&2; exit 1; }

# Reads one value from .env without running it as a script (safe with odd characters)
env_value() {
  [ -f .env ] || return 0
  { grep -E "^$1=" .env || true; } | tail -n1 | cut -d= -f2-
}

need_env() { [ -f .env ] || fail "No .env file here. Run:  bash deploy/make-env.sh"; }

DB_USER="$(env_value POSTGRES_USER)"; DB_USER="${DB_USER:-ayurveda}"
DB_NAME="$(env_value POSTGRES_DB)";   DB_NAME="${DB_NAME:-ayurveda}"
