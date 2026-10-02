from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_meta
from app.api.v1.routes.company_setup.crud_factory import require_tenant_scope
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.assets import (
    AssetAssignmentCreate,
    AssetAssignmentResponse,
    AssetAssignmentUpdate,
    AssetCreate,
    AssetResponse,
    AssetUpdate,
)
from app.schemas.common import APIResponse, PaginatedResponse
from app.services.extended_modules_service import AssetsService

router = APIRouter(prefix="/assets", tags=["Assets"])


def check_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.ASSETS, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> AssetsService:
    return AssetsService(db)


@router.get("", response_model=PaginatedResponse[AssetResponse])
def list_assets(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AssetsService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.assets.list(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@router.post("", response_model=APIResponse[AssetResponse], status_code=201)
def create_asset(
    request: Request,
    payload: AssetCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AssetsService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.assets.create(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Asset created")


@router.put("/{asset_id}", response_model=APIResponse[AssetResponse])
def update_asset(
    asset_id: UUID,
    request: Request,
    payload: AssetUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AssetsService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.assets.update(ctx.tenant_id, asset_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Asset updated")


assignments_router = APIRouter(prefix="/assignments", tags=["Asset Assignments"])


@assignments_router.get("", response_model=PaginatedResponse[AssetAssignmentResponse])
def list_assignments(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AssetsService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.assignments.list(ctx.tenant_id, page=page, page_size=page_size)


@assignments_router.post("", response_model=APIResponse[AssetAssignmentResponse], status_code=201)
def create_assignment(
    request: Request,
    payload: AssetAssignmentCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AssetsService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_assignment(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Asset assignment created")


@assignments_router.put("/{assignment_id}", response_model=APIResponse[AssetAssignmentResponse])
def update_assignment(
    assignment_id: UUID,
    request: Request,
    payload: AssetAssignmentUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AssetsService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_assignment(ctx.tenant_id, assignment_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Asset assignment updated")


router.include_router(assignments_router)
