"""Extended HR modules: expenses, travel, assets, communication, exit."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_extended_modules"
down_revision: Union[str, None] = "009_documents_helpdesk_reports"
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
        "expense_policies",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("max_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("requires_receipt", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_expense_policies_tenant_code"),
    )

    op.create_table(
        "expense_claims",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_id", sa.CHAR(36), sa.ForeignKey("expense_policies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        *_audit(),
    )

    op.create_table(
        "expense_advances",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("purpose", sa.String(500), nullable=False),
        sa.Column("requested_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        *_audit(),
    )

    op.create_table(
        "travel_policies",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("max_budget", sa.Numeric(14, 2), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_travel_policies_tenant_code"),
    )

    op.create_table(
        "travel_requests",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination", sa.String(255), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        *_audit(),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("serial_number", sa.String(100), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="available"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_assets_tenant_code"),
    )

    op.create_table(
        "asset_assignments",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.CHAR(36), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_date", sa.Date(), nullable=False),
        sa.Column("return_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit(),
    )

    op.create_table(
        "announcements",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
    )

    op.create_table(
        "communication_templates",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False, server_default="email"),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_communication_templates_tenant_code"),
    )

    op.create_table(
        "communication_logs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", sa.CHAR(36), sa.ForeignKey("communication_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False, server_default="email"),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
    )

    op.create_table(
        "resignations",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resignation_date", sa.Date(), nullable=False),
        sa.Column("last_working_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        *_audit(),
    )

    op.create_table(
        "exit_clearances",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resignation_id", sa.CHAR(36), sa.ForeignKey("resignations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checklist_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "resignation_id", name="uq_exit_clearances_tenant_resignation"),
    )

    op.create_table(
        "exit_interviews",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resignation_id", sa.CHAR(36), sa.ForeignKey("resignations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conducted_by", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("interview_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        *_audit(),
    )


def downgrade() -> None:
    for table in (
        "exit_interviews",
        "exit_clearances",
        "resignations",
        "communication_logs",
        "communication_templates",
        "announcements",
        "asset_assignments",
        "assets",
        "travel_requests",
        "travel_policies",
        "expense_advances",
        "expense_claims",
        "expense_policies",
    ):
        op.drop_table(table)
