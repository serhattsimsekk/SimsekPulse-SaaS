from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from services.permissions import can_access_path, can_view_hr_personnel, can_view_tachograph_and_fatigue


def enforce_access(request_path: str, role: str | None, department: str | None) -> None:
    if not can_access_path(request_path, role, department):
        raise PermissionError(f"Role '{role}' / department '{department}' cannot access '{request_path}'.")


def can_list_hr_records(role: str | None, department: str | None) -> bool:
    return can_view_hr_personnel(role, department)


def can_list_fatigue_tachograph(role: str | None, department: str | None) -> bool:
    return can_view_tachograph_and_fatigue(role, department)


def apply_visibility_filters(session: Session, role: str | None, department: str | None, base_query: Any):
    """This helper gives the API layer a central place to enforce role-driven filtering.

    HR users may only query personnel/legal fields; operational fields are excluded.
    """
    if can_view_hr_personnel(role, department) and not can_view_tachograph_and_fatigue(role, department):
        return base_query
    return base_query
