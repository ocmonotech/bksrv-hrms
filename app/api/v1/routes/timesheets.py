from __future__ import annotations

from datetime import date
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
from app.schemas.timesheets import (
    TimesheetDashboardStats,
    TimesheetEntryCreate,
    TimesheetEntryResponse,
    TimesheetEntryUpdate,
    TimesheetProjectCreate,
    TimesheetProjectResponse,
    TimesheetProjectUpdate,
)
from app.services.timesheet_service import TimesheetService

router = APIRouter(prefix="/timesheets", tags=["Timesheets"])


def _check(ctx: TenantContext, user: User, action: PermissionAction, db: Session) -> None:
    if user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.TIMESHEETS, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> TimesheetService:
    return TimesheetService(db)


@router.get("/dashboard", response_model=APIResponse[TimesheetDashboardStats])
def dashboard_stats(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
    employee_id: Optional[UUID] = Query(default=None),
):
    _check(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_dashboard_stats(ctx.tenant_id, employee_id=employee_id))


@router.post("/projects", response_model=APIResponse[TimesheetProjectResponse], status_code=201)
def create_project(
    request: Request,
    payload: TimesheetProjectCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.create_project(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Project created")


@router.get("/projects", response_model=PaginatedResponse[TimesheetProjectResponse])
def list_projects(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    _check(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_projects(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@router.patch("/projects/{project_id}", response_model=APIResponse[TimesheetProjectResponse])
def update_project(
    request: Request,
    project_id: UUID,
    payload: TimesheetProjectUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_project(ctx.tenant_id, project_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Project updated")


@router.post("/entries", response_model=APIResponse[TimesheetEntryResponse], status_code=201)
def create_entry(
    request: Request,
    payload: TimesheetEntryCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_entry(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Entry created")


@router.get("/entries", response_model=PaginatedResponse[TimesheetEntryResponse])
def list_entries(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    project_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
):
    _check(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_entries(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        project_id=project_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


@router.patch("/entries/{entry_id}", response_model=APIResponse[TimesheetEntryResponse])
def update_entry(
    request: Request,
    entry_id: UUID,
    payload: TimesheetEntryUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_entry(ctx.tenant_id, entry_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Entry updated")


@router.post("/entries/{entry_id}/submit", response_model=APIResponse[TimesheetEntryResponse])
def submit_entry(
    request: Request,
    entry_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.CREATE, db)
    data = service.submit_entry(ctx.tenant_id, entry_id, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Entry submitted")


@router.post("/entries/{entry_id}/approve", response_model=APIResponse[TimesheetEntryResponse])
def approve_entry(
    request: Request,
    entry_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.approve_entry(ctx.tenant_id, entry_id, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Entry approved")


@router.post("/entries/{entry_id}/reject", response_model=APIResponse[TimesheetEntryResponse])
def reject_entry(
    request: Request,
    entry_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TimesheetService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.reject_entry(ctx.tenant_id, entry_id, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Entry rejected")
