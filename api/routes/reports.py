from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.security import require_roles
from database.models import Vehicle, WaitEvent
from services.reports import executive_pdf, fleet_capacity_excel

router = APIRouter(prefix="/api/v1/reports", tags=["Raporlar"])


@router.get("/executive.pdf")
def executive_report(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    logo_data = db.execute(text("SELECT logo_data FROM tenants WHERE id::text = :tenant"), {"tenant": principal["tenant_id"]}).scalar_one_or_none()
    vehicles = list(db.scalars(select(Vehicle).where(Vehicle.tenant_id == principal["tenant_id"])))
    alerts = list(
        db.scalars(
            select(WaitEvent)
            .join(Vehicle, Vehicle.id == WaitEvent.vehicle_id)
            .where(WaitEvent.status == "open", Vehicle.tenant_id == principal["tenant_id"])
        )
    )
    summary = {"vehicle_count": len(vehicles), "active_trips": 0, "carried_ton": 0}
    payload = executive_pdf(summary, [{"location_name": a.location_name, "location_type": a.location_type, "demurrage_amount": a.demurrage_amount, "status": a.status} for a in alerts], logo_data)
    return StreamingResponse(payload, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=simseklog-executive.pdf"})


@router.get("/fleet-capacity.xlsx")
def fleet_capacity_report(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    vehicles = db.scalars(select(Vehicle).where(Vehicle.tenant_id == principal["tenant_id"])).all()
    rows = [{"plate": v.plate, "model": v.model, "capacity_ton": 0, "odometer_km": v.odometer_km, "status": v.status} for v in vehicles]
    payload = fleet_capacity_excel(rows)
    return StreamingResponse(payload, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=simseklog-fleet-capacity.xlsx"})
