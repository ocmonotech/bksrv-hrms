from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.schemas.common import ErrorDetail, ErrorResponse


class RateLimitStore(Protocol):
    def hit(self, key: str, window: int, max_requests: int) -> tuple[bool, int]:
        """Return (allowed, remaining)."""


class MemoryRateLimitStore:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, window: int, max_requests: int) -> tuple[bool, int]:
        now = time.time()
        bucket = self._requests[key]
        while bucket and bucket[0] <= now - window:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False, 0
        bucket.append(now)
        return True, max(0, max_requests - len(bucket))


class RedisRateLimitStore:
    def __init__(self, redis_url: str) -> None:
        from redis import Redis

        self.client = Redis.from_url(redis_url, decode_responses=True)

    def hit(self, key: str, window: int, max_requests: int) -> tuple[bool, int]:
        redis_key = f"ratelimit:{key}"
        count = self.client.incr(redis_key)
        if count == 1:
            self.client.expire(redis_key, window)
        remaining = max(0, max_requests - int(count))
        return int(count) <= max_requests, remaining


_memory_store = MemoryRateLimitStore()
_redis_store: RedisRateLimitStore | None = None


def _get_store() -> RateLimitStore:
    global _redis_store
    settings = get_settings()
    if settings.rate_limit_backend == "redis" and settings.redis_url:
        if _redis_store is None:
            _redis_store = RedisRateLimitStore(settings.redis_url)
        return _redis_store
    return _memory_store


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting with Redis (multi-instance) or in-memory fallback."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        store = _get_store()
        allowed, remaining = store.hit(
            client_ip,
            settings.rate_limit_window_seconds,
            settings.rate_limit_max_requests,
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error=ErrorDetail(
                        code="rate_limit_exceeded",
                        message="Too many requests. Please try again later.",
                        details={"retry_after_seconds": settings.rate_limit_window_seconds},
                    )
                ).model_dump(),
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
