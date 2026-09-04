"""store approved product metadata
Revision ID: 0006_product_metadata
Revises: 0005_final_products
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = "0006_product_metadata"
down_revision = "0005_final_products"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("products", sa.Column("category", sa.String(30), nullable=True))
    op.add_column("products", sa.Column("product_type", sa.String(160), nullable=True))
    op.add_column("products", sa.Column("colours", sa.String(300), nullable=True))
    op.add_column("products", sa.Column("materials", sa.String(300), nullable=True))
    op.add_column("products", sa.Column("features", JSONB, nullable=True))
    op.add_column("products", sa.Column("description", sa.String(320), nullable=True))

def downgrade() -> None:
    for column in ("description", "features", "materials", "colours", "product_type", "category"):
        op.drop_column("products", column)
