# Veri Katmanı

ŞimşekLog kalıcı veri katmanı PostgreSQL ve SQLAlchemy 2.x üzerine kuruludur.

## Klasör yapısı

- `base.py`: ortak declarative ORM tabanı
- `models.py`: tenant, İK, filo, sefer, kantar, bakım, yakıt/telemetri, finans ve audit modelleri
- `session.py`: `DATABASE_URL`, engine ve session üretimi
- `migrations/001_initial_schema.sql`: PostgreSQL için ilk migration

## Kurulum

```powershell
$env:DATABASE_URL = "postgresql+psycopg://simseklog:simseklog@localhost:5432/simseklog"
psql $env:DATABASE_URL -f database\migrations\001_initial_schema.sql
```

Uygulama tarafında:

```python
from database import get_session
from database.models import Vehicle

with next(get_session()) as session:
    vehicles = session.query(Vehicle).all()
```

Her tenant'a ait tabloda `tenant_id` bulunur. Uygulama servisleri sorguları tenant filtresiyle çalıştırmalı; ödeme, bakım, kantar ve telemetri kayıtları ilgili sefer/araç foreign key'leri üzerinden izlenebilir.
