from __future__ import annotations

import os
import secrets
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from services.security import create_access_token, hash_password, verify_password, decode_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Kimlik & Yetki"])

# Professional Master Bootstrap Configuration
MASTER_BOOTSTRAP_ENABLED = os.getenv("MASTER_BOOTSTRAP_ENABLED", "false").lower() == "true"
MASTER_BOOTSTRAP_EMAIL = (os.getenv("MASTER_BOOTSTRAP_EMAIL", "admin@simseklog.com") or "").lower().strip()
MASTER_BOOTSTRAP_TENANT_CODE = (os.getenv("MASTER_BOOTSTRAP_TENANT_CODE", "master") or "").lower().strip()
MASTER_BOOTSTRAP_PASSWORD = os.getenv("MASTER_BOOTSTRAP_PASSWORD", "ChangeMe123!")


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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: str
    tenant_code: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=256)


class CreateTenantRequest(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    code: str = Field(min_length=3, max_length=40)
    admin_name: str = Field(min_length=3, max_length=160)
    admin_email: str = Field(min_length=5, max_length=160)
    admin_password: str = Field(min_length=8, max_length=256)


class CreateUserRequest(BaseModel):
    tenant_id: str
    name: str = Field(min_length=3, max_length=160)
    email: str = Field(min_length=5, max_length=160)
    role: str = Field(default="user")
    department: str | None = None


def _normalize_email(value: str | None) -> str | None:
    return (value or "").strip().lower() or None


def _get_client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _get_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _log_auth_event(
    db: Session,
    tenant_id: str | None,
    user_id: str | None,
    event_type: str,
    username: str | None,
    email: str | None,
    ip_address: str | None,
    user_agent: str | None,
    details: dict[str, Any] | None,
    status: str = "success",
) -> None:
    """Log authentication events for audit trail."""
    try:
        db.execute(
            text("""
                INSERT INTO auth_audit_log (
                    id, tenant_id, user_id, event_type, username, email, ip_address, user_agent, details_json, status
                )
                VALUES (
                    gen_random_uuid()::text,
                    :tenant_id,
                    :user_id,
                    :event_type,
                    :username,
                    :email,
                    :ip_address,
                    :user_agent,
                    :details,
                    :status
                )
            """),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "event_type": event_type,
                "username": username,
                "email": email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "details": json.dumps(details or {}),
                "status": status,
            },
        )
    except Exception as e:
        print(f"[AUTH_AUDIT] Error logging event: {e}")


