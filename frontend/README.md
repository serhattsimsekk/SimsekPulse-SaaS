# ŞimşekLog Web

Next.js 14 + TypeScript + Tailwind CSS + Lucide + Leaflet frontend.

## Çalıştırma

```powershell
cd frontend
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm install
npm run dev
```

Üretim container'ı için `frontend/Dockerfile` kullanılır. Docker Compose ile API,
PostgreSQL ve web uygulaması birlikte başlatılabilir:

```powershell
$env:POSTGRES_PASSWORD = "strong-password"
docker compose up -d --build
```

## Ekranlar

- **Komuta Merkezi:** KPI kartları, gerçek Leaflet/OpenStreetMap araç haritası,
  telemetri marker'ları, tonaj/progress ve demoraj uyarıları.
- **Sürücü Portalı:** mobil kamera/dosya seçici ile OCR fiş gönderimi, vardiya
  teslimi ve mola kronometresi.
- **Bakım & Filo:** arıza kayıtları, düşük stok göstergeleri ve bakım kaydı formu.

API adresi `NEXT_PUBLIC_API_URL` ile değiştirilir. Telemetri yoksa harita demo
koordinatlarıyla boş kalmaz; API hata verdiğinde dashboard bakım ekranı demo
verisiyle çalışmaya devam eder.
