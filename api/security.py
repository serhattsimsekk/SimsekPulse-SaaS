from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from services.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def current_principal(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    try:
        claims = decode_access_token(token)
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Geçersiz veya süresi dolmuş token.") from exc
    if not claims.get("sub") or not claims.get("tenant_id") or not claims.get("role"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token kapsamı eksik.")
    return claims


def tenant_principal(request: Request, principal: Annotated[dict, Depends(current_principal)]) -> dict:
    header_tenant = request.headers.get("x-tenant-id")
    if header_tenant and header_tenant != principal["tenant_id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tenant başlığı token tenant_id ile eşleşmiyor.")
    return principal


def require_roles(*roles: str):
    def dependency(principal: Annotated[dict, Depends(current_principal)]) -> dict:
        if principal["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu işlem için rol yetkisi yok.")
        return principal

    return dependency


def require_departments(*departments: str):
    def dependency(principal: Annotated[dict, Depends(current_principal)]) -> dict:
        if principal.get("role") == "super_admin" or principal.get("department") in departments:
            return principal
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu departman için yetkiniz yok.")
    return dependency
