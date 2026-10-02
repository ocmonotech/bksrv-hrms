from __future__ import annotations

from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.mixins import Base
from app.repositories.base import BaseRepository
from app.utils.pagination import paginate_stmt

ModelT = TypeVar("ModelT", bound=Base)


class TenantScopedRepository(BaseRepository[ModelT]):
    """Repository with tenant isolation, soft delete, search, and pagination."""

    search_fields: tuple[str, ...] = ("name", "code")

    def __init__(self, db: Session, model: type[ModelT], *, search_fields: Optional[tuple[str, ...]] = None) -> None:
        super().__init__(db, model)
        if search_fields is not None:
            self.search_fields = search_fields

    def get_by_id(self, id: UUID, tenant_id: UUID) -> Optional[ModelT]:
        stmt = select(self.model).where(
            self.model.id == str(id),
            self.model.tenant_id == str(tenant_id),
            self.model.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def get_by_code(self, tenant_id: UUID, code: str) -> Optional[ModelT]:
        if not hasattr(self.model, "code"):
            return None
        stmt = select(self.model).where(
            self.model.tenant_id == str(tenant_id),
            self.model.code == code,
            self.model.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def list_paginated(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        extra_filters: Optional[list] = None,
    ) -> tuple[list[ModelT], int]:
        stmt = select(self.model).where(
            self.model.tenant_id == str(tenant_id),
            self.model.deleted_at.is_(None),
        )

        if is_active is not None:
            stmt = stmt.where(self.model.is_active.is_(is_active))

        if search and self.search_fields:
            term = f"%{search.strip().lower()}%"
            clauses = []
            for field in self.search_fields:
                if hasattr(self.model, field):
                    clauses.append(func.lower(getattr(self.model, field)).like(term))
            if clauses:
                stmt = stmt.where(or_(*clauses))

        if extra_filters:
            for condition in extra_filters:
                stmt = stmt.where(condition)

        if hasattr(self.model, "name"):
            stmt = stmt.order_by(self.model.name)
        elif hasattr(self.model, "title"):
            stmt = stmt.order_by(self.model.title)

        return paginate_stmt(self.db, stmt, page=page, page_size=page_size)

    def soft_delete(self, entity: ModelT, *, updated_by: UUID) -> ModelT:
        entity.deleted_at = datetime.now(timezone.utc)
        entity.updated_by = str(updated_by)
        self.db.flush()
        return entity
