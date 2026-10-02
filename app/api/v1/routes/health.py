from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.database import check_database_connection
from app.schemas.common import APIResponse

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
def health_check() -> APIResponse[dict]:
    return APIResponse(
        data={
            "status": "healthy",
            "app": settings.app_name,
            "environment": settings.app_env,
        }
    )


@router.get("/ready")
def readiness_check(request: Request) -> APIResponse[dict]:
    checker = getattr(request.app.state, "check_database_connection", check_database_connection)
    db_ok = checker()
    status = "ready" if db_ok else "degraded"
    return APIResponse(
        data={
            "status": status,
            "database": "up" if db_ok else "down",
        }
    )
