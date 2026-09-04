"""create durable image analysis job tables

Revision ID: 0003_analysis_jobs
Revises: 0002_products_source_assets
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_analysis_jobs"
down_revision = "0002_products_source_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("analysis_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("total_images", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_images", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_product_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(255), unique=True),
        sa.Column("error_message", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_analysis_jobs_workspace_id", "analysis_jobs", ["workspace_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    op.create_table("analysis_job_images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_asset_id", sa.String(36), sa.ForeignKey("source_assets.id", ondelete="SET NULL")),
        sa.Column("image_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("passed", sa.Boolean()),
        sa.Column("product_number", sa.Integer()),
        sa.Column("rejection_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("job_id", "image_number", name="uq_analysis_job_image_number"),
    )
    op.create_index("ix_analysis_job_images_job_id", "analysis_job_images", ["job_id"])
    op.create_index("ix_analysis_job_images_source_asset_id", "analysis_job_images", ["source_asset_id"])
    op.create_table("product_analysis_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_number", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("product_type", sa.String(160), nullable=False),
        sa.Column("colours", sa.String(300), nullable=False),
        sa.Column("materials", sa.String(300), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(320), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confirmation_status", sa.String(20), nullable=False, server_default="suggested"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("job_id", "product_number", name="uq_analysis_job_product_number"),
    )
    op.create_index("ix_product_analysis_records_job_id", "product_analysis_records", ["job_id"])


def downgrade() -> None:
    op.drop_table("product_analysis_records")
    op.drop_table("analysis_job_images")
    op.drop_table("analysis_jobs")
