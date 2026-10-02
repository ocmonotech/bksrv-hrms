"""Recruitment, onboarding, and performance modules."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_recruit_onboard_perf"
down_revision: Union[str, None] = "006_payroll"
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
        "job_openings",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("department_id", sa.CHAR(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("designation_id", sa.CHAR(36), sa.ForeignKey("designations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("branch_id", sa.CHAR(36), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("openings_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("salary_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("salary_max", sa.Numeric(12, 2), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closing_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_job_openings_tenant_code"),
    )

    op.create_table(
        "candidates",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("job_opening_id", sa.CHAR(36), sa.ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("mobile", sa.String(20), nullable=True),
        sa.Column("source", sa.String(50), server_default="direct", nullable=False),
        sa.Column("current_stage", sa.String(50), server_default="applied", nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("resume_path", sa.String(1024), nullable=True),
        sa.Column("experience_years", sa.Numeric(4, 1), nullable=True),
        sa.Column("current_company", sa.String(255), nullable=True),
        sa.Column("referred_by_employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit(),
    )

    op.create_table(
        "candidate_documents",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("candidate_id", sa.CHAR(36), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(30), server_default="uploaded", nullable=False),
        *_audit(),
    )

    op.create_table(
        "candidate_stage_histories",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("candidate_id", sa.CHAR(36), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_stage", sa.String(50), nullable=True),
        sa.Column("to_stage", sa.String(50), nullable=False),
        sa.Column("changed_by", sa.String(36), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        *_ts(),
    )

    op.create_table(
        "interviews",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("candidate_id", sa.CHAR(36), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_opening_id", sa.CHAR(36), sa.ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interview_type", sa.String(50), server_default="technical", nullable=False),
        sa.Column("interviewer_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mode", sa.String(30), server_default="online", nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), server_default="scheduled", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit(),
    )

    op.create_table(
        "interview_feedbacks",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("interview_id", sa.CHAR(36), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("recommendation", sa.String(30), server_default="hold", nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("approver_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
    )

    op.create_table(
        "offer_letters",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("candidate_id", sa.CHAR(36), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_opening_id", sa.CHAR(36), sa.ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("offered_ctc", sa.Numeric(14, 2), nullable=False),
        sa.Column("joining_date", sa.Date(), nullable=False),
        sa.Column("designation_id", sa.CHAR(36), sa.ForeignKey("designations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("approver_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_path", sa.String(1024), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit(),
    )

    op.create_table(
        "referrals",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("candidate_id", sa.CHAR(36), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("referrer_employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bonus_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("bonus_status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit(),
    )

    op.create_table(
        "onboarding_checklists",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("department_id", sa.CHAR(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_onboarding_checklists_tenant_code"),
    )

    op.create_table(
        "onboarding_tasks",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("checklist_id", sa.CHAR(36), sa.ForeignKey("onboarding_checklists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("sequence", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
    )

    op.create_table(
        "new_joiner_documents",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("verified_by", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        *_audit(),
    )

    op.create_table(
        "probation_reviews",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("reviewer_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(30), server_default="pending", nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("approver_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extension_end_date", sa.Date(), nullable=True),
        *_audit(),
    )

    op.create_table(
        "goals",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), server_default="100", nullable=False),
        sa.Column("progress", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("manager_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        *_audit(),
    )

    op.create_table(
        "okrs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("objective", sa.String(500), nullable=False),
        sa.Column("key_results_json", sa.Text(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        *_audit(),
    )

    op.create_table(
        "review_cycles",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("cycle_type", sa.String(30), server_default="annual", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_review_cycles_tenant_code"),
    )

    op.create_table(
        "self_reviews",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("review_cycle_id", sa.CHAR(36), sa.ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("responses_json", sa.Text(), nullable=False),
        sa.Column("rating", sa.Numeric(4, 2), nullable=True),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
        sa.UniqueConstraint("review_cycle_id", "employee_id", name="uq_self_reviews_cycle_emp"),
    )

    op.create_table(
        "manager_reviews",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("review_cycle_id", sa.CHAR(36), sa.ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("manager_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rating", sa.Numeric(4, 2), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("hr_override", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("approver_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
        sa.UniqueConstraint("review_cycle_id", "employee_id", name="uq_manager_reviews_cycle_emp"),
    )

    op.create_table(
        "feedback_360",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("review_cycle_id", sa.CHAR(36), sa.ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship", sa.String(50), server_default="peer", nullable=False),
        sa.Column("rating", sa.Numeric(4, 2), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
    )

    op.create_table(
        "appraisals",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("review_cycle_id", sa.CHAR(36), sa.ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("final_rating", sa.Numeric(4, 2), nullable=True),
        sa.Column("increment_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("promotion_recommended", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("approver_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit(),
        sa.UniqueConstraint("review_cycle_id", "employee_id", name="uq_appraisals_cycle_emp"),
    )

    op.create_table(
        "performance_improvement_plans",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("manager_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("goals_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("outcome", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit(),
    )


def downgrade() -> None:
    for table in (
        "performance_improvement_plans",
        "appraisals",
        "feedback_360",
        "manager_reviews",
        "self_reviews",
        "review_cycles",
        "okrs",
        "goals",
        "probation_reviews",
        "new_joiner_documents",
        "onboarding_tasks",
        "onboarding_checklists",
        "referrals",
        "offer_letters",
        "interview_feedbacks",
        "interviews",
        "candidate_stage_histories",
        "candidate_documents",
        "candidates",
        "job_openings",
    ):
        op.drop_table(table)
