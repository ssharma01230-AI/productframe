"""link approved analyses to final products
Revision ID: 0005_final_products
Revises: 0004_product_decisions
"""
from alembic import op
import sqlalchemy as sa
revision = "0005_final_products"
down_revision = "0004_product_decisions"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("product_analysis_records", sa.Column("final_product_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_analysis_final_product", "product_analysis_records", "products", ["final_product_id"], ["id"], ondelete="SET NULL")

def downgrade() -> None:
    op.drop_constraint("fk_analysis_final_product", "product_analysis_records", type_="foreignkey")
    op.drop_column("product_analysis_records", "final_product_id")
