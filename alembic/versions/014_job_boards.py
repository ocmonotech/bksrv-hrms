"""Job board integrations and interview feedback enhancements."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_job_boards"
down_revision: Union[str, None] = "013_timesheets_training_surveys"
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
        "job_board_connections",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), server_default="disconnected", nullable=False),
        sa.Column("account_name", sa.String(255), nullable=True),
        sa.Column("api_key_hint", sa.String(20), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
        sa.UniqueConstraint("tenant_id", "platform", name="uq_job_board_connections_tenant_platform"),
    )
    op.create_index("ix_job_board_connections_platform", "job_board_connections", ["platform"])

    op.create_table(
        "job_board_postings",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_opening_id", sa.CHAR(36), sa.ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("external_job_id", sa.String(100), nullable=True),
        sa.Column("external_url", sa.String(1024), nullable=True),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("applicant_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        *_audit(),
        sa.UniqueConstraint(
            "tenant_id", "job_opening_id", "platform", name="uq_job_board_postings_tenant_job_platform"
        ),
    )
    op.create_index("ix_job_board_postings_job_opening_id", "job_board_postings", ["job_opening_id"])
    op.create_index("ix_job_board_postings_platform", "job_board_postings", ["platform"])
    op.create_index("ix_job_board_postings_status", "job_board_postings", ["status"])


def downgrade() -> None:
    op.drop_table("job_board_postings")
    op.drop_table("job_board_connections")
