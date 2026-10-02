from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class TenantContext:
    """Resolved tenant scope for the current request."""

    tenant_id: Optional[UUID]
    company_id: Optional[UUID]
    is_super_admin: bool = False
    role: Optional[str] = None
    role_id: Optional[UUID] = None

    @property
    def is_platform_scope(self) -> bool:
        return self.is_super_admin and self.tenant_id is None

    @property
    def requires_tenant(self) -> bool:
        return not self.is_super_admin


def resolve_tenant_headers(
    *,
    is_super_admin: bool,
    tenant_id: Optional[UUID],
    company_id: Optional[UUID],
    role: Optional[str] = None,
    role_id: Optional[UUID] = None,
) -> TenantContext:
    """
    Super Admin may operate at platform level (no tenant) or impersonate a tenant via headers.
    Company users must always provide tenant context.
    """
    if is_super_admin:
        return TenantContext(
            tenant_id=tenant_id,
            company_id=company_id,
            is_super_admin=True,
            role=role or "super_admin",
            role_id=role_id,
        )

    if tenant_id is None:
        raise ValueError("Tenant context required for non-super-admin users")

    return TenantContext(
        tenant_id=tenant_id,
        company_id=company_id,
        is_super_admin=False,
        role=role,
        role_id=role_id,
    )
