from fastapi import APIRouter, Depends

from api.security import require_roles
from services.jobs import database_health, run_database_backup

router = APIRouter(prefix="/api/v1/system", tags=["Sistem & Yedekleme"])


@router.get("/health")
def detailed_health():
    return {"database": database_health()}


@router.post("/backup")
def manual_backup(principal: dict = Depends(require_roles("admin"))):
    return run_database_backup()
