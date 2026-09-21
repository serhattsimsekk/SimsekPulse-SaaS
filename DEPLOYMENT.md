# Production deployment

Bu kurulum Ubuntu 22.04/24.04 sunucuda Docker Engine, Docker Compose plugin,
Nginx ve Certbot kullanır.

## 1. Sunucuya bağlanın

```bash
ssh root@SUNUCU_IP
apt update && apt install -y git
git clone https://github.com/ORGANIZATION/REPOSITORY.git /var/www/simseklog
cd /var/www/simseklog
```

Özel repository kullanıyorsanız sunucudaki SSH deploy key ile clone edin.

## 2. Production değişkenlerini oluşturun

```bash
cp .env.production.example .env.production
nano .env.production
chmod 600 .env.production
```

`SECRET_KEY`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `MASTER_ADMIN_PASSWORD`,
`NEXT_PUBLIC_API_URL`, `CORS_ORIGINS` ve `CERTBOT_EMAIL` değerlerini gerçek
değerlerle değiştirin. Veritabanı parolasında `@`, `:`, `/` gibi URL karakterleri
varsa `DATABASE_URL` içinde URL-encode edin.

## 3. Docker ve Docker Compose'u kurun

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
docker compose version
```

## 4. Tek tıkla kurulum

```bash
chmod +x deploy.sh
DOMAIN=www.example.com CERTBOT_EMAIL=ops@example.com ./deploy.sh
```

Betik sırasıyla PostgreSQL ve Redis'i başlatır, migration SQL dosyalarını doğrudan
PostgreSQL container'ına aktararak uygular,
Master Tenant/Admin seed işlemini çalıştırır, backend/frontend image'larını
oluşturur, Nginx'i kurar ve Let's Encrypt sertifikasını ister.

DNS kayıtları sunucu IP'sine yönlenmiyorsa:

```bash
SKIP_CERTBOT=true ./deploy.sh
```

DNS düzeltildikten sonra yalnızca SSL adımını çalıştırın:

```bash
certbot --nginx --redirect -d www.example.com -d example.com
```

## 5. Doğrulama

```bash
docker compose --env-file .env.production ps
curl -fsS https://www.example.com/health
curl -I https://www.example.com/docs
docker compose --env-file .env.production logs --tail=100 api
```

Beklenen servisler: `simseklog-db`, `simseklog-redis`, `simseklog-api` ve
`simseklog-frontend`. PostgreSQL verisi `simseklog_pgdata`, Redis verisi
`simseklog_redisdata` volume'unda saklanır.

## Güncelleme ve yedek

```bash
cd /var/www/simseklog
git pull --ff-only
./deploy.sh
docker exec simseklog-db pg_dump -U simseklog simseklog > /var/backups/simseklog.sql
```

`.env.production` dosyasını, veritabanı dump'larını ve Docker volume'larını
public repository'ye göndermeyin.
