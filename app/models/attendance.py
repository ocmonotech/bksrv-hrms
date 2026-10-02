from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AttendancePolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "attendance_policies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    grace_minutes: Mapped[int] = mapped_column(default=10, nullable=False)
    late_threshold_minutes: Mapped[int] = mapped_column(default=15, nullable=False)
    half_day_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=4, nullable=False)
    full_day_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=8, nullable=False)
    early_leave_threshold_minutes: Mapped[int] = mapped_column(default=15, nullable=False)
    require_gps_for_mobile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_selfie_for_mobile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_attendance_policies_tenant_code"),)


class BiometricDevice(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "biometric_devices"

    device_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "device_code", name="uq_biometric_devices_tenant_code"),)


class AttendanceLog(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, AuditMixin):
    __tablename__ = "attendance_logs"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    punch_type: Mapped[str] = mapped_column(String(20), nullable=False)
    punch_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), default="web", nullable=False)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    gps_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    selfie_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("biometric_devices.id", ondelete="SET NULL"), nullable=True
    )
    device_log_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AttendanceDailySummary(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, AuditMixin):
    """Payroll-ready daily attendance aggregate."""

    __tablename__ = "attendance_daily_summaries"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    shift_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    first_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_work_minutes: Mapped[int] = mapped_column(default=0, nullable=False)
    break_minutes: Mapped[int] = mapped_column(default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="absent", nullable=False)
    late_minutes: Mapped[int] = mapped_column(default=0, nullable=False)
    early_leave_minutes: Mapped[int] = mapped_column(default=0, nullable=False)
    overtime_minutes: Mapped[int] = mapped_column(default=0, nullable=False)
    is_lop: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lop_days: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0, nullable=False)
    payable_days: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0, nullable=False)
    regularization_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_payroll_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "attendance_date", name="uq_attendance_daily_employee_date"),
    )


class AttendanceRegularization(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "attendance_regularizations"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    requested_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    hr_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)


class FieldVisit(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "field_visits"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    visit_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    check_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="mobile", nullable=False)
