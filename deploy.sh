#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/var/www/simseklog}"
DOMAIN="${DOMAIN:-www.simseklog.com}"
COMPOSE="docker compose --env-file .env.production"
BARE_DOMAIN="${DOMAIN#www.}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-admin@${BARE_DOMAIN}}"

if [ "${EUID}" -ne 0 ]; then
  echo "Run this script as root." >&2
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl git nginx certbot python3-certbot-nginx
command -v docker >/dev/null || { echo "Docker is not installed."; exit 1; }
docker compose version >/dev/null || { echo "Docker Compose plugin is not installed."; exit 1; }

mkdir -p "$APP_DIR"
cd "$APP_DIR"
if [ ! -f .env.production ]; then
  echo ".env.production is missing. Copy .env.production.example and set secrets." >&2
  exit 1
fi

$COMPOSE up -d --build db redis
$COMPOSE exec -T db pg_isready -U simseklog -d simseklog
$COMPOSE run --rm api sh -c 'psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/001_initial_schema.sql && psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/002_arvento_credentials.sql'
$COMPOSE run --rm api python seed.py
$COMPOSE up -d --build api frontend

install -m 0644 nginx_simseklog.conf /etc/nginx/sites-available/simseklog
ln -sfn /etc/nginx/sites-available/simseklog /etc/nginx/sites-enabled/simseklog
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

if [ "${SKIP_CERTBOT:-false}" != "true" ]; then
  certbot --nginx --non-interactive --agree-tos --redirect \
    --email "$CERTBOT_EMAIL" \
    -d "$DOMAIN" -d "$BARE_DOMAIN" || echo "Certbot failed; check DNS and port 80."
fi

echo "Deployment completed: https://${DOMAIN}"
echo "Check status with: $COMPOSE ps"
