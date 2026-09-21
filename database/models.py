from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    tax_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscription_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    license_key: Mapped[str | None] = mapped_column(String(120), unique=True)
    logo_data: Mapped[str | None] = mapped_column(Text)
    logo_content_type: Mapped[str | None] = mapped_column(String(100))
    arvento_api_url: Mapped[str | None] = mapped_column(Text)
    arvento_username: Mapped[str | None] = mapped_column(String(160))
    arvento_password: Mapped[str | None] = mapped_column(Text)
    arvento_api_token: Mapped[str | None] = mapped_column(Text)
    arvento_pin: Mapped[str | None] = mapped_column(String(80))


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    department: Mapped[str | None] = mapped_column(String(40))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (Index("ix_users_tenant_username", "tenant_id", "username", unique=True),)


class NotificationLog(TimestampMixin, Base):
    __tablename__ = "notification_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class BackupRun(TimestampMixin, Base):
    __tablename__ = "backup_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    backup_type: Mapped[str] = mapped_column(String(30), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)


class Driver(TimestampMixin, Base):
    __tablename__ = "drivers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    employee_no: Mapped[str | None] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    shift: Mapped[str | None] = mapped_column(String(50))
    license_no: Mapped[str | None] = mapped_column(String(50))
    license_expiry: Mapped[date | None] = mapped_column(Date)
    src_expiry: Mapped[date | None] = mapped_column(Date)
    penalty_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DriverDocument(TimestampMixin, Base):
    __tablename__ = "driver_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(80))
    expires_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    document_uri: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="valid", nullable=False)


class DisciplineRecord(TimestampMixin, Base):
    __tablename__ = "discipline_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    violation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)


class TachographViolation(TimestampMixin, Base):
    __tablename__ = "tachograph_violations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    violation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class RestBreak(TimestampMixin, Base):
    __tablename__ = "rest_breaks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    break_type: Mapped[str] = mapped_column(String(30), default="rest", nullable=False)


class ReceiptOcrRecord(TimestampMixin, Base):
    __tablename__ = "receipt_ocr_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"))
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"))
    receipt_type: Mapped[str] = mapped_column(String(30), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)
    extracted_data: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="processed", nullable=False)


class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    plate: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(40), default="tractor", nullable=False)
    brand: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(80))
    model_year: Mapped[int | None] = mapped_column(Integer)
    vin: Mapped[str | None] = mapped_column(String(50), unique=True)
    device_no: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    odometer_km: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fuel_capacity_l: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    consumption_100km: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    current_driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"))
    ownership_status: Mapped[str] = mapped_column(String(30), default="owned", nullable=False)
    acquisition_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    acquisition_date: Mapped[date | None] = mapped_column(Date)
    depreciation_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    sale_date: Mapped[date | None] = mapped_column(Date)
    sale_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class Trailer(TimestampMixin, Base):
    __tablename__ = "trailers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    plate: Mapped[str] = mapped_column(String(20), nullable=False)
    trailer_type: Mapped[str] = mapped_column(String(80), nullable=False)
    capacity_ton: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    hex_color: Mapped[str | None] = mapped_column(String(7))
    status: Mapped[str] = mapped_column(String(30), default="available", nullable=False)


class VehicleTrailerAssignment(TimestampMixin, Base):
    __tablename__ = "vehicle_trailer_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    trailer_id: Mapped[str] = mapped_column(ForeignKey("trailers.id"), nullable=False, index=True)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tax_number: Mapped[str | None] = mapped_column(String(20))
    contact_name: Mapped[str | None] = mapped_column(String(160))
    contact_phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)


class FreightContract(TimestampMixin, Base):
    __tablename__ = "freight_contracts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    contract_no: Mapped[str] = mapped_column(String(60), nullable=False)
    route: Mapped[str | None] = mapped_column(String(240))
    unit_price_ton: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)


