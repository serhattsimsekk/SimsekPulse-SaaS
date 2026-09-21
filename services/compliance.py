from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal


def parse_receipt_text(text: str, receipt_type: str) -> dict[str, str | int | float | None]:
    source = " ".join((text or "").split())
    number_pattern = r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?"
    amount_match = re.search(
        rf"({number_pattern})\s*(?:₺|TL|TRY)",
        source,
        re.I,
    ) or re.search(
        rf"(?:₺|TL|TRY)\s*({number_pattern})",
        source,
        re.I,
    )
    if not amount_match:
        amount_match = re.search(
        rf"(?:tutar|toplam|amount)\s*[:=-]?\s*({number_pattern})",
        source,
        re.I,
        )
    liters_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:L|LT|LİTRE)", source, re.I)
    weight_match = re.search(r"(\d{1,3}(?:[.,]\d{3})+|\d{4,6})\s*KG", source, re.I)
    plate_match = re.search(r"\b(\d{2}\s?[A-ZÇĞİÖŞÜ]{1,3}\s?\d{2,4})\b", source, re.I)
    ticket_match = re.search(r"(?:fiş|fis|ticket|belge)\s*(?:no|numarası)?\s*[:#-]?\s*([A-Z0-9-]{3,})", source, re.I)
    value = amount_match.group(1).replace(".", "").replace(",", ".") if amount_match else None
    return {
        "receipt_type": receipt_type,
        "ticket_no": ticket_match.group(1) if ticket_match else None,
        "plate": plate_match.group(1).upper() if plate_match else None,
        "amount": float(value) if value else None,
        "liters": float(liters_match.group(1).replace(",", ".")) if liters_match else None,
        "weight_kg": int(weight_match.group(1).replace(".", "").replace(",", "")) if weight_match else None,
        "raw_text": source,
    }


def expiry_status(expires_on: date, today: date | None = None) -> dict[str, int | bool | str]:
    reference = today or date.today()
    days = (expires_on - reference).days
    locked = days < 0
    return {
        "days_remaining": days,
        "expired": locked,
        "task_locked": locked,
        "warning": "expired" if locked else "critical" if days <= 7 else "warning" if days <= 30 else "valid",
    }


def fatigue_index(
    driving_minutes: int,
    break_minutes: int,
    tachograph_violation_count: int,
    *,
    max_driving_minutes: int = 540,
) -> dict[str, int | float | str | bool]:
    driving = max(int(driving_minutes), 0)
    breaks = max(int(break_minutes), 0)
    violations = max(int(tachograph_violation_count), 0)
    driving_score = min(driving / max(max_driving_minutes, 1), 1.0) * 70
    break_score = max(0.0, 20.0 - min(breaks / 45, 1.0) * 20)
    violation_score = min(violations * 5.0, 10.0)
    score = round(min(driving_score + break_score + violation_score, 100.0), 2)
    return {
        "fatigue_index": score,
        "risk": "critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 35 else "low",
        "rest_required": score >= 60,
        "driving_minutes": driving,
        "break_minutes": breaks,
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
