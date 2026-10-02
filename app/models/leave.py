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


class LeaveType(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "leave_types"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_half_day: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_days_per_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    color: Mapped[str] = mapped_column(String(20), default="#3B82F6", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_leave_types_tenant_code"),)


class LeavePolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "leave_policies"

    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    accrual_frequency: Mapped[str] = mapped_column(String(30), default="monthly", nullable=False)
    accrual_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    sandwich_rule_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_days_notice: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    carry_forward_max: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    allow_lop: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LeaveBalance(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, AuditMixin):
    __tablename__ = "leave_balances"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    accrued: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    used: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    adjusted: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "leave_type_id", "year", name="uq_leave_balance_emp_type_year"),
    )

    @property
    def closing_balance(self) -> Decimal:
        return self.opening_balance + self.accrued + self.adjusted - self.used


class LeaveRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "leave_requests"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_half_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    half_day_period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sandwich_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    lop_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    hr_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)


class LeaveTransaction(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "leave_transactions"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("leave_requests.id", ondelete="SET NULL"), nullable=True
    )
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    days: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class CompOffRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "comp_off_requests"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    worked_date: Mapped[date] = mapped_column(Date, nullable=False)
    comp_off_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
