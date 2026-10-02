from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Goal(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "goals"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("100"), nullable=False)
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )


class OKR(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "okrs"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    objective: Mapped[str] = mapped_column(String(500), nullable=False)
    key_results_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)


class ReviewCycle(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "review_cycles"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    cycle_type: Mapped[str] = mapped_column(String(30), default="annual", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_review_cycles_tenant_code"),)


class SelfReview(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "self_reviews"

    review_cycle_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    responses_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("review_cycle_id", "employee_id", name="uq_self_reviews_cycle_emp"),
    )


class ManagerReview(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "manager_reviews"

    review_cycle_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    hr_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("review_cycle_id", "employee_id", name="uq_manager_reviews_cycle_emp"),
    )


class Feedback360(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "feedback_360"

    review_cycle_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship: Mapped[str] = mapped_column(String(50), default="peer", nullable=False)
    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Appraisal(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "appraisals"

    review_cycle_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    final_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    increment_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    promotion_recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("review_cycle_id", "employee_id", name="uq_appraisals_cycle_emp"),
    )


class PerformanceImprovementPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "performance_improvement_plans"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    goals_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
