from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.routes.company_setup.crud_factory import (
    check_company_permission,
    register_crud_routes,
    require_tenant_scope,
)
from app.api.deps import get_current_user, get_request_meta, get_tenant_context
from app.core.database import get_db
from app.core.enums import PermissionAction
from app.core.tenant import TenantContext
from app.models.company_setup import (
    Branch,
    CostCenter,
    Department,
    Designation,
    Grade,
    Holiday,
    Policy,
)
from app.models.user import User
from app.repositories.tenant_scoped_repository import TenantScopedRepository
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.company_setup import (
    ApprovalWorkflowCreate,
    ApprovalWorkflowResponse,
    ApprovalWorkflowSummary,
    ApprovalWorkflowUpdate,
    BranchCreate,
    BranchResponse,
    BranchUpdate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
    CostCenterCreate,
    CostCenterResponse,
    CostCenterUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
    GradeCreate,
    GradeResponse,
    GradeUpdate,
    HolidayCreate,
    HolidayResponse,
    HolidayUpdate,
    PolicyCreate,
    PolicyResponse,
    PolicyUpdate,
)
from app.services.company_setup.base import TenantScopedCRUDService
from app.schemas.company_settings import (
    CareerPageResponse,
    CareerPageUpdate,
    ManagerAssignmentsResponse,
    ManagerAssignmentsUpdate,
    WeeklyOffResponse,
    WeeklyOffUpdate,
)
from app.services.tenant_setting_service import TenantSettingService
from app.services.company_setup_service import ApprovalWorkflowService, CompanyProfileService

router = APIRouter()


# --- Company Profile (singleton per tenant) ---

profile_router = APIRouter(prefix="/company", tags=["Company Profile"])


@profile_router.get("/profile", response_model=APIResponse[CompanyProfileResponse])
def get_company_profile(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.VIEW, db)
    profile = CompanyProfileService(db).get_profile(ctx.tenant_id)
    return APIResponse(data=profile)


@profile_router.put("/profile", response_model=APIResponse[CompanyProfileResponse])
def upsert_company_profile(
    payload: CompanyProfileUpdate,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.EDIT, db)
    profile = CompanyProfileService(db).upsert_profile(
        ctx.tenant_id,
        payload,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=profile, message="Company profile saved successfully")


router.include_router(profile_router)


settings_router = APIRouter(prefix="/company", tags=["Company Settings"])


@settings_router.get("/weekly-off", response_model=APIResponse[WeeklyOffResponse])
def get_weekly_off(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=TenantSettingService(db).get_weekly_off(ctx.tenant_id))


