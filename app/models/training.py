from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class TrainingCourse(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "training_courses"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_hours: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    delivery_mode: Mapped[str] = mapped_column(String(30), default="online", nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_training_courses_tenant_code"),)


class TrainingEnrollment(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "training_enrollments"

    course_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("training_courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="assigned", nullable=False, index=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "course_id", "employee_id", name="uq_training_enrollments_tenant_course_emp"),
    )
