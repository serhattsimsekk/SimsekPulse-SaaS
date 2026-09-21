from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.dependencies import get_db
from database.models import MaintenanceIssue, Part, ShiftHandover, TelemetryEvent, Trip, Vehicle, WaitEvent

router = APIRouter(prefix="/api/v1/operations", tags=["Operasyon"])


@router.get("/dashboard")
def dashboard(tenant_id: str | None = Query(None), db: Session = Depends(get_db)):
    vehicle_query = select(func.count(Vehicle.id))
    trip_query = select(func.count(Trip.id))
    tonnage_query = select(func.coalesce(func.sum(Trip.realized_ton), 0))
    if tenant_id:
        vehicle_query = vehicle_query.where(Vehicle.tenant_id == tenant_id)
        trip_query = trip_query.where(Trip.tenant_id == tenant_id)
        tonnage_query = tonnage_query.where(Trip.tenant_id == tenant_id)
    vehicle_count = db.scalar(vehicle_query) or 0
    active_trips = db.scalar(trip_query.where(Trip.status.in_(["assigned", "in_progress"]))) or 0
    carried_ton = db.scalar(tonnage_query) or Decimal("0")
    alerts = list(db.scalars(select(WaitEvent).where(WaitEvent.status == "open").order_by(WaitEvent.started_at.desc()).limit(20)))
    return {
        "vehicle_count": vehicle_count,
        "active_trips": active_trips,
        "carried_ton": carried_ton,
        "demurrage_alerts": [
            {
                "id": item.id,
                "location_name": item.location_name,
                "location_type": item.location_type,
                "demurrage_amount": item.demurrage_amount,
                "status": item.status,
            }
            for item in alerts
        ],
    }


@router.get("/trips")
def list_trips(tenant_id: str | None = None, db: Session = Depends(get_db)):
    query = select(Trip).order_by(Trip.created_at.desc()).limit(100)
    if tenant_id:
        query = query.where(Trip.tenant_id == tenant_id)
    return list(db.scalars(query))


@router.get("/telemetry/latest")
def latest_telemetry(tenant_id: str | None = None, db: Session = Depends(get_db)):
    query = select(TelemetryEvent, Vehicle.plate).join(Vehicle, Vehicle.id == TelemetryEvent.vehicle_id)
    if tenant_id:
        query = query.where(Vehicle.tenant_id == tenant_id)
    rows = db.execute(query.order_by(TelemetryEvent.recorded_at.desc()).limit(100)).all()
    return [
        {
            "vehicle_id": event.vehicle_id,
            "plate": plate,
            "recorded_at": event.recorded_at,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "speed_kmh": event.speed_kmh,
            "engine_on": event.engine_on,
        }
        for event, plate in rows
    ]


@router.get("/maintenance/issues")
def maintenance_issues(tenant_id: str | None = None, db: Session = Depends(get_db)):
    query = select(MaintenanceIssue, Vehicle.plate).join(Vehicle, Vehicle.id == MaintenanceIssue.vehicle_id)
    if tenant_id:
        query = query.where(Vehicle.tenant_id == tenant_id)
    return [
        {
            "id": issue.id,
            "vehicle_id": issue.vehicle_id,
            "plate": plate,
            "category": issue.category,
            "urgency": issue.urgency,
            "parts_needed": issue.parts_needed,
            "status": issue.status,
            "layup_days": issue.layup_days,
        }
        for issue, plate in db.execute(query.order_by(MaintenanceIssue.created_at.desc()).limit(100)).all()
    ]


@router.get("/maintenance/parts")
def maintenance_parts(tenant_id: str, db: Session = Depends(get_db)):
    parts = db.scalars(select(Part).where(Part.tenant_id == tenant_id).order_by(Part.name)).all()
    return [
        {
            "id": part.id,
            "sku": part.sku,
            "name": part.name,
            "unit": part.unit,
            "stock_quantity": part.stock_quantity,
            "critical_quantity": part.critical_quantity,
            "unit_cost": part.unit_cost,
            "low_stock": part.stock_quantity <= part.critical_quantity,
        }
        for part in parts
    ]


@router.post("/maintenance/issues")
def create_maintenance_issue(payload: dict, db: Session = Depends(get_db)):
    required = {"vehicle_id", "category"}
    missing = required - payload.keys()
    if missing:
        raise HTTPException(422, f"Eksik alanlar: {', '.join(sorted(missing))}")
    issue = MaintenanceIssue(
        vehicle_id=payload["vehicle_id"],
        reported_by_driver_id=payload.get("reported_by_driver_id"),
        category=payload["category"],
        urgency=payload.get("urgency", "normal"),
        parts_needed=payload.get("parts_needed"),
        estimated_cost=payload.get("estimated_cost"),
        layup_days=payload.get("layup_days", 0),
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return {"id": issue.id, "status": issue.status}


@router.post("/shift-handovers", status_code=201)
def create_shift_handover(payload: dict, db: Session = Depends(get_db)):
    required = {"vehicle_id", "driver_id", "closing_odometer_km", "fuel_percent"}
    missing = required - payload.keys()
    if missing:
        raise HTTPException(422, f"Eksik alanlar: {', '.join(sorted(missing))}")
    vehicle = db.get(Vehicle, payload["vehicle_id"])
    if not vehicle:
        vehicle = db.scalar(select(Vehicle).where(Vehicle.plate == payload["vehicle_id"]))
    if not vehicle:
        raise HTTPException(404, "Araç bulunamadı.")
    handover = ShiftHandover(
        vehicle_id=vehicle.id,
        driver_id=payload["driver_id"],
        incoming_driver_id=payload.get("incoming_driver_id"),
        closing_odometer_km=payload["closing_odometer_km"],
        fuel_percent=payload["fuel_percent"],
        fuel_liters=payload.get("fuel_liters"),
        photo_uri=payload.get("photo_uri"),
        notes=payload.get("notes"),
    )
    db.add(handover)
    db.commit()
    db.refresh(handover)
    return {
        "id": handover.id,
        "vehicle_id": handover.vehicle_id,
        "driver_id": handover.driver_id,
        "status": handover.status,
        "created_at": handover.created_at,
    }


@router.post("/drivers/{driver_id}/shift-handover", status_code=201)
def create_driver_shift_handover(driver_id: str, payload: dict, db: Session = Depends(get_db)):
    """Mobil portal için sürücü kimliği üzerinden vardiya teslim kısayolu."""
    normalized = {
        "vehicle_id": payload.get("vehicle_id"),
        "driver_id": driver_id,
        "incoming_driver_id": payload.get("receiving_driver_id") or payload.get("incoming_driver_id"),
        "closing_odometer_km": payload.get("closing_odometer_km", 0),
        "fuel_percent": payload.get("fuel_percent", 0),
        "fuel_liters": payload.get("fuel_liters"),
        "photo_uri": payload.get("photo_uri"),
        "notes": payload.get("notes"),
    }
    return create_shift_handover(normalized, db)
