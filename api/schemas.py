from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CustomerRateCreate(BaseModel):
    tenant_id: str
    customer_id: str
    route: str | None = None
    unit_price_ton: Decimal = Field(gt=0)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    valid_from: date
    valid_to: date | None = None


class CustomerRateRead(CustomerRateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_active: bool


class CommissionCreate(BaseModel):
    tenant_id: str
    subcontractor_id: str
    trip_id: str | None = None
    base_amount: Decimal = Field(gt=0)
    commission_rate: Decimal = Field(ge=0, le=100)


class AutoCommissionCreate(BaseModel):
    tenant_id: str
    subcontractor_id: str
    trip_id: str
    commission_rate: Decimal = Field(ge=0, le=100)


class CommissionRead(CommissionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    commission_amount: Decimal
    status: str


class ProfitabilityRead(BaseModel):
    vehicle_id: str
    vehicle_plate: str
    revenue: Decimal
    fuel_cost: Decimal
    other_cost: Decimal
    contractor_cost: Decimal
    net_profit: Decimal
    margin_percent: Decimal


class FuelAnalysisRead(BaseModel):
    vehicle_id: str
    vehicle_plate: str
    liters: Decimal
    fuel_cost: Decimal
    average_unit_price: Decimal
    kilometers: int
    liters_per_100km: Decimal | None


class SettlementRead(BaseModel):
    subcontractor_id: str
    gross_commission: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal


class DocumentCreate(BaseModel):
    document_type: str = Field(pattern="^(license|src|psychotechnic|casco|inspection)$")
    document_number: str | None = None
    expires_on: date
    document_uri: str | None = None


class DocumentRead(DocumentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    driver_id: str
    status: str


class DisciplineCreate(BaseModel):
    violation_type: str = Field(min_length=2, max_length=80)
    points: int = Field(ge=0, le=100)
    description: str | None = None
    occurred_at: datetime


class DisciplineRead(DisciplineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    driver_id: str
    status: str


class TachographViolationCreate(BaseModel):
    violation_type: str = Field(min_length=2, max_length=80)
    occurred_at: datetime
    duration_minutes: int = Field(default=0, ge=0)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    notes: str | None = None


class TachographViolationRead(TachographViolationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    driver_id: str


class RestBreakCreate(BaseModel):
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int = Field(default=0, ge=0)
    break_type: str = Field(default="rest", pattern="^(rest|meal|daily|weekly)$")


class FatigueRead(BaseModel):
    driver_id: str
    tachograph_violation_count: int
    fatigue_index: float
    risk: str
    rest_required: bool
    driving_minutes: int
    break_minutes: int


class ReportQuery(BaseModel):
    period_days: int = Field(default=30, ge=1, le=366)
    site: str | None = None


class ShiftSlotRequest(BaseModel):
    driver_ids: list[str] = Field(min_length=1, max_length=200)
    shift: str = Field(pattern="^(day|night)$")
    start_at: datetime
    duration_hours: int = Field(default=12, ge=1, le=24)


class VehicleMatchRequest(BaseModel):
    required_ton: Decimal = Field(gt=0)
    route_km: Decimal = Field(gt=0)
    preferred_vehicle_type: str | None = None


class AssistantQuery(BaseModel):
    query: str = Field(min_length=2, max_length=500)


class FuelForecastRequest(BaseModel):
    vehicle_id: str
    distance_km: Decimal = Field(gt=0)
    fuel_price: Decimal = Field(gt=0)
    load_ton: Decimal = Field(default=0, ge=0)


class WorkOrderCreate(BaseModel):
    vehicle_id: str
    category: str = Field(min_length=2, max_length=100)
    urgency: str = Field(default="normal", pattern="^(low|normal|high|critical)$")
    estimated_cost: Decimal | None = Field(default=None, ge=0)


class WeighbridgeCheckRequest(BaseModel):
    vehicle_id: str
    declared_kg: int = Field(ge=0)
    measured_kg: int = Field(ge=0)
    tolerance_kg: int = Field(default=100, ge=0)


class NotificationReportRequest(BaseModel):
    channel: str = Field(pattern="^(whatsapp|sms|email)$")
    recipient: str = Field(min_length=3, max_length=160)
    subject: str = Field(min_length=2, max_length=160)


class PlateNormalizeRequest(BaseModel):
    plate: str = Field(min_length=2, max_length=20)


class TonFormatRequest(BaseModel):
    tons: Decimal = Field(ge=0)
    locale: str = Field(default="tr-TR", pattern="^(tr-TR|en-US)$")


class StackOptimizationRequest(BaseModel):
    warehouse_capacity_ton: Decimal = Field(gt=0)
    lots: list[Decimal] = Field(min_length=1, max_length=500)


class SpreadsheetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    workbook: dict = Field(default_factory=dict)
    protection: dict = Field(default_factory=dict)


class SpreadsheetCellChange(BaseModel):
    sheet_name: str = Field(min_length=1, max_length=120)
    cell_ref: str = Field(pattern="^[A-Z]{1,3}[1-9][0-9]*$")
    value: object
    base_version: int = Field(ge=1)


class CellPermission(BaseModel):
    sheet_name: str
    cell_ref: str
    roles: list[str] = Field(min_length=1)
    editable: bool = True


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(pattern="^[a-z0-9][a-z0-9-]{2,39}$")
    license_key: str = Field(min_length=8, max_length=120)


class ManagedUserCreate(BaseModel):
    tenant_id: str
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=160)
    role: str = Field(pattern="^(admin|head_driver|driver|personnel|customer)$")
    password: str = Field(min_length=12, max_length=256)
    department: str | None = Field(default=None, pattern="^(operations|finance|maintenance|driver|hr|executive)$")


class ShiftReportQuery(BaseModel):
    hours: int = Field(default=8, ge=8, le=24)


class WeighbridgeReceiptFields(BaseModel):
    driver_id: str | None = None
    trip_id: str | None = None
    raw_text: str | None = None
