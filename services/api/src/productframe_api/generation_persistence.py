"""Small persistence helpers for the first single-generation workflow."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .generation_templates import validate_generation_template
from .models import (
    GeneratedAsset,
    GeneratedAssetStatus,
    GenerationJob,
    GenerationJobStatus,
    GenerationRun,
    GenerationRunStatus,
    Product,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_single_generation_run(
    db: Session,
    *,
    workspace_id: str,
    product_id: str,
    template_id: str,
    channel: str = "ecommerce",
) -> tuple[GenerationRun, GenerationJob]:
    """Create one run and one job after checking product/template compatibility."""
    product = db.scalar(select(Product).where(Product.id == product_id, Product.workspace_id == workspace_id))
    if product is None:
        raise ValueError("Product not found in this workspace")
    if not product.category:
        raise ValueError("Product has no category")
    template = validate_generation_template(template_id, category=product.category, channel=channel)

    run = GenerationRun(workspace_id=workspace_id, status=GenerationRunStatus.PENDING.value, total_jobs=1)
    db.add(run)
    db.flush()
    job_id = str(uuid4())
    job = GenerationJob(
        id=job_id,
        graph_thread_id=f"generation-job-{job_id}",
        generation_run_id=run.id,
        workspace_id=workspace_id,
        product_id=product.id,
        template_id=template.id,
        template_version=template.version,
    )
    db.add(job)
    db.commit()
    db.refresh(run)
    db.refresh(job)
    return run, job


def mark_generation_job_generating(db: Session, job_id: str) -> GenerationJob:
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise ValueError("Generation job not found")
    if job.status == GenerationJobStatus.COMPLETED.value:
        return job
    now = _now()
    job.status = GenerationJobStatus.GENERATING.value
    job.attempt_count += 1
    job.started_at = job.started_at or now
    job.run.status = GenerationRunStatus.RUNNING.value
    job.run.started_at = job.run.started_at or now
    db.commit()
    db.refresh(job)
    return job


def save_generation_result(
    db: Session,
    *,
    job_id: str,
    object_key: str,
    filename: str,
    content_type: str,
) -> GeneratedAsset:
    """Save one output and complete its job, safely supporting retries."""
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise ValueError("Generation job not found")
    existing = db.scalar(select(GeneratedAsset).where(GeneratedAsset.generation_job_id == job.id))
    if existing is not None:
        return existing

    asset = GeneratedAsset(
        workspace_id=job.workspace_id,
        product_id=job.product_id,
        generation_run_id=job.generation_run_id,
        generation_job_id=job.id,
        template_id=job.template_id,
        object_key=object_key,
        filename=filename,
        content_type=content_type,
        status=GeneratedAssetStatus.READY.value,
    )
    db.add(asset)
    job.status = GenerationJobStatus.COMPLETED.value
    job.completed_at = _now()
    job.run.completed_jobs += 1
    if job.run.completed_jobs == job.run.total_jobs:
        job.run.status = GenerationRunStatus.COMPLETED.value
        job.run.completed_at = _now()
    db.commit()
    db.refresh(asset)
    return asset


def reschedule_generation_job(db: Session, job_id: str, error_message: str) -> GenerationJob:
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise ValueError("Generation job not found")
    # The graph may have marked the attempt failed before the worker classifies
    # it. Undo that run-level accounting before putting it back in the queue.
    if job.status == GenerationJobStatus.FAILED.value and job.run.failed_jobs:
        job.run.failed_jobs -= 1
    job.status = GenerationJobStatus.PENDING.value
    job.error_message = error_message[:1000]
    job.next_attempt_at = _now() + timedelta(seconds=min(300, 2 ** max(job.attempt_count - 1, 0)))
    db.commit()
    return job


def mark_generation_job_failed(db: Session, *, job_id: str, error_message: str) -> GenerationJob:
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise ValueError("Generation job not found")
    job.status = GenerationJobStatus.FAILED.value
    job.error_message = error_message[:1000]
    job.run.failed_jobs += 1
    job.run.status = GenerationRunStatus.FAILED.value
    job.run.completed_at = _now()
    db.commit()
    db.refresh(job)
    return job
