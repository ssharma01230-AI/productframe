"""Small persistence helpers for the first single-generation workflow."""
from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .category_registry import get_tops_family_for_subtype
from .generation_templates import validate_generation_template
from .output_readiness import evaluate_template
from .models import (
    GeneratedAsset,
    GeneratedAssetStatus,
    GenerationJob,
    GenerationJobStatus,
    GenerationRun,
    GenerationRunStatus,
    Product,
    SourceAsset,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def planned_image_provider(*, total_jobs: int, job_index: int) -> str:
    """Use GPT for small runs; split large runs deterministically across providers."""
    if total_jobs >= 10:
        return "openai" if job_index % 2 == 0 else "gemini"
    return "openai"


def image_provider_model(provider: str) -> str:
    if provider == "gemini":
        return os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-lite-image")
    return os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare")


def recalculate_generation_run(db: Session, run_id: str) -> GenerationRun:
    """Derive run counters/status from child jobs, idempotently."""
    run = db.scalar(select(GenerationRun).where(GenerationRun.id == run_id).with_for_update())
    if run is None:
        raise ValueError("Generation run not found")
    jobs = db.scalars(select(GenerationJob).where(GenerationJob.generation_run_id == run.id)).all()
    completed = sum(job.status == GenerationJobStatus.COMPLETED.value for job in jobs)
    failed = sum(job.status == GenerationJobStatus.FAILED.value for job in jobs)
    cancelled = sum(job.status == GenerationJobStatus.CANCELLED.value for job in jobs)
    active = len(jobs) - completed - failed - cancelled
    run.completed_jobs = completed
    run.failed_jobs = failed
    if jobs and active == 0:
        if completed == len(jobs):
            run.status = GenerationRunStatus.COMPLETED.value
        elif failed == len(jobs):
            run.status = GenerationRunStatus.FAILED.value
        elif completed and failed:
            run.status = GenerationRunStatus.PARTIALLY_FAILED.value
        elif cancelled == len(jobs):
            run.status = GenerationRunStatus.CANCELLED.value
        else:
            run.status = GenerationRunStatus.RUNNING.value
        run.completed_at = _now()
    elif any(job.status in {GenerationJobStatus.GENERATING.value, GenerationJobStatus.VALIDATING.value} for job in jobs):
        run.status = GenerationRunStatus.RUNNING.value
        run.completed_at = None
    elif completed or failed or cancelled:
        run.status = GenerationRunStatus.RUNNING.value
        run.completed_at = None
    else:
        run.status = GenerationRunStatus.PENDING.value
        run.completed_at = None
    return run


def create_generation_run(
    db: Session,
    *,
    workspace_id: str,
    selections: list[dict[str, object]],
    idempotency_key: str | None = None,
    enforce_evidence: bool = False,
) -> tuple[GenerationRun, list[GenerationJob]]:
    """Create one run and all child jobs atomically after full validation."""
    if not selections:
        raise ValueError("At least one generation selection is required")
    unique_selections: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for selection in selections:
        key = (selection["product_id"], selection["template_id"], selection.get("channel", "ecommerce"))
        if key not in seen:
            seen.add(key)
            unique_selections.append(selection)

    if idempotency_key:
        existing = db.scalar(select(GenerationRun).where(
            GenerationRun.workspace_id == workspace_id,
            GenerationRun.idempotency_key == idempotency_key,
        ))
        if existing is not None:
            jobs = db.scalars(select(GenerationJob).where(GenerationJob.generation_run_id == existing.id).order_by(GenerationJob.job_index, GenerationJob.created_at, GenerationJob.id)).all()
            if not jobs:
                raise ValueError("Idempotent generation run has no jobs")
            return existing, jobs

    validated: list[tuple[Product, object, list[str], bool]] = []
    for selection in unique_selections:
        product = db.scalar(select(Product).where(Product.id == selection["product_id"], Product.workspace_id == workspace_id))
        if product is None:
            raise ValueError("Product not found in this workspace")
        if not product.category:
            raise ValueError("Product has no category")
        assets = db.scalars(select(SourceAsset).where(SourceAsset.product_id == product.id)).all()
        channel = selection.get("channel", "ecommerce")
        category_details = product.category_details if isinstance(product.category_details, dict) else {}
        family = category_details.get("family")
        if not family and product.category == "tops":
            family = get_tops_family_for_subtype(category_details.get("subtype") or product.product_type)
            if family:
                category_details = {**category_details, "family": family}
                product.category_details = category_details
        template = validate_generation_template(
            selection["template_id"], category=product.category, channel=channel,
            subtype=category_details.get("subtype"),
            product_family=family,
        )
        readiness = evaluate_template(template, [asset.media_evidence for asset in assets])
        missing_evidence = [str(item) for item in readiness["missing_evidence"]]
        evidence_override = bool(selection.get("evidence_override", False))
        if enforce_evidence:
            if not assets:
                raise ValueError("Product has no source assets")
            if missing_evidence and not evidence_override:
                raise ValueError("Missing source evidence: " + ", ".join(missing_evidence))
        validated.append((product, template, missing_evidence, evidence_override))

    run = GenerationRun(workspace_id=workspace_id, status=GenerationRunStatus.PENDING.value, idempotency_key=idempotency_key, total_jobs=len(validated))
    db.add(run)
    db.flush()
    jobs: list[GenerationJob] = []
    for job_index, (product, template, missing_evidence, evidence_override) in enumerate(validated):
        job_id = str(uuid4())
        provider = planned_image_provider(total_jobs=len(validated), job_index=job_index)
        job = GenerationJob(
            id=job_id, graph_thread_id=f"generation-job-{job_id}", generation_run_id=run.id,
            workspace_id=workspace_id, job_index=job_index, product_id=product.id, template_id=template.id,
            presentation=unique_selections[job_index].get("presentation"), template_version=template.version, provider=provider, provider_model=image_provider_model(provider), evidence_override=evidence_override, missing_evidence=missing_evidence,
        )
        db.add(job)
        jobs.append(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if not idempotency_key:
            raise
        existing = db.scalar(select(GenerationRun).where(
            GenerationRun.workspace_id == workspace_id,
            GenerationRun.idempotency_key == idempotency_key,
        ))
        if existing is None:
            raise
        jobs = db.scalars(select(GenerationJob).where(GenerationJob.generation_run_id == existing.id).order_by(GenerationJob.job_index, GenerationJob.created_at, GenerationJob.id)).all()
        if not jobs:
            raise ValueError("Idempotent generation run has no jobs")
        return existing, jobs
    db.refresh(run)
    for job in jobs:
        db.refresh(job)
    return run, jobs


def create_single_generation_run(
    db: Session,
    *,
    workspace_id: str,
    product_id: str,
    template_id: str,
    channel: str = "ecommerce",
    idempotency_key: str | None = None,
    enforce_evidence: bool = False,
) -> tuple[GenerationRun, GenerationJob]:
    """Backward-compatible single-selection wrapper."""
    run, jobs = create_generation_run(
        db, workspace_id=workspace_id,
        selections=[{"product_id": product_id, "template_id": template_id, "channel": channel}],
        idempotency_key=idempotency_key, enforce_evidence=enforce_evidence,
    )
    return run, jobs[0]
    if idempotency_key:
        existing = db.scalar(select(GenerationRun).where(
            GenerationRun.workspace_id == workspace_id,
            GenerationRun.idempotency_key == idempotency_key,
        ))
        if existing is not None:
            job = db.scalar(select(GenerationJob).where(GenerationJob.generation_run_id == existing.id).order_by(GenerationJob.created_at, GenerationJob.id))
            if job is None:
                raise ValueError("Idempotent generation run has no job")
            return existing, job
    product = db.scalar(select(Product).where(Product.id == product_id, Product.workspace_id == workspace_id))
    if product is None:
        raise ValueError("Product not found in this workspace")
    if not product.category:
        raise ValueError("Product has no category")
    assets = db.scalars(select(SourceAsset).where(SourceAsset.product_id == product.id)).all()
    category_details = product.category_details if isinstance(product.category_details, dict) else {}
    template = validate_generation_template(
        template_id,
        category=product.category,
        channel=channel,
        subtype=category_details.get("subtype"),
        product_family=category_details.get("family"),
    )
    if enforce_evidence:
        if not assets:
            raise ValueError("Product has no source assets")
        readiness = evaluate_template(template, [asset.media_evidence for asset in assets])
        if readiness["missing_evidence"]:
            raise ValueError("Missing source evidence: " + ", ".join(readiness["missing_evidence"]))

    run = GenerationRun(workspace_id=workspace_id, status=GenerationRunStatus.PENDING.value, idempotency_key=idempotency_key, total_jobs=1)
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
        presentation=None,
        template_version=template.version,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if not idempotency_key:
            raise
        existing = db.scalar(select(GenerationRun).where(
            GenerationRun.workspace_id == workspace_id,
            GenerationRun.idempotency_key == idempotency_key,
        ))
        if existing is None:
            raise
        job = db.scalar(select(GenerationJob).where(GenerationJob.generation_run_id == existing.id).order_by(GenerationJob.created_at, GenerationJob.id))
        if job is None:
            raise ValueError("Idempotent generation run has no job")
        return existing, job
    db.refresh(run)
    db.refresh(job)
    return run, job


def mark_generation_job_generating(db: Session, job_id: str) -> GenerationJob:
    job, _ = claim_generation_job(db, job_id)
    return job


def claim_generation_job(db: Session, job_id: str) -> tuple[GenerationJob, bool]:
    """Atomically claim a pending generation job for one worker attempt.

    Redis stream delivery is at-least-once. Duplicate or recovered messages must
    therefore be harmless: only the worker that changes ``pending`` to
    ``generating`` may call the image provider.
    """
    job = db.scalar(
        select(GenerationJob)
        .where(GenerationJob.id == job_id)
        .with_for_update()
    )
    if job is None:
        raise ValueError("Generation job not found")
    if job.generated_asset is not None or job.status != GenerationJobStatus.PENDING.value:
        return job, False
    now = _now()
    if job.next_attempt_at is not None:
        next_attempt = job.next_attempt_at
        if next_attempt.tzinfo is None:
            next_attempt = next_attempt.replace(tzinfo=timezone.utc)
        if next_attempt > now:
            return job, False
    job.status = GenerationJobStatus.GENERATING.value
    job.attempt_count += 1
    job.started_at = now
    job.next_attempt_at = None
    job.error_message = None
    job.run.status = GenerationRunStatus.RUNNING.value
    job.run.started_at = job.run.started_at or now
    db.commit()
    db.refresh(job)
    return job, True


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
    recalculate_generation_run(db, job.run.id)
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
    recalculate_generation_run(db, job.run.id)
    db.commit()
    return job


def mark_generation_job_failed(db: Session, *, job_id: str, error_message: str) -> GenerationJob:
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise ValueError("Generation job not found")
    if job.status == GenerationJobStatus.FAILED.value:
        return job
    job.status = GenerationJobStatus.FAILED.value
    job.error_message = error_message[:1000]
    recalculate_generation_run(db, job.run.id)
    db.commit()
    db.refresh(job)
    return job
