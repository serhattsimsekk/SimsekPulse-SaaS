#!/usr/bin/env python3
"""
Seed script for SimsekLog multi-tenant system.
Populates tenants, users, drivers, vehicles, shifts, OCR records, and workbooks.
Run with: python scripts/seed_database.py
"""

import os
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from database.session import DATABASE_URL
from database.base import Base, tenant_context
from database.models import (
    Tenant, User, Driver, Vehicle, Trailer, Trip, Customer, 
    ShiftLog, WeighbridgeReceipt, AuditLog
)
from database.models_extended import (
    DriverShift, VehicleAssignment, VehicleMaintenanceSchedule, VehiclePeriodicDoc,
    WeighbridgeOCRRecord, DriverFieldReceipt, WorkbookSheet, WorkbookCellChange, WorkbookSyncState
)
from services.security import hash_password


def seed_database():
    """Seed all base data for testing and demo."""
    engine = create_engine(DATABASE_URL, future=True)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    
    try:
        # ============ TENANTS ============
        tenant1 = Tenant(
            id=str(uuid.uuid4()),
            name="Öztrans Lojistik A.Ş.",
            code="OZTRANS",
            tax_number="1234567890",
            is_active=True,
            subscription_status="active"
        )
        tenant2 = Tenant(
            id=str(uuid.uuid4()),
            name="Anadolu Kargo Ltd.",
            code="ANADOLU",
            tax_number="0987654321",
            is_active=True,
            subscription_status="active"
        )
        session.add_all([tenant1, tenant2])
        session.commit()
        print("✓ Tenants created")
        
        # ============ USERS (Tenant 1) ============
        marker = tenant_context.set(tenant1.id)
        try:
            # Admin
            admin_user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                name="Ahmet Yönetici",
                username="admin",
                role="admin",
                department="executive",
                password_hash=hash_password("admin123"),
                is_active=True
            )
            
            # HR Officer
            hr_user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                name="Ayşe İK",
                username="hr_officer",
                role="hr_officer",
                department="hr",
                password_hash=hash_password("hr123"),
                is_active=True
            )
            
            # Chief Driver
            chief_driver_user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                name="Mehmet Baş Şoför",
                username="chief_driver",
                role="chief_driver",
                department="operations",
                password_hash=hash_password("chief123"),
                is_active=True
            )
            
            # Operations
            ops_user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                name="Fatma Sevkiyat",
                username="operations",
                role="operations",
                department="operations",
                password_hash=hash_password("ops123"),
                is_active=True
            )
            
            # Finance
            finance_user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                name="İbrahim Muhasebeci",
                username="finance",
                role="finance",
                department="finance",
                password_hash=hash_password("fin123"),
                is_active=True
            )
            
            # Driver Portal User
            driver_user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                name="Ali Şoför",
                username="driver_ali",
                role="driver",
                department="driver",
                password_hash=hash_password("driver123"),
                is_active=True
            )
            
            session.add_all([admin_user, hr_user, chief_driver_user, ops_user, finance_user, driver_user])
            session.commit()
            print("✓ Users created for Tenant 1")
            
            # ============ DRIVERS ============
            driver1 = Driver(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                employee_no="DRV001",
                name="Ali Şoför",
                phone="+905551234567",
                status="active",
                shift="morning",
                license_no="LIC001",
                license_expiry=date.today() + timedelta(days=365),
                penalty_points=0,
                blacklisted=False,
                fatigue_percentage=Decimal("45.5"),
                tachograph_remaining_hours=Decimal("9.5")
            )
            
            driver2 = Driver(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                employee_no="DRV002",
                name="Veli Şoför",
                phone="+905559876543",
                status="active",
                shift="evening",
                license_no="LIC002",
                license_expiry=date.today() + timedelta(days=200),
                penalty_points=2,
                blacklisted=False,
                fatigue_percentage=Decimal("65.0"),
                tachograph_remaining_hours=Decimal("7.0")
            )
            
            driver3 = Driver(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                employee_no="DRV003",
                name="Deli Şoför",
                phone="+905555554444",
                status="active",
                shift="night",
                license_no="LIC003",
                license_expiry=date.today() + timedelta(days=100),
                penalty_points=0,
                blacklisted=False,
                fatigue_percentage=Decimal("30.0"),
                tachograph_remaining_hours=Decimal("11.0")
            )
            
            session.add_all([driver1, driver2, driver3])
            session.commit()
            print("✓ Drivers created for Tenant 1")
            
            # ============ VEHICLES ============
            vehicle1 = Vehicle(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                plate="OZTRANS01",
                vehicle_type="tractor",
                brand="Volvo",
                model="FH16",
                model_year=2020,
                vin="VIN001",
                device_no="DEV001",
                status="active",
                odometer_km=150000,
                fuel_capacity_l=Decimal("500.00"),
                consumption_100km=Decimal("32.5"),
                current_driver_id=driver1.id,
                insurance_expiry=date.today() + timedelta(days=150),
                inspection_expiry=date.today() + timedelta(days=90)
            )
            
            vehicle2 = Vehicle(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                plate="OZTRANS02",
                vehicle_type="tractor",
                brand="Scania",
                model="R440",
                model_year=2019,
                vin="VIN002",
                device_no="DEV002",
                status="active",
                odometer_km=200000,
                fuel_capacity_l=Decimal("450.00"),
                consumption_100km=Decimal("31.0"),
                current_driver_id=driver2.id,
                insurance_expiry=date.today() + timedelta(days=200),
                inspection_expiry=date.today() + timedelta(days=120)
            )
            
            session.add_all([vehicle1, vehicle2])
            session.commit()
            print("✓ Vehicles created for Tenant 1")
            
            # ============ TRAILERS ============
            trailer1 = Trailer(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                plate="OZTRANS-T01",
                trailer_type="dry_goods",
                capacity_ton=Decimal("20.0"),
                hex_color="#FF6B6B",
                status="available"
            )
            
            session.add(trailer1)
            session.commit()
            print("✓ Trailers created for Tenant 1")
            
            # ============ CUSTOMERS ============
            customer1 = Customer(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                name="Ankara Tekstil Ltd.",
                tax_number="1111111111",
                contact_name="Zeynep Müdür",
                contact_phone="+903125551234",
                address="Ankara, Ostim"
            )
            
            session.add(customer1)
            session.commit()
            print("✓ Customers created for Tenant 1")
            
            # ============ DRIVER SHIFTS ============
            shift1 = DriverShift(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                driver_id=driver1.id,
                vehicle_id=vehicle1.id,
                shift_date=date.today(),
                shift_type="8h",
                shift_start="08:00",
                shift_end="16:00",
                assigned_by_user_id=chief_driver_user.id,
                status="scheduled",
                notes="Normal vardiya"
            )
            
            session.add(shift1)
            session.commit()
            print("✓ Driver Shifts created for Tenant 1")
            
            # ============ VEHICLE ASSIGNMENTS ============
            assignment1 = VehicleAssignment(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                vehicle_id=vehicle1.id,
                driver_id=driver1.id,
                assigned_at=datetime.utcnow(),
                assignment_reason="daily_shift",
                notes="Sabah vardiyası için atama"
            )
            
            session.add(assignment1)
            session.commit()
            print("✓ Vehicle Assignments created for Tenant 1")
            
            # ============ MAINTENANCE SCHEDULE ============
            maint1 = VehicleMaintenanceSchedule(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                vehicle_id=vehicle1.id,
                maintenance_type="inspection",
                last_done_date=date.today() - timedelta(days=30),
                due_date=date.today() + timedelta(days=60),
                interval_months=12,
                status="pending",
                notes="Periyodik muayene"
            )
            
            session.add(maint1)
            session.commit()
            print("✓ Maintenance Schedules created for Tenant 1")
            
            # ============ PERIODIC DOCS (Insurance, Inspection) ============
            doc1 = VehiclePeriodicDoc(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                vehicle_id=vehicle1.id,
                doc_type="insurance",
                issue_date=date.today() - timedelta(days=30),
                expiry_date=date.today() + timedelta(days=335),
                status="valid",
                alert_days_before=30
            )
            
            doc2 = VehiclePeriodicDoc(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                vehicle_id=vehicle1.id,
                doc_type="inspection",
                issue_date=date.today() - timedelta(days=60),
                expiry_date=date.today() + timedelta(days=270),
                status="valid",
                alert_days_before=30
            )
            
            session.add_all([doc1, doc2])
            session.commit()
            print("✓ Periodic Docs created for Tenant 1")
            
            # ============ OCR/WEIGHBRIDGE RECORDS ============
            ocr1 = WeighbridgeOCRRecord(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                driver_id=driver1.id,
                vehicle_id=vehicle1.id,
                filename="weighbridge_20260926_001.jpg",
                file_path=f"{tenant1.id}/ocr/2026/09/weighbridge_001.jpg",
                content_type="image/jpeg",
                file_size_bytes=256000,
                receipt_number="WB-2026-09-001",
                scale_name="İstanbul Kantar",
                ocr_plate="OZTRANS01",
                weighed_ton=Decimal("18.500"),
                receipt_timestamp=datetime.utcnow(),
                raw_text="OCR extracted text from receipt",
                extracted_json='{"plate": "OZTRANS01", "ton": 18.5, "time": "09:30"}',
                confidence_score=Decimal("95.50"),
                status="verified",
                verified_by_user_id=admin_user.id,
                verified_at=datetime.utcnow()
            )
            
            session.add(ocr1)
            session.commit()
            print("✓ OCR/Weighbridge Records created for Tenant 1")
            
            # ============ DRIVER FIELD RECEIPTS ============
            field_receipt1 = DriverFieldReceipt(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                driver_id=driver1.id,
                vehicle_id=vehicle1.id,
                receipt_type="weighbridge",
                filename="receipt_20260926_123.jpg",
                file_path=f"{tenant1.id}/drivers/{driver1.id}/2026/09/receipt_123.jpg",
                content_type="image/jpeg",
                file_size_bytes=250000,
                description="Kantar fişi - İstanbul 18.5 ton",
                status="approved"
            )
            
            session.add(field_receipt1)
            session.commit()
            print("✓ Driver Field Receipts created for Tenant 1")
            
            # ============ WORKBOOK SHEETS ============
            workbook1 = WorkbookSheet(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                name="Araç Envanteri",
                sheet_type="vehicles",
                owner_user_id=admin_user.id,
                workbook_json='{"sheets": [{"name": "Vehicles", "data": []}]}',
                metadata_json='{"columns": ["Plaka", "Marka", "Model", "Durum"], "permissions": {"admin": "rw", "operations": "r"}}',
                is_public=False,
                version=1
            )
            
            workbook2 = WorkbookSheet(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                name="Şoför Vardiyası",
                sheet_type="drivers",
                owner_user_id=chief_driver_user.id,
                workbook_json='{"sheets": [{"name": "Shifts", "data": []}]}',
                metadata_json='{"columns": ["Şoför", "Tarih", "Araç", "Saat"], "permissions": {"chief_driver": "rw", "operations": "r"}}',
                is_public=False,
                version=1
            )
            
            session.add_all([workbook1, workbook2])
            session.commit()
            print("✓ Workbook Sheets created for Tenant 1")
            
            # ============ WORKBOOK SYNC STATES ============
            sync1 = WorkbookSyncState(
                id=str(uuid.uuid4()),
                tenant_id=tenant1.id,
                workbook_id=workbook1.id,
                last_synced_version=1,
                last_sync_at=datetime.utcnow(),
                sync_status="in_sync"
            )
            
            session.add(sync1)
            session.commit()
            print("✓ Workbook Sync States created for Tenant 1")
            
        finally:
            tenant_context.reset(marker)
        
        # ============ USERS (Tenant 2) ============
        marker = tenant_context.set(tenant2.id)
        try:
            admin_user_2 = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant2.id,
                name="Hasim Admin",
                username="admin2",
                role="admin",
                department="executive",
                password_hash=hash_password("admin456"),
                is_active=True
            )
            
            session.add(admin_user_2)
            session.commit()
            print("✓ Users created for Tenant 2")
            
        finally:
            tenant_context.reset(marker)
        
        print("\n" + "="*50)
        print("✓ DATABASE SEED COMPLETED SUCCESSFULLY")
        print("="*50)
        print(f"Tenant 1: {tenant1.code} (ID: {tenant1.id})")
        print(f"Tenant 2: {tenant2.code} (ID: {tenant2.id})")
        print("\nTest Credentials (Tenant 1):")
        print("  Admin:       admin / admin123")
        print("  HR Officer:  hr_officer / hr123")
        print("  Chief Driver: chief_driver / chief123")
        print("  Operations:  operations / ops123")
        print("  Finance:     finance / fin123")
        print("  Driver:      driver_ali / driver123")
        print("\nTest Credentials (Tenant 2):")
        print("  Admin:       admin2 / admin456")
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ ERROR during seed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
