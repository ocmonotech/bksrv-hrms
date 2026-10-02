"""Employee master — core profile and related detail tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_employee_master"
down_revision: Union[str, None] = "003_company_setup"
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


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("company_id", sa.CHAR(36), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("employee_code", sa.String(50), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("mobile", sa.String(20), nullable=True),
        sa.Column("photo_url", sa.String(512), nullable=True),
        sa.Column("branch_id", sa.CHAR(36), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("department_id", sa.CHAR(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("designation_id", sa.CHAR(36), sa.ForeignKey("designations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("grade_id", sa.CHAR(36), sa.ForeignKey("grades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reporting_manager_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("confirmation_date", sa.Date(), nullable=True),
        sa.Column("exit_date", sa.Date(), nullable=True),
        sa.Column("employment_type", sa.String(50), nullable=False, server_default="full_time"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "employee_code", name="uq_employees_tenant_code"),
    )
    op.create_index("ix_employees_tenant_id", "employees", ["tenant_id"])
    op.create_index("ix_employees_email", "employees", ["email"])
    op.create_index("ix_employees_status", "employees", ["status"])

    detail_tables = [
        (
            "employee_personal_details",
            [
                sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True),
                sa.Column("date_of_birth", sa.Date(), nullable=True),
                sa.Column("gender", sa.String(20), nullable=True),
                sa.Column("marital_status", sa.String(30), nullable=True),
                sa.Column("blood_group", sa.String(10), nullable=True),
                sa.Column("nationality", sa.String(100), server_default="Indian", nullable=False),
                sa.Column("personal_email", sa.String(255), nullable=True),
                sa.Column("current_address", sa.Text(), nullable=True),
                sa.Column("permanent_address", sa.Text(), nullable=True),
                sa.Column("emergency_contact_name", sa.String(255), nullable=True),
                sa.Column("emergency_contact_phone", sa.String(20), nullable=True),
                sa.Column("pan_number", sa.String(10), nullable=True),
                sa.Column("aadhaar_number", sa.String(12), nullable=True),
            ],
        ),
        (
            "employee_job_details",
            [
                sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True),
                sa.Column("job_title", sa.String(255), nullable=True),
                sa.Column("work_location", sa.String(255), nullable=True),
                sa.Column("shift_type", sa.String(50), nullable=True),
                sa.Column("probation_end_date", sa.Date(), nullable=True),
                sa.Column("notice_period_days", sa.Integer(), nullable=True),
                sa.Column("cost_center_id", sa.CHAR(36), sa.ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True),
            ],
        ),
        (
            "employee_bank_details",
            [
                sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True),
                sa.Column("account_holder_name", sa.String(255), nullable=False),
                sa.Column("bank_name", sa.String(255), nullable=False),
                sa.Column("account_number", sa.String(50), nullable=False),
                sa.Column("ifsc_code", sa.String(20), nullable=False),
                sa.Column("branch_name", sa.String(255), nullable=True),
                sa.Column("is_primary", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            ],
        ),
        (
            "employee_salary_details",
            [
                sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True),
                sa.Column("basic_salary", sa.Numeric(12, 2), nullable=True),
                sa.Column("gross_salary", sa.Numeric(12, 2), nullable=True),
                sa.Column("net_salary", sa.Numeric(12, 2), nullable=True),
                sa.Column("ctc_annual", sa.Numeric(14, 2), nullable=True),
                sa.Column("currency", sa.String(8), server_default="INR", nullable=False),
                sa.Column("pay_frequency", sa.String(20), server_default="monthly", nullable=False),
                sa.Column("effective_from", sa.Date(), nullable=True),
            ],
        ),
        (
            "employee_statutory_details",
            [
                sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True),
                sa.Column("pf_number", sa.String(50), nullable=True),
                sa.Column("uan", sa.String(20), nullable=True),
                sa.Column("esi_number", sa.String(50), nullable=True),
                sa.Column("pt_state", sa.String(100), nullable=True),
                sa.Column("tax_regime", sa.String(20), server_default="new", nullable=False),
                sa.Column("pan_linked", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            ],
        ),
    ]

    for table_name, extra_cols in detail_tables:
        op.create_table(
            table_name,
            sa.Column("id", sa.CHAR(36), primary_key=True),
            sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
            *extra_cols,
            *_audit(),
        )

    op.create_table(
        "employee_family_details",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("relationship", sa.String(50), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("contact_number", sa.String(20), nullable=True),
        sa.Column("is_dependent", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        *_audit(),
    )

    op.create_table(
        "employee_education",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution", sa.String(255), nullable=False),
        sa.Column("degree", sa.String(255), nullable=False),
        sa.Column("field_of_study", sa.String(255), nullable=True),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(50), nullable=True),
        *_audit(),
    )

    op.create_table(
        "employee_experience",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("job_title", sa.String(255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        *_audit(),
    )

    op.create_table(
        "employee_documents",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", sa.String(36), nullable=True),
        *_audit(),
    )

    op.create_table(
        "employee_timeline",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "employee_profile_update_requests",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("changes_json", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("employee_profile_update_requests")
    op.drop_table("employee_timeline")
    op.drop_table("employee_documents")
    op.drop_table("employee_experience")
    op.drop_table("employee_education")
    op.drop_table("employee_family_details")
    op.drop_table("employee_statutory_details")
    op.drop_table("employee_salary_details")
    op.drop_table("employee_bank_details")
    op.drop_table("employee_job_details")
    op.drop_table("employee_personal_details")
    op.drop_table("employees")
