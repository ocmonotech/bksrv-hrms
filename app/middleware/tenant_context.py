from __future__ import annotations

from typing import Optional
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import safe_decode_token


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Detects tenant and company context from headers and JWT.
    Attaches tenant_id, company_id, role, role_id to request.state.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.tenant_id = None
        request.state.company_id = None
        request.state.role = None
        request.state.role_id = None
        request.state.is_super_admin = False

        header_tenant = request.headers.get("X-Tenant-Id")
        header_company = request.headers.get("X-Company-Id")

        if header_tenant:
            try:
                request.state.tenant_id = UUID(header_tenant)
            except ValueError:
                request.state.tenant_id = None

        if header_company:
            try:
                request.state.company_id = UUID(header_company)
            except ValueError:
                request.state.company_id = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = safe_decode_token(token)
            if payload and payload.get("type") == "access":
                request.state.is_super_admin = bool(payload.get("is_super_admin"))
                if payload.get("role"):
                    request.state.role = payload["role"]
                if payload.get("role_id"):
                    try:
                        request.state.role_id = UUID(str(payload["role_id"]))
                    except ValueError:
                        pass
                if not request.state.tenant_id and payload.get("tenant_id"):
                    try:
                        request.state.tenant_id = UUID(str(payload["tenant_id"]))
                    except ValueError:
                        pass
                if not request.state.company_id and payload.get("company_id"):
                    try:
                        request.state.company_id = UUID(str(payload["company_id"]))
                    except ValueError:
                        pass

        return await call_next(request)
