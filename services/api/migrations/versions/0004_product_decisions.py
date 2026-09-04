"""add product names and review decisions

Revision ID: 0004_product_decisions
Revises: 0003_analysis_jobs
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_product_decisions"
down_revision = "0003_analysis_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_analysis_records", sa.Column("product_name", sa.String(160), nullable=False, server_default="Unconfirmed product"))
    op.alter_column("product_analysis_records", "confirmation_status", server_default="suggested")


def downgrade() -> None:
    op.drop_column("product_analysis_records", "product_name")
