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
from app.schemas.expenses import (
    ExpenseAdvanceCreate,
    ExpenseAdvanceResponse,
    ExpenseAdvanceUpdate,
    ExpenseClaimCreate,
    ExpenseClaimResponse,
    ExpenseClaimUpdate,
    ExpensePolicyCreate,
    ExpensePolicyResponse,
    ExpensePolicyUpdate,
)
from app.services.extended_modules_service import ExpensesService

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def check_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.EXPENSES, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> ExpensesService:
    return ExpensesService(db)


@router.get("/policies", response_model=PaginatedResponse[ExpensePolicyResponse])
def list_policies(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExpensesService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.policies.list(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@router.post("/policies", response_model=APIResponse[ExpensePolicyResponse], status_code=201)
def create_policy(
    request: Request,
    payload: ExpensePolicyCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExpensesService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.policies.create(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Expense policy created")


@router.put("/policies/{policy_id}", response_model=APIResponse[ExpensePolicyResponse])
def update_policy(
    policy_id: UUID,
    request: Request,
    payload: ExpensePolicyUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExpensesService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.policies.update(ctx.tenant_id, policy_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Expense policy updated")


@router.get("/claims", response_model=PaginatedResponse[ExpenseClaimResponse])
def list_claims(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExpensesService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.claims.list(ctx.tenant_id, page=page, page_size=page_size, search=search)


@router.post("/claims", response_model=APIResponse[ExpenseClaimResponse], status_code=201)
def create_claim(
    request: Request,
    payload: ExpenseClaimCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExpensesService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_claim(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Expense claim created")


@router.put("/claims/{claim_id}", response_model=APIResponse[ExpenseClaimResponse])
def update_claim(
    claim_id: UUID,
    request: Request,
    payload: ExpenseClaimUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExpensesService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_claim(ctx.tenant_id, claim_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Expense claim updated")


@router.get("/advances", response_model=PaginatedResponse[ExpenseAdvanceResponse])
def list_advances(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExpensesService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.advances.list(ctx.tenant_id, page=page, page_size=page_size, search=search)


@router.post("/advances", response_model=APIResponse[ExpenseAdvanceResponse], status_code=201)
def create_advance(
    request: Request,
    payload: ExpenseAdvanceCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExpensesService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_advance(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Expense advance created")


@router.put("/advances/{advance_id}", response_model=APIResponse[ExpenseAdvanceResponse])
def update_advance(
    advance_id: UUID,
    request: Request,
    payload: ExpenseAdvanceUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ExpensesService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_advance(ctx.tenant_id, advance_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Expense advance updated")
