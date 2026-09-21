from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import (
    AssistantQuery,
    FuelForecastRequest,
    NotificationReportRequest,
    PlateNormalizeRequest,
    ReportQuery,
    StackOptimizationRequest,
    ShiftSlotRequest,
    TonFormatRequest,
    VehicleMatchRequest,
    WeighbridgeCheckRequest,
    WorkOrderCreate,
)
from api.security import require_roles
from database.models import (
    Driver,
    DriverTask,
    Expense,
    FuelTransaction,
    GeofenceEvent,
    Incident,
    MaintenanceIssue,
    Part,
    RestBreak,
    ShiftHandover,
    TachographViolation,
    TelemetryEvent,
    Trip,
    Vehicle,
    WaitEvent,
    WeighbridgeTicket,
    WorkOrder,
)
from services.compliance import fatigue_index

router = APIRouter(prefix="/api/v1/command-center", tags=["75 Modül Komuta Merkezi"])


def tenant(principal: dict) -> str:
    return principal["tenant_id"]


def _vehicle_ids(db: Session, tenant_id: str) -> list[str]:
    return list(db.scalars(select(Vehicle.id).where(Vehicle.tenant_id == tenant_id)))


@router.get("/master-dashboard")
def master_dashboard(principal: dict = Depends(require_roles("admin", "head_driver", "customer")), db: Session = Depends(get_db)):
    tid = tenant(principal)
    vehicle_ids = _vehicle_ids(db, tid)
    total_planned, total_realized = db.execute(
        select(func.coalesce(func.sum(Trip.planned_ton), 0), func.coalesce(func.sum(Trip.realized_ton), 0))
        .where(Trip.tenant_id == tid)
    ).one()
    active = db.scalar(select(func.count(Trip.id)).where(Trip.tenant_id == tid, Trip.status.in_(["assigned", "in_progress"]))) or 0
    open_waits = db.scalar(select(func.count(WaitEvent.id)).where(WaitEvent.vehicle_id.in_(vehicle_ids), WaitEvent.status == "open")) if vehicle_ids else 0
    open_incidents = db.scalar(select(func.count(Incident.id)).where(Incident.vehicle_id.in_(vehicle_ids), Incident.status == "open")) if vehicle_ids else 0
    remaining = max(Decimal(str(total_planned)) - Decimal(str(total_realized)), Decimal("0"))
    return {
        "tenant_id": tid, "vehicle_count": len(vehicle_ids), "active_trips": active,
        "planned_ton": total_planned, "realized_ton": total_realized, "remaining_ton": remaining,
        "progress_percent": round(float(total_realized / total_planned * 100), 2) if total_planned else 0,
        "open_demurrage_alerts": open_waits, "open_risk_events": open_incidents,
        "generated_at": datetime.now(timezone.utc),
    }


@router.get("/operation-matrix")
def operation_matrix(principal: dict = Depends(require_roles("admin", "head_driver", "customer")), db: Session = Depends(get_db)):
    tid = tenant(principal)
    trips = db.scalars(select(Trip).where(Trip.tenant_id == tid).order_by(Trip.created_at.desc()).limit(500)).all()
    result = []
    for trip in trips:
        planned = Decimal(str(trip.planned_ton or 0))
        realized = Decimal(str(trip.realized_ton or 0))
        result.append({"trip_id": trip.id, "route": trip.route, "status": trip.status, "planned_ton": planned,
                       "realized_ton": realized, "remaining_ton": max(planned - realized, 0),
                       "progress_percent": round(float(realized / planned * 100), 2) if planned else 0,
                       "eta_hours": ceil(float(max(planned - realized, 0)) / 10) if planned else 0})
    return result


@router.get("/heatmap")
def fleet_heatmap(principal: dict = Depends(require_roles("admin", "head_driver", "customer")), db: Session = Depends(get_db)):
    tid = tenant(principal)
    rows = db.execute(
        select(TelemetryEvent.latitude, TelemetryEvent.longitude, TelemetryEvent.speed_kmh, Vehicle.plate)
        .join(Vehicle, Vehicle.id == TelemetryEvent.vehicle_id)
        .where(Vehicle.tenant_id == tid)
        .order_by(TelemetryEvent.recorded_at.desc()).limit(1000)
    ).all()
    points = [{"lat": lat, "lng": lng, "weight": 1 if (speed or 0) > 5 else 3, "plate": plate} for lat, lng, speed, plate in rows]
    return {"points": points, "bottleneck_count": sum(point["weight"] > 1 for point in points)}


