# ŞimşekLog API

ŞimşekLog artık Streamlit içermez. Uygulama FastAPI + PostgreSQL + SQLAlchemy olarak çalışır.

## Yerel çalıştırma

```powershell
$env:DATABASE_URL = "postgresql+psycopg://simseklog:simseklog@localhost:5432/simseklog"
$env:PORT = "8000"
uvicorn app:app --host 0.0.0.0 --port $env:PORT
```

- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Docker / DigitalOcean

App Platform için container portu `8000` ve `DATABASE_URL` secret/environment variable olarak tanımlanır. App Platform'ın verdiği `PORT` değeri otomatik kullanılır.

Droplet veya yerel PostgreSQL için:

```powershell
$env:POSTGRES_PASSWORD = "strong-password"
docker compose up -d --build
```

Üretimde `POSTGRES_PASSWORD`, `DATABASE_URL` ve `CORS_ORIGINS` değerlerini `.env` veya DigitalOcean secret olarak sağlayın. Migration dosyası PostgreSQL ilk kurulumunda otomatik çalışır.

Detaylı Ubuntu production kurulumu, Redis servisi, kalıcı volume'lar, Nginx ve
Certbot adımları için [DEPLOYMENT.md](./DEPLOYMENT.md) dosyasını kullanın.
Production değişken şablonu [.env.production.example](./.env.production.example)
dosyasındadır. Compose stack'i `api`, `frontend`, `db` ve `redis` servislerini
çalıştırır.

## Faz 3 uçları

- `POST /api/v1/finance/customer-rates`: müşteri bazlı özel ton fiyatı
- `GET /api/v1/finance/customer-rates`: fiyat kartı sorgulama
- `POST /api/v1/finance/commissions`: taşeron komisyon/hakediş oluşturma
- `POST /api/v1/finance/commissions/auto`: sefer tonajı ve sözleşme fiyatından otomatik hakediş
- `GET /api/v1/finance/subcontractors/{id}/settlement`: taşeron cari özeti
- `GET /api/v1/finance/vehicles/{id}/fuel-analysis`: araç yakıt/maliyet analizi
- `GET /api/v1/finance/vehicles/{id}/profitability`: araç net kârlılık skorkardı

## Faz 4 uçları

- `POST /api/v1/receipts/ocr`: multipart fiş yükleme ve OCR metin analizi
- `POST/GET /api/v1/drivers/{id}/documents`: sürücü dokümanı ve bitiş tarihi
- `GET /api/v1/drivers/{id}/document-alerts`: kalan gün, uyarı ve görev kilidi
- `POST/GET /api/v1/drivers/{id}/discipline`: disiplin ihlali ve puan geçmişi
- `PATCH /api/v1/drivers/{id}/blacklist`: kara liste aç/kapat
- `POST /api/v1/drivers/{id}/breaks`: mola kaydı
- `POST /api/v1/drivers/{id}/tachograph-violations`: takograf ihlali
- `GET /api/v1/drivers/{id}/fatigue-index`: yorulma endeksi

## Faz 5 Web frontend

Next.js frontend [frontend/](./frontend/) altında bulunur:

- `frontend/app/page.tsx`: executive dashboard, sürücü portalı ve bakım ekranı
- `frontend/components/fleet-map.tsx`: SSR-safe Leaflet/OpenStreetMap haritası
- `frontend/lib/api.ts`: `NEXT_PUBLIC_API_URL` tabanlı API istemcisi
- `frontend/Dockerfile`: production standalone Next.js container

Web uygulaması `FRONTEND_PORT` ile (varsayılan `3000`) çalışır. API için
`NEXT_PUBLIC_API_URL` değerini frontend container build argümanı olarak verin.

## Faz 7 - 75 modül Komuta Merkezi

`/api/v1/command-center` router'ı operasyon, canlı GPS/telemetri, ısı haritası,
ETA/tonaj, demoraj, vardiya, yorulma, akaryakıt, bakım, kantar, kârlılık,
ESG, kapasite projeksiyonu ve AI yardımcı servislerini tek bir tenant kapsamı
ile sunar. Tüm uçlar OAuth2 Bearer JWT ve rol denetimi ile Swagger'da test
edilebilir:

- `/api/v1/command-center/master-dashboard`
- `/api/v1/command-center/operation-matrix`
- `/api/v1/command-center/heatmap`
- `/api/v1/command-center/telemetry/live`
- `/api/v1/command-center/demurrage/early-warning`
- `/api/v1/command-center/shift-analysis`
- `/api/v1/command-center/driver-performance`
- `/api/v1/command-center/fuel-forecast`
- `/api/v1/command-center/maintenance/predictive`
- `/api/v1/command-center/profitability-map`
- `/api/v1/command-center/esg/carbon`
- `/api/v1/command-center/assistant/query`

Typed istek sözleşmeleri [api/schemas.py](./api/schemas.py) içinde tutulur.

