from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from database.models import Tenant, User
from services.security import create_access_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Kimlik & Yetki"])


class LoginRequest(BaseModel):
    tenant_id: str | None = None
    tenant_code: str | None = None
    email: str | None = Field(default=None, min_length=3, max_length=160)
    username: str | None = Field(default=None, min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    tenant_id: str
    department: str | None = None


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    tenant_id = payload.tenant_id
    if not tenant_id and payload.tenant_code:
        tenant_id = db.execute(
            text("SELECT id::text FROM tenants WHERE code = :code AND is_active = true"),
            {"code": payload.tenant_code},
        ).scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(422, "tenant_id veya tenant_code zorunludur.")
    username = payload.email or payload.username
    if not username:
        raise HTTPException(422, "E-posta zorunludur.")
    tenant = db.execute(
        text("SELECT id::text FROM tenants WHERE id::text = :id AND is_active = true AND subscription_status = 'active'"),
        {"id": tenant_id},
    ).scalar_one_or_none()
    if not tenant:
        raise HTTPException(403, "Şirket hesabı aktif bir lisansa sahip değil.")
    row = db.execute(
        text("SELECT id::text, tenant_id::text, role, department, password_hash FROM users WHERE tenant_id::text = :tenant_id AND username = :username AND is_active = true"),
        {"tenant_id": tenant_id, "username": username},
    ).mappings().first()
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "Kullanıcı adı veya şifre hatalı.")
    return TokenResponse(
        access_token=create_access_token(row["id"], row["tenant_id"], row["role"], department=row["department"]),
        role=row["role"],
        tenant_id=row["tenant_id"],
        department=row["department"],
    )
