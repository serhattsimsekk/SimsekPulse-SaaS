from __future__ import annotations

import os
import secrets

from sqlalchemy import text

from database.session import SessionLocal
from services.security import hash_password


def seed_master_admin() -> tuple[str, str, str, str]:
    tenant_code = os.getenv("MASTER_TENANT_CODE", "master").strip().lower()
    email = os.getenv("MASTER_ADMIN_EMAIL", "admin@simseklog.com").strip().lower()
    password = os.getenv("ADMIN_SEED_PASSWORD") or os.getenv("MASTER_ADMIN_PASSWORD") or secrets.token_urlsafe(18)
    with SessionLocal() as db:
        tenant_id = db.execute(
            text("SELECT id::text FROM tenants WHERE LOWER(code) = :code"),
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
        # `users` tablosunda tenant_id bazlı Row-Level Security politikası
        # var (bkz. database/migrations/001_initial_schema.sql). Bu betik
        # herhangi bir HTTP isteği/JWT bağlamı olmadan çalıştığından
        # "app.tenant_id" Postgres oturum değişkeni hiç ayarlanmaz; bu da
        # RLS'nin INSERT/UPDATE'i sessizce engellemesine (WITH CHECK ihlali)
        # yol açar. Bu yüzden ilgili tenant için işlem-yerel olarak açıkça
        # set ediyoruz.
        db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )
        # Her uygulama başlangıcında (app.py lifespan) çalıştığından, bu
        # INSERT/ON CONFLICT DO UPDATE hem hesabı oluşturur hem de daha
        # önce (ör. hatalı giriş denemeleri yüzünden) kilitlenmiş olabilecek
        # hesabı otomatik olarak açar ve şifreyi her zaman .env'deki
        # ADMIN_SEED_PASSWORD ile senkron tutar; böylece master admin girişi
        # manuel bir script/komut çalıştırmaya gerek kalmadan kendi kendini
        # onarır.
        db.execute(text(
            "INSERT INTO users (tenant_id, name, username, role, department, password_hash, is_active, "
            "failed_login_attempts, locked_until) "
            "VALUES (CAST(:tenant_id AS uuid), :name, :username, 'super_admin', 'executive', :password_hash, true, 0, NULL) "
            "ON CONFLICT (tenant_id, username) DO UPDATE SET role = 'super_admin', department = 'executive', "
            "is_active = true, password_hash = :password_hash, failed_login_attempts = 0, locked_until = NULL"
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
        # Bu, ayrı bir oturum/işlem olduğu için "app.tenant_id" burada da
        # ayrıca ayarlanmalı (yukarıdaki açıklamayla aynı RLS gerekçesi).
        db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )
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
    from dotenv import load_dotenv

    load_dotenv()
    tenant_id, tenant_code, email, password = seed_master_admin()
    print("MASTER_TENANT_ID=" + tenant_id)
    print("MASTER_TENANT_CODE=" + tenant_code)
    print("MASTER_ADMIN_EMAIL=" + email)
    print("MASTER_ADMIN_PASSWORD=" + password)
