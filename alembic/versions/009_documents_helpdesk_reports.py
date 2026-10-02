"""Documents, helpdesk, and reports modules."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_documents_helpdesk_reports"
down_revision: Union[str, None] = "008_ai_logs"
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
        "document_categories",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("parent_id", sa.CHAR(36), sa.ForeignKey("document_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_document_categories_tenant_code"),
    )

    op.create_table(
        "document_employee_documents",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.CHAR(36), sa.ForeignKey("document_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("is_confidential", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("uploaded_by", sa.String(36), nullable=True),
        *_audit(),
    )

    op.create_table(
        "document_company_documents",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.CHAR(36), sa.ForeignKey("document_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("branch_id", sa.CHAR(36), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("department_id", sa.CHAR(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("visibility", sa.String(30), nullable=False, server_default="all"),
        sa.Column("version", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
    )

    op.create_table(
        "letter_templates",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("letter_type", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("placeholders", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_letter_templates_tenant_code"),
    )

    op.create_table(
        "generated_letters",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", sa.CHAR(36), sa.ForeignKey("letter_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("generated_by", sa.String(36), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        *_audit(),
    )

    op.create_table(
        "ticket_categories",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("default_sla_hours", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_ticket_categories_tenant_code"),
    )

    op.create_table(
        "helpdesk_tickets",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.CHAR(36), sa.ForeignKey("ticket_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ticket_number", sa.String(30), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("requester_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("department_id", sa.CHAR(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("branch_id", sa.CHAR(36), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "ticket_number", name="uq_helpdesk_tickets_tenant_number"),
    )

    op.create_table(
        "ticket_replies",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", sa.CHAR(36), sa.ForeignKey("helpdesk_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        *_audit(),
    )

    op.create_table(
        "ticket_assignments",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", sa.CHAR(36), sa.ForeignKey("helpdesk_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_to", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        *_audit(),
    )

    op.create_table(
        "ticket_slas",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.CHAR(36), sa.ForeignKey("ticket_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("response_hours", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("resolution_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "category_id", "priority", name="uq_ticket_slas_tenant_category_priority"),
    )


def downgrade() -> None:
    op.drop_table("ticket_slas")
    op.drop_table("ticket_assignments")
    op.drop_table("ticket_replies")
    op.drop_table("helpdesk_tickets")
    op.drop_table("ticket_categories")
    op.drop_table("generated_letters")
    op.drop_table("letter_templates")
    op.drop_table("document_company_documents")
    op.drop_table("document_employee_documents")
    op.drop_table("document_categories")
