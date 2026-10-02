from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import check_database_connection
from app.core.logging_config import configure_logging
from app.middleware.audit_logging import AuditLoggingMiddleware
from app.middleware.error_handler import register_exception_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.tenant_context import TenantContextMiddleware
from app.workers import start_scheduler, stop_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    import app.workers  # noqa: F401 — register background tasks

    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "X-Response-Time-Ms", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(AuditLoggingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["Root"])
    def root() -> dict:
        return {
            "app": settings.app_name,
            "version": "1.0.0",
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
            "ready": f"{settings.api_v1_prefix}/ready",
        }

    app.state.check_database_connection = check_database_connection

    return app
