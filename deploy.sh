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

# .env.production sadece docker-compose'a --env-file olarak veriliyordu; bu
# betiğin kendisi POSTGRES_USER/POSTGRES_DB değerlerini bilmediği için
# "psql -U simseklog" gibi sabit (hardcoded) değerler kullanıyordu. Sunucuda
# .env.production farklı bir POSTGRES_USER/POSTGRES_DB ile ayarlandığında
# (veya "simseklog" rolü henüz oluşmadığında) bu satırlar "FATAL: role
# ... does not exist" hatasıyla başarısız oluyordu. Aşağıda dosyayı bu kabuk
# (shell) için de export ediyoruz, böylece gerçek değerler kullanılır.
set -a
# shellcheck disable=SC1091
source .env.production
set +a
POSTGRES_USER="${POSTGRES_USER:?POSTGRES_USER must be set in .env.production}"
POSTGRES_DB="${POSTGRES_DB:?POSTGRES_DB must be set in .env.production}"

$COMPOSE up -d --build db redis
# db container'ı henüz sağlıklı (healthy) olmayabilir; docker-compose'un
# healthcheck'i bekleyene kadar kısa bir bekleme + tekrar deneme ekliyoruz.
db_ready=false
for attempt in $(seq 1 30); do
  if $COMPOSE exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    db_ready=true
    break
  fi
  echo "Postgres henüz hazır değil, bekleniyor (${attempt}/30)..."
  sleep 2
done

if [ "$db_ready" != "true" ]; then
  echo "----------------------------------------------------------------" >&2
  echo "HATA: Postgres, '$POSTGRES_USER' rolü / '$POSTGRES_DB' veritabanı ile" >&2
  echo "hazır hale gelmedi (ör. 'FATAL: role \"$POSTGRES_USER\" does not exist')." >&2
  echo "" >&2
  echo "Bu genellikle 'simseklog_pgdata' Docker volume'unun DAHA ÖNCEKİ bir" >&2
  echo "denemede farklı (veya boş) POSTGRES_USER/POSTGRES_PASSWORD ile ilk kez" >&2
  echo "initialize edilmiş olmasından kaynaklanır: postgres imajı bu değişkenleri" >&2
  echo "SADECE veri dizini ilk defa oluşturulurken uygular; .env.production'ı" >&2
  echo "sonradan değiştirmek mevcut volume'daki rolleri güncellemez." >&2
  echo "" >&2
  echo "Çözüm seçenekleri:" >&2
  echo "  1) Veritabanında henüz korunacak veri yoksa, volume'u sıfırlayıp" >&2
  echo "     yeniden initialize edin (TÜM VERİYİ SİLER):" >&2
  echo "       $COMPOSE down db" >&2
  echo "       docker volume rm simseklog_pgdata" >&2
  echo "       bash deploy.sh" >&2
  echo "  2) Mevcut veriyi korumak istiyorsanız, container içinde eksik rolü" >&2
  echo "     mevcut bir superuser ile elle oluşturun, örn.:" >&2
  echo "       $COMPOSE exec -T db psql -U postgres -c \\" >&2
  echo "         \"CREATE ROLE $POSTGRES_USER LOGIN PASSWORD '<POSTGRES_PASSWORD>' SUPERUSER;\"" >&2
  echo "       $COMPOSE exec -T db psql -U postgres -c \\" >&2
  echo "         \"CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;\"" >&2
  echo "----------------------------------------------------------------" >&2
  exit 1
fi
# database/migrations/ altındaki tüm .sql dosyalarını dosya adına göre
# (001, 002, ...) sırayla uygular; yeni migration eklendiğinde bu betiğin
# güncellenmesi gerekmez.
for migration in $(find database/migrations -maxdepth 1 -name '*.sql' | sort); do
  echo "Applying migration: ${migration}"
  $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$migration"
done
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