def _generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def _hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _issue_reset_token(db: Session, user_id: str, tenant_id: str) -> str:
    """Create a password reset token."""
    token = _generate_reset_token()
    token_hash = _hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

    db.execute(
        text("""
            INSERT INTO password_reset_tokens (id, tenant_id, user_id, token_hash, expires_at)
            VALUES (gen_random_uuid()::text, :tenant_id, :user_id, :token_hash, :expires_at)
        """),
        {"tenant_id": tenant_id, "user_id": user_id, "token_hash": token_hash, "expires_at": expires_at},
    )
    db.commit()
    return token


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Professional login endpoint with master bootstrap support.
    Bootstrap only works when MASTER_BOOTSTRAP_ENABLED=true and credentials match environment config.
    """
    tenant_code = (payload.tenant_code or "").strip().lower()
    username_input = _normalize_email(payload.email) or (payload.username or "").strip().lower()
    ip_address = _get_client_ip(request)
    user_agent = _get_user_agent(request)

    # Safe master bootstrap - only when explicitly enabled via environment
    if (
        MASTER_BOOTSTRAP_ENABLED
        and tenant_code == MASTER_BOOTSTRAP_TENANT_CODE
        and username_input == MASTER_BOOTSTRAP_EMAIL
    ):
        tenant_id = db.execute(
            text("""
                SELECT id::text
                FROM tenants
                WHERE LOWER(code) = LOWER(:code) AND is_active = true
                LIMIT 1
            """),
            {"code": MASTER_BOOTSTRAP_TENANT_CODE},
        ).scalar_one_or_none()

        if not tenant_id:
            _log_auth_event(
                db, None, None, "bootstrap_failure", MASTER_BOOTSTRAP_EMAIL, MASTER_BOOTSTRAP_EMAIL, ip_address, user_agent,
                {"reason": "master_tenant_not_found"}, "failure"
            )
            db.commit()
            raise HTTPException(403, "Master bootstrap tenant bulunamadı.")

        # `users` tablosundaki RLS politikası, doğrulanmış tenant_id işlem-yerel
        # olarak set edilmeden sorgulandığında satırı görünmez kılar (bkz. normal
        # login akışındaki aynı gerekçe).
        db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )

        user = db.execute(
            text("""
                SELECT id::text, tenant_id::text, role, department, password_hash
                FROM users
                WHERE LOWER(username) = LOWER(:username)
                  AND tenant_id::text = :tenant_id
                  AND is_active = true
                LIMIT 1
            """),
            {"username": MASTER_BOOTSTRAP_EMAIL, "tenant_id": tenant_id},
        ).mappings().first()

        if user is None:
            raise HTTPException(403, "Master bootstrap kullanıcısı yapılandırılmadı. Sistem yöneticisine başvurun.")

        if not verify_password(payload.password, user["password_hash"]):
            _log_auth_event(
                db, tenant_id, user["id"], "bootstrap_failure", MASTER_BOOTSTRAP_EMAIL, MASTER_BOOTSTRAP_EMAIL, ip_address, user_agent,
                {"reason": "bad_password"}, "failure"
            )
            db.commit()
            raise HTTPException(401, "Bootstrap şifresi hatalı.")

        token = create_access_token(user["id"], user["tenant_id"], user["role"], department=user["department"])
        _log_auth_event(
            db, tenant_id, user["id"], "bootstrap_success", user["username"], MASTER_BOOTSTRAP_EMAIL, ip_address, user_agent,
            {}, "success"
        )
        db.commit()

        return TokenResponse(
            access_token=token,
            role=user["role"],
            tenant_id=user["tenant_id"],
            department=user["department"],
        )

    # ============ NORMAL LOGIN FLOW ============
    tenant_id = payload.tenant_id
    if not tenant_id and payload.tenant_code:
        # Şirket kodu karşılaştırması büyük/küçük harf ve baştaki/sondaki
        # boşluk farklarından etkilenmemeli.
        tenant_id = db.execute(
            text("SELECT id::text FROM tenants WHERE LOWER(code) = LOWER(:code) AND is_active = true LIMIT 1"),
            {"code": payload.tenant_code.strip()},
        ).scalar_one_or_none()

    if not tenant_id:
        raise HTTPException(422, "tenant_id veya tenant_code zorunludur.")

    username = payload.email or payload.username
    if not username:
        raise HTTPException(422, "E-posta veya kullanıcı adı zorunludur.")
    username = username.strip()

    tenant = db.execute(
        text("""
            SELECT id::text
            FROM tenants
            WHERE id::text = :id AND is_active = true AND subscription_status = 'active'
        """),
        {"id": tenant_id},
    ).scalar_one_or_none()

    if not tenant:
        _log_auth_event(db, tenant_id, None, "login_failure", username, username, ip_address, user_agent, {"reason": "tenant_inactive"}, "failure")
        db.commit()
        raise HTTPException(403, "Şirket hesabı aktif bir lisansa sahip değil.")

    # `users` tablosunda tenant_id bazlı Row-Level Security politikası var.
    # Kimlik doğrulamadan önce (JWT/istek bağlamı olmadan) bu oturum için
    # Postgres tarafında "app.tenant_id" ayarlanmazsa RLS, şifre doğru olsa
    # dahi satırı görünmez kılar. Bu yüzden sorgudan önce doğrulanmış
    # tenant_id'yi işlem-yerel (is_local=true) olarak açıkça set ediyoruz.
    db.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": tenant_id},
    )

    row = db.execute(
        text("""
            SELECT id::text, tenant_id::text, role, department, password_hash, failed_login_attempts, locked_until
            FROM users
            WHERE tenant_id::text = :tenant_id
              AND LOWER(username) = LOWER(:username)
              AND is_active = true
            LIMIT 1
        """),
        {"tenant_id": tenant_id, "username": username},
    ).mappings().first()

    if not row:
        _log_auth_event(db, tenant_id, None, "login_failure", username, username, ip_address, user_agent, {"reason": "user_not_found"}, "failure")
        db.commit()
        raise HTTPException(401, "Kullanıcı adı veya şifre hatalı.")

    # Check account lockout
    if row["locked_until"] and row["locked_until"] > datetime.now(timezone.utc):
        _log_auth_event(
            db, tenant_id, row["id"], "login_failure", row["username"], username, ip_address, user_agent,
            {"reason": "account_locked"}, "failure"
        )
        db.commit()
        raise HTTPException(403, "Hesabınız geçici olarak kilitlenmiştir. Lütfen daha sonra tekrar deneyin.")

    # Verify password
    if not verify_password(payload.password, row["password_hash"]):
        failed_attempts = (row["failed_login_attempts"] or 0) + 1
        locked_until = None
        if failed_attempts >= 5:
            locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

        db.execute(
            text("""
                UPDATE users
                SET failed_login_attempts = :failed_attempts,
                    locked_until = :locked_until
                WHERE id::text = :user_id
            """),
            {"failed_attempts": failed_attempts, "locked_until": locked_until, "user_id": row["id"]},
        )
        _log_auth_event(
            db, tenant_id, row["id"], "login_failure", row["username"], username, ip_address, user_agent,
            {"reason": "bad_password", "attempt": failed_attempts}, "failure"
        )
        db.commit()
        raise HTTPException(401, "Kullanıcı adı veya şifre hatalı.")

    # Reset failed attempts on successful login
    db.execute(
        text("""
            UPDATE users
            SET failed_login_attempts = 0,
                locked_until = NULL
            WHERE id::text = :user_id
        """),
        {"user_id": row["id"]},
    )

    token = create_access_token(row["id"], row["tenant_id"], row["role"], department=row["department"])
    _log_auth_event(
        db, tenant_id, row["id"], "login_success", row["username"], username, ip_address, user_agent,
        {"method": "password"}, "success"
    )
    db.commit()

    return TokenResponse(
        access_token=token,
        role=row["role"],
        tenant_id=row["tenant_id"],
        department=row["department"],
    )


@router.post("/password/change")
def change_password(payload: ChangePasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Allow authenticated users to change their password."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Token gerekli.")

    token = auth.split(" ", 1)[1].strip()
    try:
        claims = decode_access_token(token)
    except Exception:
        raise HTTPException(401, "Geçersiz token.")

    user = db.execute(
        text("""
            SELECT id::text, tenant_id::text, password_hash, username
            FROM users
            WHERE id::text = :user_id AND is_active = true
        """),
        {"user_id": claims.get("sub")},
    ).mappings().first()

    if not user:
        raise HTTPException(401, "Kullanıcı bulunamadı.")

    if not verify_password(payload.current_password, user["password_hash"]):
        _log_auth_event(
            db, user["tenant_id"], user["id"], "password_change_failure", user["username"], user["username"],
            _get_client_ip(request), _get_user_agent(request), {"reason": "bad_current_password"}, "failure"
        )
        db.commit()
        raise HTTPException(401, "Geçerli mevcut şifre hatalı.")

    new_hash = hash_password(payload.new_password)

    # Store old password in history
    db.execute(
        text("""
            INSERT INTO user_password_history (id, tenant_id, user_id, password_hash_old, changed_by_user_id, ip_address)
            VALUES (gen_random_uuid()::text, :tenant_id, :user_id, :password_hash_old, :changed_by_user_id, :ip_address)
        """),
        {
            "tenant_id": user["tenant_id"],
            "user_id": user["id"],
            "password_hash_old": user["password_hash"],
            "changed_by_user_id": user["id"],
            "ip_address": _get_client_ip(request),
        },
    )

    db.execute(
        text("""
            UPDATE users
            SET password_hash = :new_hash,
                last_password_change_at = now(),
                password_expires_at = now() + interval '90 days',
                failed_login_attempts = 0,
                locked_until = NULL
            WHERE id::text = :user_id
        """),
        {"user_id": user["id"], "new_hash": new_hash},
    )

    _log_auth_event(
        db, user["tenant_id"], user["id"], "password_change_success", user["username"], user["username"],
        _get_client_ip(request), _get_user_agent(request), {}, "success"
    )
    db.commit()

    return {"status": "ok", "message": "Şifre başarıyla değiştirildi."}


@router.post("/password/forgot")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Request password reset token via email."""
    email = _normalize_email(payload.email)
    if not email:
        raise HTTPException(422, "Geçerli e-posta gerekli.")

    user = db.execute(
        text("""
            SELECT id::text, tenant_id::text, username, name
            FROM users
            WHERE LOWER(username) = :email AND is_active = true
            LIMIT 1
        """),
        {"email": email},
    ).mappings().first()

    if not user:
        _log_auth_event(
            db, None, None, "password_reset_request_failure", email, email,
            _get_client_ip(request), _get_user_agent(request), {"reason": "user_not_found"}, "failure"
        )
        db.commit()
        # Return success even if user not found (security best practice)
        return {
            "status": "ok",
            "message": "Şifre sıfırlama linki gönderildi (eğer bu e-posta sistemde varsa).",
            "expires_in_minutes": 120,
        }

    if payload.tenant_code:
        tenant = db.execute(
            text("SELECT id::text FROM tenants WHERE LOWER(code) = LOWER(:code) AND is_active = true LIMIT 1"),
            {"code": payload.tenant_code},
        ).scalar_one_or_none()

        if tenant and tenant != user["tenant_id"]:
            raise HTTPException(403, "Bu şirket içinde bu kullanıcı bulunamadı.")

    token = _issue_reset_token(db, user["id"], user["tenant_id"])
    _log_auth_event(
        db, user["tenant_id"], user["id"], "password_reset_token_issued", user["username"], email,
        _get_client_ip(request), _get_user_agent(request), {}, "success"
    )

    # In production, send token via email service (SES, SendGrid, etc.)
    # For now, return token for development/test environments
    return {
        "status": "ok",
        "message": "Şifre sıfırlama linki gönderildi.",
        "token": token,
        "expires_in_minutes": 120,
    }


