from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OnboardingChecklist(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "onboarding_checklists"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_onboarding_checklists_tenant_code"),)


class OnboardingTask(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "onboarding_tasks"

    checklist_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("onboarding_checklists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class NewJoinerDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "new_joiner_documents"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class ProbationReview(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "probation_reviews"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    extension_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
