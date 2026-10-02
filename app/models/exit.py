from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Resignation(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "resignations"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resignation_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_working_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)


class ExitClearance(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "exit_clearances"

    resignation_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("resignations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checklist_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    cleared_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "resignation_id", name="uq_exit_clearances_tenant_resignation"),)


class ExitInterview(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "exit_interviews"

    resignation_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("resignations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conducted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    interview_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", nullable=False, index=True)
