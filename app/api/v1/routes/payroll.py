from __future__ import annotations

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
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.payroll import (
    AssignStructureRequest,
    CreatePayrollBatchRequest,
    EmployeeSalaryStructureResponse,
    FnFCreateRequest,
    FnFResponse,
    PayrollBatchDetailResponse,
    PayrollBatchResponse,
    PayrollOverviewResponse,
    PayrollPreviewResponse,
    PayrollReportResponse,
    PayrollRunRequest,
    PayrollRunResponse,
    PayslipResponse,
    SalaryComponentCreate,
    SalaryComponentResponse,
    SalaryComponentUpdate,
    SalaryStructureCreate,
    SalaryStructureResponse,
    StatutorySettingResponse,
    StatutorySettingUpdate,
    TaxDeclarationCreate,
    TaxDeclarationResponse,
    TaxDeclarationUpdate,
)
from app.services.payroll_service import PayrollService

router = APIRouter(prefix="/payroll", tags=["Payroll"])


def check_payroll_permission(
    ctx: TenantContext,
    current_user: User,
    action: PermissionAction,
    db: Session,
) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.PAYROLL, action, db=db, role_id=ctx.role_id)


def get_payroll_service(db: Session = Depends(get_db)) -> PayrollService:
    return PayrollService(db)


@router.post("/components", response_model=APIResponse[SalaryComponentResponse], status_code=201)
def create_component(
    request: Request,
    payload: SalaryComponentCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_component(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Salary component created")


@router.get("/components", response_model=PaginatedResponse[SalaryComponentResponse])
def list_components(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_components(
        ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active
    )


@router.put("/components/{component_id}", response_model=APIResponse[SalaryComponentResponse])
def update_component(
    component_id: UUID,
    request: Request,
    payload: SalaryComponentUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_component(
        ctx.tenant_id, component_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Salary component updated")


@router.post("/salary-structures", response_model=APIResponse[SalaryStructureResponse], status_code=201)
def create_salary_structure(
    request: Request,
    body: dict = Body(...),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.CREATE, db)
    payload = SalaryStructureCreate.model_validate(body)
    data = service.create_structure(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Salary structure created")


@router.get("/salary-structures", response_model=PaginatedResponse[SalaryStructureResponse])
def list_salary_structures(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_structures(
        ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active
    )


@router.post("/assign-structure", response_model=APIResponse[EmployeeSalaryStructureResponse], status_code=201)
def assign_structure(
    request: Request,
    payload: AssignStructureRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.assign_structure(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Salary structure assigned")


@router.post("/run", response_model=APIResponse[PayrollRunResponse], status_code=201)
def run_payroll(
    request: Request,
    payload: PayrollRunRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.run_payroll(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Payroll run completed")


@router.get("/run/{run_id}/preview", response_model=APIResponse[PayrollPreviewResponse])
def preview_payroll(
    run_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.preview_run(ctx.tenant_id, run_id)
    return APIResponse(data=data)


@router.put("/run/{run_id}/approve", response_model=APIResponse[PayrollRunResponse])
def approve_payroll(
    run_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.approve_run(
        ctx.tenant_id, run_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Payroll approved")


@router.put("/run/{run_id}/lock", response_model=APIResponse[PayrollRunResponse])
def lock_payroll(
    run_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.lock_run(
        ctx.tenant_id, run_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Payroll locked")


@router.get("/payslips/{employee_id}", response_model=APIResponse[list[PayslipResponse]])
def get_payslips(
    employee_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.get_payslips(ctx.tenant_id, employee_id, year=year)
    return APIResponse(data=data)


@router.get("/reports", response_model=APIResponse[PayrollReportResponse])
def payroll_reports(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.get_reports(ctx.tenant_id)
    return APIResponse(data=data)


@router.post("/fnf", response_model=APIResponse[FnFResponse], status_code=201)
def create_fnf(
    request: Request,
    payload: FnFCreateRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_fnf(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Full and final settlement created")


@router.get("/tax-declarations", response_model=PaginatedResponse[TaxDeclarationResponse])
def list_tax_declarations(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    financial_year: Optional[str] = Query(default=None),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_tax_declarations(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        financial_year=financial_year,
    )


@router.post("/tax-declarations", response_model=APIResponse[TaxDeclarationResponse], status_code=201)
def create_tax_declaration(
    request: Request,
    payload: TaxDeclarationCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_tax_declaration(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Tax declaration created")


@router.put("/tax-declarations/{declaration_id}", response_model=APIResponse[TaxDeclarationResponse])
def update_tax_declaration(
    declaration_id: UUID,
    request: Request,
    payload: TaxDeclarationUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_tax_declaration(
        ctx.tenant_id, declaration_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Tax declaration updated")


@router.get("/statutory-settings", response_model=APIResponse[StatutorySettingResponse])
def get_statutory_settings(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_statutory_settings(ctx.tenant_id))


@router.put("/statutory-settings", response_model=APIResponse[StatutorySettingResponse])
def update_statutory_settings(
    request: Request,
    payload: StatutorySettingUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.update_statutory_settings(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Statutory settings updated")


@router.get("/overview", response_model=APIResponse[PayrollOverviewResponse])
def payroll_overview(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
    financial_year: str = Query(..., min_length=4, max_length=12),
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.get_payroll_overview(
        ctx.tenant_id, financial_year=financial_year, month=month, year=year
    )
    return APIResponse(data=data)


@router.get("/batches/{batch_id}", response_model=APIResponse[PayrollBatchDetailResponse])
def get_payroll_batch(
    batch_id: str,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_payroll_batch(ctx.tenant_id, batch_id))


@router.post("/batches", response_model=APIResponse[PayrollBatchResponse], status_code=201)
def create_payroll_batch(
    request: Request,
    payload: CreatePayrollBatchRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_payroll_batch(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Payroll batch created")


@router.put("/batches/{batch_id}/lock", response_model=APIResponse[PayrollBatchResponse])
def lock_payroll_batch(
    batch_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.lock_payroll_batch(
        ctx.tenant_id, batch_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Payroll batch locked")


@router.put("/batches/{batch_id}/unlock", response_model=APIResponse[PayrollBatchResponse])
def unlock_payroll_batch(
    batch_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.unlock_payroll_batch(
        ctx.tenant_id, batch_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Payroll batch unlocked")


@router.post("/batches/{batch_id}/release-slips", response_model=APIResponse[PayrollBatchResponse])
def release_salary_slips(
    batch_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.release_salary_slips(
        ctx.tenant_id, batch_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Salary slips released")


@router.put("/batches/{batch_id}/discard", response_model=APIResponse[PayrollBatchResponse])
def discard_payroll_batch(
    batch_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.discard_payroll_batch(
        ctx.tenant_id, batch_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Payroll batch discarded")


@router.put("/batches/{batch_id}/revise", response_model=APIResponse[PayrollBatchResponse])
def revise_payroll_batch(
    batch_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
):
    check_payroll_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.revise_payroll_batch(
        ctx.tenant_id, batch_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Payroll batch marked for revision")


@router.get("/batches/{batch_id}/salary-slip-zip", response_model=APIResponse[dict])
def download_salary_slip_zip(
    batch_id: str,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PayrollService = Depends(get_payroll_service),
    register_id: Optional[str] = Query(default=None),
):
    check_payroll_permission(ctx, current_user, PermissionAction.VIEW, db)
    data = service.download_salary_slip_zip(ctx.tenant_id, batch_id, register_id=register_id)
    return APIResponse(data=data)
