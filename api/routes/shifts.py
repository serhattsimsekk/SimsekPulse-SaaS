from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.security import current_principal
from database.models import ShiftLog, Trip, WeighbridgeReceipt
from services.compliance import parse_receipt_text

router = APIRouter(tags=["Şoför & Vardiya Portalı"])


def _shift_window(now: datetime, hours: int) -> tuple[str, datetime, datetime]:
    now = now.astimezone(timezone.utc)
    anchor = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now < anchor:
        anchor -= timedelta(days=1)
    end = anchor + timedelta(hours=hours)
    if hours == 8:
        slot = "1" if now.hour < 16 and now.hour >= 8 else "2" if now.hour < 24 and now.hour >= 16 else "3"
    else:
        slot = "24"
    return slot, end - timedelta(hours=hours), end


def _assert_access(principal: dict) -> None:
    if principal.get("role") not in {"super_admin", "admin", "head_driver", "driver"} and principal.get("department") not in {"operations", "driver"}:
        raise HTTPException(403, "Vardiya ve kantar fişi modülüne erişim yetkiniz yok.")


@router.post("/api/v1/ocr/weighbridge", status_code=201)
async def upload_weighbridge_receipt(
    file: UploadFile = File(...),
    driver_id: str | None = Form(None),
    raw_text: str | None = Form(None),
    principal: dict = Depends(current_principal),
    db: Session = Depends(get_db),
):
    _assert_access(principal)
    if not file.content_type or not file.content_type.startswith(("image/", "application/pdf")):
        raise HTTPException(415, "Yalnızca görsel veya PDF kantar fişi kabul edilir.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Fiş görseli 10 MB sınırını aşamaz.")
    extracted = parse_receipt_text(raw_text or "", "weighbridge")
    driver_id = driver_id or (principal["sub"] if principal.get("role") == "driver" else None)
    active = None
    if driver_id:
        active = db.execute(text(
            "SELECT h.vehicle_id::text, v.plate FROM shift_handovers h "
            "JOIN vehicles v ON v.id = h.vehicle_id "
            "WHERE v.tenant_id::text = :tenant AND (h.driver_id::text = :driver OR h.incoming_driver_id::text = :driver) "
            "ORDER BY h.created_at DESC LIMIT 1"
        ), {"tenant": principal["tenant_id"], "driver": driver_id}).mappings().first()
    vehicle_id = active["vehicle_id"] if active else None
    active_plate = active["plate"] if active else None
    ocr_plate = extracted.get("plate")
    mismatch = bool(ocr_plate and active_plate and "".join(str(ocr_plate).split()) != "".join(str(active_plate).split()))
    status = "review_required" if mismatch else "matched" if active else "awaiting_assignment"
    receipt = WeighbridgeReceipt(
        tenant_id=principal["tenant_id"], driver_id=driver_id, vehicle_id=vehicle_id,
        filename=file.filename or "weighbridge-receipt", receipt_number=extracted.get("ticket_no"),
        scale_name=None, ocr_plate=ocr_plate, weighed_ton=Decimal(str(extracted["weight_kg"] or 0)) / 1000,
        receipt_at=None, raw_text=extracted.get("raw_text"), confidence=100 if raw_text else 0,
        status=status, review_reason="Plaka uyuşmazlığı / inceleme bekliyor" if mismatch else None,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return {
        "id": receipt.id, "status": status, "vehicle_id": vehicle_id, "active_plate": active_plate,
        "driver_id": driver_id, "extracted": extracted,
        "alert": "Plaka Uyuşmazlığı / İnceleme Bekliyor" if mismatch else None,
    }


@router.get("/api/v1/shifts/reports")
def shift_report(hours: int = 8, principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    _assert_access(principal)
    if hours not in (8, 24):
        raise HTTPException(422, "hours yalnızca 8 veya 24 olabilir.")
    shift_code, starts_at, ends_at = _shift_window(datetime.now(timezone.utc), hours)
    trip_stats = db.execute(text(
        "SELECT count(*)::int AS trip_count, coalesce(sum(realized_ton), 0) AS total_ton "
        "FROM trips WHERE tenant_id::text = :tenant AND created_at >= :starts_at AND created_at < :ends_at"
    ), {"tenant": principal["tenant_id"], "starts_at": starts_at, "ends_at": ends_at}).mappings().one()
    receipt_count = db.execute(text(
        "SELECT count(*)::int FROM weighbridge_receipts "
        "WHERE tenant_id::text = :tenant AND created_at >= :starts_at AND created_at < :ends_at"
    ), {"tenant": principal["tenant_id"], "starts_at": starts_at, "ends_at": ends_at}).scalar_one()
    return {
        "period": {"hours": hours, "shift_code": shift_code, "starts_at": starts_at, "ends_at": ends_at},
        "drivers": [], "total_ton": trip_stats["total_ton"], "trip_count": trip_stats["trip_count"],
        "receipt_count": receipt_count, "fuel_liters": Decimal("0"), "distance_km": 0,
        "contractor_settlement": Decimal("0"), "driver_efficiency": 0,
        "distribution": {"pdf": f"/api/v1/shifts/reports/{hours}/pdf", "whatsapp": True, "email": True},
    }


@router.get("/api/v1/shifts/reports/{hours}/pdf")
def shift_report_pdf(hours: int, principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    from services.reports import executive_pdf
    from fastapi.responses import StreamingResponse
    if hours not in (8, 24):
        raise HTTPException(422, "hours yalnızca 8 veya 24 olabilir.")
    report = shift_report(hours, principal, db)
    return StreamingResponse(executive_pdf(report, []), media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename=shift-report-{hours}h.pdf"})
