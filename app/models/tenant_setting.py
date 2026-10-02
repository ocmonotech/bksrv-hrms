from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class TenantSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "tenant_settings"

    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_tenant_settings_tenant_key"),)
