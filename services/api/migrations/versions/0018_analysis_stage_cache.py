"""add durable image analysis stage state and cache

Revision ID: 0018_analysis_stage_cache
Revises: 0017_evidence_override
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_analysis_stage_cache"
down_revision = "0017_evidence_override"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_jobs", sa.Column("stage_state", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("analysis_job_images", sa.Column("image_hash", sa.String(length=64), nullable=True))
    op.add_column("analysis_job_images", sa.Column("stage_results", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.create_index("ix_analysis_job_images_image_hash", "analysis_job_images", ["image_hash"])
    op.create_table(
        "image_analysis_cache",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("image_hash", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("moderation_result", sa.JSON(), nullable=True),
        sa.Column("screening_result", sa.JSON(), nullable=True),
        sa.Column("identity_result", sa.JSON(), nullable=True),
        sa.Column("classification_result", sa.JSON(), nullable=True),
        sa.Column("media_evidence", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("image_hash", "model", "prompt_version", "schema_version", name="uq_image_analysis_cache_key"),
    )
    op.create_index("ix_image_analysis_cache_image_hash", "image_analysis_cache", ["image_hash"])


def downgrade() -> None:
    op.drop_index("ix_image_analysis_cache_image_hash", table_name="image_analysis_cache")
    op.drop_table("image_analysis_cache")
    op.drop_index("ix_analysis_job_images_image_hash", table_name="analysis_job_images")
    op.drop_column("analysis_job_images", "stage_results")
    op.drop_column("analysis_job_images", "image_hash")
    op.drop_column("analysis_jobs", "stage_state")
