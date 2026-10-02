from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantScopedMixin:
    """All company-level records must belong to a tenant."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36),
        ForeignKey("tenants.id"),
        index=True,
        nullable=False,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditMixin:
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class TimestampedModelMixin(TimestampMixin):
    """Base mixin for created/updated timestamps."""


class SoftDeleteModelMixin(SoftDeleteMixin):
    """Base mixin for soft-delete support via deleted_at."""


class AuditableModelMixin(AuditMixin):
    """Base mixin for created_by / updated_by tracking."""


class TenantAuditableModelMixin(TenantScopedMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """Standard tenant-scoped model with timestamps, soft delete, and audit columns."""
