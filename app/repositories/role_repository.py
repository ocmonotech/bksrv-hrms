from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.permission import RolePermission
from app.models.role import Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Role)

    def get_by_slug(self, slug: str, tenant_id: Optional[UUID] = None) -> Optional[Role]:
        stmt = select(Role).where(Role.slug == slug, Role.is_active.is_(True))
        if tenant_id is None:
            stmt = stmt.where(Role.tenant_id.is_(None))
        else:
            stmt = stmt.where(
                or_(Role.tenant_id.is_(None), Role.tenant_id == str(tenant_id))
            )
        return self.db.scalar(stmt)

    def get_system_role_by_slug(self, slug: str) -> Optional[Role]:
        stmt = select(Role).where(
            Role.slug == slug,
            Role.tenant_id.is_(None),
            Role.is_system.is_(True),
            Role.is_active.is_(True),
        )
        return self.db.scalar(stmt)

    def list_roles(self, tenant_id: Optional[UUID] = None, include_system: bool = True) -> list[Role]:
        stmt = select(Role).where(Role.is_active.is_(True))
        if tenant_id is not None:
            stmt = stmt.where(or_(Role.tenant_id.is_(None), Role.tenant_id == str(tenant_id)))
        elif not include_system:
            stmt = stmt.where(Role.tenant_id.isnot(None))
        stmt = stmt.order_by(Role.is_system.desc(), Role.name)
        return list(self.db.scalars(stmt).all())

    def get_with_permissions(self, role_id: UUID) -> Optional[Role]:
        stmt = (
            select(Role)
            .options(joinedload(Role.role_permissions).joinedload(RolePermission.permission))
            .where(Role.id == str(role_id))
        )
        return self.db.scalar(stmt)

    def slug_exists(self, slug: str, tenant_id: Optional[UUID] = None) -> bool:
        stmt = select(Role.id).where(Role.slug == slug)
        if tenant_id is None:
            stmt = stmt.where(Role.tenant_id.is_(None))
        else:
            stmt = stmt.where(Role.tenant_id == str(tenant_id))
        return self.db.scalar(stmt) is not None
