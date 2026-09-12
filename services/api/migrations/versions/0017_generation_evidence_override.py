"""persist explicit missing-evidence generation overrides

Revision ID: 0017_evidence_override
Revises: 0016_generation_presentation
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_evidence_override"
down_revision = "0016_generation_presentation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generation_jobs", sa.Column("evidence_override", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("generation_jobs", sa.Column("missing_evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))


def downgrade() -> None:
    op.drop_column("generation_jobs", "missing_evidence")
    op.drop_column("generation_jobs", "evidence_override")
