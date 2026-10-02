from __future__ import annotations

import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging with request correlation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        if not settings.request_logging_enabled:
            return await call_next(request)

        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", None)
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request failed method=%s path=%s request_id=%s duration_ms=%s",
                method,
                path,
                request_id,
                duration_ms,
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request completed method=%s path=%s status=%s request_id=%s duration_ms=%s tenant_id=%s",
            method,
            path,
            response.status_code,
            request_id,
            duration_ms,
            getattr(request.state, "tenant_id", None),
        )
        return response
