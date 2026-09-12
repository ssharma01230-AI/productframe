"""persist requested generation model presentation

Revision ID: 0016_generation_presentation
Revises: 0015_generation_provider_routing
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_generation_presentation"
down_revision = "0015_generation_provider_routing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generation_jobs", sa.Column("presentation", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("generation_jobs", "presentation")
