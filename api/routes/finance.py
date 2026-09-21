from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import (
    CommissionCreate,
    CommissionRead,
    AutoCommissionCreate,
    CustomerRateCreate,
    CustomerRateRead,
    FuelAnalysisRead,
    ProfitabilityRead,
    SettlementRead,
)
from database.models import (
    ContractorCommission,
    CustomerFreightRate,
    Expense,
    FreightContract,
    FuelTransaction,
    Subcontractor,
    SupplierSettlement,
    Trip,
    Vehicle,
)

router = APIRouter(prefix="/api/v1/finance", tags=["Finans & Navlun"])


@router.post("/customer-rates", response_model=CustomerRateRead, status_code=status.HTTP_201_CREATED)
def create_customer_rate(payload: CustomerRateCreate, db: Session = Depends(get_db)):
    if payload.valid_to and payload.valid_to < payload.valid_from:
        raise HTTPException(400, "Geçerlilik bitiş tarihi başlangıçtan önce olamaz.")
    rate = CustomerFreightRate(**payload.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.get("/customer-rates", response_model=list[CustomerRateRead])
def list_customer_rates(
    tenant_id: str,
    customer_id: str | None = None,
    active_on: date | None = None,
    db: Session = Depends(get_db),
):
    query = select(CustomerFreightRate).where(
        CustomerFreightRate.tenant_id == tenant_id,
        CustomerFreightRate.is_active.is_(True),
    )
    if customer_id:
        query = query.where(CustomerFreightRate.customer_id == customer_id)
    if active_on:
        query = query.where(
            CustomerFreightRate.valid_from <= active_on,
            (CustomerFreightRate.valid_to.is_(None) | (CustomerFreightRate.valid_to >= active_on)),
        )
    return list(db.scalars(query.order_by(CustomerFreightRate.valid_from.desc())))


@router.post("/commissions", response_model=CommissionRead, status_code=status.HTTP_201_CREATED)
def create_commission(payload: CommissionCreate, db: Session = Depends(get_db)):
    subcontractor = db.get(Subcontractor, payload.subcontractor_id)
    if not subcontractor:
        raise HTTPException(404, "Taşeron bulunamadı.")
    amount = (payload.base_amount * payload.commission_rate / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    commission = ContractorCommission(
        **payload.model_dump(),
        commission_amount=amount,
    )
    db.add(commission)
    db.commit()
    db.refresh(commission)
    return commission


@router.post("/commissions/auto", response_model=CommissionRead, status_code=status.HTTP_201_CREATED)
def create_automatic_commission(payload: AutoCommissionCreate, db: Session = Depends(get_db)):
    """Sefer tonajı ve sözleşme fiyatından taşeron hakedişini otomatik üretir."""
    trip = db.get(Trip, payload.trip_id)
    if not trip or trip.tenant_id != payload.tenant_id:
        raise HTTPException(404, "Sefer bulunamadı.")
    if not db.get(Subcontractor, payload.subcontractor_id):
        raise HTTPException(404, "Taşeron bulunamadı.")
    if not trip.realized_ton or not trip.contract_id:
        raise HTTPException(400, "Seferde gerçekleşen tonaj ve navlun sözleşmesi bulunmalıdır.")
    contract = db.get(FreightContract, trip.contract_id)
    if not contract:
        raise HTTPException(404, "Navlun sözleşmesi bulunamadı.")
    base_amount = (trip.realized_ton * contract.unit_price_ton).quantize(Decimal("0.01"))
    commission_amount = (base_amount * payload.commission_rate / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    commission = ContractorCommission(
        tenant_id=payload.tenant_id,
        subcontractor_id=payload.subcontractor_id,
        trip_id=payload.trip_id,
        base_amount=base_amount,
        commission_rate=payload.commission_rate,
        commission_amount=commission_amount,
    )
    db.add(commission)
    db.commit()
    db.refresh(commission)
    return commission


@router.get("/subcontractors/{subcontractor_id}/settlement", response_model=SettlementRead)
def subcontractor_settlement(subcontractor_id: str, db: Session = Depends(get_db)):
    if not db.get(Subcontractor, subcontractor_id):
        raise HTTPException(404, "Taşeron bulunamadı.")
    gross = db.scalar(
        select(func.coalesce(func.sum(ContractorCommission.commission_amount), 0)).where(
            ContractorCommission.subcontractor_id == subcontractor_id
        )
    ) or Decimal("0")
    paid = db.scalar(
        select(func.coalesce(func.sum(SupplierSettlement.amount), 0)).where(
            SupplierSettlement.subcontractor_id == subcontractor_id,
            SupplierSettlement.status == "paid",
        )
    ) or Decimal("0")
    return SettlementRead(
        subcontractor_id=subcontractor_id,
        gross_commission=gross,
        paid_amount=paid,
        outstanding_amount=max(gross - paid, Decimal("0")),
    )


@router.get("/vehicles/{vehicle_id}/fuel-analysis", response_model=FuelAnalysisRead)
def vehicle_fuel_analysis(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Araç bulunamadı.")
    liters, fuel_cost, avg_price = db.execute(
        select(
            func.coalesce(func.sum(FuelTransaction.liters), 0),
            func.coalesce(func.sum(FuelTransaction.liters * FuelTransaction.unit_price), 0),
            func.coalesce(func.avg(FuelTransaction.unit_price), 0),
        ).where(FuelTransaction.vehicle_id == vehicle_id)
    ).one()
    kilometers = int(vehicle.odometer_km or 0)
    l100 = (Decimal(str(liters)) / kilometers * 100).quantize(Decimal("0.01")) if kilometers else None
    return FuelAnalysisRead(
        vehicle_id=vehicle.id,
        vehicle_plate=vehicle.plate,
        liters=Decimal(str(liters)),
        fuel_cost=Decimal(str(fuel_cost)),
        average_unit_price=Decimal(str(avg_price)),
        kilometers=kilometers,
        liters_per_100km=l100,
    )


@router.get("/vehicles/{vehicle_id}/profitability", response_model=ProfitabilityRead)
def vehicle_profitability(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Araç bulunamadı.")
    revenue = db.scalar(
        select(func.coalesce(func.sum(Trip.realized_ton * FreightContract.unit_price_ton), 0))
        .join(FreightContract, Trip.contract_id == FreightContract.id, isouter=True)
        .where(Trip.vehicle_id == vehicle_id)
    ) or Decimal("0")
    fuel = db.scalar(
        select(func.coalesce(func.sum(FuelTransaction.liters * FuelTransaction.unit_price), 0))
        .where(FuelTransaction.vehicle_id == vehicle_id)
    ) or Decimal("0")
    other = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.vehicle_id == vehicle_id, Expense.category != "fuel"
        )
    ) or Decimal("0")
    contractor = db.scalar(
        select(func.coalesce(func.sum(ContractorCommission.commission_amount), 0))
        .join(Trip, ContractorCommission.trip_id == Trip.id, isouter=True)
        .where(Trip.vehicle_id == vehicle_id)
    ) or Decimal("0")
    net = revenue - fuel - other - contractor
    margin = (net / revenue * 100).quantize(Decimal("0.01")) if revenue else Decimal("0")
    return ProfitabilityRead(
        vehicle_id=vehicle.id,
        vehicle_plate=vehicle.plate,
        revenue=revenue,
        fuel_cost=fuel,
        other_cost=other,
        contractor_cost=contractor,
        net_profit=net,
        margin_percent=margin,
    )
