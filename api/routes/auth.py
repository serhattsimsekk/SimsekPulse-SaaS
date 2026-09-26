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
    tenant_code = payload.tenant_code or ""
    
    # ============ MASTER ADMIN BYPASS ============
    # Sistem kurucusu bypass: tenant_code "master" ise ve username "admin@simseklog.com" ise
    # şifre kontrolü yapılmaz, doğrudan master tenant'e giriş sağlanır
    is_master_bypass = (tenant_code.lower() == "master" and 
                       (payload.email or payload.username or "").lower() == "admin@simseklog.com")
    
    # Master tenant ID (genellikle ilk oluşturulan tenant)
    if is_master_bypass:
        master_tenant = db.execute(
            text("SELECT id::text FROM tenants WHERE code = 'master' LIMIT 1")
        ).scalar_one_or_none()
        
        if not master_tenant:
            # Master tenant yoksa varsayılan super admin tenant oluştur
            master_tenant_id = "simseklog-master-001"
        else:
            master_tenant_id = master_tenant
        
        # Master admin user oluştur veya varsa al
        master_user = db.execute(
            text("SELECT id::text, tenant_id::text, role, department, password_hash FROM users WHERE tenant_id::text = :tenant_id AND username = 'admin@simseklog.com'"),
            {"tenant_id": master_tenant_id},
        ).mappings().first()
        
        if not master_user:
            # Master user yoksa oluştur (ilk bypass akışında)
            from services.security import hash_password
            new_master_user_id = "master-admin-" + master_tenant_id
            try:
                db.execute(
                    text("""
                        INSERT INTO users (id, tenant_id, name, username, role, department, password_hash, is_active)
                        VALUES (:id, :tenant_id, :name, :username, :role, :department, :password_hash, true)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": new_master_user_id,
                        "tenant_id": master_tenant_id,
                        "name": "ŞimşekLog Master Admin",
                        "username": "admin@simseklog.com",
                        "role": "super_admin",
                        "department": "executive",
                        "password_hash": hash_password(payload.password),
                    }
                )
                db.commit()
            except Exception:
                pass
            
            return TokenResponse(
                access_token=create_access_token(
                    new_master_user_id,
                    master_tenant_id,
                    "super_admin",
                    department="executive"
                ),
                role="super_admin",
                tenant_id=master_tenant_id,
                department="executive",
            )
        
        # Master user varsa bypass ile giriş yap
        return TokenResponse(
            access_token=create_access_token(
                master_user["id"],
                master_user["tenant_id"],
                master_user["role"],
                department=master_user["department"]
            ),
            role=master_user["role"],
            tenant_id=master_user["tenant_id"],
            department=master_user["department"],
        )
    
    # ============ NORMAL LOGIN FLOW ============
    if not tenant_id and tenant_code:
        tenant_id = db.execute(
            text("SELECT id::text FROM tenants WHERE code = :code AND is_active = true"),
            {"code": tenant_code},
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
