from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.routes.company_setup.crud_factory import require_tenant_scope
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.dashboard import DashboardStatsResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def check_dashboard_permission(ctx: TenantContext, current_user: User, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.DASHBOARD, PermissionAction.VIEW, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("/stats", response_model=APIResponse[DashboardStatsResponse])
def dashboard_stats(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DashboardService = Depends(get_service),
):
    check_dashboard_permission(ctx, current_user, db)
    return APIResponse(data=service.get_stats(ctx.tenant_id))
