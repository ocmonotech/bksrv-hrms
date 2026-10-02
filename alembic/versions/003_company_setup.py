"""Company setup module — profiles, branches, departments, and related entities."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_company_setup"
down_revision: Union[str, None] = "002_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list:
    return [
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("company_id", sa.CHAR(36), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("registration_number", sa.String(100), nullable=True),
        sa.Column("tax_id", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.String(512), nullable=True),
        sa.Column("address_line1", sa.String(255), nullable=True),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=False, server_default="India"),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="INR"),
        sa.Column("fiscal_year_start_month", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
    )
    op.create_index("ix_company_profiles_tenant_id", "company_profiles", ["tenant_id"])

    op.create_table(
        "branches",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address_line1", sa.String(255), nullable=True),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=False, server_default="India"),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("is_head_office", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_branches_tenant_code"),
    )
    op.create_index("ix_branches_tenant_id", "branches", ["tenant_id"])

    op.create_table(
        "departments",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("branch_id", sa.CHAR(36), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_id", sa.CHAR(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("head_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_departments_tenant_code"),
    )

    op.create_table(
        "grades",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_grades_tenant_code"),
    )

    op.create_table(
        "designations",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("department_id", sa.CHAR(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("grade_id", sa.CHAR(36), sa.ForeignKey("grades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_designations_tenant_code"),
    )

    op.create_table(
        "cost_centers",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("department_id", sa.CHAR(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("budget_code", sa.String(50), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_cost_centers_tenant_code"),
    )

    op.create_table(
        "holidays",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("holiday_type", sa.String(50), nullable=False, server_default="public"),
        sa.Column("branch_id", sa.CHAR(36), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
    )
    op.create_index("ix_holidays_holiday_date", "holidays", ["holiday_date"])

    op.create_table(
        "policies",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=False, server_default="general"),
        sa.Column("summary", sa.String(500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("document_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_policies_tenant_code"),
    )

    op.create_table(
        "approval_workflows",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_approval_workflows_tenant_code"),
    )

    op.create_table(
        "approval_steps",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("workflow_id", sa.CHAR(36), sa.ForeignKey("approval_workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("approver_type", sa.String(50), nullable=False, server_default="role"),
        sa.Column("approver_role", sa.String(50), nullable=True),
        sa.Column("approver_user_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit_columns(),
        sa.UniqueConstraint("workflow_id", "step_order", name="uq_approval_steps_workflow_order"),
    )


def downgrade() -> None:
    op.drop_table("approval_steps")
    op.drop_table("approval_workflows")
    op.drop_table("policies")
    op.drop_table("holidays")
    op.drop_table("cost_centers")
    op.drop_table("designations")
    op.drop_table("grades")
    op.drop_table("departments")
    op.drop_table("branches")
    op.drop_table("company_profiles")