class CustomerFreightRate(TimestampMixin, Base):
    __tablename__ = "customer_freight_rates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    route: Mapped[str | None] = mapped_column(String(240))
    unit_price_ton: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ContractorCommission(TimestampMixin, Base):
    __tablename__ = "contractor_commissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    subcontractor_id: Mapped[str] = mapped_column(ForeignKey("subcontractors.id"), nullable=False, index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), index=True)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Trip(TimestampMixin, Base):
    __tablename__ = "trips"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"))
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"))
    contract_id: Mapped[str | None] = mapped_column(ForeignKey("freight_contracts.id"))
    route: Mapped[str] = mapped_column(String(240), nullable=False)
    cargo_description: Mapped[str | None] = mapped_column(String(240))
    planned_ton: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    realized_ton: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    status: Mapped[str] = mapped_column(String(30), default="assigned", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DriverTask(TimestampMixin, Base):
    __tablename__ = "driver_tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="assigned", nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ShiftHandover(TimestampMixin, Base):
    __tablename__ = "shift_handovers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    incoming_driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"))
    closing_odometer_km: Mapped[int] = mapped_column(Integer, nullable=False)
    fuel_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    fuel_liters: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    photo_uri: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class ShiftLog(TimestampMixin, Base):
    __tablename__ = "shift_logs"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    driver_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("drivers.id"), index=True)
    vehicle_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("vehicles.id"), index=True)
    shift_code: Mapped[str] = mapped_column(String(20), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_ton: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    trip_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    receipt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fuel_liters: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    distance_km: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    report_status: Mapped[str] = mapped_column(String(30), default="generated", nullable=False)


class WeighbridgeReceipt(TimestampMixin, Base):
    __tablename__ = "weighbridge_receipts"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    shift_log_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("shift_logs.id"), index=True)
    driver_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("drivers.id"), index=True)
    vehicle_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("vehicles.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    receipt_number: Mapped[str | None] = mapped_column(String(80))
    scale_name: Mapped[str | None] = mapped_column(String(160))
    ocr_plate: Mapped[str | None] = mapped_column(String(20))
    weighed_ton: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    receipt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="matched", nullable=False)
    review_reason: Mapped[str | None] = mapped_column(Text)


class Waybill(TimestampMixin, Base):
    __tablename__ = "waybills"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"))
    waybill_no: Mapped[str] = mapped_column(String(80), nullable=False)
    cargo_ton: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    document_uri: Mapped[str | None] = mapped_column(Text)


class WeighbridgeTicket(TimestampMixin, Base):
    __tablename__ = "weighbridge_tickets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), index=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    ticket_no: Mapped[str] = mapped_column(String(80), nullable=False)
    gross_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    tare_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    net_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    waybill_kg: Mapped[int | None] = mapped_column(Integer)
    deviation_kg: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    ocr_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_uri: Mapped[str | None] = mapped_column(Text)
    weighed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WaitEvent(TimestampMixin, Base):
    __tablename__ = "wait_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), index=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    location_type: Mapped[str] = mapped_column(String(30), nullable=False)
    location_name: Mapped[str] = mapped_column(String(160), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    free_minutes: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    rate_per_hour: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    demurrage_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)


class MaintenanceIssue(TimestampMixin, Base):
    __tablename__ = "maintenance_issues"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    reported_by_driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"))
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    urgency: Mapped[str] = mapped_column(String(30), default="normal", nullable=False)
    parts_needed: Mapped[str | None] = mapped_column(Text)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    layup_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)


class WorkOrder(TimestampMixin, Base):
    __tablename__ = "work_orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    issue_id: Mapped[str | None] = mapped_column(ForeignKey("maintenance_issues.id"))
    assigned_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    labor_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="planned", nullable=False)


