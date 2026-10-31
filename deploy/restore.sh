#!/usr/bin/env bash
# Puts a backup back: the database and the private patient files. Works on a brand new server too.
# ASK FIRST before editing.
#
#   bash deploy/restore.sh backups/daily/2026-10-17_0200 --test   -> safe practice run: loads the backup into a
#                                                                     temporary database, shows counts, deletes it.
#                                                                     Nothing live is touched.
#   bash deploy/restore.sh backups/daily/2026-10-17_0200           -> REAL restore. Replaces the current data!
#   add --yes to skip the "type RESTORE" question.
#
# On a NEW server first: install (server-setup.sh), clone the code, copy your OLD .env file into the project
# folder (it must contain the same FIELD_ENCRYPTION_KEY), copy the backup folder to backups/, run:
#   docker compose -f docker-compose.prod.yml build
# then run this script.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

SRC="${1:-}"; shift || true
TEST=0; YES=0
for arg in "$@"; do
  case "$arg" in --test) TEST=1 ;; --yes) YES=1 ;; *) fail "Unknown option: $arg" ;; esac
done
[ -n "$SRC" ] || fail "Tell me which backup folder to use, for example: bash deploy/restore.sh backups/daily/2026-10-17_0200 --test"
[ -f "$SRC/db.sql.gz" ] || fail "Cannot find $SRC/db.sql.gz"
need_env

say "Checking the backup files..."
gzip -t "$SRC/db.sql.gz" || fail "db.sql.gz is damaged."
if [ -f "$SRC/files.tar.gz" ]; then gzip -t "$SRC/files.tar.gz" || fail "files.tar.gz is damaged."; fi
if [ -f "$SRC/MANIFEST.txt" ]; then
  ( cd "$SRC" && grep -E "db.sql.gz|files.tar.gz" MANIFEST.txt | sha256sum -c - ) || fail "Checksums do not match: the backup was changed or damaged."
fi

say "Starting the database..."
dc up -d db >/dev/null
for i in $(seq 1 30); do dc exec -T db pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1 && break; sleep 2; done
psql_admin() { dc exec -T db psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 "$@"; }

if [ "$TEST" = "1" ]; then
  TMPDB="restore_test_$(date +%s)"
  say "PRACTICE RUN: loading into temporary database $TMPDB (your live data is not touched)."
  psql_admin -q -c "CREATE DATABASE $TMPDB OWNER $DB_USER;"
  trap 'psql_admin -q -c "DROP DATABASE IF EXISTS $TMPDB WITH (FORCE);" >/dev/null 2>&1 || true' EXIT
  zcat "$SRC/db.sql.gz" | dc exec -T db psql -q -U "$DB_USER" -d "$TMPDB" -v ON_ERROR_STOP=1 -o /dev/null \
    || fail "Loading the backup FAILED."
  say "Loaded. What the backup contains:"
  dc exec -T db psql -U "$DB_USER" -d "$TMPDB" -At -c \
    "SELECT 'patients: '||count(*) FROM patients_patient UNION ALL SELECT 'invoices: '||count(*) FROM billing_invoice UNION ALL SELECT 'users: '||count(*) FROM accounts_user UNION ALL SELECT 'tables: '||count(*) FROM information_schema.tables WHERE table_schema='public';" \
    || say "(could not count some tables)"
  [ -f "$SRC/files.tar.gz" ] && say "Files archive: $(tar tzf "$SRC/files.tar.gz" | wc -l) entries."
  say "PRACTICE RUN OK. This backup can be restored."
  exit 0
fi

echo
echo "!!! This REPLACES the current database and patient files with the backup in: $SRC"
if [ "$YES" != "1" ]; then
  read -r -p "Type RESTORE (capital letters) to continue: " answer
  [ "$answer" = "RESTORE" ] || fail "Cancelled. Nothing was changed."
fi

say "Stopping the app (the database stays up)..."
dc stop caddy backend >/dev/null 2>&1 || true

say "Replacing the database..."
psql_admin -q -c "DROP DATABASE IF EXISTS $DB_NAME WITH (FORCE);"
psql_admin -q -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
zcat "$SRC/db.sql.gz" | dc exec -T db psql -q -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -o /dev/null \
  || fail "Loading the database FAILED. The app is stopped. Ask your helper; the backup file is untouched."

if [ -f "$SRC/files.tar.gz" ]; then
  say "Restoring patient files..."
  dc run --rm --no-deps -T backend sh -c 'rm -rf /app/private_media/* /app/media/* && tar xzf - -C /app' < "$SRC/files.tar.gz" \
    || fail "Restoring the files FAILED."
fi

say "Starting everything..."
dc up -d
say "RESTORE DONE. Open the app, log in and check a few patients. (Starting takes about a minute.)"
