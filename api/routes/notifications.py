import os
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.security import require_roles
from database.models import NotificationLog

router = APIRouter(prefix="/api/v1/notifications", tags=["WhatsApp & SMS"])


class ShiftMessageRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=30)
    driver_name: str
    vehicle_plate: str
    closing_km: int = Field(ge=0)
    fuel_liters: float = Field(ge=0)
    notes: str = ""


class EmergencyRequest(BaseModel):
    channel: str = Field(pattern="^(whatsapp|sms)$")
    recipient: str = Field(min_length=7, max_length=100)
    title: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=2, max_length=2000)


@router.post("/shift-message")
def shift_message(payload: ShiftMessageRequest, principal: dict = Depends(require_roles("admin", "head_driver", "driver"))):
    message = (
        f"ŞİMŞEKLOG VARDİYA DEVİR\nSürücü: {payload.driver_name}\n"
        f"Araç: {payload.vehicle_plate}\nKapanış KM: {payload.closing_km}\n"
        f"Mazot: {payload.fuel_liters:.2f} L\nNot: {payload.notes or '-'}"
    )
    return {"channel": "whatsapp", "phone": payload.phone, "message": message, "url": f"https://wa.me/{payload.phone.lstrip('+')}?text={quote(message)}"}


@router.post("/emergency", status_code=status.HTTP_202_ACCEPTED)
def emergency_notification(
    payload: EmergencyRequest,
    principal: dict = Depends(require_roles("admin", "head_driver")),
    db: Session = Depends(get_db),
):
    provider_configured = bool(
        os.getenv("WHATSAPP_ACCESS_TOKEN") if payload.channel == "whatsapp" else os.getenv("SMS_PROVIDER_URL")
    )
    log = NotificationLog(
        tenant_id=principal["tenant_id"],
        user_id=principal["sub"],
        channel=payload.channel,
        recipient=payload.recipient,
        title=payload.title,
        message=payload.message,
        status="queued" if provider_configured else "provider_not_configured",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"id": log.id, "status": log.status, "provider_configured": provider_configured}
