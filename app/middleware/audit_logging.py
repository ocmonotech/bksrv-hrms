from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Optional
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import safe_decode_token
from app.services.audit_service import AuditService

logger = logging.getLogger("app.audit")

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIP_PATH_PREFIXES = ("/docs", "/redoc", "/openapi.json", "/api/v1/health", "/api/v1/ready")


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Persist lightweight HTTP audit entries for mutating API calls."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        settings = get_settings()
        if not settings.audit_middleware_enabled:
            return response

        path = request.url.path
        if request.method not in MUTATING_METHODS or any(path.startswith(p) for p in SKIP_PATH_PREFIXES):
            return response

        actor_id = self._resolve_actor_id(request)
        tenant_id = getattr(request.state, "tenant_id", None)
        request_id = getattr(request.state, "request_id", None)

        db = SessionLocal()
        try:
            AuditService(db).log(
                f"http.{request.method.lower()}",
                actor_id=actor_id,
                tenant_id=tenant_id,
                resource_type="http",
                resource_id=path,
                details={
                    "status_code": response.status_code,
                    "request_id": request_id,
                    "query": str(request.url.query) if request.url.query else None,
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                severity="info" if response.status_code < 400 else "warning",
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("audit middleware failed for %s %s", request.method, path)
        finally:
            db.close()

        return response

    @staticmethod
    def _resolve_actor_id(request: Request) -> Optional[UUID]:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        payload = safe_decode_token(auth_header[7:])
        if not payload or not payload.get("sub"):
            return None
        try:
            return UUID(str(payload["sub"]))
        except ValueError:
            return None
