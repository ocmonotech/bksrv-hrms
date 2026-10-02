from __future__ import annotations

from datetime import date, datetime, timezone
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
from app.schemas.attendance import (
    AttendanceDashboardStats,
    AttendancePolicyResponse,
    AttendancePolicyUpdate,
    BiometricDeviceCreate,
    BiometricDeviceResponse,
    BiometricSyncResponse,
    DailySummaryResponse,
    FieldVisitCreate,
    FieldVisitResponse,
    MonthlyAttendanceSummary,
    PunchRequest,
    PunchResponse,
    RegularizationApprove,
    RegularizationCreate,
    RegularizationResponse,
)
from app.schemas.common import APIResponse
from app.services.attendance_service import AttendanceService
from app.workers import enqueue

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def check_attendance_permission(
    ctx: TenantContext,
    current_user: User,
    action: PermissionAction,
    db: Session,
) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.ATTENDANCE, action, db=db, role_id=ctx.role_id)


def get_attendance_service(db: Session = Depends(get_db)) -> AttendanceService:
    return AttendanceService(db)


@router.post("/punch", response_model=APIResponse[PunchResponse], status_code=201)
def punch(
    request: Request,
    payload: PunchRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.CREATE, db)
    meta = get_request_meta(request)
    result = service.punch(
        ctx.tenant_id,
        payload,
        actor_id=current_user.id,
        ip_address=meta.get("ip_address"),
        user_agent=meta.get("user_agent"),
        meta=meta,
    )
    return APIResponse(data=result, message="Punch recorded successfully")


@router.get("/daily", response_model=APIResponse[list[DailySummaryResponse]])
def daily_attendance(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
    attendance_date: Optional[date] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_attendance_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.list_daily(
        ctx.tenant_id,
        attendance_date=attendance_date,
        employee_id=employee_id,
        branch_id=branch_id,
        department_id=department_id,
        status=status,
    )
    return APIResponse(data=data)


@router.get("/monthly", response_model=APIResponse[MonthlyAttendanceSummary])
def monthly_attendance(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
    employee_id: UUID = Query(...),
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    check_attendance_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.monthly_summary(ctx.tenant_id, year=year, month=month, employee_id=employee_id)
    return APIResponse(data=data)


@router.post("/regularization", response_model=APIResponse[RegularizationResponse], status_code=201)
def create_regularization(
    request: Request,
    payload: RegularizationCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_regularization(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Regularization request submitted")


@router.put("/regularization/{reg_id}/approve", response_model=APIResponse[RegularizationResponse])
def approve_regularization(
    reg_id: UUID,
    request: Request,
    payload: RegularizationApprove = RegularizationApprove(),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.approve_regularization(
        ctx.tenant_id,
        reg_id,
        actor_id=current_user.id,
        hr_override=payload.hr_override,
        rejection_reason=payload.rejection_reason,
        meta=get_request_meta(request),
    )
    message = "Regularization rejected" if payload.rejection_reason else "Regularization approved"
    return APIResponse(data=data, message=message)


@router.get("/policies", response_model=APIResponse[AttendancePolicyResponse])
def get_attendance_policy(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_policy(ctx.tenant_id, actor_id=current_user.id))


@router.put("/policies", response_model=APIResponse[AttendancePolicyResponse])
def update_attendance_policy(
    request: Request,
    payload: AttendancePolicyUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_policy(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Attendance policy updated")


@router.get("/biometric", response_model=APIResponse[list[BiometricDeviceResponse]])
def list_biometric_devices(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.list_biometric_devices(ctx.tenant_id))


@router.post("/biometric", response_model=APIResponse[BiometricDeviceResponse], status_code=201)
def create_biometric_device(
    request: Request,
    payload: BiometricDeviceCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_biometric_device(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Biometric device created")


@router.post("/biometric/{device_id}/sync", response_model=APIResponse[BiometricSyncResponse])
def sync_biometric_device(
    device_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
    background: bool = Query(default=False, description="Enqueue sync as background job"),
):
    check_attendance_permission(ctx, current_user, PermissionAction.EDIT, db)
    if background:
        job_id = enqueue(
            "biometric_sync",
            str(ctx.tenant_id),
            str(device_id),
            str(current_user.id),
        )
        return APIResponse(
            data=BiometricSyncResponse(
                device_id=device_id,
                records_synced=0,
                last_sync_at=datetime.now(timezone.utc),
            ),
            message=f"Biometric sync queued (job {job_id})",
        )
    data = service.sync_biometric_device(
        ctx.tenant_id, device_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Biometric device synced")


@router.get("/field", response_model=APIResponse[list[FieldVisitResponse]])
def list_field_visits(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
    visit_date: Optional[date] = Query(default=None),
):
    check_attendance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.list_field_visits(ctx.tenant_id, visit_date=visit_date))


@router.post("/field", response_model=APIResponse[FieldVisitResponse], status_code=201)
def create_field_visit(
    request: Request,
    payload: FieldVisitCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_field_visit(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Field visit recorded")


@router.get("/dashboard", response_model=APIResponse[AttendanceDashboardStats])
def attendance_dashboard(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.dashboard_stats(ctx.tenant_id))


@router.get("/regularization", response_model=APIResponse[list[RegularizationResponse]])
def list_pending_regularizations(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service),
):
    check_attendance_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.list_pending_regularizations(ctx.tenant_id))
