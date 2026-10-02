from __future__ import annotations

from typing import Any, Callable, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.mixins import Base
from app.repositories.tenant_scoped_repository import TenantScopedRepository
from app.schemas.common import PaginatedResponse
from app.services.audit_service import AuditService
from app.utils.pagination import total_pages

ModelT = TypeVar("ModelT", bound=Base)
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


def _coerce_payload(data: dict) -> dict:
    coerced = {}
    for key, value in data.items():
        if isinstance(value, UUID):
            coerced[key] = str(value)
        else:
            coerced[key] = value
    return coerced


class TenantScopedCRUDService(Generic[ModelT, CreateT, UpdateT, ResponseT]):
    resource_type: str = "resource"

    def __init__(
        self,
        db: Session,
        repo: TenantScopedRepository[ModelT],
        *,
        response_schema: type[ResponseT],
        resource_type: Optional[str] = None,
    ) -> None:
        self.db = db
        self.repo = repo
        self.response_schema = response_schema
        if resource_type:
            self.resource_type = resource_type
        self.audit = AuditService(db)

    def list(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[ResponseT]:
        items, total = self.repo.list_paginated(
            tenant_id, page=page, page_size=page_size, search=search, is_active=is_active
        )
        return PaginatedResponse(
            data=[self.response_schema.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def get(self, tenant_id: UUID, entity_id: UUID) -> ResponseT:
        entity = self.repo.get_by_id(entity_id, tenant_id)
        if not entity:
            raise NotFoundError(f"{self.resource_type} not found")
        return self.response_schema.model_validate(entity)

    def create(
        self,
        tenant_id: UUID,
        payload: CreateT,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
        before_save: Optional[Callable[[ModelT], None]] = None,
    ) -> ResponseT:
        data = _coerce_payload(payload.model_dump(exclude_unset=True))
        code = data.get("code")
        if code and self.repo.get_by_code(tenant_id, code.upper() if hasattr(code, "upper") else code):
            raise ConflictError(f"{self.resource_type} with code '{code}' already exists")

        if "code" in data and isinstance(data["code"], str):
            data["code"] = data["code"].upper()

        entity = self.repo.model(
            tenant_id=str(tenant_id),
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        if before_save:
            before_save(entity)
        self.repo.add(entity)
        self._audit("create", tenant_id, actor_id, entity.id, meta)
        self.db.commit()
        self.db.refresh(entity)
        return self.response_schema.model_validate(entity)

    def update(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        payload: UpdateT,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> ResponseT:
        entity = self.repo.get_by_id(entity_id, tenant_id)
        if not entity:
            raise NotFoundError(f"{self.resource_type} not found")

        data = _coerce_payload(payload.model_dump(exclude_unset=True))
        new_code = data.get("code")
        if new_code:
            new_code = new_code.upper()
            existing = self.repo.get_by_code(tenant_id, new_code)
            if existing and str(existing.id) != str(entity_id):
                raise ConflictError(f"{self.resource_type} with code '{new_code}' already exists")
            data["code"] = new_code

        for key, value in data.items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)

        self._audit("update", tenant_id, actor_id, entity.id, meta, details=data)
        self.db.commit()
        self.db.refresh(entity)
        return self.response_schema.model_validate(entity)

    def delete(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> None:
        entity = self.repo.get_by_id(entity_id, tenant_id)
        if not entity:
            raise NotFoundError(f"{self.resource_type} not found")

        self.repo.soft_delete(entity, updated_by=actor_id)
        self._audit("delete", tenant_id, actor_id, entity.id, meta)
        self.db.commit()

    def _audit(
        self,
        action: str,
        tenant_id: UUID,
        actor_id: UUID,
        entity_id: UUID,
        meta: Optional[dict],
        details: Optional[dict] = None,
    ) -> None:
        self.audit.log(
            f"company_setup.{self.resource_type}.{action}",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type=self.resource_type,
            resource_id=str(entity_id),
            details=details,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
