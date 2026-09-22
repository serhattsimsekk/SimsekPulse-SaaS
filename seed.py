from __future__ import annotations

import os
import secrets

from sqlalchemy import text

from database.session import SessionLocal
from services.security import hash_password


def seed_master_admin() -> tuple[str, str, str, str]:
    tenant_code = os.getenv("MASTER_TENANT_CODE", "master")
    email = os.getenv("MASTER_ADMIN_EMAIL", "admin@simseklog.com")
    password = os.getenv("ADMIN_SEED_PASSWORD") or os.getenv("MASTER_ADMIN_PASSWORD") or secrets.token_urlsafe(18)
    with SessionLocal() as db:
        tenant_id = db.execute(
            text("SELECT id::text FROM tenants WHERE code = :code"),
            {"code": tenant_code},
        ).scalar_one_or_none()
        if tenant_id is None:
            tenant_id = db.execute(text(
                "INSERT INTO tenants (name, code, is_active, subscription_status) "
                "VALUES (:name, :code, true, 'active') "
                "RETURNING id::text"
            ), {"name": "ŞimşekLog SaaS Master", "code": tenant_code}).scalar_one()
        else:
            db.execute(text(
                "UPDATE tenants SET is_active = true, subscription_status = 'active' "
                "WHERE id = CAST(:tenant_id AS uuid)"
            ), {"tenant_id": tenant_id})
        db.execute(text(
            "INSERT INTO users (tenant_id, name, username, role, department, password_hash, is_active) "
            "VALUES (CAST(:tenant_id AS uuid), :name, :username, 'super_admin', 'executive', :password_hash, true) "
            "ON CONFLICT (tenant_id, username) DO UPDATE SET role = 'super_admin', department = 'executive', is_active = true, password_hash = :password_hash"
        ), {"tenant_id": tenant_id, "name": "SaaS Master Admin", "username": email, "password_hash": hash_password(password)})
        db.commit()
        seed_simulator_vehicles(tenant_id)
        return tenant_id, tenant_code, email, password


def seed_simulator_vehicles(tenant_id: str) -> None:
    vehicles = [
        ("34 SIM 001", "İstanbul İçİ", "SIM-IST-001"),
        ("06 SIM 002", "Ankara İçİ", "SIM-ANK-002"),
        ("35 SIM 003", "İzmir İçİ", "SIM-IZM-003"),
        ("41 SIM 004", "Marmara", "SIM-MAR-004"),
    ]
    with SessionLocal() as db:
        for plate, status, device_no in vehicles:
            db.execute(text(
                "INSERT INTO vehicles (tenant_id, plate, vehicle_type, brand, model, device_no, status, "
                "odometer_km, ownership_status) VALUES (CAST(:tenant AS uuid), :plate, 'tractor', "
                "'Simulation', 'Fleet Test', :device_no, :status, 120000, 'owned') "
                "ON CONFLICT (tenant_id, plate) DO UPDATE SET device_no = EXCLUDED.device_no, "
                "status = EXCLUDED.status, ownership_status = 'owned'"
            ), {"tenant": tenant_id, "plate": plate, "status": status, "device_no": device_no})
        db.commit()


if __name__ == "__main__":
    tenant_id, tenant_code, email, password = seed_master_admin()
    print("MASTER_TENANT_ID=" + tenant_id)
    print("MASTER_TENANT_CODE=" + tenant_code)
    print("MASTER_ADMIN_EMAIL=" + email)
    print("MASTER_ADMIN_PASSWORD=" + password)
