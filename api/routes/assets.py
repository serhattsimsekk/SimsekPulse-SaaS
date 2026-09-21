from __future__ import annotations

import base64
import os
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.security import current_principal, require_roles
from database.models import AssetDocument
from services.arvento_service import ARVENTO_REPORT_URL, ArventoConfigurationError, ArventoRequestError, client_from_settings, fetch_live, mask_secret
from services.compliance import expiry_status

router = APIRouter(tags=["Filo Evrak & Arvento"])
ALLOWED_LOGO_TYPES = {"image/svg+xml", "image/png", "image/jpeg", "image/webp"}


@router.get("/api/v1/branding/{tenant_code}")
def public_branding(tenant_code: str, db: Session = Depends(get_db)):
    row = db.execute(text(
        "SELECT code, logo_data, logo_content_type FROM tenants "
        "WHERE code = :code AND is_active = true"
    ), {"code": tenant_code}).mappings().first()
    if not row:
        raise HTTPException(404, "Şirket bulunamadı.")
    return {"tenant_code": row["code"], "logo_data": row["logo_data"], "content_type": row["logo_content_type"]}


@router.put("/api/v1/branding/logo")
async def upload_branding_logo(
    file: UploadFile = File(...),
    principal: dict = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(415, "SVG, PNG, JPEG veya WEBP logo yükleyin.")
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "Logo 2 MB sınırını aşamaz.")
    encoded = "data:" + file.content_type + ";base64," + base64.b64encode(content).decode("ascii")
    db.execute(text(
        "UPDATE tenants SET logo_data = :logo, logo_content_type = :content_type WHERE id = CAST(:tenant_id AS uuid)"
    ), {"logo": encoded, "content_type": file.content_type, "tenant_id": principal["tenant_id"]})
    db.commit()
    return {"status": "updated", "logo_data": encoded}


@router.post("/api/v1/fleet/documents", status_code=201)
def create_asset_document(
    payload: dict,
    principal: dict = Depends(require_roles("super_admin", "admin", "head_driver")),
    db: Session = Depends(get_db),
):
    required = {"asset_type", "document_type", "expires_on"}
    if missing := required - payload.keys():
        raise HTTPException(422, f"Eksik alanlar: {', '.join(sorted(missing))}")
    if payload["asset_type"] not in {"vehicle", "trailer"}:
        raise HTTPException(422, "asset_type vehicle veya trailer olmalıdır.")
    if payload["asset_type"] == "vehicle" and not payload.get("vehicle_id"):
        raise HTTPException(422, "Araç evrakı için vehicle_id zorunludur.")
    if payload["asset_type"] == "trailer" and not payload.get("trailer_id"):
        raise HTTPException(422, "Dorse evrakı için trailer_id zorunludur.")
    document = AssetDocument(
        tenant_id=principal["tenant_id"], asset_type=payload["asset_type"],
        vehicle_id=payload.get("vehicle_id"), trailer_id=payload.get("trailer_id"),
        document_type=payload["document_type"], expires_on=date.fromisoformat(payload["expires_on"]),
        document_uri=payload.get("document_uri"),
    )
    document.status = expiry_status(document.expires_on)["warning"]
    db.add(document)
    db.commit()
    db.refresh(document)
    return {"id": document.id, "status": document.status, "days_remaining": expiry_status(document.expires_on)["days_remaining"]}


@router.get("/api/v1/fleet/document-alerts")
def asset_document_alerts(principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT d.id::text, d.asset_type, d.document_type, d.expires_on, "
        "coalesce(v.plate, t.plate) AS plate "
        "FROM asset_documents d LEFT JOIN vehicles v ON v.id = d.vehicle_id "
        "LEFT JOIN trailers t ON t.id = d.trailer_id WHERE d.tenant_id::text = :tenant "
        "AND d.expires_on <= CURRENT_DATE + 10 ORDER BY d.expires_on"
    ), {"tenant": principal["tenant_id"]}).mappings().all()
    alerts = []
    for row in rows:
        status = expiry_status(row["expires_on"])
        alerts.append({**dict(row), **status, "severity": "critical" if status["days_remaining"] <= 3 else "warning"})
    return {"critical_count": sum(item["severity"] == "critical" for item in alerts), "alerts": alerts}


