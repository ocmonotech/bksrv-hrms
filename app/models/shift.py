from __future__ import annotations

import uuid
from datetime import date, time
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Shift(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "shifts"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_minutes: Mapped[int] = mapped_column(default=60, nullable=False)
    grace_minutes: Mapped[int] = mapped_column(default=10, nullable=False)
    is_night_shift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_shifts_tenant_code"),)


class EmployeeShiftAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_shift_assignments"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Roster(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "rosters"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    roster_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "roster_date", name="uq_rosters_employee_date"),
    )


class ShiftSwapRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "shift_swap_requests"

    requester_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    roster_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    current_shift_id: Mapped[uuid.UUID] = mapped_column(CHAR(36), ForeignKey("shifts.id"), nullable=False)
    requested_shift_id: Mapped[uuid.UUID] = mapped_column(CHAR(36), ForeignKey("shifts.id"), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
