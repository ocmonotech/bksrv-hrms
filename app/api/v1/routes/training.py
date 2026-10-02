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
from app.schemas.training import (
    TrainingCourseCreate,
    TrainingCourseResponse,
    TrainingCourseUpdate,
    TrainingDashboardStats,
    TrainingEnrollmentCreate,
    TrainingEnrollmentResponse,
    TrainingEnrollmentUpdate,
)
from app.services.training_service import TrainingService

router = APIRouter(prefix="/training", tags=["Training"])


def _check(ctx: TenantContext, user: User, action: PermissionAction, db: Session) -> None:
    if user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.TRAINING, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> TrainingService:
    return TrainingService(db)


@router.get("/dashboard", response_model=APIResponse[TrainingDashboardStats])
def dashboard_stats(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TrainingService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_dashboard_stats(ctx.tenant_id))


@router.post("/courses", response_model=APIResponse[TrainingCourseResponse], status_code=201)
def create_course(
    request: Request,
    payload: TrainingCourseCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TrainingService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.create_course(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Course created")


@router.get("/courses", response_model=PaginatedResponse[TrainingCourseResponse])
def list_courses(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TrainingService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    _check(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_courses(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@router.patch("/courses/{course_id}", response_model=APIResponse[TrainingCourseResponse])
def update_course(
    request: Request,
    course_id: UUID,
    payload: TrainingCourseUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TrainingService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_course(ctx.tenant_id, course_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Course updated")


@router.post("/enrollments", response_model=APIResponse[TrainingEnrollmentResponse], status_code=201)
def create_enrollment(
    request: Request,
    payload: TrainingEnrollmentCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TrainingService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_enrollment(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Enrollment created")


@router.get("/enrollments", response_model=PaginatedResponse[TrainingEnrollmentResponse])
def list_enrollments(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TrainingService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    course_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    _check(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_enrollments(
        ctx.tenant_id, page=page, page_size=page_size, employee_id=employee_id, course_id=course_id, status=status
    )


@router.patch("/enrollments/{enrollment_id}", response_model=APIResponse[TrainingEnrollmentResponse])
def update_enrollment(
    request: Request,
    enrollment_id: UUID,
    payload: TrainingEnrollmentUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: TrainingService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_enrollment(
        ctx.tenant_id, enrollment_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Enrollment updated")
