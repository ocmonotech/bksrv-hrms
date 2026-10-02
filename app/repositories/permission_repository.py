from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.permission import Permission, RolePermission
from app.models.role import Role
from app.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Permission)

    def list_all(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.module, Permission.action)
        return list(self.db.scalars(stmt).all())

    def get_by_module_action(self, module: str, action: str) -> Optional[Permission]:
        stmt = select(Permission).where(Permission.module == module, Permission.action == action)
        return self.db.scalar(stmt)

    def get_actions_for_role(self, role_id: UUID, module: str) -> Optional[set[str]]:
        stmt = (
            select(Permission.action)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == str(role_id), Permission.module == module)
        )
        actions = set(self.db.scalars(stmt).all())
        return actions if actions else None

    def get_all_for_role(self, role_id: UUID) -> dict[str, set[str]]:
        stmt = (
            select(Permission.module, Permission.action)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == str(role_id))
        )
        result: dict[str, set[str]] = {}
        for module, action in self.db.execute(stmt).all():
            result.setdefault(module, set()).add(action)
        return result

    def set_role_permissions(self, role_id: UUID, permission_ids: list[UUID]) -> None:
        self.db.query(RolePermission).filter(RolePermission.role_id == str(role_id)).delete()
        for perm_id in permission_ids:
            self.db.add(RolePermission(role_id=role_id, permission_id=perm_id))
        self.db.flush()
