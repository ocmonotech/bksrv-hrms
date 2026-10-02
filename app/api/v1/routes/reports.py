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
from app.schemas.common import APIResponse
from app.schemas.reports import ReportFilters, ReportResponse, CustomReportCreate, CustomReportResponse, ReportsDashboardStats, ReportExportRequest, ReportExportResponse, LiveAnalyticsResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


def check_reports_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.REPORTS, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)


def _filters(
    date_from: Optional[date],
    date_to: Optional[date],
    branch_id: Optional[UUID],
    department_id: Optional[UUID],
    employee_id: Optional[UUID],
) -> ReportFilters:
    return ReportFilters(
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
        department_id=department_id,
        employee_id=employee_id,
    )


@router.get("/headcount", response_model=APIResponse[ReportResponse])
def headcount_report(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    filters = _filters(None, None, branch_id, department_id, employee_id)
    return APIResponse(
        data=service.headcount(
            ctx.tenant_id, filters=filters, page=page, page_size=page_size, actor_id=current_user.id, meta=get_request_meta(request)
        )
    )


@router.get("/attendance", response_model=APIResponse[ReportResponse])
def attendance_report(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    filters = _filters(date_from, date_to, branch_id, department_id, employee_id)
    return APIResponse(
        data=service.attendance(
            ctx.tenant_id, filters=filters, page=page, page_size=page_size, actor_id=current_user.id, meta=get_request_meta(request)
        )
    )


@router.get("/leave", response_model=APIResponse[ReportResponse])
def leave_report(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    filters = _filters(date_from, date_to, branch_id, department_id, employee_id)
    return APIResponse(
        data=service.leave(
            ctx.tenant_id, filters=filters, page=page, page_size=page_size, actor_id=current_user.id, meta=get_request_meta(request)
        )
    )


@router.get("/payroll", response_model=APIResponse[ReportResponse])
def payroll_report(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    filters = _filters(date_from, date_to, branch_id, department_id, employee_id)
    return APIResponse(
        data=service.payroll(
            ctx.tenant_id, filters=filters, page=page, page_size=page_size, actor_id=current_user.id, meta=get_request_meta(request)
        )
    )


@router.get("/recruitment", response_model=APIResponse[ReportResponse])
def recruitment_report(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    filters = _filters(date_from, date_to, None, None, None)
    return APIResponse(
        data=service.recruitment(
            ctx.tenant_id, filters=filters, page=page, page_size=page_size, actor_id=current_user.id, meta=get_request_meta(request)
        )
    )


@router.get("/performance", response_model=APIResponse[ReportResponse])
def performance_report(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    filters = _filters(None, None, branch_id, department_id, employee_id)
    return APIResponse(
        data=service.performance(
            ctx.tenant_id, filters=filters, page=page, page_size=page_size, actor_id=current_user.id, meta=get_request_meta(request)
        )
    )


@router.get("/attrition", response_model=APIResponse[ReportResponse])
def attrition_report(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    filters = _filters(date_from, date_to, branch_id, department_id, None)
    return APIResponse(
        data=service.attrition(
            ctx.tenant_id, filters=filters, page=page, page_size=page_size, actor_id=current_user.id, meta=get_request_meta(request)
        )
    )


@router.get("/dashboard", response_model=APIResponse[ReportsDashboardStats])
def reports_dashboard(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.dashboard_stats(ctx.tenant_id))


@router.get("/analytics/live", response_model=APIResponse[LiveAnalyticsResponse])
def live_analytics(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.live_analytics(ctx.tenant_id))


@router.get("/custom", response_model=APIResponse[list[CustomReportResponse]])
def list_custom_reports(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.list_custom_reports(ctx.tenant_id))


@router.post("/custom", response_model=APIResponse[CustomReportResponse], status_code=201)
def create_custom_report(
    request: Request,
    payload: CustomReportCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
):
    check_reports_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_custom_report(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Custom report created")


@router.get("/custom/{report_id}", response_model=APIResponse[CustomReportResponse])
def get_custom_report(
    report_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_custom_report(ctx.tenant_id, report_id))


@router.post("/export", response_model=APIResponse[ReportExportResponse])
def export_report(
    request: Request,
    payload: ReportExportRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_service),
):
    check_reports_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.export_report(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Report exported")
