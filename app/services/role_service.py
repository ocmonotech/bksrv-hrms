from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import PermissionModule
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import get_role_permissions_from_db
from app.models.role import Role
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.role import (
    ModuleActions,
    PermissionMatrixItem,
    RoleCreate,
    RolePermissionsUpdate,
    RoleResponse,
    RoleWithPermissionsResponse,
)


class RoleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.roles = RoleRepository(db)
        self.permissions = PermissionRepository(db)

    def list_roles(self, tenant_id: Optional[UUID] = None) -> list[RoleResponse]:
        items = self.roles.list_roles(tenant_id=tenant_id)
        return [self._to_response(r) for r in items]

    def create_role(self, payload: RoleCreate, tenant_id: Optional[UUID], *, is_super_admin: bool) -> RoleResponse:
        if not is_super_admin and tenant_id is None:
            raise ForbiddenError("Tenant context required to create roles")

        slug = payload.slug.strip().lower()
        if not re.match(r"^[a-z0-9_]+$", slug):
            raise ValidationError("Slug must contain only lowercase letters, numbers, and underscores")

        scope_tenant = tenant_id if not payload.is_system else None
        if payload.is_system and not is_super_admin:
            raise ForbiddenError("Only super admin can create system roles")

        if self.roles.slug_exists(slug, scope_tenant):
            raise ConflictError(f"Role with slug '{slug}' already exists")

        role = Role(
            tenant_id=scope_tenant,
            slug=slug,
            name=payload.name.strip(),
            description=payload.description,
            is_system=payload.is_system,
            is_active=True,
        )
        self.roles.add(role)
        self.db.commit()
        self.db.refresh(role)
        return self._to_response(role)

    def get_role_with_permissions(self, role_id: UUID) -> RoleWithPermissionsResponse:
        role = self.roles.get_with_permissions(role_id)
        if not role:
            raise NotFoundError("Role not found")
        return RoleWithPermissionsResponse(
            **self._to_response(role).model_dump(),
            permissions=self._build_matrix(role.id),
        )

    def update_role_permissions(
        self,
        role_id: UUID,
        payload: RolePermissionsUpdate,
        *,
        tenant_id: Optional[UUID],
        is_super_admin: bool,
    ) -> RoleWithPermissionsResponse:
        role = self.roles.get_by_id(role_id)
        if not role:
            raise NotFoundError("Role not found")

        if role.is_system and not is_super_admin:
            raise ForbiddenError("Only super admin can modify system role permissions")

        if role.tenant_id and tenant_id and str(role.tenant_id) != str(tenant_id):
            raise ForbiddenError("Cannot modify roles outside your tenant")

        permission_ids = self._resolve_permission_ids(payload.permissions)
        self.permissions.set_role_permissions(role_id, permission_ids)
        self.db.commit()

        from app.services.audit_service import AuditService

        AuditService(self.db).log(
            "role.permissions.updated",
            resource_type="role",
            resource_id=str(role_id),
            details={"permission_count": len(permission_ids)},
            tenant_id=tenant_id,
        )
        self.db.commit()
        return self.get_role_with_permissions(role_id)

    def _resolve_permission_ids(self, matrix: list[PermissionMatrixItem]) -> list[UUID]:
        ids: list[UUID] = []
        for item in matrix:
            for action, enabled in item.actions.model_dump().items():
                if not enabled:
                    continue
                perm = self.permissions.get_by_module_action(item.module, action)
                if not perm:
                    raise ValidationError(f"Unknown permission: {item.module}.{action}")
                ids.append(perm.id)
        return ids

    def _build_matrix(self, role_id: UUID) -> list[PermissionMatrixItem]:
        from app.core.enums import PermissionAction, PermissionModule

        role_perms = get_role_permissions_from_db(self.db, role_id)
        matrix: list[PermissionMatrixItem] = []
        for module in PermissionModule:
            actions = role_perms.get(module.value, set())
            matrix.append(
                PermissionMatrixItem(
                    module=module.value,
                    actions=ModuleActions(
                        **{action.value: action.value in actions for action in PermissionAction}
                    ),
                )
            )
        return matrix

    def _to_response(self, role: Role) -> RoleResponse:
        return RoleResponse(
            id=role.id,
            tenant_id=role.tenant_id,
            slug=role.slug,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            is_active=role.is_active,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )
