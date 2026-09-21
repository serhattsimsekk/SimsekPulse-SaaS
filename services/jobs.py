from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, text

from database.models import BackupRun, ShiftLog
from database.session import SessionLocal, engine


def database_health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def run_database_backup() -> dict[str, str | int]:
    destination_dir = Path(os.getenv("BACKUP_DIR", "/var/backups/simseklog"))
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"simseklog-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.dump"
    command = os.getenv("PG_DUMP_BIN", "pg_dump")
    url = os.getenv("DATABASE_URL", "")
    record = BackupRun(backup_type="postgresql", destination=str(destination), status="started")
    with SessionLocal() as session:
        session.add(record)
        session.commit()
        try:
            subprocess.run([command, "--format=custom", "--file", str(destination), url], check=True, timeout=600, capture_output=True, text=True)
            record.status = "completed"
            record.size_bytes = destination.stat().st_size
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            record.status = "failed"
            record.error_message = str(exc)
        session.commit()
        return {"id": record.id, "status": record.status, "destination": str(destination), "size_bytes": record.size_bytes or 0}


def generate_shift_reports() -> int:
    now = datetime.now(timezone.utc)
    anchor = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now < anchor:
        anchor = anchor.replace(day=anchor.day - 1)
    starts_at = anchor - timedelta(hours=8)
    with SessionLocal() as session:
        created = 0
        tenant_rows = session.execute(text("SELECT id::text FROM tenants")).scalars().all()
        for tenant_id in tenant_rows:
            stats = session.execute(text(
                "SELECT count(*)::int AS trips, coalesce(sum(realized_ton), 0) AS ton "
                "FROM trips WHERE tenant_id::text = :tenant AND created_at >= :starts_at AND created_at < :ends_at"
            ), {"tenant": tenant_id, "starts_at": starts_at, "ends_at": anchor}).mappings().one()
            receipts = session.execute(text(
                "SELECT count(*)::int FROM weighbridge_receipts "
                "WHERE tenant_id::text = :tenant AND created_at >= :starts_at AND created_at < :ends_at"
            ), {"tenant": tenant_id, "starts_at": starts_at, "ends_at": anchor}).scalar_one()
            session.add(ShiftLog(tenant_id=tenant_id, shift_code="scheduled-8h", starts_at=starts_at,
                                 ends_at=anchor, total_ton=stats["ton"], trip_count=stats["trips"], receipt_count=receipts))
            created += 1
        session.commit()
        return created


def run_asset_document_alerts() -> int:
    with SessionLocal() as session:
        rows = session.execute(text(
            "SELECT d.tenant_id::text, coalesce(v.plate, t.plate) AS plate, d.document_type, "
            "d.expires_on, (d.expires_on - CURRENT_DATE)::int AS days_remaining "
            "FROM asset_documents d LEFT JOIN vehicles v ON v.id = d.vehicle_id "
            "LEFT JOIN trailers t ON t.id = d.trailer_id "
            "WHERE d.expires_on <= CURRENT_DATE + 10"
        )).mappings().all()
        for row in rows:
            message = f"{row['plate']} - {row['document_type']} belgesi {row['days_remaining']} gün içinde sona eriyor."
            session.execute(text(
                "INSERT INTO notification_logs (id, tenant_id, channel, recipient, title, message, status) "
                "VALUES (gen_random_uuid(), CAST(:tenant AS uuid), 'system', 'fleet-manager', 'Kritik Evrak/Muayene Uyarısı', :message, 'queued')"
            ), {"tenant": row["tenant_id"], "message": message})
        session.commit()
        return len(rows)
