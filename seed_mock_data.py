from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from database.session import SessionLocal


def seed_mock_data() -> None:
    """Populate the master tenant with repeatable records for every operations module."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        tenant_id = db.execute(text("SELECT id FROM tenants WHERE code = 'master'")).scalar_one()
        admin_id = db.execute(
            text("SELECT id FROM users WHERE tenant_id = :tenant AND username = 'admin@simseklog.com'"),
            {"tenant": tenant_id},
        ).scalar_one()

        drivers: list[str] = []
        for employee_no, name, phone, shift in [
            ("DRV-001", "Murat Yılmaz", "+90 532 000 0001", "08:00-16:00"),
            ("DRV-002", "Ayşe Demir", "+90 532 000 0002", "16:00-00:00"),
            ("DRV-003", "Mehmet Kaya", "+90 532 000 0003", "00:00-08:00"),
        ]:
            driver_id = db.execute(
                text(
                    "INSERT INTO drivers (tenant_id, employee_no, name, phone, shift, license_no, license_expiry, src_expiry) "
                    "SELECT :tenant, :employee, :name, :phone, :shift, :license, CURRENT_DATE + 300, CURRENT_DATE + 180 "
                    "WHERE NOT EXISTS (SELECT 1 FROM drivers WHERE tenant_id = :tenant AND employee_no = :employee) "
                    "RETURNING id"
                ),
                {"tenant": tenant_id, "employee": employee_no, "name": name, "phone": phone, "shift": shift, "license": f"LIC-{employee_no}"},
            ).scalar_one_or_none()
            if driver_id is None:
                driver_id = db.execute(
                    text("SELECT id FROM drivers WHERE tenant_id = :tenant AND employee_no = :employee"),
                    {"tenant": tenant_id, "employee": employee_no},
                ).scalar_one()
            drivers.append(str(driver_id))

        vehicles = db.execute(
            text("SELECT id, plate FROM vehicles WHERE tenant_id = :tenant ORDER BY plate LIMIT 4"),
            {"tenant": tenant_id},
        ).all()
        if len(vehicles) < 4:
            raise RuntimeError("Master tenant must have the simulator vehicles before mock data is seeded.")

        customer_id = db.execute(
            text(
                "INSERT INTO customers (tenant_id, name, tax_number, contact_name, contact_phone, address) "
                "SELECT :tenant, 'Marmara Lojistik A.Ş.', '1111111111', 'Elif Çetin', '+90 212 000 0011', 'İstanbul' "
                "WHERE NOT EXISTS (SELECT 1 FROM customers WHERE tenant_id = :tenant AND tax_number = '1111111111') RETURNING id"
            ),
            {"tenant": tenant_id},
        ).scalar_one_or_none()
        if customer_id is None:
            customer_id = db.execute(text("SELECT id FROM customers WHERE tenant_id = :tenant AND tax_number = '1111111111'"), {"tenant": tenant_id}).scalar_one()

        contract_id = db.execute(
            text(
                "INSERT INTO freight_contracts (tenant_id, customer_id, contract_no, route, unit_price_ton, status, valid_from) "
                "SELECT :tenant, :customer, 'FRT-2026-001', 'Marmara Hatları', 1850, 'active', CURRENT_DATE "
                "WHERE NOT EXISTS (SELECT 1 FROM freight_contracts WHERE tenant_id = :tenant AND contract_no = 'FRT-2026-001') RETURNING id"
            ),
            {"tenant": tenant_id, "customer": customer_id},
        ).scalar_one_or_none()
        if contract_id is None:
            contract_id = db.execute(text("SELECT id FROM freight_contracts WHERE tenant_id = :tenant AND contract_no = 'FRT-2026-001'"), {"tenant": tenant_id}).scalar_one()

        trip_ids: list[str] = []
        for index, (vehicle_id, driver_id, route, status, planned, realized) in enumerate([
            (vehicles[0].id, drivers[0], "Ambarlı Limanı → Gebze Fabrika", "in_progress", 24, 16),
            (vehicles[1].id, drivers[1], "Ankara → İstanbul", "assigned", 18, 0),
            (vehicles[2].id, drivers[2], "İzmir → Bursa", "completed", 22, 22),
        ]):
            trip_id = db.execute(
                text(
                    "INSERT INTO trips (tenant_id, customer_id, contract_id, vehicle_id, driver_id, route, status, planned_ton, realized_ton, started_at) "
                    "SELECT :tenant, :customer, :contract, :vehicle, :driver, :route, :status, :planned, :realized, :started "
                    "WHERE NOT EXISTS (SELECT 1 FROM trips WHERE tenant_id = :tenant AND route = :route AND started_at::date = CURRENT_DATE) RETURNING id"
                ),
                {"tenant": tenant_id, "customer": customer_id, "contract": contract_id, "vehicle": vehicle_id, "driver": driver_id, "route": route, "status": status, "planned": planned, "realized": realized, "started": now - timedelta(hours=index * 3)},
            ).scalar_one_or_none()
            if trip_id is None:
                trip_id = db.execute(text("SELECT id FROM trips WHERE tenant_id = :tenant AND route = :route AND started_at::date = CURRENT_DATE"), {"tenant": tenant_id, "route": route}).scalar_one()
            trip_ids.append(str(trip_id))

        for vehicle, coords in zip(vehicles, [(41.005, 28.978), (40.766, 29.940), (38.423, 27.142), (40.765, 29.940)]):
            db.execute(
                text(
                    "INSERT INTO telemetry_events (vehicle_id, recorded_at, latitude, longitude, speed_kmh, fuel_percent, engine_on) "
                    "SELECT :vehicle, :recorded, :lat, :lng, :speed, :fuel, :engine "
                    "WHERE NOT EXISTS (SELECT 1 FROM telemetry_events WHERE vehicle_id = :vehicle AND recorded_at::date = CURRENT_DATE)"
                ),
                {"vehicle": vehicle.id, "recorded": now, "lat": coords[0], "lng": coords[1], "speed": 52 if vehicle.plate != "06 SIM 002" else 0, "fuel": 64, "engine": vehicle.plate != "06 SIM 002"},
            )

        db.execute(
            text(
                "INSERT INTO wait_events (trip_id, vehicle_id, location_type, location_name, started_at, free_minutes, rate_per_hour, demurrage_amount, status) "
                "SELECT :trip, :vehicle, 'port', 'Ambarlı Limanı', :started, 120, 1850, 18500, 'open' "
                "WHERE NOT EXISTS (SELECT 1 FROM wait_events WHERE vehicle_id = :vehicle AND location_name = 'Ambarlı Limanı' AND status = 'open')"
            ),
            {"tenant": tenant_id, "trip": trip_ids[0], "vehicle": vehicles[0].id, "started": now - timedelta(hours=4)},
        )
        for sku, name, stock, critical, cost in [("FLT-001", "Yağ filtresi", 18, 10, 420), ("TYR-295", "315/80 R22.5 lastik", 4, 8, 9500)]:
            db.execute(
                text(
                    "INSERT INTO parts (tenant_id, sku, name, unit, stock_quantity, critical_quantity, unit_cost) "
                    "SELECT :tenant, :sku, :name, 'adet', :stock, :critical, :cost "
                    "WHERE NOT EXISTS (SELECT 1 FROM parts WHERE tenant_id = :tenant AND sku = :sku)"
                ),
                {"tenant": tenant_id, "sku": sku, "name": name, "stock": stock, "critical": critical, "cost": cost},
            )
        db.execute(
            text(
                "INSERT INTO maintenance_issues (vehicle_id, reported_by_driver_id, category, urgency, parts_needed, estimated_cost, layup_days, status) "
                "SELECT :vehicle, :driver, 'Lastik basıncı', 'high', '315/80 R22.5 lastik', 12500, 1, 'open' "
                "WHERE NOT EXISTS (SELECT 1 FROM maintenance_issues WHERE vehicle_id = :vehicle AND category = 'Lastik basıncı' AND status = 'open')"
            ),
            {"vehicle": vehicles[0].id, "driver": drivers[0]},
        )
        db.execute(
            text(
                "INSERT INTO inspections (vehicle_id, inspection_type, due_date, status) "
                "SELECT :vehicle, 'Muayene', CURRENT_DATE + 8, 'upcoming' "
                "WHERE NOT EXISTS (SELECT 1 FROM inspections WHERE vehicle_id = :vehicle AND inspection_type = 'Muayene' AND due_date > CURRENT_DATE)"
            ),
            {"vehicle": vehicles[1].id},
        )
        db.execute(
            text(
                "INSERT INTO fuel_transactions (vehicle_id, driver_id, liters, unit_price, odometer_km, station, transaction_at) "
                "SELECT :vehicle, :driver, 420, 47.25, 120450, 'Opet Gebze', :at "
                "WHERE NOT EXISTS (SELECT 1 FROM fuel_transactions WHERE vehicle_id = :vehicle AND station = 'Opet Gebze' AND transaction_at::date = CURRENT_DATE)"
            ),
            {"vehicle": vehicles[0].id, "driver": drivers[0], "at": now},
        )
        db.execute(
            text(
                "INSERT INTO expenses (tenant_id, trip_id, vehicle_id, category, amount, description, incurred_at) "
                "SELECT :tenant, :trip, :vehicle, 'fuel', 19845, 'Örnek yakıt maliyeti', :at "
                "WHERE NOT EXISTS (SELECT 1 FROM expenses WHERE tenant_id = :tenant AND description = 'Örnek yakıt maliyeti' AND incurred_at::date = CURRENT_DATE)"
            ),
            {"tenant": tenant_id, "trip": trip_ids[0], "vehicle": vehicles[0].id, "at": now},
        )
        db.execute(
            text(
                "INSERT INTO notification_logs (tenant_id, user_id, channel, recipient, title, message, status) "
                "SELECT :tenant, :user, 'system', 'admin@simseklog.com', 'Demuraj uyarısı', 'Ambarlı Limanı bekleme süresi aşıldı.', 'sent' "
                "WHERE NOT EXISTS (SELECT 1 FROM notification_logs WHERE tenant_id = :tenant AND title = 'Demuraj uyarısı' AND created_at::date = CURRENT_DATE)"
            ),
            {"tenant": tenant_id, "user": admin_id},
        )
        db.commit()


if __name__ == "__main__":
    seed_mock_data()
    print("MOCK_DATA_SEEDED=true")
