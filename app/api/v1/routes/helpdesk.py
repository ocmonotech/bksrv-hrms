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
from app.schemas.helpdesk import (
    TicketAssignRequest,
    TicketCategoryCreate,
    TicketCategoryResponse,
    TicketCategoryUpdate,
    TicketCloseRequest,
    TicketCreate,
    TicketReplyCreate,
    TicketReplyResponse,
    TicketResponse,
)
from app.services.helpdesk_service import HelpdeskService

router = APIRouter(prefix="/helpdesk", tags=["Helpdesk"])


def check_helpdesk_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.HELPDESK, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> HelpdeskService:
    return HelpdeskService(db)


@router.post("/categories", response_model=APIResponse[TicketCategoryResponse], status_code=201)
def create_category(
    request: Request,
    payload: TicketCategoryCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.create_category(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Category created")


@router.get("/categories", response_model=PaginatedResponse[TicketCategoryResponse])
def list_categories(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_categories(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@router.patch("/categories/{category_id}", response_model=APIResponse[TicketCategoryResponse])
def update_category(
    request: Request,
    category_id: UUID,
    payload: TicketCategoryUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.update_category(ctx.tenant_id, category_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Category updated")


@router.post("/tickets", response_model=APIResponse[TicketResponse], status_code=201)
def create_ticket(
    request: Request,
    payload: TicketCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_ticket(
        ctx.tenant_id,
        payload,
        requester_id=current_user.id,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Ticket created")


@router.get("/tickets", response_model=PaginatedResponse[TicketResponse])
def list_tickets(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    assigned_to: Optional[UUID] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    branch_id: Optional[UUID] = Query(default=None),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_tickets(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        priority=priority,
        category_id=category_id,
        assigned_to=assigned_to,
        employee_id=employee_id,
        department_id=department_id,
        branch_id=branch_id,
    )


@router.get("/tickets/{ticket_id}", response_model=APIResponse[TicketResponse])
def get_ticket(
    ticket_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_ticket(ctx.tenant_id, ticket_id))


@router.get("/tickets/{ticket_id}/replies", response_model=APIResponse[list[TicketReplyResponse]])
def list_replies(
    ticket_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.list_replies(ctx.tenant_id, ticket_id))


@router.post("/tickets/{ticket_id}/reply", response_model=APIResponse[TicketReplyResponse], status_code=201)
def reply_ticket(
    request: Request,
    ticket_id: UUID,
    payload: TicketReplyCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.add_reply(ctx.tenant_id, ticket_id, payload, author_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Reply added")


@router.post("/tickets/{ticket_id}/assign", response_model=APIResponse[TicketResponse])
def assign_ticket(
    request: Request,
    ticket_id: UUID,
    payload: TicketAssignRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.assign_ticket(ctx.tenant_id, ticket_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Ticket assigned")


@router.post("/tickets/{ticket_id}/close", response_model=APIResponse[TicketResponse])
def close_ticket(
    request: Request,
    ticket_id: UUID,
    payload: TicketCloseRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: HelpdeskService = Depends(get_service),
):
    check_helpdesk_permission(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.close_ticket(ctx.tenant_id, ticket_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Ticket closed")
