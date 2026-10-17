#!/usr/bin/env bash
# Shows if everything is fine: containers, disk, memory, last backup, HTTPS certificate. Changes nothing.
# SAFE TO EDIT: the warning limits (WARN_*) below.
set -uo pipefail
source "$(dirname "$0")/lib.sh"

WARN_DISK_PERCENT=80
WARN_BACKUP_HOURS=36
WARN_CERT_DAYS=14
problems=0
warn() { echo "  !! $*"; problems=$((problems + 1)); }

echo "=== Containers ==="
dc ps || problems=$((problems + 1))
for svc in db backend caddy; do
  state="$(docker inspect -f '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' "$(dc ps -q $svc 2>/dev/null)" 2>/dev/null || echo missing)"
  case "$state" in running/healthy) ;; *) warn "$svc is not healthy ($state)";; esac
done

echo; echo "=== Disk ==="
df -h / | tail -n +1
used="$(df --output=pcent / | tail -n1 | tr -dc 0-9)"
[ "${used:-0}" -ge "$WARN_DISK_PERCENT" ] && warn "Disk is ${used}% full. Old backups or logs may need cleaning."
docker system df 2>/dev/null | head -n 5

echo; echo "=== Memory ==="
free -h

echo; echo "=== Last backup ==="
newest="$({ ls -1d "$BACKUP_DIR"/daily/20* 2>/dev/null || true; } | sort | tail -n1)"
if [ -z "$newest" ]; then
  warn "No backup found in $BACKUP_DIR/daily. Run: bash deploy/backup.sh"
else
  age_h=$(( ( $(date +%s) - $(stat -c %Y "$newest") ) / 3600 ))
  echo "  $newest  (${age_h} hours ago)"
  [ "$age_h" -ge "$WARN_BACKUP_HOURS" ] && warn "The last backup is older than $WARN_BACKUP_HOURS hours. Is the nightly timer running?"
fi
echo "  Backups kept: $(ls -1d "$BACKUP_DIR"/daily/20* 2>/dev/null | wc -l) daily, $(ls -1d "$BACKUP_DIR"/weekly/20* 2>/dev/null | wc -l) weekly"
[ -z "$(env_value OFFSITE_RCLONE_REMOTE)$(env_value OFFSITE_SCP_TARGET)" ] && warn "No off-server backup copy is set up (OFFSITE_* in .env)."

echo; echo "=== HTTPS certificate and website ==="
domain="$(env_value APP_DOMAIN)"
if [ -n "$domain" ] && command -v openssl >/dev/null 2>&1; then
  end="$(echo | openssl s_client -connect 127.0.0.1:"${HTTPS_PORT:-443}" -servername "$domain" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)"
  if [ -z "$end" ]; then
    warn "Could not read the certificate (Caddy not running, or the certificate is not issued yet)."
  else
    days=$(( ( $(date -d "$end" +%s) - $(date +%s) ) / 86400 ))
    echo "  $domain certificate ends: $end ($days days left; it renews by itself)"
    [ "$days" -le "$WARN_CERT_DAYS" ] && warn "Certificate ends in $days days and has not renewed. Check: docker compose -f $COMPOSE_FILE_PROD logs caddy --tail 50"
  fi
  code="$(curl -sk -o /dev/null -w '%{http_code}' --resolve "$domain:${HTTPS_PORT:-443}:127.0.0.1" "https://$domain:${HTTPS_PORT:-443}/api/v1/health/" || true)"
  echo "  /api/v1/health/ answers: $code"
  [ "$code" != "200" ] && warn "The health page did not answer 200."
fi

echo
if [ "$problems" -eq 0 ]; then echo "ALL GOOD."; else echo "$problems thing(s) need attention (marked !! above)."; fi
exit 0
