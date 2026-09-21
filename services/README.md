# Çekirdek operasyon servisleri

`core_operations.py`, arayüzden bağımsız ve veritabanı modellerine taşınabilecek iş kurallarını içerir:

- `complete_plate`: Türkiye plaka biçimi ve il kodu doğrulaması
- `build_shift_handover`: KM, litre, depo yüzdesi ve fotoğraf referansını doğrulayan devir kaydı
- `calculate_tonnage_progress`: planlanan, taşınan ve kalan tonaj/progress hesabı
- `calculate_weighbridge_deviation`: kantar-irsaliye sapması ve tolerans alarmı
- `calculate_demurrage`: serbest süre sonrası saatlik demoraj tutarı

FastAPI router'ları bu iş kurallarını ve SQLAlchemy repository işlemlerini kullanır.
