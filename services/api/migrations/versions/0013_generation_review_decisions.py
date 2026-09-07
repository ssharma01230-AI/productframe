"""persist generation review decisions

Revision ID: 0013_generation_review_decisions
Revises: 0012_generation_run_idempotency
"""
from alembic import op
import sqlalchemy as sa


revision = "0013_generation_review_decisions"
down_revision = "0012_generation_run_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generation_jobs", sa.Column("review_decision", sa.String(length=20), nullable=True))
    op.add_column("generation_jobs", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("generation_jobs", sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_generation_jobs_reviewed_by_user_id_users",
        "generation_jobs",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_generation_jobs_review_decision", "generation_jobs", ["review_decision"])
    op.create_index("ix_generation_jobs_reviewed_by_user_id", "generation_jobs", ["reviewed_by_user_id"])
    # Preserve review outcomes created by the interrupt-based workflow. Older
    # approvals are recorded on the asset, while a rejection ended the job
    # without creating a final asset.
    op.execute(sa.text("""
        UPDATE generation_jobs AS job
        SET review_decision = asset.status,
            reviewed_at = COALESCE(job.completed_at, CURRENT_TIMESTAMP)
        FROM generated_assets AS asset
        WHERE asset.generation_job_id = job.id
          AND job.review_decision IS NULL
          AND asset.status IN ('approved', 'rejected')
    """))
    op.execute(sa.text("""
        UPDATE generation_jobs
        SET review_decision = 'rejected',
            reviewed_at = COALESCE(completed_at, CURRENT_TIMESTAMP)
        WHERE review_decision IS NULL
          AND status = 'cancelled'
          AND preview_object_key IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_reviewed_by_user_id", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_review_decision", table_name="generation_jobs")
    op.drop_constraint("fk_generation_jobs_reviewed_by_user_id_users", "generation_jobs", type_="foreignkey")
    op.drop_column("generation_jobs", "reviewed_by_user_id")
    op.drop_column("generation_jobs", "reviewed_at")
    op.drop_column("generation_jobs", "review_decision")
