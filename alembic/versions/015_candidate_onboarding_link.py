"""Candidate onboarding link."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_candidate_onboarding_link"
down_revision: Union[str, None] = "014_job_boards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("employee_id", sa.CHAR(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_candidates_employee_id", "candidates", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_candidates_employee_id", table_name="candidates")
    op.drop_column("candidates", "employee_id")
