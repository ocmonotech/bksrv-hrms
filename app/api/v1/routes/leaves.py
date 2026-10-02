from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_meta
from app.api.v1.routes.company_setup.crud_factory import require_tenant_scope
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.repositories.leave_repository import LeavePolicyRepository, LeaveTypeRepository
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.leave import (
    CompOffCreate,
    CompOffResponse,
    GenerateBalanceRequest,
    LeaveApplyRequest,
    LeaveApproveRequest,
    LeaveBalanceResponse,
    LeaveCalendarEntry,
    LeavePolicyCreate,
    LeavePolicyResponse,
    LeavePolicyUpdate,
    LeaveRejectRequest,
    LeaveRequestResponse,
    LeaveTypeCreate,
    LeaveTypeResponse,
    LeaveTypeUpdate,
)
from app.services.company_setup.base import TenantScopedCRUDService
from app.services.leave_service import LeaveService

router = APIRouter(prefix="/leaves", tags=["Leave"])


def check_leave_permission(
    ctx: TenantContext,
    current_user: User,
    action: PermissionAction,
    db: Session,
) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.LEAVE, action, db=db, role_id=ctx.role_id)


def get_leave_service(db: Session = Depends(get_db)) -> LeaveService:
    return LeaveService(db)


def leave_type_service(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db,
        LeaveTypeRepository(db),
        response_schema=LeaveTypeResponse,
        resource_type="leave_type",
    )


def leave_policy_service(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db,
        LeavePolicyRepository(db),
        response_schema=LeavePolicyResponse,
        resource_type="leave_policy",
    )


@router.post("/apply", response_model=APIResponse[LeaveRequestResponse], status_code=201)
def apply_leave(
    request: Request,
    payload: LeaveApplyRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
):
    check_leave_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.apply_leave(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Leave request submitted")


@router.get("/requests", response_model=PaginatedResponse[LeaveRequestResponse])
def list_leave_requests(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
):
    check_leave_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_requests(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )


@router.put("/{request_id}/approve", response_model=APIResponse[LeaveRequestResponse])
def approve_leave(
    request_id: UUID,
    request: Request,
    payload: LeaveApproveRequest = LeaveApproveRequest(),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
):
    check_leave_permission(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.approve_leave(
        ctx.tenant_id,
        request_id,
        actor_id=current_user.id,
        hr_override=payload.hr_override,
        notes=payload.notes,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Leave approved")


@router.put("/{request_id}/reject", response_model=APIResponse[LeaveRequestResponse])
def reject_leave(
    request_id: UUID,
    request: Request,
    payload: LeaveRejectRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
):
    check_leave_permission(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.reject_leave(
        ctx.tenant_id,
        request_id,
        actor_id=current_user.id,
        rejection_reason=payload.rejection_reason,
        hr_override=payload.hr_override,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Leave rejected")


@router.put("/{request_id}/cancel", response_model=APIResponse[LeaveRequestResponse])
def cancel_leave(
    request_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
):
    check_leave_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.cancel_leave(
        ctx.tenant_id, request_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Leave cancelled")


@router.get("/balance/{employee_id}", response_model=APIResponse[list[LeaveBalanceResponse]])
def get_leave_balance(
    employee_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
):
    check_leave_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.get_balance(ctx.tenant_id, employee_id, year=year)
    return APIResponse(data=data)


@router.get("/calendar", response_model=APIResponse[list[LeaveCalendarEntry]])
def leave_calendar(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
    start_date: date = Query(...),
    end_date: date = Query(...),
    employee_id: Optional[UUID] = Query(default=None),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
):
    check_leave_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.calendar(
        ctx.tenant_id,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id,
        branch_id=branch_id,
        department_id=department_id,
    )
    return APIResponse(data=data)


@router.post("/balance/generate", response_model=APIResponse[dict])
def generate_balances(
    request: Request,
    payload: GenerateBalanceRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
):
    check_leave_permission(ctx, current_user, PermissionAction.MANAGE, db)
    created = service.generate_balances(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data={"created": created}, message=f"{created} balance record(s) created")


@router.post("/comp-off", response_model=APIResponse[CompOffResponse], status_code=201)
def create_comp_off(
    request: Request,
    payload: CompOffCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
):
    check_leave_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_comp_off(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Comp-off request submitted")


@router.get("/comp-off", response_model=PaginatedResponse[CompOffResponse])
def list_comp_off(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: LeaveService = Depends(get_leave_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_leave_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_comp_off(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        status=status,
    )


types_router = APIRouter(prefix="/types", tags=["Leave Types"])


@types_router.get("", response_model=PaginatedResponse[LeaveTypeResponse])
def list_leave_types(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_leave_permission(ctx, current_user, PermissionAction.VIEW, db)
    return leave_type_service(db).list(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@types_router.post("", response_model=APIResponse[LeaveTypeResponse], status_code=201)
def create_leave_type(
    request: Request,
    body: dict = Body(...),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_leave_permission(ctx, current_user, PermissionAction.CREATE, db)
    payload = LeaveTypeCreate.model_validate(body)
    item = leave_type_service(db).create(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=item, message="Leave type created")


@types_router.put("/{item_id}", response_model=APIResponse[LeaveTypeResponse])
def update_leave_type(
    item_id: UUID,
    request: Request,
    body: dict = Body(...),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_leave_permission(ctx, current_user, PermissionAction.EDIT, db)
    payload = LeaveTypeUpdate.model_validate(body)
    item = leave_type_service(db).update(
        ctx.tenant_id, item_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=item, message="Leave type updated")


policies_router = APIRouter(prefix="/policies", tags=["Leave Policies"])


@policies_router.get("", response_model=PaginatedResponse[LeavePolicyResponse])
def list_leave_policies(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_leave_permission(ctx, current_user, PermissionAction.VIEW, db)
    return leave_policy_service(db).list(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@policies_router.post("", response_model=APIResponse[LeavePolicyResponse], status_code=201)
def create_leave_policy(
    request: Request,
    body: dict = Body(...),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_leave_permission(ctx, current_user, PermissionAction.CREATE, db)
    payload = LeavePolicyCreate.model_validate(body)
    item = leave_policy_service(db).create(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=item, message="Leave policy created")


@policies_router.put("/{item_id}", response_model=APIResponse[LeavePolicyResponse])
def update_leave_policy(
    item_id: UUID,
    request: Request,
    body: dict = Body(...),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_leave_permission(ctx, current_user, PermissionAction.EDIT, db)
    payload = LeavePolicyUpdate.model_validate(body)
    item = leave_policy_service(db).update(
        ctx.tenant_id, item_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=item, message="Leave policy updated")


router.include_router(types_router)
router.include_router(policies_router)
