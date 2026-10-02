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
from app.schemas.shift import (
    RosterCreate,
    RosterResponse,
    RosterUpdate,
    ShiftCreate,
    ShiftResponse,
    ShiftSwapCreate,
    ShiftSwapResponse,
    ShiftSwapUpdate,
    ShiftUpdate,
)
from app.services.shift_service import roster_service, shift_service, shift_swap_service

router = APIRouter()


def check_shift_permission(
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


def _register(
    prefix: str,
    tag: str,
    service_factory,
    create_schema,
    update_schema,
    response_schema,
) -> None:
    sub = APIRouter(prefix=prefix, tags=[tag])

    @sub.get("", response_model=PaginatedResponse[response_schema])
    def list_items(
        ctx: TenantContext = Depends(require_tenant_scope),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        search: Optional[str] = Query(default=None, max_length=100),
        is_active: Optional[bool] = Query(default=None),
    ):
        check_shift_permission(ctx, current_user, PermissionAction.VIEW, db)
        return service_factory(db).list(
            ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active
        )

    @sub.get("/{item_id}", response_model=APIResponse[response_schema])
    def get_item(
        item_id: UUID,
        ctx: TenantContext = Depends(require_tenant_scope),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        check_shift_permission(ctx, current_user, PermissionAction.VIEW, db)
        return APIResponse(data=service_factory(db).get(ctx.tenant_id, item_id))

    @sub.post("", response_model=APIResponse[response_schema], status_code=201)
    def create_item(
        request: Request,
        body: dict = Body(...),
        ctx: TenantContext = Depends(require_tenant_scope),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        check_shift_permission(ctx, current_user, PermissionAction.CREATE, db)
        payload = create_schema.model_validate(body)
        item = service_factory(db).create(
            ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
        )
        return APIResponse(data=item, message=f"{tag} created successfully")

    @sub.put("/{item_id}", response_model=APIResponse[response_schema])
    def update_item(
        item_id: UUID,
        request: Request,
        body: dict = Body(...),
        ctx: TenantContext = Depends(require_tenant_scope),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        check_shift_permission(ctx, current_user, PermissionAction.EDIT, db)
        payload = update_schema.model_validate(body)
        item = service_factory(db).update(
            ctx.tenant_id, item_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
        )
        return APIResponse(data=item, message=f"{tag} updated successfully")

    @sub.delete("/{item_id}", response_model=APIResponse[dict])
    def delete_item(
        item_id: UUID,
        request: Request,
        ctx: TenantContext = Depends(require_tenant_scope),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        check_shift_permission(ctx, current_user, PermissionAction.DELETE, db)
        service_factory(db).delete(
            ctx.tenant_id, item_id, actor_id=current_user.id, meta=get_request_meta(request)
        )
        return APIResponse(data={"deleted": True}, message=f"{tag} deleted successfully")

    router.include_router(sub)


_register("/shifts", "Shifts", shift_service, ShiftCreate, ShiftUpdate, ShiftResponse)
_register("/rosters", "Rosters", roster_service, RosterCreate, RosterUpdate, RosterResponse)
_register(
    "/shift-swap-requests",
    "Shift Swap Requests",
    shift_swap_service,
    ShiftSwapCreate,
    ShiftSwapUpdate,
    ShiftSwapResponse,
)