@router.post("/password/reset")
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Reset password using a valid reset token."""
    token = payload.token.strip()
    if not token:
        raise HTTPException(422, "Token gerekli.")

    token_hash = _hash_token(token)
    row = db.execute(
        text("""
            SELECT id::text, tenant_id::text, user_id, expires_at
            FROM password_reset_tokens
            WHERE token_hash = :token_hash
              AND used_at IS NULL
              AND expires_at > now()
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"token_hash": token_hash},
    ).mappings().first()

    if not row:
        raise HTTPException(400, "Geçersiz veya süresi dolmuş şifre sıfırlama tokeni.")

    user = db.execute(
        text("""
            SELECT id::text, tenant_id::text, password_hash, username
            FROM users
            WHERE id::text = :user_id AND is_active = true
        """),
        {"user_id": row["user_id"]},
    ).mappings().first()

    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı.")

    new_hash = hash_password(payload.new_password)

    # Store old password in history
    db.execute(
        text("""
            INSERT INTO user_password_history (id, tenant_id, user_id, password_hash_old, ip_address)
            VALUES (gen_random_uuid()::text, :tenant_id, :user_id, :password_hash_old, :ip_address)
        """),
        {
            "tenant_id": user["tenant_id"],
            "user_id": user["id"],
            "password_hash_old": user["password_hash"],
            "ip_address": _get_client_ip(request),
        },
    )

    db.execute(
        text("""
            UPDATE users
            SET password_hash = :new_hash,
                last_password_change_at = now(),
                password_expires_at = now() + interval '90 days',
                failed_login_attempts = 0,
                locked_until = NULL
            WHERE id::text = :user_id
        """),
        {"user_id": user["id"], "new_hash": new_hash},
    )

    db.execute(
        text("""
            UPDATE password_reset_tokens
            SET used_at = now(),
                used_ip_address = :ip
            WHERE id::text = :token_id
        """),
        {"token_id": row["id"], "ip": _get_client_ip(request)},
    )

    _log_auth_event(
        db, user["tenant_id"], user["id"], "password_reset_success", user["username"], user["username"],
        _get_client_ip(request), _get_user_agent(request), {}, "success"
    )
    db.commit()

    return {"status": "ok", "message": "Şifre başarıyla sıfırlandı. Lütfen yeni şifrenizle giriş yapın."}


