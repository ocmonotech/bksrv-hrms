from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, TenantScopedMixin, UUIDPrimaryKeyMixin


class CustomReport(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "custom_reports"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    modules: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    columns: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    filters: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
