from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.security import require_roles
from api.schemas import ManagedUserCreate, TenantCreate
from database.models import AuditLog, Tenant, User
from services.security import hash_password
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

router = APIRouter(prefix="/api/v1/tenants", tags=["SaaS Tenant Yönetimi"])


@router.post("", status_code=201)
def create_tenant(payload: TenantCreate, principal: dict = Depends(require_roles("super_admin")), db: Session = Depends(get_db)):
    tenant_id = str(uuid4())
    try:
        db.execute(text(
            "INSERT INTO tenants (id, name, code, license_key, subscription_status, is_active) "
            "VALUES (CAST(:id AS uuid), :name, :code, :license, 'active', true)"
        ), {"id": tenant_id, "name": payload.name, "code": payload.code, "license": payload.license_key})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Şirket kodu veya lisans anahtarı zaten kullanılıyor.") from exc
    return {"id": tenant_id, "name": payload.name, "code": payload.code, "subscription_status": "active"}


@router.post("/users", status_code=201)
def create_user(payload: ManagedUserCreate, principal: dict = Depends(require_roles("super_admin")), db: Session = Depends(get_db)):
    tenant_exists = db.execute(text(
        "SELECT 1 FROM tenants WHERE id::text = :id AND is_active = true AND subscription_status = 'active'"
    ), {"id": payload.tenant_id}).scalar_one_or_none()
    if not tenant_exists:
        raise HTTPException(404, "Aktif lisanslı şirket bulunamadı.")
    user_id = str(uuid4())
    try:
        db.execute(text(
            "INSERT INTO users (id, tenant_id, name, username, role, department, password_hash, is_active) "
            "VALUES (CAST(:id AS uuid), CAST(:tenant_id AS uuid), :name, :email, :role, :department, :password, true)"
        ), {"id": user_id, "tenant_id": payload.tenant_id, "name": payload.name, "email": payload.email,
            "role": payload.role, "department": payload.department, "password": hash_password(payload.password)})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Bu e-posta şirket içinde zaten kayıtlı.") from exc
    return {"id": user_id, "tenant_id": payload.tenant_id, "email": payload.email, "role": payload.role}


@router.get("/master-admin")
def master_admin_dashboard(principal: dict = Depends(require_roles("super_admin")), db: Session = Depends(get_db)):
    tenants = db.scalars(select(Tenant).order_by(Tenant.name)).all()
    return [{"tenant_id": tenant.id, "code": tenant.code, "name": tenant.name, "is_active": tenant.is_active,
             "active_users": db.scalar(select(func.count(User.id)).where(User.tenant_id == tenant.id, User.is_active.is_(True))) or 0,
             "audit_events": db.scalar(select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tenant.id)) or 0} for tenant in tenants]
