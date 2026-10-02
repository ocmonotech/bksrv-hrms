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
from app.schemas.performance import (
    AppraisalApproveRequest,
    AppraisalCreate,
    AppraisalResponse,
    AppraisalUpdate,
    GoalCreate,
    GoalResponse,
    GoalUpdate,
    OKRCreate,
    OKRResponse,
    OKRUpdate,
    ReviewCreate,
    ReviewCycleCreate,
    ReviewCycleResponse,
    ReviewCycleUpdate,
    ReviewResponse,
    ReviewUpdate,
)
from app.services.performance_service import PerformanceService

router = APIRouter(prefix="/performance", tags=["Performance"])


def check_performance_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.PERFORMANCE, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> PerformanceService:
    return PerformanceService(db)


@router.post("/goals", response_model=APIResponse[GoalResponse], status_code=201)
def create_goal(
    request: Request,
    payload: GoalCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_goal(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Goal created")


@router.get("/goals", response_model=PaginatedResponse[GoalResponse])
def list_goals(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_performance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_goals(ctx.tenant_id, page=page, page_size=page_size, employee_id=employee_id, status=status)


@router.put("/goals/{goal_id}", response_model=APIResponse[GoalResponse])
def update_goal(
    goal_id: UUID,
    request: Request,
    payload: GoalUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_goal(ctx.tenant_id, goal_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Goal updated")


@router.post("/okrs", response_model=APIResponse[OKRResponse], status_code=201)
def create_okr(
    request: Request,
    payload: OKRCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_okr(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="OKR created")


@router.get("/okrs", response_model=PaginatedResponse[OKRResponse])
def list_okrs(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    year: Optional[int] = Query(default=None),
    quarter: Optional[int] = Query(default=None, ge=1, le=4),
    status: Optional[str] = Query(default=None),
):
    check_performance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_okrs(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        year=year,
        quarter=quarter,
        status=status,
    )


@router.put("/okrs/{okr_id}", response_model=APIResponse[OKRResponse])
def update_okr(
    okr_id: UUID,
    request: Request,
    payload: OKRUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_okr(ctx.tenant_id, okr_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="OKR updated")


@router.post("/review-cycles", response_model=APIResponse[ReviewCycleResponse], status_code=201)
def create_review_cycle(
    request: Request,
    payload: ReviewCycleCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_review_cycle(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Review cycle created")


@router.get("/review-cycles", response_model=PaginatedResponse[ReviewCycleResponse])
def list_review_cycles(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_performance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_review_cycles(
        ctx.tenant_id, page=page, page_size=page_size, status=status, is_active=is_active
    )


@router.put("/review-cycles/{cycle_id}", response_model=APIResponse[ReviewCycleResponse])
def update_review_cycle(
    cycle_id: UUID,
    request: Request,
    payload: ReviewCycleUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_review_cycle(
        ctx.tenant_id, cycle_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Review cycle updated")


@router.post("/reviews", response_model=APIResponse[ReviewResponse], status_code=201)
def create_review(
    request: Request,
    payload: ReviewCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_review(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Review created")


@router.get("/reviews", response_model=PaginatedResponse[ReviewResponse])
def list_reviews(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
    review_type: str = Query(..., pattern="^(self|manager|360)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    review_cycle_id: Optional[UUID] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_performance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_reviews(
        ctx.tenant_id,
        review_type=review_type,
        page=page,
        page_size=page_size,
        review_cycle_id=review_cycle_id,
        employee_id=employee_id,
        status=status,
    )


@router.put("/reviews/{review_id}", response_model=APIResponse[ReviewResponse])
def update_review(
    review_id: UUID,
    request: Request,
    payload: ReviewUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
    review_type: str = Query(..., pattern="^(self|manager|360)$"),
):
    check_performance_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_review(
        ctx.tenant_id,
        review_id,
        review_type,
        payload,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Review updated")


@router.post("/appraisals", response_model=APIResponse[AppraisalResponse], status_code=201)
def create_appraisal(
    request: Request,
    payload: AppraisalCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_appraisal(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Appraisal created")


@router.get("/appraisals", response_model=PaginatedResponse[AppraisalResponse])
def list_appraisals(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    review_cycle_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_performance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_appraisals(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        review_cycle_id=review_cycle_id,
        status=status,
    )


@router.put("/appraisals/{appraisal_id}", response_model=APIResponse[AppraisalResponse])
def update_appraisal(
    appraisal_id: UUID,
    request: Request,
    payload: AppraisalUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_appraisal(
        ctx.tenant_id, appraisal_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Appraisal updated")


@router.put("/appraisals/{appraisal_id}/approve", response_model=APIResponse[AppraisalResponse])
def approve_appraisal(
    appraisal_id: UUID,
    request: Request,
    payload: AppraisalApproveRequest = AppraisalApproveRequest(),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PerformanceService = Depends(get_service),
):
    check_performance_permission(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.approve_appraisal(
        ctx.tenant_id, appraisal_id, actor_id=current_user.id, payload=payload, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Appraisal approved")
