import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import (
    DisciplineCreate,
    DisciplineRead,
    DocumentCreate,
    DocumentRead,
    FatigueRead,
    RestBreakCreate,
    TachographViolationCreate,
    TachographViolationRead,
)
from database.models import (
    DisciplineRecord,
    Driver,
    DriverDocument,
    ReceiptOcrRecord,
    RestBreak,
    TachographViolation,
)
from services.compliance import expiry_status, fatigue_index, parse_receipt_text, utc_now

router = APIRouter(prefix="/api/v1", tags=["AI OCR & Sürücü Uyum"])


@router.post("/receipts/ocr", status_code=status.HTTP_201_CREATED)
async def analyze_receipt(
    tenant_id: str = Form(...),
    receipt_type: str = Form(..., pattern="^(weighbridge|fuel)$"),
    driver_id: str | None = Form(None),
    vehicle_id: str | None = Form(None),
    raw_text: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Fiş görseli 10 MB sınırını aşamaz.")
    if not file.content_type or not file.content_type.startswith(("image/", "application/pdf")):
        raise HTTPException(415, "Yalnızca görsel veya PDF fiş kabul edilir.")
    extracted = parse_receipt_text(raw_text or "", receipt_type)
    record = ReceiptOcrRecord(
        tenant_id=tenant_id,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        receipt_type=receipt_type,
        filename=file.filename or "receipt",
        content_type=file.content_type,
        file_size_bytes=len(content),
        raw_text=extracted["raw_text"],
        extracted_data=json.dumps(extracted, ensure_ascii=False),
        confidence=100 if raw_text else 0,
        status="processed" if raw_text else "awaiting_ocr_provider",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "status": record.status,
        "filename": record.filename,
        "extracted": extracted,
        "confidence": float(record.confidence),
        "message": "OCR metni analiz edildi." if raw_text else "Dosya kaydedildi; OCR sağlayıcısı yapılandırılmadığı için metin bekleniyor.",
    }


@router.post("/drivers/{driver_id}/documents", response_model=DocumentRead, status_code=201)
def create_document(driver_id: str, payload: DocumentCreate, db: Session = Depends(get_db)):
    if not db.get(Driver, driver_id):
        raise HTTPException(404, "Sürücü bulunamadı.")
    document = DriverDocument(driver_id=driver_id, **payload.model_dump())
    document.status = expiry_status(document.expires_on)["warning"]
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/drivers/{driver_id}/documents", response_model=list[DocumentRead])
def list_documents(driver_id: str, db: Session = Depends(get_db)):
    documents = list(db.scalars(select(DriverDocument).where(DriverDocument.driver_id == driver_id)))
    for document in documents:
        document.status = expiry_status(document.expires_on)["warning"]
    return documents


@router.get("/drivers/{driver_id}/document-alerts")
def document_alerts(driver_id: str, db: Session = Depends(get_db)):
    if not db.get(Driver, driver_id):
        raise HTTPException(404, "Sürücü bulunamadı.")
    documents = list(db.scalars(select(DriverDocument).where(DriverDocument.driver_id == driver_id)))
    alerts = [{"id": item.id, "document_type": item.document_type, "expires_on": item.expires_on, **expiry_status(item.expires_on)} for item in documents]
    return {"driver_id": driver_id, "task_locked": any(item["task_locked"] for item in alerts), "documents": alerts}


@router.post("/drivers/{driver_id}/discipline", response_model=DisciplineRead, status_code=201)
def create_discipline(driver_id: str, payload: DisciplineCreate, db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404, "Sürücü bulunamadı.")
    record = DisciplineRecord(driver_id=driver_id, **payload.model_dump())
    driver.penalty_points += record.points
    if driver.penalty_points >= 100:
        driver.blacklisted = True
        driver.status = "blacklisted"
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/drivers/{driver_id}/discipline", response_model=list[DisciplineRead])
def list_discipline(driver_id: str, db: Session = Depends(get_db)):
    return list(db.scalars(select(DisciplineRecord).where(DisciplineRecord.driver_id == driver_id).order_by(DisciplineRecord.occurred_at.desc())))


@router.patch("/drivers/{driver_id}/blacklist")
def set_blacklist(driver_id: str, blacklisted: bool, db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404, "Sürücü bulunamadı.")
    driver.blacklisted = blacklisted
    driver.status = "blacklisted" if blacklisted else "active"
    db.commit()
    return {"driver_id": driver_id, "blacklisted": driver.blacklisted, "status": driver.status}


@router.post("/drivers/{driver_id}/tachograph-violations", response_model=TachographViolationRead, status_code=201)
def create_tachograph_violation(driver_id: str, payload: TachographViolationCreate, db: Session = Depends(get_db)):
    if not db.get(Driver, driver_id):
        raise HTTPException(404, "Sürücü bulunamadı.")
    violation = TachographViolation(driver_id=driver_id, **payload.model_dump())
    db.add(violation)
    db.commit()
    db.refresh(violation)
    return violation


@router.get("/drivers/{driver_id}/fatigue-index", response_model=FatigueRead)
def driver_fatigue_index(driver_id: str, driving_minutes: int, break_minutes: int, db: Session = Depends(get_db)):
    if not db.get(Driver, driver_id):
        raise HTTPException(404, "Sürücü bulunamadı.")
    violations = db.scalar(select(func.count(TachographViolation.id)).where(TachographViolation.driver_id == driver_id)) or 0
    return {"driver_id": driver_id, "tachograph_violation_count": violations, **fatigue_index(driving_minutes, break_minutes, violations)}


@router.post("/drivers/{driver_id}/breaks", status_code=201)
def create_rest_break(driver_id: str, payload: RestBreakCreate, db: Session = Depends(get_db)):
    if not db.get(Driver, driver_id):
        raise HTTPException(404, "Sürücü bulunamadı.")
    if payload.ended_at and payload.ended_at < payload.started_at:
        raise HTTPException(400, "Mola bitişi başlangıçtan önce olamaz.")
    duration = payload.duration_minutes
    if payload.ended_at:
        duration = max(int((payload.ended_at - payload.started_at).total_seconds() // 60), 0)
    rest_break = RestBreak(driver_id=driver_id, **payload.model_dump(exclude={"duration_minutes"}), duration_minutes=duration)
    db.add(rest_break)
    db.commit()
    db.refresh(rest_break)
    return {
        "id": rest_break.id,
        "driver_id": driver_id,
        "started_at": rest_break.started_at,
        "ended_at": rest_break.ended_at,
        "duration_minutes": rest_break.duration_minutes,
        "break_type": rest_break.break_type,
    }


@router.get("/drivers/{driver_id}/breaks")
def list_rest_breaks(driver_id: str, db: Session = Depends(get_db)):
    if not db.get(Driver, driver_id):
        raise HTTPException(404, "Sürücü bulunamadı.")
    return list(db.scalars(select(RestBreak).where(RestBreak.driver_id == driver_id).order_by(RestBreak.started_at.desc())))
