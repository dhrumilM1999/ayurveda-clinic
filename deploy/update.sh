#!/usr/bin/env bash
# Updates the live app to the newest code, safely. ASK FIRST before editing.
#
#   bash deploy/update.sh              -> backup, download new code, rebuild, restart, check it works
#   bash deploy/update.sh --rollback   -> go back to the code that ran before the last update
#   bash deploy/update.sh --skip-backup  (only if you just made a backup yourself)
#
# Rollback goes back to the old CODE. If the update changed the database design (a migration), the data stays
# in the new design; if something is badly wrong, restore the backup made just before the update
# (bash deploy/restore.sh backups/daily/<newest> ), see docs/GO_LIVE.md.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
need_env

STATE_FILE="$PROJECT_DIR/.deploy-previous-commit"
ROLLBACK=0; SKIP_BACKUP=0
for arg in "$@"; do
  case "$arg" in --rollback) ROLLBACK=1 ;; --skip-backup) SKIP_BACKUP=1 ;; *) fail "Unknown option: $arg" ;; esac
done

wait_until_healthy() {
  say "Waiting for the app to start (up to 4 minutes)..."
  for i in $(seq 1 48); do
    backend="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$(dc ps -q backend)" 2>/dev/null || echo none)"
    caddy="$(docker inspect -f '{{.State.Status}}' "$(dc ps -q caddy)" 2>/dev/null || echo none)"
    if [ "$backend" = "healthy" ] && [ "$caddy" = "running" ]; then say "The app is up and healthy."; return 0; fi
    sleep 5
  done
  return 1
}

if [ "$ROLLBACK" = "1" ]; then
  [ -f "$STATE_FILE" ] || fail "No earlier version is recorded (update.sh has not run before)."
  PREV="$(cat "$STATE_FILE")"
  git diff --quiet && git diff --cached --quiet || fail "Files in this folder were edited by hand. Ask your helper before rolling back."
  say "Going back to version $PREV ..."
  git reset --hard "$PREV"
  dc up -d --build
  wait_until_healthy || fail "The old version did not become healthy either. Run: bash deploy/status.sh  and  docker compose -f $COMPOSE_FILE_PROD logs backend --tail 100"
  say "Rolled back. If data looks wrong, restore the backup made before the update."
  exit 0
fi

CURRENT="$(git rev-parse HEAD)"
git diff --quiet && git diff --cached --quiet || fail "Files in this folder were edited by hand. Ask your helper before updating."

if [ "$SKIP_BACKUP" = "0" ]; then
  say "Making a backup first..."
  bash "$PROJECT_DIR/deploy/backup.sh" || fail "The backup failed, so I did NOT update. Fix the backup first (or use --skip-backup if you are sure)."
fi

say "Downloading the newest code..."
git fetch origin
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
git merge --ff-only "origin/$BRANCH" || fail "Cannot update cleanly. Ask your helper."
NEW="$(git rev-parse HEAD)"
if [ "$NEW" = "$CURRENT" ]; then
  say "Already on the newest version ($(git rev-parse --short HEAD)). Rebuilding anyway to be sure."
else
  echo "$CURRENT" > "$STATE_FILE"
  say "Updated: ${CURRENT:0:7} -> ${NEW:0:7}"
fi

say "Building and restarting (a minute or two)..."
dc up -d --build --remove-orphans
if wait_until_healthy; then
  docker image prune -f >/dev/null 2>&1 || true
  say "UPDATE DONE."
else
  say "The new version did not become healthy."
  say "Look at the messages:  docker compose -f $COMPOSE_FILE_PROD logs backend --tail 100"
  say "To go back:           bash deploy/update.sh --rollback"
  exit 1
fi
