"""persist image provider routing and fallback metadata

Revision ID: 0015_generation_provider_routing
Revises: 0014_generation_job_order
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_generation_provider_routing"
down_revision = "0014_generation_job_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generation_jobs", sa.Column("provider", sa.String(length=30), nullable=True))
    op.add_column("generation_jobs", sa.Column("provider_model", sa.String(length=120), nullable=True))
    op.add_column("generation_jobs", sa.Column("provider_fallback_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_generation_jobs_provider", "generation_jobs", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_provider", table_name="generation_jobs")
    op.drop_column("generation_jobs", "provider_fallback_count")
    op.drop_column("generation_jobs", "provider_model")
    op.drop_column("generation_jobs", "provider")
