"""persist detailed product understanding and graph job identity

Revision ID: 0009_generation_context
Revises: 0008_generation_persistence
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_generation_context"
down_revision = "0008_generation_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("products", "product_analysis_records"):
        op.add_column(table, sa.Column("global_details", sa.JSON(), nullable=True))
        op.add_column(table, sa.Column("category_details", sa.JSON(), nullable=True))
        op.add_column(table, sa.Column("confidence_details", sa.JSON(), nullable=True))

    op.add_column("generation_jobs", sa.Column("graph_thread_id", sa.String(length=120), nullable=True))
    op.add_column("generation_jobs", sa.Column("preview_object_key", sa.String(length=500), nullable=True))
    op.add_column("generation_jobs", sa.Column("provider_request_id", sa.String(length=255), nullable=True))
    op.add_column("generation_jobs", sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE generation_jobs SET graph_thread_id = 'generation-job-' || id WHERE graph_thread_id IS NULL")
    op.create_unique_constraint("uq_generation_job_graph_thread_id", "generation_jobs", ["graph_thread_id"])


def downgrade() -> None:
    op.drop_constraint("uq_generation_job_graph_thread_id", "generation_jobs", type_="unique")
    for column in ("next_attempt_at", "provider_request_id", "preview_object_key", "graph_thread_id"):
        op.drop_column("generation_jobs", column)
    for table in ("product_analysis_records", "products"):
        for column in ("confidence_details", "category_details", "global_details"):
            op.drop_column(table, column)
