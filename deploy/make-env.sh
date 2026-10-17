#!/usr/bin/env bash
# Creates the ".env" settings file for the live server, with fresh random secrets.
# SAFE TO EDIT: the messages. ASK FIRST before changing how secrets are made.
#
# Usage (on the server, inside the project folder):
#   bash deploy/make-env.sh                          (asks for the address)
#   bash deploy/make-env.sh app.vednathayurved.com you@example.com
#
# The secrets are written to .env (readable only by you) and are NEVER printed on the screen.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -e .env ]; then
  echo "A .env file already exists. I will not overwrite it (it holds the secrets of a running clinic)."
  echo "If you really want a fresh one, rename the old one first:  mv .env .env.old"
  exit 1
fi
[ -f .env.production.example ] || { echo "Cannot find .env.production.example. Run this from the project folder."; exit 1; }

DOMAIN="${1:-}"
EMAIL="${2:-}"
if [ -z "$DOMAIN" ]; then
  read -r -p "Web address of the app (for example app.vednathayurved.com, without https://): " DOMAIN
fi
DOMAIN="$(echo "$DOMAIN" | tr 'A-Z' 'a-z' | sed -e 's#^https\?://##' -e 's#/.*$##' -e 's/[[:space:]]//g')"
if ! echo "$DOMAIN" | grep -Eq '^([a-z0-9-]+\.)+[a-z]{2,}$|^localhost$'; then
  echo "\"$DOMAIN\" does not look like a web address. Example: app.vednathayurved.com"
  exit 1
fi
if [ -z "$EMAIL" ] && [ -t 0 ]; then
  read -r -p "Your email (for certificate warnings; press Enter to skip): " EMAIL || true
fi

# random text of a given length using only letters and numbers (lowercase=1 for lowercase only)
rand() {
  local len="$1" set='A-Za-z0-9'
  [ "${2:-0}" = "1" ] && set='a-z0-9'
  LC_ALL=C tr -dc "$set" < /dev/urandom | head -c "$len" || true   # head closes the pipe early: that is normal
}
SECRET_KEY="$(rand 64)"
DB_PASSWORD="$(rand 32)"
ADMIN_PATH="manage-$(rand 12 1)"
# Fernet key: 32 random bytes, URL-safe base64
FIELD_KEY="$(head -c 32 /dev/urandom | base64 | tr '+/' '-_' | tr -d '\n')"

umask 077   # the new file is readable only by you
TMP="$(mktemp .env.XXXXXX)"
sed \
  -e "s|^APP_DOMAIN=.*|APP_DOMAIN=$DOMAIN|" \
  -e "s|^ACME_EMAIL=.*|ACME_EMAIL=$EMAIL|" \
  -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$SECRET_KEY|" \
  -e "s|^DJANGO_ALLOWED_HOSTS=.*|DJANGO_ALLOWED_HOSTS=$DOMAIN|" \
  -e "s|^DJANGO_CSRF_TRUSTED_ORIGINS=.*|DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMAIN|" \
  -e "s|^PUBLIC_APP_URL=.*|PUBLIC_APP_URL=https://$DOMAIN|" \
  -e "s|^ADMIN_URL=.*|ADMIN_URL=$ADMIN_PATH|" \
  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$DB_PASSWORD|" \
  -e "s|^FIELD_ENCRYPTION_KEY=.*|FIELD_ENCRYPTION_KEY=$FIELD_KEY|" \
  .env.production.example > "$TMP"
chmod 600 "$TMP"
mv "$TMP" .env

if grep -Eq '^[A-Z_]+=CHANGE-ME' .env; then
  echo "Something was not filled in (CHANGE-ME is still in .env). Please tell your helper."
  exit 1
fi

echo
echo "Done. The file .env was created (only you can read it)."
echo "  Web address : https://$DOMAIN"
echo "  Admin page  : https://$DOMAIN/$ADMIN_PATH/   (secret address, write it down)"
echo
echo "VERY IMPORTANT: copy the .env file somewhere SAFE outside this server (a password manager or"
echo "an encrypted USB). Without FIELD_ENCRYPTION_KEY, old medical notes cannot be read again,"
echo "and backups do not contain it. To see the file:  nano .env   (do not paste it into chat or email)"
