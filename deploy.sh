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
# `pg_isready` herhangi bir kimlik doğrulaması yapmaz (sadece sunucunun
# bağlantı kabul edip etmediğine bakar), bu yüzden "simseklog" rolü hiç
# var olmasa bile bu kontrol başarılı görünebilir. Asıl hata, migration'ları
# uygulayan gerçek `psql` bağlantısında ortaya çıkar: "FATAL: role
# \"simseklog\" does not exist". Bunun en yaygın nedeni, "simseklog_pgdata"
# volume'unun DAHA ÖNCE (POSTGRES_USER ayarlanmadan/varsayılan "postgres"
# ile) initialize edilmiş olması; postgres imajı POSTGRES_USER'ı SADECE veri
# dizini ilk kez oluşturulurken uygular, sonradan .env.production'ı
# değiştirmek mevcut rolleri güncellemez.
#
# Bu yüzden migration'ları uygulamadan önce, container içinde gerçekten
# çalışan bir "admin" rolü (POSTGRES_USER veya postgres imajının yerleşik
# varsayılanı "postgres") otomatik tespit edilir; eksikse $POSTGRES_USER
# rolü/$POSTGRES_DB veritabanı bu admin rol ile oluşturulur.
db_up=false
for attempt in $(seq 1 30); do
  if $COMPOSE exec -T db pg_isready -d postgres >/dev/null 2>&1; then
    db_up=true
    break
  fi
  echo "Postgres henüz ayakta değil, bekleniyor (${attempt}/30)..."
  sleep 2
done
if [ "$db_up" != "true" ]; then
  echo "HATA: Postgres container'ı (db) 60 saniye içinde bağlantı kabul etmedi." >&2
  exit 1
fi

# <user> ile "postgres" (bakım/varsayılan) veritabanına bağlanıp basit bir
# sorgu çalıştırarak o rolün gerçekten var olup olmadığını test eder.
pg_role_works() {
  $COMPOSE exec -T db psql -U "$1" -d postgres -tAc "SELECT 1" >/dev/null 2>&1
}

ADMIN_PG_USER=""
if pg_role_works "$POSTGRES_USER"; then
  ADMIN_PG_USER="$POSTGRES_USER"
elif pg_role_works postgres; then
  ADMIN_PG_USER="postgres"
  echo "UYARI: '$POSTGRES_USER' rolü bulunamadı; 'postgres' imajının" >&2
  echo "yerleşik varsayılan superuser'ı ('postgres') ile devam ediliyor ve" >&2
  echo "'$POSTGRES_USER' rolü/'$POSTGRES_DB' veritabanı otomatik oluşturulacak." >&2
else
  echo "----------------------------------------------------------------" >&2
  echo "HATA: Ne '$POSTGRES_USER' ne de 'postgres' rolüyle veritabanına" >&2
  echo "bağlanılamadı (ör. 'FATAL: role \"$POSTGRES_USER\" does not exist')." >&2
  echo "'simseklog_pgdata' volume'u beklenmedik bir kimlik bilgisiyle" >&2
  echo "initialize edilmiş olabilir. Veri henüz önemli değilse volume'u" >&2
  echo "sıfırlayıp yeniden deneyin (TÜM VERİYİ SİLER):" >&2
  echo "  $COMPOSE down db" >&2
  echo "  docker volume rm simseklog_pgdata" >&2
  echo "  bash deploy.sh" >&2
  echo "----------------------------------------------------------------" >&2
  exit 1
fi

if [ "$ADMIN_PG_USER" != "$POSTGRES_USER" ]; then
  # $POSTGRES_USER rolü ve $POSTGRES_DB veritabanı yoksa, tespit edilen
  # admin rol (postgres) ile idempotent şekilde oluşturur.
  $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$ADMIN_PG_USER" -d postgres -c "
    DO \$do\$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$POSTGRES_USER') THEN
        CREATE ROLE \"$POSTGRES_USER\" LOGIN PASSWORD '$POSTGRES_PASSWORD' SUPERUSER;
      END IF;
    END
    \$do\$;
  "
  if ! $COMPOSE exec -T db psql -U "$ADMIN_PG_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB'" | grep -q 1; then
    $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$ADMIN_PG_USER" -d postgres \
      -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\";"
  fi
fi

# database/migrations/ altındaki tüm .sql dosyalarını dosya adına göre
# (001, 002, ...) sırayla uygular; yeni migration eklendiğinde bu betiğin
# güncellenmesi gerekmez. Artık $POSTGRES_USER rolünün var olduğu garanti
# edildiğinden migration'lar bu rolle çalıştırılır.
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