@router.put("/api/v1/fleet/vehicles/{vehicle_id}/ownership")
def update_vehicle_ownership(
    vehicle_id: str,
    payload: dict,
    principal: dict = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    if payload.get("ownership_status") not in {"owned", "for_sale", "sold", "transferred"}:
        raise HTTPException(422, "Geçersiz ownership_status.")
    result = db.execute(text(
        "UPDATE vehicles SET ownership_status = :status, sale_date = CAST(:sale_date AS date), "
        "sale_amount = :sale_amount, status = CASE WHEN :status IN ('sold','transferred') THEN 'inactive' ELSE status END "
        "WHERE id::text = :vehicle_id AND tenant_id::text = :tenant RETURNING id::text, plate, ownership_status, status"
    ), {"status": payload["ownership_status"], "sale_date": payload.get("sale_date"),
        "sale_amount": payload.get("sale_amount"), "vehicle_id": vehicle_id, "tenant": principal["tenant_id"]}).mappings().first()
    if not result:
        raise HTTPException(404, "Araç bulunamadı.")
    db.commit()
    return dict(result)


def _arvento_settings(db: Session, tenant_id: str) -> dict:
    row = db.execute(text(
        "SELECT arvento_api_url, arvento_username, arvento_password, arvento_api_token, arvento_pin "
        "FROM tenants WHERE id::text = :tenant"
    ), {"tenant": tenant_id}).mappings().first()
    return {key: row[column] if row else None for key, column in (
        ("api_url", "arvento_api_url"), ("username", "arvento_username"),
        ("password", "arvento_password"), ("api_token", "arvento_api_token"), ("pin", "arvento_pin"),
    )}


def _arvento_request(path: str, method: str = "GET", payload: dict | None = None, settings: dict | None = None) -> dict:
    try:
        client = client_from_settings(settings or {})
        if path == "/vehicles":
            return client.get_vehicle_status_v3()
        raise ArventoRequestError(f"Desteklenmeyen Arvento SOAP işlemi: {path}")
    except ArventoConfigurationError as exc:
        return {"configured": False, "message": str(exc), "data": []}
    except ArventoRequestError as exc:
        return {"configured": True, "error": str(exc), "data": []}


@router.get("/api/v1/arvento/settings")
def get_arvento_settings(principal: dict = Depends(require_roles("super_admin", "admin")), db: Session = Depends(get_db)):
    settings = _arvento_settings(db, principal["tenant_id"])
    return {"api_url": ARVENTO_REPORT_URL, "username": settings["username"],
            "password_configured": bool(settings["password"]),
            "api_token": mask_secret(settings["api_token"]), "pin": mask_secret(settings["pin"])}


@router.put("/api/v1/arvento/settings")
def update_arvento_settings(payload: dict, principal: dict = Depends(require_roles("super_admin", "admin")), db: Session = Depends(get_db)):
    if not payload.get("username") or not payload.get("password"):
        raise HTTPException(422, "Arvento kullanıcı adı ve şifresi zorunludur.")
    db.execute(text(
        "UPDATE tenants SET arvento_api_url = :api_url, arvento_username = :username, "
        "arvento_password = :password, arvento_api_token = :api_token, arvento_pin = :pin WHERE id::text = :tenant"
    ), {"api_url": ARVENTO_REPORT_URL, "username": payload["username"], "password": payload["password"],
        "api_token": payload.get("api_token") or None, "pin": payload.get("pin") or None,
        "tenant": principal["tenant_id"]})
    db.commit()
    return {"status": "updated", "api_token_configured": bool(payload.get("api_token")),
            "pin_configured": bool(payload.get("pin"))}


@router.get("/api/v1/arvento/live")
def arvento_live(principal: dict = Depends(current_principal), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT v.id::text, v.plate, v.device_no, e.latitude, e.longitude, e.speed_kmh, "
        "e.engine_on, e.recorded_at FROM vehicles v LEFT JOIN LATERAL ("
        "SELECT * FROM telemetry_events x WHERE x.vehicle_id = v.id ORDER BY x.recorded_at DESC LIMIT 1"
        ") e ON true WHERE v.tenant_id::text = :tenant AND v.ownership_status = 'owned'"
    ), {"tenant": principal["tenant_id"]}).mappings().all()
    provider = fetch_live(_arvento_settings(db, principal["tenant_id"]), [dict(row) for row in rows])
    live_vehicles = provider.get("vehicles", []) if isinstance(provider, dict) else []
    return {"provider": provider, "vehicles": live_vehicles or [dict(row) for row in rows],
            "live_vehicle_count": len(live_vehicles), "map_connected": bool(live_vehicles),
            "mode": provider.get("mode", "unknown")}


@router.post("/api/v1/arvento/groups/sync")
def sync_arvento_groups(
    payload: dict,
    principal: dict = Depends(require_roles("super_admin", "admin", "head_driver")),
):
    groups = payload.get("groups", [])
    if not isinstance(groups, list):
        raise HTTPException(422, "groups liste olmalıdır.")
    return {"tenant_id": principal["tenant_id"],
            "groups": [{"group": group, "mode": "simulation", "status": "synced",
                        "log": f"Fleet Simulator group updated: {group.get('name', 'unnamed')}"} for group in groups],
            "synced": True, "mode": "simulation"}
