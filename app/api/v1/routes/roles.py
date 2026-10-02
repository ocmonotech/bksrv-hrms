from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_role_service, get_tenant_context
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.role import (
    RoleCreate,
    RolePermissionsUpdate,
    RoleResponse,
    RoleWithPermissionsResponse,
)
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=APIResponse[list[RoleResponse]])
def list_roles(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RoleService = Depends(get_role_service),
) -> APIResponse[list[RoleResponse]]:
    if not current_user.is_super_admin and ctx.role:
        require_permission(
            ctx.role,
            PermissionModule.SETTINGS,
            PermissionAction.VIEW,
            db=db,
            role_id=ctx.role_id,
        )
    roles = service.list_roles(tenant_id=ctx.tenant_id)
    return APIResponse(data=roles)


@router.post("", response_model=APIResponse[RoleResponse], status_code=201)
def create_role(
    payload: RoleCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RoleService = Depends(get_role_service),
) -> APIResponse[RoleResponse]:
    if not current_user.is_super_admin and ctx.role:
        require_permission(
            ctx.role,
            PermissionModule.SETTINGS,
            PermissionAction.MANAGE,
            db=db,
            role_id=ctx.role_id,
        )
    role = service.create_role(payload, ctx.tenant_id, is_super_admin=current_user.is_super_admin)
    return APIResponse(data=role, message="Role created successfully")


@router.get("/{role_id}", response_model=APIResponse[RoleWithPermissionsResponse])
def get_role(
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RoleService = Depends(get_role_service),
) -> APIResponse[RoleWithPermissionsResponse]:
    role = service.get_role_with_permissions(role_id)
    return APIResponse(data=role)


@router.put("/{role_id}/permissions", response_model=APIResponse[RoleWithPermissionsResponse])
def update_role_permissions(
    role_id: UUID,
    payload: RolePermissionsUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RoleService = Depends(get_role_service),
) -> APIResponse[RoleWithPermissionsResponse]:
    if not current_user.is_super_admin and ctx.role:
        require_permission(
            ctx.role,
            PermissionModule.SETTINGS,
            PermissionAction.MANAGE,
            db=db,
            role_id=ctx.role_id,
        )
    role = service.update_role_permissions(
        role_id,
        payload,
        tenant_id=ctx.tenant_id,
        is_super_admin=current_user.is_super_admin,
    )
    return APIResponse(data=role, message="Role permissions updated successfully")
