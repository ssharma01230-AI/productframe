"""require stable generation graph thread IDs

Revision ID: 0010_require_graph_thread_id
Revises: 0009_generation_context
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_require_graph_thread_id"
down_revision = "0009_generation_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE generation_jobs SET graph_thread_id = 'generation-job-' || id WHERE graph_thread_id IS NULL")
    op.alter_column("generation_jobs", "graph_thread_id", existing_type=sa.String(length=120), nullable=False)


def downgrade() -> None:
    op.alter_column("generation_jobs", "graph_thread_id", existing_type=sa.String(length=120), nullable=True)
