from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from database.base import tenant_bypass, tenant_context
from services.security import decode_access_token


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        protected_api = request.url.path.startswith("/api/v1/") and request.url.path not in {"/api/v1/auth/login", "/api/v1/system/health"} and not request.url.path.startswith("/api/v1/branding/") and not request.url.path.startswith("/api/v1/tracking/public/")
        token = request.headers.get("authorization", "")
        header_tenant = request.headers.get("x-tenant-id")
        tenant_id = None
        bypass = False
        claims = {}
        if token.lower().startswith("bearer "):
            try:
                claims = decode_access_token(token[7:].strip())
                token_tenant = claims.get("tenant_id")
                if header_tenant and header_tenant != token_tenant:
                    return JSONResponse({"detail": "Tenant başlığı JWT tenant bilgisiyle eşleşmiyor."}, status_code=403)
                tenant_id = token_tenant
                bypass = claims.get("role") == "super_admin"
            except Exception:
                tenant_id = None
        if protected_api and not tenant_id:
            return JSONResponse({"detail": "Geçerli JWT erişim belirteci zorunludur."}, status_code=401)
        if protected_api and claims:
            role = claims.get("role")
            department = claims.get("department")
            if role not in {"super_admin", "admin"}:
                restricted = (
                    (request.url.path.startswith("/api/v1/finance") and department not in {"finance", "executive"}) or
                    (request.url.path.startswith("/api/v1/operations/maintenance") and department not in {"maintenance", "operations"}) or
                    (request.url.path.startswith("/api/v1/ocr") and department not in {"driver", "operations", "executive"}) or
                    (request.url.path.startswith("/api/v1/shifts") and department not in {"driver", "operations", "executive"})
                )
                if restricted:
                    return JSONResponse({"detail": "Bu departman için yetkiniz yok."}, status_code=403)
        marker = tenant_context.set(tenant_id)
        bypass_marker = tenant_bypass.set(bypass)
        try:
            response = await call_next(request)
            if tenant_id:
                response.headers["X-Tenant-ID"] = tenant_id
            return response
        finally:
            tenant_context.reset(marker)
            tenant_bypass.reset(bypass_marker)
