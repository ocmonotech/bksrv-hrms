"""Attendance, shift, roster, and leave modules."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_attendance_shift_leave"
down_revision: Union[str, None] = "004_employee_master"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit() -> list:
    return [
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _ts() -> list:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "shifts",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("break_minutes", sa.Integer(), server_default="60", nullable=False),
        sa.Column("grace_minutes", sa.Integer(), server_default="10", nullable=False),
        sa.Column("is_night_shift", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_shifts_tenant_code"),
    )
    op.create_index("ix_shifts_tenant_id", "shifts", ["tenant_id"])

    op.create_table(
        "employee_shift_assignments",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shift_id", sa.CHAR(36), sa.ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
    )

    op.create_table(
        "rosters",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shift_id", sa.CHAR(36), sa.ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("roster_date", sa.Date(), nullable=False),
        sa.Column("branch_id", sa.CHAR(36), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "employee_id", "roster_date", name="uq_rosters_employee_date"),
    )

    op.create_table(
        "shift_swap_requests",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("requester_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("roster_date", sa.Date(), nullable=False),
        sa.Column("current_shift_id", sa.CHAR(36), sa.ForeignKey("shifts.id"), nullable=False),
        sa.Column("requested_shift_id", sa.CHAR(36), sa.ForeignKey("shifts.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("approver_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.Date(), nullable=True),
        *_audit(),
    )

    op.create_table(
        "attendance_policies",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("grace_minutes", sa.Integer(), server_default="10", nullable=False),
        sa.Column("late_threshold_minutes", sa.Integer(), server_default="15", nullable=False),
        sa.Column("half_day_hours", sa.Numeric(4, 2), server_default="4", nullable=False),
        sa.Column("full_day_hours", sa.Numeric(4, 2), server_default="8", nullable=False),
        sa.Column("early_leave_threshold_minutes", sa.Integer(), server_default="15", nullable=False),
        sa.Column("require_gps_for_mobile", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("require_selfie_for_mobile", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_attendance_policies_tenant_code"),
    )

    op.create_table(
        "biometric_devices",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("device_code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("branch_id", sa.CHAR(36), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "device_code", name="uq_biometric_devices_tenant_code"),
    )

    op.create_table(
        "attendance_logs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("punch_type", sa.String(20), nullable=False),
        sa.Column("punch_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(30), server_default="web", nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("gps_accuracy", sa.Numeric(8, 2), nullable=True),
        sa.Column("selfie_path", sa.String(1024), nullable=True),
        sa.Column("device_id", sa.CHAR(36), sa.ForeignKey("biometric_devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("device_log_id", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("remarks", sa.String(500), nullable=True),
        sa.Column("is_valid", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "attendance_daily_summaries",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("shift_id", sa.CHAR(36), sa.ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("first_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_work_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("break_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(30), server_default="absent", nullable=False),
        sa.Column("late_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("early_leave_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("overtime_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_lop", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("lop_days", sa.Numeric(3, 2), server_default="0", nullable=False),
        sa.Column("payable_days", sa.Numeric(3, 2), server_default="0", nullable=False),
        sa.Column("regularization_status", sa.String(30), nullable=True),
        sa.Column("is_payroll_locked", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("tenant_id", "employee_id", "attendance_date", name="uq_attendance_daily_employee_date"),
    )

    op.create_table(
        "attendance_regularizations",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("requested_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("approver_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("hr_override", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("manager_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        *_audit(),
    )

    op.create_table(
        "leave_types",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("is_paid", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("allow_half_day", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("max_days_per_year", sa.Numeric(5, 2), nullable=True),
        sa.Column("color", sa.String(20), server_default="#3B82F6", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_leave_types_tenant_code"),
    )

    op.create_table(
        "leave_policies",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("leave_type_id", sa.CHAR(36), sa.ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("accrual_frequency", sa.String(30), server_default="monthly", nullable=False),
        sa.Column("accrual_days", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("sandwich_rule_enabled", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("min_days_notice", sa.Integer(), server_default="0", nullable=False),
        sa.Column("carry_forward_max", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("allow_lop", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
    )

    op.create_table(
        "leave_balances",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_type_id", sa.CHAR(36), sa.ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("opening_balance", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("accrued", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("used", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("adjusted", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("tenant_id", "employee_id", "leave_type_id", "year", name="uq_leave_balance_emp_type_year"),
    )

    op.create_table(
        "leave_requests",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_type_id", sa.CHAR(36), sa.ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("total_days", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_half_day", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("half_day_period", sa.String(20), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("approver_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("sandwich_days", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("lop_days", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("hr_override", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("manager_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        *_audit(),
    )

    op.create_table(
        "leave_transactions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_type_id", sa.CHAR(36), sa.ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_request_id", sa.CHAR(36), sa.ForeignKey("leave_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("days", sa.Numeric(5, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(6, 2), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        *_ts(),
    )

    op.create_table(
        "comp_off_requests",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("worked_date", sa.Date(), nullable=False),
        sa.Column("comp_off_date", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("approver_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        *_audit(),
    )


def downgrade() -> None:
    for table in (
        "comp_off_requests",
        "leave_transactions",
        "leave_requests",
        "leave_balances",
        "leave_policies",
        "leave_types",
        "attendance_regularizations",
        "attendance_daily_summaries",
        "attendance_logs",
        "biometric_devices",
        "attendance_policies",
        "shift_swap_requests",
        "rosters",
        "employee_shift_assignments",
        "shifts",
    ):
        op.drop_table(table)
