"""create users, workspaces, and memberships

Revision ID: 0001_workspace_memberships
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_workspace_memberships"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("clerk_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("clerk_user_id"),
    )
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"])
    op.create_table("workspaces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table("workspace_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),
    )
    op.create_index("ix_workspace_memberships_workspace_id", "workspace_memberships", ["workspace_id"])
    op.create_index("ix_workspace_memberships_user_id", "workspace_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_table("workspace_memberships")
    op.drop_table("workspaces")
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_table("users")