@router.post("/tenants/create")
def create_tenant(payload: CreateTenantRequest, request: Request, db: Session = Depends(get_db)):
    """
    Create a new tenant with admin user.
    Only accessible to super_admin or master admin.
    """
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Token gerekli.")

    token = auth.split(" ", 1)[1].strip()
    try:
        claims = decode_access_token(token)
    except Exception:
        raise HTTPException(401, "Geçersiz token.")

    if claims.get("role") not in {"super_admin", "admin"}:
        raise HTTPException(403, "Yalnızca master admin veya admin yetkisi ile yeni tenant oluşturabilirsiniz.")

    # Check if tenant code already exists
    existing = db.execute(
        text("SELECT id FROM tenants WHERE LOWER(code) = LOWER(:code) LIMIT 1"),
        {"code": payload.code},
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(409, "Bu şirket kodu zaten kullanılıyor.")

    tenant_id = str(secrets.token_hex(8))

    db.execute(
        text("""
            INSERT INTO tenants (id, name, code, is_active, subscription_status)
            VALUES (:id, :name, :code, true, 'active')
        """),
        {"id": tenant_id, "name": payload.name, "code": payload.code.lower()},
    )

    admin_user_id = str(secrets.token_hex(12))
    admin_hash = hash_password(payload.admin_password)

    db.execute(
        text("""
            INSERT INTO users (
                id, tenant_id, name, username, role, department, password_hash, is_active,
                last_password_change_at, password_expires_at
            )
            VALUES (
                :id, :tenant_id, :name, :username, :role, :department, :password_hash, true,
                now(), now() + interval '90 days'
            )
        """),
        {
            "id": admin_user_id,
            "tenant_id": tenant_id,
            "name": payload.admin_name,
            "username": payload.admin_email.lower(),
            "role": "admin",
            "department": "executive",
            "password_hash": admin_hash,
        },
    )

    _log_auth_event(
        db, tenant_id, admin_user_id, "tenant_created", payload.admin_email, payload.admin_email,
        _get_client_ip(request), _get_user_agent(request), {"tenant_id": tenant_id, "tenant_name": payload.name}, "success"
    )
    db.commit()

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "admin_user_id": admin_user_id,
        "message": "Yeni tenant ve admin kullanıcı başarıyla oluşturuldu.",
    }