class Part(TimestampMixin, Base):
    __tablename__ = "parts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="piece", nullable=False)
    stock_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    critical_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class PartMovement(TimestampMixin, Base):
    __tablename__ = "part_movements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), nullable=False, index=True)
    work_order_id: Mapped[str | None] = mapped_column(ForeignKey("work_orders.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)


class Inspection(TimestampMixin, Base):
    __tablename__ = "inspections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    inspection_type: Mapped[str] = mapped_column(String(50), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_odometer_km: Mapped[int | None] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="upcoming", nullable=False)


class AssetDocument(TimestampMixin, Base):
    __tablename__ = "asset_documents"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("vehicles.id"), index=True)
    trailer_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("trailers.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    expires_on: Mapped[date] = mapped_column(Date, nullable=False)
    document_uri: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="valid", nullable=False)


class FuelTransaction(TimestampMixin, Base):
    __tablename__ = "fuel_transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"))
    liters: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    odometer_km: Mapped[int | None] = mapped_column(Integer)
    station: Mapped[str | None] = mapped_column(String(160))
    receipt_uri: Mapped[str | None] = mapped_column(Text)
    transaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TelemetryEvent(TimestampMixin, Base):
    __tablename__ = "telemetry_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    speed_kmh: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    fuel_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    engine_on: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload: Mapped[str | None] = mapped_column(Text)


class Geofence(TimestampMixin, Base):
    __tablename__ = "geofences"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    geometry_wkt: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GeofenceEvent(TimestampMixin, Base):
    __tablename__ = "geofence_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    geofence_id: Mapped[str] = mapped_column(ForeignKey("geofences.id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))


class Tire(TimestampMixin, Base):
    __tablename__ = "tires"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(30), nullable=False)
    serial_no: Mapped[str | None] = mapped_column(String(80))
    brand: Mapped[str | None] = mapped_column(String(80))
    tread_mm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)


class TireIncident(TimestampMixin, Base):
    __tablename__ = "tyre_incidents"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("vehicles.id"), nullable=False, index=True)
    driver_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("drivers.id"), index=True)
    trailer_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("trailers.id"), index=True)
    tire_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("tires.id"))
    route: Mapped[str | None] = mapped_column(String(240))
    location: Mapped[str | None] = mapped_column(String(240))
    cause: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    brand: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(80))
    damage_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RoadsideAssistanceLog(TimestampMixin, Base):
    __tablename__ = "road_side_assistance_logs"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    incident_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("tyre_incidents.id"))
    vehicle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("vehicles.id"), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(160), nullable=False)
    location: Mapped[str | None] = mapped_column(String(240))
    cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    response_minutes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="completed", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FuelAnomaly(TimestampMixin, Base):
    __tablename__ = "fuel_anomalies"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("vehicles.id"), nullable=False, index=True)
    fuel_transaction_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("fuel_transactions.id"))
    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    expected_liters: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    actual_liters: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    details: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CustomerTrackingLink(TimestampMixin, Base):
    __tablename__ = "customer_tracking_links"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trips.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TireRotation(TimestampMixin, Base):
    __tablename__ = "tire_rotations"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    tire_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tires.id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("vehicles.id"), nullable=False)
    from_position: Mapped[str] = mapped_column(String(30), nullable=False)
    to_position: Mapped[str] = mapped_column(String(30), nullable=False)
    rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    odometer_km: Mapped[int | None] = mapped_column(Integer)


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"))
    incident_type: Mapped[str] = mapped_column(String(50), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    repair_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    layup_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)


class Subcontractor(TimestampMixin, Base):
    __tablename__ = "subcontractors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tax_number: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(30))
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)


class SupplierSettlement(TimestampMixin, Base):
    __tablename__ = "supplier_settlements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    subcontractor_id: Mapped[str] = mapped_column(ForeignKey("subcontractors.id"), nullable=False, index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"))
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"))
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    incurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Bid(TimestampMixin, Base):
    __tablename__ = "bids"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"))
    route: Mapped[str] = mapped_column(String(240), nullable=False)
    requested_ton: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    proposed_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36))
    payload: Mapped[str | None] = mapped_column(Text)


class SpreadsheetWorkbook(TimestampMixin, Base):
    __tablename__ = "spreadsheet_workbooks"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    workbook_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    protection_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class SpreadsheetChange(TimestampMixin, Base):
    __tablename__ = "spreadsheet_changes"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    workbook_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("spreadsheet_workbooks.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(120), nullable=False)
    cell_ref: Mapped[str] = mapped_column(String(30), nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