@router.get("/risk-map")
def risk_map(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    tid = tenant(principal)
    ids = _vehicle_ids(db, tid)
    waits = db.scalars(select(WaitEvent).where(WaitEvent.vehicle_id.in_(ids), WaitEvent.status == "open")).all() if ids else []
    incidents = db.scalars(select(Incident).where(Incident.vehicle_id.in_(ids), Incident.status == "open")).all() if ids else []
    return {"risks": [{"type": "demurrage", "id": x.id, "severity": "high", "location": x.location_name} for x in waits]
            + [{"type": "incident", "id": x.id, "severity": "high", "location": x.incident_type} for x in incidents]}


@router.get("/kpis")
def operational_kpis(query: ReportQuery = Depends(), principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    tid = tenant(principal)
    since = datetime.now(timezone.utc) - timedelta(days=query.period_days)
    completed = db.scalar(select(func.count(Trip.id)).where(Trip.tenant_id == tid, Trip.status == "completed", Trip.updated_at >= since)) or 0
    ton = db.scalar(select(func.coalesce(func.sum(Trip.realized_ton), 0)).where(Trip.tenant_id == tid, Trip.updated_at >= since)) or Decimal("0")
    return {"period_days": query.period_days, "completed_trips": completed, "daily_tonnage_rate": Decimal(str(ton)) / query.period_days,
            "performance_index": round(min(float(ton) / max(completed, 1), 100), 2)}


@router.get("/telemetry/live")
def live_telemetry(principal: dict = Depends(require_roles("admin", "head_driver", "customer")), db: Session = Depends(get_db)):
    tid = tenant(principal)
    rows = db.execute(select(TelemetryEvent, Vehicle.plate, Vehicle.device_no).join(Vehicle).where(Vehicle.tenant_id == tid).order_by(TelemetryEvent.recorded_at.desc()).limit(500)).all()
    return [{"vehicle_id": event.vehicle_id, "plate": plate, "device_no": device, "latitude": event.latitude,
             "longitude": event.longitude, "speed_kmh": event.speed_kmh, "engine_on": event.engine_on,
             "recorded_at": event.recorded_at} for event, plate, device in rows]


@router.get("/geofences/events")
def geofence_events(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    ids = _vehicle_ids(db, tenant(principal))
    return list(db.scalars(select(GeofenceEvent).where(GeofenceEvent.vehicle_id.in_(ids)).order_by(GeofenceEvent.created_at.desc()).limit(200))) if ids else []


@router.get("/demurrage/early-warning")
def demurrage_warning(principal: dict = Depends(require_roles("admin", "head_driver", "customer")), db: Session = Depends(get_db)):
    ids = _vehicle_ids(db, tenant(principal))
    waits = db.scalars(select(WaitEvent).where(WaitEvent.vehicle_id.in_(ids), WaitEvent.status == "open")).all() if ids else []
    now = datetime.now(timezone.utc)
    return [{"id": event.id, "location_name": event.location_name, "elapsed_minutes": max(int((now - event.started_at).total_seconds() / 60), 0),
             "free_minutes": event.free_minutes, "demurrage_amount": event.demurrage_amount,
             "warning": (now - event.started_at).total_seconds() / 60 >= event.free_minutes * 0.8} for event in waits]


@router.post("/shift-slots")
def shift_slots(payload: ShiftSlotRequest, principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    drivers = db.scalars(select(Driver).where(Driver.tenant_id == tenant(principal), Driver.id.in_(payload.driver_ids))).all()
    return [{"driver_id": driver.id, "driver_name": driver.name, "shift": payload.shift,
             "start_at": payload.start_at + timedelta(hours=index * payload.duration_hours / max(len(drivers), 1)),
             "end_at": payload.start_at + timedelta(hours=(index + 1) * payload.duration_hours / max(len(drivers), 1))}
            for index, driver in enumerate(drivers)]


@router.get("/shift-analysis")
def shift_analysis(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    tid = tenant(principal)
    rows = db.execute(select(Driver.shift, func.count(Trip.id), func.coalesce(func.sum(Trip.realized_ton), 0))
                      .join(Trip, Trip.driver_id == Driver.id, isouter=True).where(Driver.tenant_id == tid)
                      .group_by(Driver.shift)).all()
    return [{"shift": shift or "unassigned", "trip_count": count, "realized_ton": ton,
             "night_efficiency_index": round(float(ton) / max(count, 1), 2)} for shift, count, ton in rows]


@router.get("/driver-performance")
def driver_performance(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    rows = db.execute(select(Driver.id, Driver.name, func.count(Trip.id), func.coalesce(func.sum(Trip.realized_ton), 0))
                      .join(Trip, Trip.driver_id == Driver.id, isouter=True).where(Driver.tenant_id == tenant(principal))
                      .group_by(Driver.id, Driver.name)).all()
    return [{"driver_id": driver_id, "driver_name": name, "trip_count": count, "realized_ton": ton,
             "efficiency_score": round(float(ton) / max(count, 1), 2)} for driver_id, name, count, ton in rows]


@router.get("/fatigue/{driver_id}")
def fatigue(driver_id: str, driving_minutes: int = 0, break_minutes: int = 0, principal: dict = Depends(require_roles("admin", "head_driver", "driver")), db: Session = Depends(get_db)):
    driver = db.scalar(select(Driver).where(Driver.id == driver_id, Driver.tenant_id == tenant(principal)))
    if not driver:
        raise HTTPException(404, "Sürücü bulunamadı.")
    violations = db.scalar(select(func.count(TachographViolation.id)).where(TachographViolation.driver_id == driver_id)) or 0
    return {"driver_id": driver_id, **fatigue_index(driving_minutes, break_minutes, violations)}


@router.get("/rest-alerts")
def rest_alerts(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    ids = list(db.scalars(select(Driver.id).where(Driver.tenant_id == tenant(principal))))
    open_breaks = db.scalars(select(RestBreak).where(RestBreak.driver_id.in_(ids), RestBreak.ended_at.is_(None))).all() if ids else []
    return [{"driver_id": item.driver_id, "started_at": item.started_at, "elapsed_minutes": int((datetime.now(timezone.utc) - item.started_at).total_seconds() / 60)} for item in open_breaks]


@router.post("/vehicle-match")
def vehicle_match(payload: VehicleMatchRequest, principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    query = select(Vehicle).where(Vehicle.tenant_id == tenant(principal), Vehicle.status == "active")
    if payload.preferred_vehicle_type:
        query = query.where(Vehicle.vehicle_type == payload.preferred_vehicle_type)
    vehicles = db.scalars(query).all()
    return {"recommendations": [{"vehicle_id": v.id, "plate": v.plate, "score": round(100 - abs(float(payload.required_ton) - float(v.fuel_capacity_l or 0)), 2)} for v in vehicles[:20]]}


@router.post("/fuel-forecast")
def fuel_forecast(payload: FuelForecastRequest, principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == payload.vehicle_id, Vehicle.tenant_id == tenant(principal)))
    if not vehicle:
        raise HTTPException(404, "Araç bulunamadı.")
    base = Decimal(str(vehicle.consumption_100km or 30))
    adjusted = base * (Decimal("1") + payload.load_ton / Decimal("1000"))
    liters = payload.distance_km * adjusted / Decimal("100")
    return {"vehicle_id": vehicle.id, "estimated_liters": liters.quantize(Decimal("0.01")), "estimated_cost": (liters * payload.fuel_price).quantize(Decimal("0.01")),
            "consumption_l100km": adjusted.quantize(Decimal("0.01"))}


@router.get("/fuel-security")
def fuel_security(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    ids = _vehicle_ids(db, tenant(principal))
    rows = db.execute(select(FuelTransaction.vehicle_id, func.sum(FuelTransaction.liters), func.count(FuelTransaction.id)).where(FuelTransaction.vehicle_id.in_(ids)).group_by(FuelTransaction.vehicle_id)).all() if ids else []
    return [{"vehicle_id": vehicle_id, "liters": liters, "transaction_count": count, "high_consumption_alert": float(liters or 0) > 1000} for vehicle_id, liters, count in rows]


@router.post("/maintenance/work-orders")
def create_work_order(payload: WorkOrderCreate, principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == payload.vehicle_id, Vehicle.tenant_id == tenant(principal)))
    if not vehicle:
        raise HTTPException(404, "Araç bulunamadı.")
    issue = MaintenanceIssue(vehicle_id=vehicle.id, category=payload.category, urgency=payload.urgency, estimated_cost=payload.estimated_cost)
    db.add(issue)
    db.flush()
    order = WorkOrder(vehicle_id=vehicle.id, issue_id=issue.id, labor_cost=payload.estimated_cost, status="planned")
    db.add(order)
    db.commit()
    return {"issue_id": issue.id, "work_order_id": order.id, "status": order.status}


@router.get("/maintenance/predictive")
def predictive_maintenance(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    ids = _vehicle_ids(db, tenant(principal))
    rows = db.execute(select(Vehicle.id, Vehicle.plate, func.count(MaintenanceIssue.id))
                      .join(MaintenanceIssue, MaintenanceIssue.vehicle_id == Vehicle.id, isouter=True)
                      .where(Vehicle.id.in_(ids)).group_by(Vehicle.id, Vehicle.plate)).all() if ids else []
    return [{"vehicle_id": vehicle_id, "plate": plate, "issue_count": count, "risk_score": min(count * 20, 100),
             "recommended_inspection": count >= 3} for vehicle_id, plate, count in rows]


@router.post("/weighbridge/check")
def weighbridge_check(payload: WeighbridgeCheckRequest, principal: dict = Depends(require_roles("admin", "head_driver", "driver")), db: Session = Depends(get_db)):
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == payload.vehicle_id, Vehicle.tenant_id == tenant(principal)))
    if not vehicle:
        raise HTTPException(404, "Araç bulunamadı.")
    deviation = payload.measured_kg - payload.declared_kg
    return {"vehicle_id": vehicle.id, "declared_kg": payload.declared_kg, "measured_kg": payload.measured_kg,
            "deviation_kg": deviation, "within_tolerance": abs(deviation) <= payload.tolerance_kg,
            "status": "accepted" if abs(deviation) <= payload.tolerance_kg else "investigation_required"}


@router.get("/profitability-map")
def profitability_map(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    ids = _vehicle_ids(db, tenant(principal))
    rows = db.execute(select(Vehicle.id, Vehicle.plate, func.coalesce(func.sum(Trip.realized_ton), 0),
                             func.coalesce(func.sum(FuelTransaction.liters * FuelTransaction.unit_price), 0))
                      .join(Trip, Trip.vehicle_id == Vehicle.id, isouter=True)
                      .join(FuelTransaction, FuelTransaction.vehicle_id == Vehicle.id, isouter=True)
                      .where(Vehicle.id.in_(ids)).group_by(Vehicle.id, Vehicle.plate)).all() if ids else []
    return [{"vehicle_id": vehicle_id, "plate": plate, "ton": ton, "fuel_cost": fuel, "profitability_index": round(float(ton) - float(fuel) / 100, 2)} for vehicle_id, plate, ton, fuel in rows]


@router.get("/esg/carbon")
def carbon_report(query: ReportQuery = Depends(), principal: dict = Depends(require_roles("admin", "head_driver", "customer")), db: Session = Depends(get_db)):
    ids = _vehicle_ids(db, tenant(principal))
    liters = db.scalar(select(func.coalesce(func.sum(FuelTransaction.liters), 0)).where(FuelTransaction.vehicle_id.in_(ids))) if ids else 0
    co2_kg = Decimal(str(liters)) * Decimal("2.68")
    return {"period_days": query.period_days, "fuel_liters": liters, "co2_kg": co2_kg.quantize(Decimal("0.01")), "methodology": "fuel_liters * 2.68 kg CO2e"}


@router.get("/fleet-capacity-projection")
def capacity_projection(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    tid = tenant(principal)
    vehicle_count = db.scalar(select(func.count(Vehicle.id)).where(Vehicle.tenant_id == tid)) or 0
    completed = db.scalar(select(func.count(Trip.id)).where(Trip.tenant_id == tid, Trip.status == "completed")) or 0
    return {"current_vehicle_count": vehicle_count, "completed_trips": completed, "next_month_required_vehicle_count": max(0, ceil(completed / 26) - vehicle_count),
            "projection_basis": "completed_trips / 26 working days"}


@router.post("/assistant/query")
def assistant_query(payload: AssistantQuery, principal: dict = Depends(require_roles("admin", "head_driver", "customer")), db: Session = Depends(get_db)):
    query = payload.query.lower()
    dashboard = master_dashboard(principal, db)
    intent = "dashboard"
    if "yakıt" in query or "fuel" in query:
        intent = "fuel"
    elif "demoraj" in query or "bekleme" in query:
        intent = "demurrage"
    elif "tonaj" in query:
        intent = "tonnage"
    return {"intent": intent, "answer": dashboard, "disclaimer": "Sonuçlar operasyon veritabanındaki güncel kayıtlardan üretilmiştir."}


@router.post("/notification-report")
def notification_report(payload: NotificationReportRequest, principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    return {"status": "queued", "channel": payload.channel, "recipient": payload.recipient, "subject": payload.subject,
            "tenant_id": tenant(principal), "message": "Rapor kuyruğa alındı; sağlayıcı entegrasyonu yapılandırıldığında gönderilecektir."}


@router.post("/plate/normalize")
def normalize_plate(payload: PlateNormalizeRequest):
    value = re.sub(r"[^A-Za-z0-9]", "", payload.plate).upper()
    if len(value) < 5:
        raise HTTPException(422, "Plaka en az il kodu ve harf/rakam bölümü içermelidir.")
    return {"input": payload.plate, "normalized": value, "display": f"{value[:2]} {value[2:]}"}


@router.post("/tonnage/format")
def format_tonnage(payload: TonFormatRequest):
    formatted = f"{payload.tons:,.3f}"
    if payload.locale == "tr-TR":
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return {"tons": payload.tons, "formatted": f"{formatted} ton", "locale": payload.locale}


@router.post("/stack/optimize")
def optimize_stack(payload: StackOptimizationRequest):
    ordered = sorted(payload.lots, reverse=True)
    bins: list[dict] = []
    for lot in ordered:
        target = next((item for item in bins if item["remaining_ton"] >= lot), None)
        if target is None:
            target = {"bin": len(bins) + 1, "remaining_ton": payload.warehouse_capacity_ton, "lots": []}
            bins.append(target)
        target["lots"].append(lot)
        target["remaining_ton"] -= lot
    return {"bins": bins, "bin_count": len(bins), "utilization_percent": round(float(sum(payload.lots) / (payload.warehouse_capacity_ton * len(bins)) * 100), 2)}


@router.get("/qr/{entity_type}/{entity_id}")
def identity_qr(entity_type: str, entity_id: str, principal: dict = Depends(require_roles("admin", "head_driver", "driver"))):
    if entity_type not in {"driver", "vehicle", "trailer"}:
        raise HTTPException(422, "entity_type driver, vehicle veya trailer olmalıdır.")
    return {"entity_type": entity_type, "entity_id": entity_id, "payload": f"simseklog://{entity_type}/{entity_id}", "format": "QR-compatible"}


@router.get("/blacklist")
def blacklist(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    return [{"id": driver.id, "name": driver.name, "penalty_points": driver.penalty_points, "status": driver.status}
            for driver in db.scalars(select(Driver).where(Driver.tenant_id == tenant(principal), Driver.blacklisted.is_(True)))]


@router.get("/tasks/overview")
def tasks_overview(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    driver_ids = list(db.scalars(select(Driver.id).where(Driver.tenant_id == tenant(principal))))
    tasks = db.scalars(select(DriverTask).where(DriverTask.driver_id.in_(driver_ids)).order_by(DriverTask.due_at)).all() if driver_ids else []
    return [{"id": task.id, "driver_id": task.driver_id, "description": task.description, "status": task.status, "due_at": task.due_at} for task in tasks]


@router.get("/parts/stock")
def parts_stock(principal: dict = Depends(require_roles("admin", "head_driver")), db: Session = Depends(get_db)):
    parts = db.scalars(select(Part).where(Part.tenant_id == tenant(principal)).order_by(Part.name)).all()
    return [{"id": part.id, "sku": part.sku, "name": part.name, "stock_quantity": part.stock_quantity,
             "critical": part.stock_quantity <= part.critical_quantity} for part in parts]
