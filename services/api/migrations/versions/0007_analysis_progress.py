"""add durable analysis progress
Revision ID: 0007_analysis_progress
Revises: 0006_product_metadata
"""
from alembic import op
import sqlalchemy as sa
revision = "0007_analysis_progress"
down_revision = "0006_product_metadata"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("analysis_jobs", sa.Column("progress_stage", sa.String(40), nullable=False, server_default="queued"))
    op.add_column("analysis_jobs", sa.Column("progress_message", sa.String(240), nullable=True))
    op.add_column("analysis_jobs", sa.Column("progress_completed", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("analysis_jobs", sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("analysis_jobs", sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"))

def downgrade() -> None:
    for column in ("progress_percent", "progress_total", "progress_completed", "progress_message", "progress_stage"):
        op.drop_column("analysis_jobs", column)