@settings_router.put("/weekly-off", response_model=APIResponse[WeeklyOffResponse])
def update_weekly_off(
    payload: WeeklyOffUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = TenantSettingService(db).update_weekly_off(ctx.tenant_id, payload)
    return APIResponse(data=data, message="Weekly off updated")


@settings_router.get("/manager-assignments", response_model=APIResponse[ManagerAssignmentsResponse])
def get_manager_assignments(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=TenantSettingService(db).get_manager_assignments(ctx.tenant_id))


@settings_router.put("/manager-assignments", response_model=APIResponse[ManagerAssignmentsResponse])
def update_manager_assignments(
    payload: ManagerAssignmentsUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = TenantSettingService(db).update_manager_assignments(ctx.tenant_id, payload)
    return APIResponse(data=data, message="Manager assignments updated")


router.include_router(settings_router)


# --- CRUD resources ---

def _branch_svc(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db, TenantScopedRepository(db, Branch), response_schema=BranchResponse, resource_type="branch"
    )


def _department_svc(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db, TenantScopedRepository(db, Department), response_schema=DepartmentResponse, resource_type="department"
    )


def _designation_svc(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db, TenantScopedRepository(db, Designation), response_schema=DesignationResponse, resource_type="designation"
    )


def _grade_svc(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db, TenantScopedRepository(db, Grade), response_schema=GradeResponse, resource_type="grade"
    )


def _cost_center_svc(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db, TenantScopedRepository(db, CostCenter), response_schema=CostCenterResponse, resource_type="cost_center"
    )


def _holiday_svc(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db,
        TenantScopedRepository(db, Holiday, search_fields=("name",)),
        response_schema=HolidayResponse,
        resource_type="holiday",
    )


def _policy_svc(db: Session) -> TenantScopedCRUDService:
    return TenantScopedCRUDService(
        db,
        TenantScopedRepository(db, Policy, search_fields=("title", "code", "category")),
        response_schema=PolicyResponse,
        resource_type="policy",
    )


register_crud_routes(router, prefix="/branches", tag="Branches", service_factory=_branch_svc,
                     create_schema=BranchCreate, update_schema=BranchUpdate, response_schema=BranchResponse)
register_crud_routes(router, prefix="/departments", tag="Departments", service_factory=_department_svc,
                     create_schema=DepartmentCreate, update_schema=DepartmentUpdate, response_schema=DepartmentResponse)
register_crud_routes(router, prefix="/designations", tag="Designations", service_factory=_designation_svc,
                     create_schema=DesignationCreate, update_schema=DesignationUpdate, response_schema=DesignationResponse)
register_crud_routes(router, prefix="/grades", tag="Grades", service_factory=_grade_svc,
                     create_schema=GradeCreate, update_schema=GradeUpdate, response_schema=GradeResponse)
register_crud_routes(router, prefix="/cost-centers", tag="Cost Centers", service_factory=_cost_center_svc,
                     create_schema=CostCenterCreate, update_schema=CostCenterUpdate, response_schema=CostCenterResponse)
register_crud_routes(router, prefix="/holidays", tag="Holidays", service_factory=_holiday_svc,
                     create_schema=HolidayCreate, update_schema=HolidayUpdate, response_schema=HolidayResponse)
register_crud_routes(router, prefix="/policies", tag="Policies", service_factory=_policy_svc,
                     create_schema=PolicyCreate, update_schema=PolicyUpdate, response_schema=PolicyResponse)


# --- Approval Workflows (custom service) ---

workflow_router = APIRouter(prefix="/approval-workflows", tags=["Approval Workflows"])


@workflow_router.get("", response_model=PaginatedResponse[ApprovalWorkflowSummary])
def list_workflows(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None, max_length=100),
    is_active: Optional[bool] = Query(default=None),
):
    check_company_permission(ctx, current_user, PermissionAction.VIEW, db)
    return ApprovalWorkflowService(db).list(
        ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active
    )


@workflow_router.get("/{workflow_id}", response_model=APIResponse[ApprovalWorkflowResponse])
def get_workflow(
    workflow_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=ApprovalWorkflowService(db).get(ctx.tenant_id, workflow_id))


@workflow_router.post("", response_model=APIResponse[ApprovalWorkflowResponse], status_code=201)
def create_workflow(
    payload: ApprovalWorkflowCreate,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.CREATE, db)
    item = ApprovalWorkflowService(db).create(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=item, message="Approval workflow created successfully")


@workflow_router.put("/{workflow_id}", response_model=APIResponse[ApprovalWorkflowResponse])
def update_workflow(
    workflow_id: UUID,
    payload: ApprovalWorkflowUpdate,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.EDIT, db)
    item = ApprovalWorkflowService(db).update(
        ctx.tenant_id, workflow_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=item, message="Approval workflow updated successfully")


@workflow_router.delete("/{workflow_id}", response_model=APIResponse[dict])
def delete_workflow(
    workflow_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_company_permission(ctx, current_user, PermissionAction.DELETE, db)
    ApprovalWorkflowService(db).delete(
        ctx.tenant_id, workflow_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data={"deleted": True}, message="Approval workflow deleted successfully")


router.include_router(workflow_router)
