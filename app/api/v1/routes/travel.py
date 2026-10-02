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
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.travel import (
    TravelPolicyCreate,
    TravelPolicyResponse,
    TravelPolicyUpdate,
    TravelRequestCreate,
    TravelRequestResponse,
    TravelRequestUpdate,
)
from app.services.extended_modules_service import TravelService

router = APIRouter(prefix="/travel", tags=["Travel"])


def check_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.EXPENSES, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> TravelService:
    return TravelService(db)


@router.get("/policies", response_model=PaginatedResponse[TravelPolicyResponse])
def list_policies(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TravelService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.policies.list(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@router.post("/policies", response_model=APIResponse[TravelPolicyResponse], status_code=201)
def create_policy(
    request: Request,
    payload: TravelPolicyCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TravelService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.policies.create(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Travel policy created")


@router.put("/policies/{policy_id}", response_model=APIResponse[TravelPolicyResponse])
def update_policy(
    policy_id: UUID,
    request: Request,
    payload: TravelPolicyUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TravelService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.policies.update(ctx.tenant_id, policy_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Travel policy updated")


@router.get("/requests", response_model=PaginatedResponse[TravelRequestResponse])
def list_requests(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TravelService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.requests.list(ctx.tenant_id, page=page, page_size=page_size, search=search)


@router.post("/requests", response_model=APIResponse[TravelRequestResponse], status_code=201)
def create_request(
    request: Request,
    payload: TravelRequestCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TravelService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_request(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Travel request created")


@router.put("/requests/{request_id}", response_model=APIResponse[TravelRequestResponse])
def update_request(
    request_id: UUID,
    request: Request,
    payload: TravelRequestUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TravelService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_request(ctx.tenant_id, request_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Travel request updated")
