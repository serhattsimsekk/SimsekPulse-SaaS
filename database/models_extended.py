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


# ============ CHIEF DRIVER MODELS ============

class DriverShift(TimestampMixin, Base):
    __tablename__ = "driver_shifts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    driver_id: Mapped[str] = mapped_column(String(36), ForeignKey("drivers.id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_type: Mapped[str] = mapped_column(String(30), default="8h")
    shift_start: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    shift_end: Mapped[str] = mapped_column(String(5), nullable=False)    # HH:MM
    assigned_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (Index("ix_driver_shifts_tenant_date", "tenant_id", "shift_date"),)


class VehicleAssignment(TimestampMixin, Base):
    __tablename__ = "vehicle_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    driver_id: Mapped[str] = mapped_column(String(36), ForeignKey("drivers.id"), nullable=False, index=True)
    
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    assignment_reason: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)


class VehicleMaintenanceSchedule(TimestampMixin, Base):
    __tablename__ = "vehicle_maintenance_schedule"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    maintenance_type: Mapped[str] = mapped_column(String(40), nullable=False)
    
    last_done_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    interval_months: Mapped[int | None] = mapped_column(Integer)
    
    status: Mapped[str] = mapped_column(String(30), default="pending")
    notes: Mapped[str | None] = mapped_column(Text)


class VehiclePeriodicDoc(TimestampMixin, Base):
    __tablename__ = "vehicle_periodic_docs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(40), nullable=False)
    
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    document_uri: Mapped[str | None] = mapped_column(Text)
    
    status: Mapped[str] = mapped_column(String(30), default="valid")
    alert_days_before: Mapped[int] = mapped_column(Integer, default=30)


# ============ OCR & WEIGHBRIDGE MODELS (TENANT-ISOLATED) ============

class WeighbridgeOCRRecord(TimestampMixin, Base):
    """Kantar fişi OCR kaydı - şoför tarafından yüklenir, tenant_id ile izole edilir."""
    __tablename__ = "weighbridge_ocr_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    driver_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("drivers.id"), index=True)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicles.id"), index=True)
    trip_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("trips.id"))
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # tenant_id/year/month/file
    content_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    
    # OCR extracted fields
    receipt_number: Mapped[str | None] = mapped_column(String(80))
    scale_name: Mapped[str | None] = mapped_column(String(160))
    ocr_plate: Mapped[str | None] = mapped_column(String(20))
    weighed_ton: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    receipt_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    raw_text: Mapped[str | None] = mapped_column(Text)
    extracted_json: Mapped[str | None] = mapped_column(Text)  # {"plate": "...", "ton": 12.5, ...}
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, processed, verified, rejected
    review_notes: Mapped[str | None] = mapped_column(Text)
    verified_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    __table_args__ = (
        Index("ix_weighbridge_ocr_tenant_date", "tenant_id", "created_at"),
        Index("ix_weighbridge_ocr_driver", "driver_id", "created_at"),
    )


class DriverFieldReceipt(TimestampMixin, Base):
    """Sürücü tarafından yüklenen operasyonel fişler (kantar, yakıt, vb) - tenant-isolated."""
    __tablename__ = "driver_field_receipts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    driver_id: Mapped[str] = mapped_column(String(36), ForeignKey("drivers.id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    
    receipt_type: Mapped[str] = mapped_column(String(40), nullable=False)  # weighbridge, fuel, maintenance, incident
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # tenant_id/drivers/driver_id/year/month/file
    content_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="submitted")  # submitted, reviewed, approved, rejected
    
    __table_args__ = (
        Index("ix_driver_field_receipts_tenant_driver", "tenant_id", "driver_id"),
    )


# ============ EXCEL WORKBOOK SYNC MODELS (TENANT-ISOLATED) ============

class WorkbookSheet(TimestampMixin, Base):
    """Excel benzeri çalışma kitabı (workbook) - tenant_id ile izole, rol tabanlı erişim."""
    __tablename__ = "workbook_sheets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sheet_type: Mapped[str] = mapped_column(String(40), default="default")  # vehicles, drivers, trips, finance, etc
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Workbook veri depolanması
    workbook_json: Mapped[str] = mapped_column(Text, default="{}")  # {"sheets": [...], "data": [...]}
    metadata_json: Mapped[str | None] = mapped_column(Text)  # {"columns": [...], "permissions": {...}}
    
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    __table_args__ = (
        Index("ix_workbook_sheets_tenant", "tenant_id", "created_at"),
    )


class WorkbookCellChange(TimestampMixin, Base):
    """Excel hücre seviyesi değişiklik takibi - tenant_id ile izole."""
    __tablename__ = "workbook_cell_changes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    workbook_id: Mapped[str] = mapped_column(String(36), ForeignKey("workbook_sheets.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    sheet_name: Mapped[str] = mapped_column(String(120), nullable=False)
    cell_ref: Mapped[str] = mapped_column(String(30), nullable=False)  # A1, B2, etc
    
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    change_type: Mapped[str] = mapped_column(String(20), default="update")  # insert, update, delete
    
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    
    __table_args__ = (
        Index("ix_workbook_changes_workbook", "workbook_id", "created_at"),
        Index("ix_workbook_changes_tenant", "tenant_id", "created_at"),
    )


class WorkbookSyncState(TimestampMixin, Base):
    """WebSocket/sync için workbook senkronizasyon durumu."""
    __tablename__ = "workbook_sync_states"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    workbook_id: Mapped[str] = mapped_column(String(36), ForeignKey("workbook_sheets.id"), nullable=False, unique=True)
    
    last_synced_version: Mapped[int] = mapped_column(Integer, default=0)
    last_sync_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    sync_status: Mapped[str] = mapped_column(String(30), default="in_sync")  # in_sync, pending, conflict
    
    __table_args__ = (
        Index("ix_workbook_sync_tenant", "tenant_id"),
    )
