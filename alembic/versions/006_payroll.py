"""Payroll module — salary structures, runs, payslips, statutory, F&F."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_payroll"
down_revision: Union[str, None] = "005_attendance_shift_leave"
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
        "salary_components",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("component_type", sa.String(20), nullable=False),
        sa.Column("calculation_type", sa.String(30), server_default="fixed", nullable=False),
        sa.Column("is_taxable", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_statutory", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("pf_applicable", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("esi_applicable", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("pt_applicable", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_salary_components_tenant_code"),
    )

    op.create_table(
        "salary_structures",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("annual_ctc", sa.Numeric(14, 2), nullable=True),
        sa.Column("components_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_salary_structures_tenant_code"),
    )

    op.create_table(
        "statutory_settings",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("pf_employee_rate", sa.Numeric(5, 4), server_default="0.12", nullable=False),
        sa.Column("pf_employer_rate", sa.Numeric(5, 4), server_default="0.12", nullable=False),
        sa.Column("pf_wage_ceiling", sa.Numeric(12, 2), server_default="15000", nullable=False),
        sa.Column("esi_employee_rate", sa.Numeric(5, 4), server_default="0.0075", nullable=False),
        sa.Column("esi_employer_rate", sa.Numeric(5, 4), server_default="0.0325", nullable=False),
        sa.Column("esi_gross_threshold", sa.Numeric(12, 2), server_default="21000", nullable=False),
        sa.Column("pt_slabs_json", sa.Text(), nullable=False),
        sa.Column("tds_rate", sa.Numeric(5, 4), server_default="0", nullable=False),
        sa.Column("overtime_multiplier", sa.Numeric(4, 2), server_default="2", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_statutory_settings_tenant_code"),
    )

    op.create_table(
        "employee_salary_structures",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("structure_id", sa.CHAR(36), sa.ForeignKey("salary_structures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("annual_ctc", sa.Numeric(14, 2), nullable=False),
        sa.Column("arrears_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
    )

    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("working_days", sa.Integer(), server_default="26", nullable=False),
        sa.Column("run_date", sa.Date(), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_gross", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("total_deductions", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("total_net", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("employee_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("tenant_id", "month", "year", name="uq_payroll_runs_tenant_period"),
    )

    op.create_table(
        "payroll_employees",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("payroll_run_id", sa.CHAR(36), sa.ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("working_days", sa.Integer(), server_default="26", nullable=False),
        sa.Column("payable_days", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("lop_days", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("overtime_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gross_earnings", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_deductions", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("net_pay", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("arrears_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("reimbursement_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("pf_employee", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("pf_employer", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("esi_employee", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("esi_employer", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("professional_tax", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("tds_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("lop_deduction", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("is_processed", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("payroll_run_id", "employee_id", name="uq_payroll_employees_run_emp"),
    )

    op.create_table(
        "payroll_earnings",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("payroll_employee_id", sa.CHAR(36), sa.ForeignKey("payroll_employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_id", sa.CHAR(36), sa.ForeignKey("salary_components.id", ondelete="SET NULL"), nullable=True),
        sa.Column("component_code", sa.String(50), nullable=False),
        sa.Column("component_name", sa.String(255), nullable=False),
        sa.Column("earning_type", sa.String(30), server_default="regular", nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        *_ts(),
    )

    op.create_table(
        "payroll_deductions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("payroll_employee_id", sa.CHAR(36), sa.ForeignKey("payroll_employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_id", sa.CHAR(36), sa.ForeignKey("salary_components.id", ondelete="SET NULL"), nullable=True),
        sa.Column("component_code", sa.String(50), nullable=False),
        sa.Column("component_name", sa.String(255), nullable=False),
        sa.Column("deduction_type", sa.String(30), server_default="other", nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        *_ts(),
    )

    op.create_table(
        "payslips",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("payroll_employee_id", sa.CHAR(36), sa.ForeignKey("payroll_employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payroll_run_id", sa.CHAR(36), sa.ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("gross_earnings", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_deductions", sa.Numeric(14, 2), nullable=False),
        sa.Column("net_pay", sa.Numeric(14, 2), nullable=False),
        sa.Column("line_items_json", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("tenant_id", "employee_id", "month", "year", name="uq_payslips_emp_period"),
    )

    op.create_table(
        "tax_declarations",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("financial_year", sa.String(10), nullable=False),
        sa.Column("regime", sa.String(20), server_default="new", nullable=False),
        sa.Column("section", sa.String(50), nullable=False),
        sa.Column("declared_amount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("approved_amount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        *_audit(),
    )

    op.create_table(
        "investment_proofs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tax_declaration_id", sa.CHAR(36), sa.ForeignKey("tax_declarations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("proof_type", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("document_path", sa.String(1024), nullable=True),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        *_audit(),
    )

    op.create_table(
        "full_and_final_settlements",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_working_date", sa.Date(), nullable=False),
        sa.Column("settlement_json", sa.Text(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_deductions", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("net_payable", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit(),
    )


def downgrade() -> None:
    for table in (
        "full_and_final_settlements",
        "investment_proofs",
        "tax_declarations",
        "payslips",
        "payroll_deductions",
        "payroll_earnings",
        "payroll_employees",
        "payroll_runs",
        "employee_salary_structures",
        "statutory_settings",
        "salary_structures",
        "salary_components",
    ):
        op.drop_table(table)
