"""Timesheets, training, surveys modules."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_timesheets_training_surveys"
down_revision: Union[str, None] = "012_production_features"
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
        "timesheet_projects",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_billable", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_timesheet_projects_tenant_code"),
    )

    op.create_table(
        "timesheet_entries",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.CHAR(36), sa.ForeignKey("timesheet_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Numeric(5, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        *_audit(),
    )
    op.create_index("ix_timesheet_entries_employee_date", "timesheet_entries", ["employee_id", "entry_date"])

    op.create_table(
        "training_courses",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_hours", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("delivery_mode", sa.String(30), nullable=False, server_default="online"),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_training_courses_tenant_code"),
    )

    op.create_table(
        "training_enrollments",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.CHAR(36), sa.ForeignKey("training_courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="assigned"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "course_id", "employee_id", name="uq_training_enrollments_tenant_course_emp"),
    )

    op.create_table(
        "surveys",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("survey_type", sa.String(30), nullable=False, server_default="engagement"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        *_audit(),
    )

    op.create_table(
        "survey_questions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("survey_id", sa.CHAR(36), sa.ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(20), nullable=False, server_default="rating"),
        sa.Column("options_json", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        *_audit(),
    )

    op.create_table(
        "survey_responses",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("survey_id", sa.CHAR(36), sa.ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.CHAR(36), sa.ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("response_value", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        *_audit(),
    )


def downgrade() -> None:
    op.drop_table("survey_responses")
    op.drop_table("survey_questions")
    op.drop_table("surveys")
    op.drop_table("training_enrollments")
    op.drop_table("training_courses")
    op.drop_index("ix_timesheet_entries_employee_date", table_name="timesheet_entries")
    op.drop_table("timesheet_entries")
    op.drop_table("timesheet_projects")
