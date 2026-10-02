from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.role import Role
from app.models.tenant import Tenant
from app.repositories.user_repository import TenantRepository
from app.schemas.tenant import TenantCreate, TenantResponse


class TenantService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tenants = TenantRepository(db)

    def create(self, payload: TenantCreate, *, is_super_admin: bool) -> TenantResponse:
        if not is_super_admin:
            raise ForbiddenError("Only super admin can create tenants")

        slug = payload.slug.strip().lower()
        if not re.match(r"^[a-z0-9-]+$", slug):
            raise ValidationError("Slug must contain only lowercase letters, numbers, and hyphens")

        if self.tenants.get_by_slug(slug):
            raise ConflictError(f"Tenant with slug '{slug}' already exists")

        tenant = Tenant(
            name=payload.name.strip(),
            slug=slug,
            plan=payload.plan or "standard",
            is_active=True,
        )
        self.tenants.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return TenantResponse.model_validate(tenant)

    def list_tenants(self, *, is_super_admin: bool, tenant_id: Optional[UUID] = None) -> list[TenantResponse]:
        if is_super_admin:
            tenants = self.tenants.list_active()
        elif tenant_id:
            tenant = self.tenants.get_by_id(tenant_id)
            tenants = [tenant] if tenant and tenant.is_active else []
        else:
            raise ForbiddenError("Tenant context required")

        return [TenantResponse.model_validate(t) for t in tenants]
