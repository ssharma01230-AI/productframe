"""add generation runs, jobs and generated assets

Revision ID: 0008_generation_persistence
Revises: 0007_analysis_progress
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_generation_persistence"
down_revision = "0007_analysis_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generation_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("total_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_generation_runs_workspace_id", "generation_runs", ["workspace_id"])
    op.create_index("ix_generation_runs_status", "generation_runs", ["status"])

    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("generation_run_id", sa.String(length=36), sa.ForeignKey("generation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", sa.String(length=160), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("aspect_ratio", sa.String(length=20), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("generation_run_id", "product_id", "template_id", name="uq_generation_job_selection"),
    )
    for index, column in (("generation_run_id", "generation_run_id"), ("workspace_id", "workspace_id"), ("product_id", "product_id"), ("status", "status")):
        op.create_index(f"ix_generation_jobs_{index}", "generation_jobs", [column])

    op.create_table(
        "generated_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation_run_id", sa.String(length=36), sa.ForeignKey("generation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation_job_id", sa.String(length=36), sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", sa.String(length=160), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False, unique=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ready"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("generation_job_id", name="uq_generated_asset_job"),
    )
    for index, column in (("workspace_id", "workspace_id"), ("product_id", "product_id"), ("generation_run_id", "generation_run_id"), ("generation_job_id", "generation_job_id"), ("status", "status")):
        op.create_index(f"ix_generated_assets_{index}", "generated_assets", [column])


def downgrade() -> None:
    op.drop_table("generated_assets")
    op.drop_table("generation_jobs")
    op.drop_table("generation_runs")
