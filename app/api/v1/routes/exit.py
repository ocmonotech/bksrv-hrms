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
from app.schemas.exit import (
    ExitClearanceResponse,
    ExitClearanceUpdate,
    ExitInterviewCreate,
    ExitInterviewResponse,
    ExitInterviewUpdate,
    ResignationCreate,
    ResignationResponse,
    ResignationUpdate,
)
from app.services.extended_modules_service import ExitService

router = APIRouter(prefix="/exit", tags=["Exit"])


def check_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.EMPLOYEES, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> ExitService:
    return ExitService(db)


@router.get("/resignations", response_model=PaginatedResponse[ResignationResponse])
def list_resignations(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExitService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.resignations.list(ctx.tenant_id, page=page, page_size=page_size)


@router.post("/resignations", response_model=APIResponse[ResignationResponse], status_code=201)
def create_resignation(
    request: Request,
    payload: ResignationCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExitService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_resignation(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Resignation created")


@router.put("/resignations/{resignation_id}", response_model=APIResponse[ResignationResponse])
def update_resignation(
    resignation_id: UUID,
    request: Request,
    payload: ResignationUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExitService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_resignation(
        ctx.tenant_id, resignation_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Resignation updated")


@router.get("/resignations/{resignation_id}/clearance", response_model=APIResponse[ExitClearanceResponse])
def get_clearance(
    resignation_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExitService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_clearance(ctx.tenant_id, resignation_id))


@router.put("/resignations/{resignation_id}/clearance", response_model=APIResponse[ExitClearanceResponse])
def update_clearance(
    resignation_id: UUID,
    request: Request,
    payload: ExitClearanceUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExitService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_clearance(
        ctx.tenant_id, resignation_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Exit clearance updated")


@router.get("/interviews", response_model=PaginatedResponse[ExitInterviewResponse])
def list_interviews(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExitService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.interviews.list(ctx.tenant_id, page=page, page_size=page_size)


@router.post("/interviews", response_model=APIResponse[ExitInterviewResponse], status_code=201)
def create_interview(
    request: Request,
    payload: ExitInterviewCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExitService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_interview(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Exit interview created")


@router.put("/interviews/{interview_id}", response_model=APIResponse[ExitInterviewResponse])
def update_interview(
    interview_id: UUID,
    request: Request,
    payload: ExitInterviewUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExitService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_interview(
        ctx.tenant_id, interview_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Exit interview updated")
