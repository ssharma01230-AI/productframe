"""add deterministic ordering for generation jobs

Revision ID: 0014_generation_job_order
Revises: 0013_generation_review_decisions
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_generation_job_order"
down_revision = "0013_generation_review_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generation_jobs", sa.Column("job_index", sa.Integer(), nullable=True))
    op.execute(sa.text("UPDATE generation_jobs SET job_index = 0 WHERE job_index IS NULL"))
    op.alter_column("generation_jobs", "job_index", nullable=False, server_default="0")


def downgrade() -> None:
    op.drop_column("generation_jobs", "job_index")
