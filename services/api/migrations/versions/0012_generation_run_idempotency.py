"""add generation run idempotency keys

Revision ID: 0012_generation_run_idempotency
Revises: 0011_source_media_evidence
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_generation_run_idempotency"
down_revision = "0011_source_media_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generation_runs", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    op.create_index("ix_generation_runs_idempotency_key", "generation_runs", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_generation_runs_idempotency_key", table_name="generation_runs")
    op.drop_column("generation_runs", "idempotency_key")