## Enterprise Multi-Tenant ve Web Excel

- Her istekte JWT `tenant_id` veya `X-Tenant-ID` middleware ile `tenant_context` içine alınır.
- SQLAlchemy sorguları tenant taşıyan tüm modellerde otomatik `WHERE tenant_id = current_tenant` kriteri alır.
- PostgreSQL migration'ı tenant kolonlu tablolarda RLS policy oluşturur ve `app.tenant_id` transaction değişkenini kullanır.
- Kurumsal müşteriler için `TENANT_DATABASE_URLS` JSON map'i ile tenant başına ayrı PostgreSQL bağlantısı seçilebilir.
- `POST/GET /api/v1/spreadsheets/workbooks`, `POST /api/v1/spreadsheets/import`,
  `GET /api/v1/spreadsheets/workbooks/{id}/export` ve WebSocket
  `/api/v1/spreadsheets/workbooks/{id}/sync` Excel senkronizasyon yüzeyidir.
- Next.js masaüstü Excel ekranı `/excel` adresindedir; `.xlsx` içe/dışa aktarım,
  rol tabanlı hücre düzenleme ve salt-okunur görünüm sunar.
- `GET /api/v1/tenants/master-admin` yalnızca `super_admin` rolüyle tenant
  durumu, aktif kullanıcı ve audit kullanımını döndürür.
## Departman Bazlı Sidebar, OCR ve Vardiya Raporları

Kapalı SaaS girişinden sonra JWT içindeki `role` ve `department` alanları sol menüdeki 10 ana kategori için görünürlük filtresi olarak kullanılır. Backend middleware'i de finans, bakım, OCR ve vardiya rotalarında aynı departman sınırını HTTP `403` ile uygular.

- `POST /api/v1/ocr/weighbridge`: Mobil kantar fişi yükleme, OCR plaka/tonaj/fiş numarası çıkarımı ve aktif vardiya aracıyla eşleştirme.
- `GET /api/v1/shifts/reports?hours=8|24`: 8 saatlik vardiya veya 08:00 bazlı 24 saatlik filo özeti.
- `GET /api/v1/shifts/reports/{hours}/pdf`: Vardiya özetinin PDF çıktısı.

Vardiya raporları UTC `00:00`, `08:00` ve `16:00` saatlerinde background scheduler tarafından `shift_logs` tablosuna da yazılır. `shift_logs` ve `weighbridge_receipts` tenant RLS politikalarıyla korunur.

## Saha operasyonları ve maliyet kontrolü

Lastik olayları, yol yardım müdahaleleri, yakıt anomalileri, sürücü eco-driving
puanı, müşteri canlı takip bağlantıları ve lastik rotasyon/ömür kayıtları tenant
kapsamında tutulur:

- `POST /api/v1/field/tyre-incidents`
- `POST /api/v1/field/roadside-assistance`
- `GET /api/v1/field/tyre-analytics`
- `GET /api/v1/field/fuel-anomalies`
- `GET /api/v1/field/drivers/{id}/eco-score`
- `POST /api/v1/trips/{id}/tracking-link`
- `GET /api/v1/tracking/public/{token}`
- `GET /api/v1/field/vehicles/{id}/tires`
- `POST /api/v1/field/tires/{id}/rotation`

Bakım ekranı bu analizleri canlı alarm kartları olarak gösterir. Müşteri takip
token'ı hash'lenerek saklanır ve 24 saat sonra geçersiz olur.
## Arvento kimlik dogrulamasi

Arvento entegrasyonu tenant bazli ayarlardan API URL, kullanici adi ve sifre
ile calisir. PIN ve API token alanlari opsiyoneldir; yalnizca doldurulduklarinda
isteklere eklenir.

- `GET /api/v1/arvento/settings`
- `PUT /api/v1/arvento/settings`
- `GET /api/v1/arvento/live`

Arvento canli konum servisi portal adresini kullanmaz. Backend, sabit
`https://ws.arvento.com/v1/report.asmx` SOAP adresine `GetVehicleStatusByNodeV3`
cagrisi yapar. Resmi WSDL'de V3 operasyonu bu isimle yayinlanmaktadir.
Donen alanlar plaka, enlem, boylam, hiz, kilometre, surucu ve kontak alanlarini
icerir; kontak alani provider paketinde yoksa `null` doner.

SOAP sonucu bos oldugunda `arvento_service.py` cookie tabanli portal oturumunu
kontrol eder ve veri adapteri bulunamazsa Fleet Simulator moduna gecer.
Simulator, ozmal araclar icin Istanbul, Ankara, Izmir ve Marmara merkezli
hareketli koordinat, hiz, kilometre ve kontak verisi uretir. Excel grup
senkronizasyonu bu modda guncelleme logu ile yanitlanir. Portal oturum kontrolu
`ENABLE_ARVENTO_PORTAL_SCRAPER=false` ile kapatilabilir.
