"""create products and source assets

Revision ID: 0002_products_source_assets
Revises: 0001_workspace_memberships
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_products_source_assets"
down_revision = "0001_workspace_memberships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("products",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_products_workspace_id", "products", ["workspace_id"])
    op.create_table("source_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_source_assets_product_id", "source_assets", ["product_id"])


def downgrade() -> None:
    op.drop_table("source_assets")
    op.drop_table("products")
