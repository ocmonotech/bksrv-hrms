from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.default_role_permissions import DEFAULT_ROLE_DEFINITIONS, ROLE_PERMISSIONS
from app.core.enums import PermissionAction, PermissionModule, UserRole
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    safe_decode_token,
    verify_password,
)
from app.models.audit import AuditLog
from app.models.permission import Permission, RolePermission
from app.models.role import RefreshToken, Role
from app.models.user import User
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import AuditLogRepository, UserRepository

settings = get_settings()


class RBACSeedService:
    """Seeds global permissions catalog and system roles."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.permissions = PermissionRepository(db)
        self.roles = RoleRepository(db)

    def seed_all(self) -> None:
        perm_map = self._seed_permissions()
        self._seed_system_roles(perm_map)

    def _seed_permissions(self) -> dict[tuple[str, str], UUID]:
        perm_map: dict[tuple[str, str], UUID] = {}
        for module in PermissionModule:
            for action in PermissionAction:
                existing = self.permissions.get_by_module_action(module.value, action.value)
                if existing:
                    perm_map[(module.value, action.value)] = existing.id
                    continue
                perm = Permission(
                    module=module.value,
                    action=action.value,
                    description=f"{action.value} on {module.value}",
                )
                self.permissions.add(perm)
                self.db.flush()
                perm_map[(module.value, action.value)] = perm.id
        return perm_map

    def _seed_system_roles(self, perm_map: dict[tuple[str, str], UUID]) -> None:
        for role_def in DEFAULT_ROLE_DEFINITIONS:
            slug = role_def["slug"]
            role = self.roles.get_system_role_by_slug(slug)
            if not role:
                role = Role(
                    tenant_id=None,
                    slug=slug,
                    name=role_def["name"],
                    description=role_def["description"],
                    is_system=True,
                    is_active=True,
                )
                self.roles.add(role)
                self.db.flush()

            try:
                enum_role = UserRole(slug)
            except ValueError:
                continue

            matrix = ROLE_PERMISSIONS.get(enum_role, {})
            permission_ids: list[UUID] = []
            for module, actions in matrix.items():
                for action in actions:
                    key = (module.value, action.value)
                    if key in perm_map:
                        permission_ids.append(perm_map[key])

            self.permissions.set_role_permissions(role.id, permission_ids)