@router.post("/users/create")
def create_user(payload: CreateUserRequest, request: Request, db: Session = Depends(get_db)):
    """
    Create a new user in a tenant.
    Only accessible to admin users of that tenant.
    """
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Token gerekli.")

    token = auth.split(" ", 1)[1].strip()
    try:
        claims = decode_access_token(token)
    except Exception:
        raise HTTPException(401, "Geçersiz token.")

    # Check tenant access
    if claims.get("tenant_id") != payload.tenant_id and claims.get("role") not in {"super_admin", "admin"}:
        raise HTTPException(403, "Bu tenant'a erişim izniniz yok.")

    # Verify user has admin role
    user = db.execute(
        text("""
            SELECT id, role, tenant_id FROM users
            WHERE id::text = :user_id AND is_active = true
        """),
        {"user_id": claims.get("sub")},
    ).mappings().first()

    if not user or (user["role"] not in {"admin", "super_admin"} or str(user["tenant_id"]) != payload.tenant_id):
        if user["role"] not in {"super_admin"}:
            raise HTTPException(403, "Bu işlem için yeterli izniniz yok.")

    # Check if user already exists
    existing = db.execute(
        text("""
            SELECT id FROM users
            WHERE tenant_id::text = :tenant_id AND LOWER(username) = LOWER(:email)
            LIMIT 1
        """),
        {"tenant_id": payload.tenant_id, "email": payload.email},
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(409, "Bu e-posta adresi zaten kullanılıyor.")

    new_user_id = str(secrets.token_hex(12))
    temp_password = secrets.token_urlsafe(12)
    password_hash = hash_password(temp_password)

    db.execute(
        text("""
            INSERT INTO users (
                id, tenant_id, name, username, role, department, password_hash, is_active,
                last_password_change_at, password_expires_at
            )
            VALUES (
                :id, :tenant_id, :name, :username, :role, :department, :password_hash, true,
                now(), now() + interval '7 days'
            )
        """),
        {
            "id": new_user_id,
            "tenant_id": payload.tenant_id,
            "name": payload.name,
            "username": payload.email.lower(),
            "role": payload.role,
            "department": payload.department,
            "password_hash": password_hash,
        },
    )

    _log_auth_event(
        db, payload.tenant_id, new_user_id, "user_created", payload.email, payload.email,
        _get_client_ip(request), _get_user_agent(request),
        {"created_by": claims.get("sub"), "role": payload.role, "department": payload.department}, "success"
    )
    db.commit()

    return {
        "status": "ok",
        "user_id": new_user_id,
        "temp_password": temp_password,
        "message": "Yeni kullanıcı başarıyla oluşturuldu. Kullanıcıya geçici şifreyi iletin.",
        "note": "Kullanıcı ilk girişinde şifresi değiştirmek zorunda olacaktır.",
    }
