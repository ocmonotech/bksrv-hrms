from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Role definition. System roles have tenant_id=NULL and is_system=True.
    Tenants may create custom roles scoped to their tenant.
    """

    __tablename__ = "roles"

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    slug: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped[Optional["Tenant"]] = relationship(back_populates="roles")
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    user_access: Mapped[list["UserTenantAccess"]] = relationship(back_populates="role")

    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_roles_tenant_slug"),)


class UserTenantAccess(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    """
    Links a user to a tenant (+ optional company) with a role.
    Super Admin does not require a record here.
    """

    __tablename__ = "user_tenant_access"

    user_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("roles.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("users.id"), nullable=True
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="tenant_access", foreign_keys=[user_id])
    tenant: Mapped["Tenant"] = relationship(back_populates="user_access")
    company: Mapped[Optional["Company"]] = relationship(back_populates="user_access")
    role: Mapped["Role"] = relationship(back_populates="user_access")

    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", "company_id", name="uq_user_tenant_company_access"),
    )


class RefreshToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
