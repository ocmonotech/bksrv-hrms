"""RBAC system — roles, permissions, user_tenant_access, audit_logs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_rbac"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("module", sa.String(50), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.UniqueConstraint("module", "action", name="uq_permissions_module_action"),
    )
    op.create_index("ix_permissions_module", "permissions", ["module"])
    op.create_index("ix_permissions_action", "permissions", ["action"])

    op.create_table(
        "roles",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_roles_tenant_slug"),
    )
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])
    op.create_index("ix_roles_slug", "roles", ["slug"])

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("role_id", sa.CHAR(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.CHAR(36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    op.create_table(
        "user_tenant_access",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.CHAR(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role_id", sa.CHAR(36), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("assigned_by", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("user_id", "tenant_id", "company_id", name="uq_user_tenant_company_access"),
    )
    op.create_index("ix_user_tenant_access_tenant_id", "user_tenant_access", ["tenant_id"])
    op.create_index("ix_user_tenant_access_user_id", "user_tenant_access", ["user_id"])
    op.create_index("ix_user_tenant_access_company_id", "user_tenant_access", ["company_id"])
    op.create_index("ix_user_tenant_access_role_id", "user_tenant_access", ["role_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("target_user_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # Drop legacy membership table if present
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "tenant_memberships" in inspector.get_table_names():
        op.drop_table("tenant_memberships")


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("user_tenant_access")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")

    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("tenant_id", sa.CHAR(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", sa.CHAR(36), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="employee"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("user_id", "tenant_id", "company_id", name="uq_membership_user_tenant_company"),
    )
