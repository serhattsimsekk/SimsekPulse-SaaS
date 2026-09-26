from __future__ import annotations

from typing import Any


HR_SCOPE_PREFIXES = (
    "/api/v1/hr",
    "/api/v1/personnel",
    "/api/v1/employee",
)

OPS_SCOPE_PREFIXES = (
    "/api/v1/operations",
    "/api/v1/command-center",
    "/api/v1/shifts",
    "/api/v1/driver-performance",
)

CHIEF_DRIVER_SCOPE_PREFIXES = (
    "/api/v1/chief-driver",
    "/api/v1/driver-shifts",
    "/api/v1/vehicle-assignments",
    "/api/v1/vehicle-maintenance",
)

OCR_SCOPE_PREFIXES = (
    "/api/v1/ocr",
    "/api/v1/receipts",
    "/api/v1/weighbridge",
)

FINANCE_SCOPE_PREFIXES = (
    "/api/v1/finance",
    "/api/v1/accounting",
)

MAINTENANCE_SCOPE_PREFIXES = (
    "/api/v1/maintenance",
    "/api/v1/assets",
)

TENANT_ADMIN_PREFIXES = (
    "/api/v1/tenants",
    "/api/v1/system",
)


def _matches_any(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def _role_is_admin(role: str | None) -> bool:
    return (role or "").lower() in {"super_admin", "admin"}


def can_access_path(path: str, role: str | None, department: str | None) -> bool:
    role_name = (role or "").lower()
    dept_name = (department or "").lower()

    if _role_is_admin(role_name):
        return True

    if _matches_any(path, HR_SCOPE_PREFIXES):
        return role_name in {"hr_officer", "hr_viewer", "admin", "super_admin"} or dept_name in {"hr", "executive"}

    if _matches_any(path, CHIEF_DRIVER_SCOPE_PREFIXES):
        return role_name in {"chief_driver", "operations", "admin", "super_admin", "fleet_manager"} or dept_name in {"operations", "executive"}

    if _matches_any(path, OPS_SCOPE_PREFIXES):
        return role_name in {"chief_driver", "operations", "fleet_manager", "admin", "super_admin"} or dept_name in {"operations", "driver", "executive"}

    if _matches_any(path, OCR_SCOPE_PREFIXES):
        return role_name in {"driver", "chief_driver", "operations", "fleet_manager", "admin", "super_admin"} or dept_name in {"driver", "operations", "executive"}

    if _matches_any(path, FINANCE_SCOPE_PREFIXES):
        return role_name in {"finance", "accounting", "admin", "super_admin"} or dept_name in {"finance", "executive"}

    if _matches_any(path, MAINTENANCE_SCOPE_PREFIXES):
        return role_name in {"maintenance", "operations", "fleet_manager", "admin", "super_admin"} or dept_name in {"maintenance", "operations", "executive"}

    if _matches_any(path, TENANT_ADMIN_PREFIXES):
        return role_name in {"admin", "super_admin", "operations", "fleet_manager"} or dept_name in {"executive", "operations"}

    return True


def is_operational_driver_field_access(path: str, role: str | None, department: str | None) -> bool:
    role_name = (role or "").lower()
    dept_name = (department or "").lower()
    if _role_is_admin(role_name):
        return True
    return role_name in {"chief_driver", "operations", "fleet_manager", "driver"} or dept_name in {"operations", "executive"}


def can_view_hr_personnel(role: str | None, department: str | None) -> bool:
    role_name = (role or "").lower()
    dept_name = (department or "").lower()
    return role_name in {"hr_officer", "hr_viewer", "admin", "super_admin"} or dept_name in {"hr", "executive"}


def can_view_driver_operational_data(role: str | None, department: str | None) -> bool:
    role_name = (role or "").lower()
    dept_name = (department or "").lower()
    if _role_is_admin(role_name):
        return True
    return role_name in {"chief_driver", "operations", "fleet_manager"} or dept_name in {"operations", "executive"}


def can_view_tachograph_and_fatigue(role: str | None, department: str | None) -> bool:
    role_name = (role or "").lower()
    dept_name = (department or "").lower()
    if _role_is_admin(role_name):
        return True
    return role_name in {"chief_driver", "operations", "fleet_manager"} or dept_name in {"operations", "executive"}
