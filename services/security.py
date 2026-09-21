from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

ALGORITHM = "HS256"
SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
if not SECRET:
    SECRET = "development-only-change-me"
TOKEN_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256$240000${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded or not encoded.startswith("pbkdf2_sha256$"):
        return False
    try:
        _, rounds, salt, expected = encoded.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds)
        )
        return hmac.compare_digest(
            base64.urlsafe_b64encode(digest).decode(), expected
        )
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, tenant_id: str, role: str, department: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "department": department,
            "iat": now,
            "exp": now + timedelta(minutes=TOKEN_MINUTES),
        },
        SECRET,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
