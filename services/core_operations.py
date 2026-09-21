from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Mapping


TR_PLATE_PREFIXES = {"01", "02", "06", "31", "34", "35", "41", "42", "54", "59", "61", "67", "78", "80"}


def normalize_plate(value: str) -> str:
    return " ".join(str(value or "").upper().strip().split())


def complete_plate(prefix: str, letters: str, number: str) -> str:
    prefix = "".join(ch for ch in str(prefix) if ch.isdigit())[:2]
    letters = "".join(ch for ch in str(letters).upper() if ch.isalpha())[:3]
    number = "".join(ch for ch in str(number) if ch.isdigit())[:4]
    if len(prefix) != 2 or not letters or not number:
        raise ValueError("Plaka; iki haneli il kodu, harf ve numara içermelidir.")
    if prefix not in TR_PLATE_PREFIXES:
        raise ValueError("Geçersiz veya desteklenmeyen il plaka kodu.")
    return normalize_plate(f"{prefix} {letters} {number}")


def calculate_tonnage_progress(planned_ton: float | Decimal, carried_ton: float | Decimal) -> dict[str, float | bool]:
    planned = max(Decimal(str(planned_ton or 0)), Decimal("0"))
    carried = max(Decimal(str(carried_ton or 0)), Decimal("0"))
    remaining = max(planned - carried, Decimal("0"))
    ratio = (carried / planned * 100) if planned else Decimal("0")
    return {
        "planned_ton": float(planned),
        "carried_ton": float(carried),
        "remaining_ton": float(remaining),
        "progress_percent": float(min(ratio, Decimal("100"))),
        "overloaded": carried > planned if planned else False,
    }


def calculate_weighbridge_deviation(net_kg: int, waybill_kg: int, tolerance_kg: int = 50) -> dict[str, int | bool | str]:
    deviation = int(net_kg) - int(waybill_kg)
    return {
        "deviation_kg": deviation,
        "within_tolerance": abs(deviation) <= tolerance_kg,
        "status": "uyumlu" if abs(deviation) <= tolerance_kg else "kritik_sapma",
    }


def calculate_demurrage(
    waited_minutes: int,
    free_minutes: int,
    rate_per_hour: float | Decimal,
) -> dict[str, float | int | bool]:
    waited = max(int(waited_minutes), 0)
    free = max(int(free_minutes), 0)
    chargeable_minutes = max(waited - free, 0)
    amount = (Decimal(chargeable_minutes) / Decimal("60") * Decimal(str(rate_per_hour))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return {
        "waited_minutes": waited,
        "free_minutes": free,
        "chargeable_minutes": chargeable_minutes,
        "amount": float(amount),
        "alert": chargeable_minutes > 0,
    }


def build_shift_handover(
    *,
    vehicle_id: str,
    outgoing_driver_id: str,
    incoming_driver_id: str | None,
    closing_odometer_km: int,
    fuel_liters: float,
    fuel_percent: float,
    photo_uri: str | None,
    notes: str = "",
) -> dict[str, Any]:
    if closing_odometer_km < 0 or fuel_liters < 0 or not 0 <= fuel_percent <= 100:
        raise ValueError("KM ve yakıt değerleri geçerli aralıkta olmalıdır.")
    return {
        "vehicle_id": vehicle_id,
        "outgoing_driver_id": outgoing_driver_id,
        "incoming_driver_id": incoming_driver_id,
        "closing_odometer_km": int(closing_odometer_km),
        "fuel_liters": round(float(fuel_liters), 2),
        "fuel_percent": round(float(fuel_percent), 2),
        "photo_uri": photo_uri,
        "notes": notes.strip(),
        "status": "pending",
        "submitted_at": datetime.utcnow().isoformat(timespec="seconds"),
    }


def active_assignments(assignments: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [item for item in assignments if not item.get("ended_at") and item.get("status", "active") == "active"]
