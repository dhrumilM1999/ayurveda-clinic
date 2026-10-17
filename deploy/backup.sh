#!/usr/bin/env bash
# Makes a backup of the database and the private patient files, and copies it off the server if set up.
# SAFE TO EDIT: KEEP_DAILY / KEEP_WEEKLY below. ASK FIRST for anything else.
#
# Run by hand:        bash deploy/backup.sh
# Run every night:    see docs/GO_LIVE.md (a systemd timer or cron line)
#
# Result: backups/daily/2026-10-17_0200/{db.sql.gz, files.tar.gz, MANIFEST.txt}
# Keeps the last 14 daily backups and the last 8 weekly ones (the Sunday backup is copied to backups/weekly).
# NOT included: the .env file (it holds secrets). Keep your own copy of it outside the server.
#
# Why: DPDP Act 2023 asks you to protect patient data and to be able to restore it after a loss.
# A backup on the SAME server is not enough (disk dies = both gone), so copy it to another place too.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

KEEP_DAILY="${KEEP_DAILY:-14}"
KEEP_WEEKLY="${KEEP_WEEKLY:-8}"
need_env
umask 077
mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"
LOG="$BACKUP_DIR/backup.log"
exec > >(tee -a "$LOG") 2>&1

STAMP="$(date '+%Y-%m-%d_%H%M')"
TARGET="$BACKUP_DIR/daily/$STAMP"
TMP="$BACKUP_DIR/daily/.incomplete-$STAMP"
trap 'rc=$?; if [ $rc -ne 0 ]; then say "BACKUP FAILED (code $rc). Partial files removed."; rm -rf "$TMP"; fi' EXIT

say "Backup started -> $TARGET"
dc ps --status running db | grep -q db || fail "The database container is not running."
mkdir -p "$TMP"

# 1) Database (pg_dump inside the db container, compressed)
say "Dumping the database..."
dc exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-privileges | gzip -9 > "$TMP/db.sql.gz"
gzip -t "$TMP/db.sql.gz" || fail "The database dump is damaged."
zcat "$TMP/db.sql.gz" | tail -n 5 | grep -q "PostgreSQL database dump complete" || fail "The database dump looks incomplete."
[ "$(stat -c %s "$TMP/db.sql.gz")" -gt 2000 ] || fail "The database dump is suspiciously small."

# 2) Private patient files (documents, photos, signatures) and public media (logos)
say "Packing the patient files..."
dc exec -T backend tar czf - -C /app private_media media > "$TMP/files.tar.gz"
gzip -t "$TMP/files.tar.gz" || fail "The files archive is damaged."

{
  echo "Backup made: $(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "App version: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "Database: $DB_NAME"
  ( cd "$TMP" && sha256sum db.sql.gz files.tar.gz )
} > "$TMP/MANIFEST.txt"

mv "$TMP" "$TARGET"
say "Saved: $(du -sh "$TARGET" | cut -f1) in $TARGET"

# Sunday backup also goes to the weekly folder
if [ "$(date +%u)" = "7" ]; then
  cp -r "$TARGET" "$BACKUP_DIR/weekly/$STAMP"
  say "Weekly copy made."
fi

# 3) Remove old ones
prune() { # folder, how many to keep
  { ls -1d "$1"/20* 2>/dev/null || true; } | sort -r | tail -n +$(($2 + 1)) | while read -r old; do
    say "Removing old backup $old"; rm -rf "$old"
  done
}
prune "$BACKUP_DIR/daily" "$KEEP_DAILY"
prune "$BACKUP_DIR/weekly" "$KEEP_WEEKLY"

# 4) Copy off the server (optional; set in .env, see docs/GO_LIVE.md)
RCLONE_REMOTE="$(env_value OFFSITE_RCLONE_REMOTE)"   # e.g. mydrive:ayurveda-backups
SCP_TARGET="$(env_value OFFSITE_SCP_TARGET)"         # e.g. backup@other-machine:/backups/ayurveda
if [ -n "$RCLONE_REMOTE" ]; then
  say "Copying off the server with rclone to $RCLONE_REMOTE ..."
  rclone copy "$BACKUP_DIR" "$RCLONE_REMOTE" --exclude "backup.log" --exclude ".incomplete-*/**" \
    || fail "The off-server copy (rclone) FAILED. The backup is still on this server."
  say "Off-server copy done."
elif [ -n "$SCP_TARGET" ]; then
  say "Copying off the server with scp to $SCP_TARGET ..."
  scp -r -q "$TARGET" "$SCP_TARGET/" || fail "The off-server copy (scp) FAILED. The backup is still on this server."
  say "Off-server copy done."
else
  say "NOTE: no off-server copy is set up (OFFSITE_RCLONE_REMOTE / OFFSITE_SCP_TARGET in .env). Please set one up."
fi

trap - EXIT
say "Backup finished OK."
