from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.security import current_principal, require_roles

router = APIRouter(tags=["Saha Operasyonları & Maliyet Kontrolü"])


def _tenant(principal: dict) -> str:
    return principal["tenant_id"]


@router.post("/api/v1/field/tyre-incidents", status_code=201)
def create_tyre_incident(payload: dict, principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    required = {"vehicle_id", "occurred_at"}
    if missing := required - payload.keys():
        raise HTTPException(422, f"Eksik alanlar: {', '.join(sorted(missing))}")
    row = db.execute(text(
        "INSERT INTO tyre_incidents (tenant_id, vehicle_id, driver_id, trailer_id, tire_id, route, location, "
        "cause, brand, model, damage_cost, occurred_at) VALUES "
        "(CAST(:tenant AS uuid), CAST(:vehicle AS uuid), CAST(:driver AS uuid), CAST(:trailer AS uuid), "
        "CAST(:tire AS uuid), :route, :location, :cause, :brand, :model, :cost, :occurred_at) "
        "RETURNING id::text"
    ), {"tenant": _tenant(principal), "vehicle": payload["vehicle_id"], "driver": payload.get("driver_id"),
        "trailer": payload.get("trailer_id"), "tire": payload.get("tire_id"), "route": payload.get("route"),
        "location": payload.get("location"), "cause": payload.get("cause", "unknown"), "brand": payload.get("brand"),
        "model": payload.get("model"), "cost": payload.get("damage_cost", 0), "occurred_at": payload["occurred_at"]}).scalar_one()
    db.commit()
    return {"id": row, "status": "recorded", "scorecard_penalty": 10 if payload.get("cause") in {"harsh_driving", "overload"} else 5}


@router.post("/api/v1/field/roadside-assistance", status_code=201)
def create_roadside_log(payload: dict, principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    required = {"vehicle_id", "provider_type", "provider_name", "occurred_at"}
    if missing := required - payload.keys():
        raise HTTPException(422, f"Eksik alanlar: {', '.join(sorted(missing))}")
    row = db.execute(text(
        "INSERT INTO road_side_assistance_logs (tenant_id, incident_id, vehicle_id, provider_type, provider_name, "
        "location, cost, response_minutes, occurred_at) VALUES (CAST(:tenant AS uuid), CAST(:incident AS uuid), "
        "CAST(:vehicle AS uuid), :provider_type, :provider_name, :location, :cost, :response_minutes, :occurred_at) "
        "RETURNING id::text"
    ), {"tenant": _tenant(principal), "incident": payload.get("incident_id"), "vehicle": payload["vehicle_id"],
        "provider_type": payload["provider_type"], "provider_name": payload["provider_name"],
        "location": payload.get("location"), "cost": payload.get("cost", 0),
        "response_minutes": payload.get("response_minutes"), "occurred_at": payload["occurred_at"]}).scalar_one()
    db.commit()
    return {"id": row, "status": "completed"}


@router.get("/api/v1/field/tyre-analytics")
def tyre_analytics(principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    tenant = _tenant(principal)
    driver_rows = db.execute(text(
        "SELECT i.driver_id::text, coalesce(d.name, 'Bilinmiyor') AS driver_name, count(*)::int incidents, "
        "coalesce(sum(i.damage_cost),0) AS damage_cost FROM tyre_incidents i LEFT JOIN drivers d ON d.id=i.driver_id "
        "WHERE i.tenant_id::text=:tenant GROUP BY i.driver_id,d.name ORDER BY incidents DESC"
    ), {"tenant": tenant}).mappings().all()
    vehicle_rows = db.execute(text(
        "SELECT i.vehicle_id::text, v.plate, count(*)::int incidents, coalesce(sum(i.damage_cost),0) AS damage_cost "
        "FROM tyre_incidents i JOIN vehicles v ON v.id=i.vehicle_id WHERE i.tenant_id::text=:tenant "
        "GROUP BY i.vehicle_id,v.plate ORDER BY incidents DESC"
    ), {"tenant": tenant}).mappings().all()
    routes = db.execute(text(
        "SELECT coalesce(route,'Bilinmiyor') route, count(*)::int incidents FROM tyre_incidents "
        "WHERE tenant_id::text=:tenant GROUP BY route ORDER BY incidents DESC"
    ), {"tenant": tenant}).mappings().all()
    durability = db.execute(text(
        "SELECT coalesce(brand,'Bilinmiyor') brand, coalesce(model,'Bilinmiyor') model, count(*)::int incidents, "
        "round(avg(damage_cost),2) average_damage_cost FROM tyre_incidents WHERE tenant_id::text=:tenant "
        "GROUP BY brand,model ORDER BY incidents ASC"
    ), {"tenant": tenant}).mappings().all()
    return {"drivers": [dict(row) for row in driver_rows], "vehicles": [dict(row) for row in vehicle_rows],
            "routes": [dict(row) for row in routes], "durability": [dict(row) for row in durability]}


@router.get("/api/v1/field/fuel-anomalies")
def fuel_anomalies(principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT f.id::text, f.vehicle_id::text, v.plate, f.liters, f.odometer_km, f.transaction_at, "
        "v.consumption_100km, CASE WHEN f.liters > coalesce(v.fuel_capacity_l, 1000) * .8 THEN 'large_fill' "
        "WHEN f.liters > coalesce(v.consumption_100km, 35) * 2 THEN 'high_consumption' ELSE 'review' END anomaly_type "
        "FROM fuel_transactions f JOIN vehicles v ON v.id=f.vehicle_id WHERE v.tenant_id::text=:tenant "
        "AND f.transaction_at >= now() - interval '30 days' ORDER BY f.transaction_at DESC"
    ), {"tenant": _tenant(principal)}).mappings().all()
    return {"anomalies": [dict(row) for row in rows if row["anomaly_type"] != "review"], "checked_transactions": len(rows)}


@router.get("/api/v1/field/drivers/{driver_id}/eco-score")
def driver_eco_score(driver_id: str, principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    tenant = _tenant(principal)
    hard_events = db.execute(text(
        "SELECT count(*)::int FROM telemetry_events e JOIN vehicles v ON v.id=e.vehicle_id "
        "WHERE v.tenant_id::text=:tenant AND v.current_driver_id::text=:driver AND "
        "(e.speed_kmh > 90 OR e.payload ILIKE '%harsh_brake%' OR e.payload ILIKE '%idle%')"
    ), {"tenant": tenant, "driver": driver_id}).scalar_one()
    tyre_events = db.execute(text(
        "SELECT count(*)::int FROM tyre_incidents WHERE tenant_id::text=:tenant AND driver_id::text=:driver "
        "AND occurred_at >= now() - interval '7 days'"
    ), {"tenant": tenant, "driver": driver_id}).scalar_one()
    score = max(0, min(100, 100 - hard_events * 2 - tyre_events * 10))
    return {"driver_id": driver_id, "period": "last_7_days", "score": score,
            "hard_event_count": hard_events, "tyre_incident_count": tyre_events,
            "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"}


@router.post("/api/v1/trips/{trip_id}/tracking-link")
def create_tracking_link(trip_id: str, principal: dict = Depends(require_roles("super_admin", "admin", "head_driver")), db: Session = Depends(get_db)):
    exists = db.execute(text("SELECT 1 FROM trips WHERE id::text=:trip AND tenant_id::text=:tenant"), {"trip": trip_id, "tenant": _tenant(principal)}).scalar_one_or_none()
    if not exists:
        raise HTTPException(404, "Sefer bulunamadı.")
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.execute(text(
        "INSERT INTO customer_tracking_links (tenant_id, trip_id, token_hash, expires_at) "
        "VALUES (CAST(:tenant AS uuid), CAST(:trip AS uuid), :hash, :expires)"
    ), {"tenant": _tenant(principal), "trip": trip_id, "hash": hashlib.sha256(token.encode()).hexdigest(), "expires": expires})
    db.commit()
    return {"trip_id": trip_id, "token": token, "expires_at": expires, "url": "/api/v1/tracking/public/" + token}


@router.get("/api/v1/tracking/public/{token}")
def public_tracking(token: str, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = db.execute(text(
        "SELECT l.trip_id::text, l.expires_at, t.vehicle_id::text, v.plate, v.device_no, "
        "e.latitude, e.longitude, e.speed_kmh, e.recorded_at FROM customer_tracking_links l "
        "JOIN trips t ON t.id=l.trip_id JOIN vehicles v ON v.id=t.vehicle_id LEFT JOIN LATERAL "
        "(SELECT * FROM telemetry_events x WHERE x.vehicle_id=v.id ORDER BY x.recorded_at DESC LIMIT 1) e ON true "
        "WHERE l.token_hash=:hash AND l.revoked_at IS NULL AND l.expires_at > now()"
    ), {"hash": token_hash}).mappings().first()
    if not row:
        raise HTTPException(404, "Takip bağlantısı geçersiz veya süresi dolmuş.")
    return {"trip_id": row["trip_id"], "eta_minutes": max(0, int(180 - (row["speed_kmh"] or 0))),
            "vehicle": dict(row)}


@router.get("/api/v1/field/vehicles/{vehicle_id}/tires")
def vehicle_tires(vehicle_id: str, principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT t.id::text, t.position, t.serial_no, t.brand, t.tread_mm, t.status, "
        "(SELECT max(rotated_at) FROM tire_rotations r WHERE r.tire_id=t.id) last_rotation "
        "FROM tires t JOIN vehicles v ON v.id=t.vehicle_id WHERE t.vehicle_id::text=:vehicle AND v.tenant_id::text=:tenant "
        "ORDER BY t.position"
    ), {"vehicle": vehicle_id, "tenant": _tenant(principal)}).mappings().all()
    return {"vehicle_id": vehicle_id, "schema": "tractor-trailer-axle-grid", "tires": [dict(row) for row in rows]}


@router.post("/api/v1/field/tires/{tire_id}/rotation", status_code=201)
def rotate_tire(tire_id: str, payload: dict, principal: dict = Depends(require_roles("super_admin", "admin", "head_driver")), db: Session = Depends(get_db)):
    row = db.execute(text(
        "INSERT INTO tire_rotations (tenant_id, tire_id, vehicle_id, from_position, to_position, rotated_at, odometer_km) "
        "SELECT CAST(:tenant AS uuid), t.id, t.vehicle_id, :from_position, :to_position, :rotated_at, :odometer "
        "FROM tires t JOIN vehicles v ON v.id=t.vehicle_id WHERE t.id::text=:tire AND v.tenant_id::text=:tenant "
        "RETURNING id::text"
    ), {"tenant": _tenant(principal), "tire": tire_id, "from_position": payload["from_position"],
        "to_position": payload["to_position"], "rotated_at": payload.get("rotated_at", datetime.now(timezone.utc)),
        "odometer": payload.get("odometer_km")}).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Lastik bulunamadı.")
    db.commit()
    return {"id": row, "status": "recorded"}
