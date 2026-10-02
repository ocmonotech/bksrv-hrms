"""AI request logs table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_ai_logs"
down_revision: Union[str, None] = "007_recruit_onboard_perf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_request_logs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("module_name", sa.String(50), nullable=False),
        sa.Column("prompt_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False, server_default="mock"),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("request_summary", sa.Text(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_request_logs_tenant_id", "ai_request_logs", ["tenant_id"])
    op.create_index("ix_ai_request_logs_user_id", "ai_request_logs", ["user_id"])
    op.create_index("ix_ai_request_logs_module_name", "ai_request_logs", ["module_name"])
    op.create_index("ix_ai_request_logs_prompt_type", "ai_request_logs", ["prompt_type"])
    op.create_index("ix_ai_request_logs_created_at", "ai_request_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_request_logs_created_at", table_name="ai_request_logs")
    op.drop_index("ix_ai_request_logs_prompt_type", table_name="ai_request_logs")
    op.drop_index("ix_ai_request_logs_module_name", table_name="ai_request_logs")
    op.drop_index("ix_ai_request_logs_user_id", table_name="ai_request_logs")
    op.drop_index("ix_ai_request_logs_tenant_id", table_name="ai_request_logs")
    op.drop_table("ai_request_logs")
