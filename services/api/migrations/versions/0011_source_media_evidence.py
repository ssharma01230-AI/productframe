"""persist model-derived source media evidence

Revision ID: 0011_source_media_evidence
Revises: 0010_require_graph_thread_id
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_source_media_evidence"
down_revision = "0010_require_graph_thread_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("source_assets", sa.Column("media_evidence", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("source_assets", "media_evidence")
