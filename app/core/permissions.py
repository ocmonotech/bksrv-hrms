from __future__ import annotations

from typing import Optional, Set, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.default_role_permissions import ROLE_PERMISSIONS
from app.core.enums import PermissionAction, PermissionModule, UserRole
from app.core.exceptions import ForbiddenError
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository


def has_permission(
    role: Union[UserRole, str],
    module: PermissionModule,
    action: PermissionAction,
    *,
    db: Optional[Session] = None,
    role_id: Optional[UUID] = None,
) -> bool:
    role_slug = role.value if isinstance(role, UserRole) else role
    if role_slug == UserRole.SUPER_ADMIN.value:
        return True

    if db is not None and role_id is not None:
        perms = PermissionRepository(db).get_actions_for_role(role_id, module.value)
        if perms is not None:
            return action.value in perms

    if db is not None:
        role_obj = RoleRepository(db).get_by_slug(role_slug)
        if role_obj:
            perms = PermissionRepository(db).get_actions_for_role(role_obj.id, module.value)
            if perms is not None:
                return action.value in perms

    try:
        enum_role = UserRole(role_slug)
    except ValueError:
        return False

    module_perms = ROLE_PERMISSIONS.get(enum_role, {})
    allowed = module_perms.get(module, set())
    return action in allowed


def require_permission(
    role: Union[UserRole, str],
    module: PermissionModule,
    action: PermissionAction,
    *,
    db: Optional[Session] = None,
    role_id: Optional[UUID] = None,
) -> None:
    if not has_permission(role, module, action, db=db, role_id=role_id):
        slug = role.value if isinstance(role, UserRole) else role
        raise ForbiddenError(
            f"Role '{slug}' lacks '{action.value}' permission on '{module.value}'"
        )


def get_role_permissions_from_db(db: Session, role_id: UUID) -> dict[str, Set[str]]:
    return PermissionRepository(db).get_all_for_role(role_id)
