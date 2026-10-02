from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Announcement(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "announcements"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CommunicationTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "communication_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(30), default="email", nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_communication_templates_tenant_code"),)


class CommunicationLog(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "communication_logs"

    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("communication_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(30), default="email", nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
