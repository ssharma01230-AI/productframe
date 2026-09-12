from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import logging
import os
import time
from typing import Any

import boto3
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from productframe_api.analysis_cache import ANALYSIS_PROMPT_VERSION, ANALYSIS_SCHEMA_VERSION, load_cached_stages, normalized_image_hash, save_cached_stage
from productframe_api.config import get_settings
from productframe_api.db import SessionLocal
from productframe_api.description_utils import bound_description, concise_product_description
from productframe_api.generation_persistence import (
    image_provider_model,
    planned_image_provider,
    recalculate_generation_run,
    reschedule_generation_job,
)
from productframe_api.image_recognition import analyze_media_evidence, analyze_product_images
from productframe_api.image_processing import normalize_image_orientation
from productframe_api.models import AnalysisJob, AnalysisJobImage, AnalysisImageStatus, AnalysisJobStatus, GenerationJob, ProductAnalysisRecord, SourceAsset

from .generation_graph import run_persisted_generation
from .generation_storage import MinioGeneratedImageStorage
from .fidelity_validator import OpenAIProductFidelityValidator
from .gemini_image_provider import GeminiImageGenerationProvider
from .openai_image_provider import OpenAIImageGenerationError, OpenAIImageGenerationProvider

QUEUE = "productframe:analysis"
GENERATION_QUEUE = "productframe:generation"
CONSUMER_GROUP = "productframe-workers"
MAX_GENERATION_ATTEMPTS = 3
GENERATION_RECOVERY_LEASE_SECONDS = 600
_RECOVERY_DONE = False
logger = logging.getLogger(__name__)


def _image_generation_provider(provider: str) -> Any:
    """Build the selected provider without exposing credentials to callers."""
    if provider == "openai":
        return OpenAIImageGenerationProvider()
    if provider == "gemini":
        return GeminiImageGenerationProvider()
    raise ValueError("Image generation provider must be 'openai' or 'gemini'")


def _ensure_job_provider(job: GenerationJob, db: Session) -> str:
    provider = (job.provider or planned_image_provider(
        total_jobs=job.run.total_jobs, job_index=job.job_index
    )).strip().lower()
    if provider not in {"openai", "gemini"}:
        provider = "openai"
    if job.provider != provider or not job.provider_model:
        job.provider = provider
        job.provider_model = image_provider_model(provider)
        db.commit()
    return provider


def _fallback_provider(provider: str) -> str:
    return "gemini" if provider == "openai" else "openai"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_upright_source_image(s3: Any, bucket: str, asset: SourceAsset) -> bytes:
    """Return display-oriented pixels and persist them for recognition previews."""
    stored = s3.get_object(Bucket=bucket, Key=asset.object_key)
    body = stored["Body"]
    try:
        source = body.read()
    finally:
        body.close()
    # Real uploaded assets always have an image content type. Keeping the
    # fallback makes the analysis worker's small test doubles and malformed
    # upload handling behave as before.
    if not getattr(asset, "content_type", "").startswith("image/"):
        return source
    normalized = normalize_image_orientation(source)
    s3.put_object(
        Bucket=bucket,
        Key=asset.object_key,
        Body=normalized.content,
        ContentType=normalized.content_type,
    )
    asset.content_type = normalized.content_type
    return normalized.content


def _prepare_analysis_asset(asset: SourceAsset, settings: Any) -> tuple[bytes, str]:
    """Download and normalize one asset without touching the coordinator session."""
    from types import SimpleNamespace

    s3 = boto3.client(
        "s3", endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1",
    )
    detached_asset = SimpleNamespace(object_key=asset.object_key, content_type=getattr(asset, "content_type", ""))
    content = _read_upright_source_image(s3, settings.minio_bucket, detached_asset)
    return content, detached_asset.content_type


def process_media_evidence(asset_id: str, db: Session | None = None) -> None:
    own_session = db is None
    db = db or SessionLocal()
    settings = get_settings()
    try:
        asset = db.get(SourceAsset, asset_id)
        if asset is None:
            return
        s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
        content = _read_upright_source_image(s3, settings.minio_bucket, asset)
        asset.media_evidence = analyze_media_evidence(content)
        db.commit()
    finally:
        if own_session:
            db.close()


def process_job(job_id: str, db: Session | None = None) -> None:
    own_session = db is None
    db = db or SessionLocal()
    settings = get_settings()
    try:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            return
        # A restarted worker can encounter the original stream entry after
        # an operator or retry has requeued the same analysis. Do not repeat
        # expensive provider calls or insert duplicate product records.
        if job.status in {AnalysisJobStatus.AWAITING_CONFIRMATION.value, AnalysisJobStatus.COMPLETED.value}:
            return
        existing_records = db.scalars(select(ProductAnalysisRecord).where(ProductAnalysisRecord.job_id == job.id)).all()
        if existing_records:
            job.status = AnalysisJobStatus.AWAITING_CONFIRMATION.value
            job.error_message = None
            job.completed_at = job.completed_at or _now()
            db.commit()
            return
        job.status = AnalysisJobStatus.SCREENING.value
        job.started_at = _now()
        db.commit()
        job_images = db.scalars(select(AnalysisJobImage).where(AnalysisJobImage.job_id == job.id).order_by(AnalysisJobImage.image_number)).all()
        assets_to_prepare: list[tuple[AnalysisJobImage, SourceAsset]] = []
        for item in job_images:
            asset = db.get(SourceAsset, item.source_asset_id) if item.source_asset_id else None
            if asset is None:
                item.status = AnalysisImageStatus.REJECTED.value
                item.passed = False
                item.rejection_reason = "Source image record was not found."
                continue
            assets_to_prepare.append((item, asset))
        # MinIO I/O and image normalization are independent. Keep ORM writes on
        # the coordinator thread because SQLAlchemy sessions are not thread-safe.
        with ThreadPoolExecutor(max_workers=min(4, max(1, len(assets_to_prepare))), thread_name_prefix="asset-preparation") as executor:
            prepared = list(executor.map(lambda pair: _prepare_analysis_asset(pair[1], settings), assets_to_prepare))
        image_bytes: list[bytes] = []
        image_hashes: dict[int, str] = {}
        cached_stage_results: dict[str, dict[str, object]] = {}
        submitted_image_numbers: dict[int, int] = {}
        for (item, asset), (content, normalized_content_type) in zip(assets_to_prepare, prepared):
            asset.content_type = normalized_content_type
            image_bytes.append(content)
            image_hashes[item.image_number] = normalized_image_hash(content)
            cached_stage_results[str(item.image_number)] = dict(getattr(item, "stage_results", None) or {})
            cached_stage_results[str(item.image_number)].update(load_cached_stages(
                db, image_hash=image_hashes[item.image_number],
                model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                prompt_version=ANALYSIS_PROMPT_VERSION, schema_version=ANALYSIS_SCHEMA_VERSION,
            ))
            # The analyzer numbers its supplied images from one. Missing sources
            # must not shift those results onto different original uploads.
            submitted_image_numbers[len(image_bytes)] = item.image_number
        db.commit()
        def report_progress(stage: str, message: str, completed: int, total: int, percent: int) -> None:
            job.status = AnalysisJobStatus.SCREENING.value if stage in {"validation", "screening"} else AnalysisJobStatus.ANALYSING.value
            job.progress_stage = stage
            job.progress_message = message
            job.progress_completed = completed
            job.progress_total = total
            job.progress_percent = percent
            db.commit()

        job.status = AnalysisJobStatus.SCREENING.value
        job.progress_stage = "validation"
        job.progress_message = "Checking uploaded images"
        job.progress_total = job.total_images
        db.commit()
        cached_stage_state = dict(getattr(job, "stage_state", None) or {})

        def checkpoint_stage(image_number: str, stages: dict[str, object]) -> None:
            # The analysis coordinator owns the main session; this checkpoint
            # uses a short independent session so completed work survives an
            # interruption before the final product transaction.
            with SessionLocal() as checkpoint_db:
                checkpoint = checkpoint_db.scalar(select(AnalysisJobImage).where(
                    AnalysisJobImage.job_id == job.id,
                    AnalysisJobImage.image_number == int(image_number),
                ))
                if checkpoint is not None:
                    checkpoint.stage_results = stages
                    checkpoint.image_hash = image_hashes.get(int(image_number))
                    checkpoint_db.commit()

        def checkpoint_job_stage(stage: str, value: dict[str, object]) -> None:
            with SessionLocal() as checkpoint_db:
                checkpoint_job = checkpoint_db.get(AnalysisJob, job.id)
                if checkpoint_job is None:
                    return
                state = dict(checkpoint_job.stage_state or {})
                if stage == "grouping":
                    state["grouping"] = value
                elif stage.startswith("synthesis:"):
                    synthesis = dict(state.get("synthesis") or {})
                    synthesis[stage.split(":", 1)[1]] = value
                    state["synthesis"] = synthesis
                checkpoint_job.stage_state = state
                checkpoint_db.commit()

        result = analyze_product_images(
            image_bytes, progress_callback=report_progress,
            cached_stage_results=cached_stage_results,
            stage_result_callback=checkpoint_stage,
            cached_stage_state=cached_stage_state,
            stage_state_callback=checkpoint_job_stage,
        )
        job.status = AnalysisJobStatus.ANALYSING.value
        job.progress_stage = "complete"
        job.progress_message = "Analysis complete — ready for review"
        job.progress_completed = job.total_images
        job.progress_total = job.total_images
        job.progress_percent = 100
        job.processed_images = job.total_images
        job.unique_product_count = result.unique_product_count
        cache_model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        for image_number, stages in getattr(result, "stage_results", {}).items():
            image_hash = image_hashes.get(int(image_number))
            if not image_hash:
                continue
            for stage, stage_result in stages.items():
                save_cached_stage(
                    db, image_hash=image_hash, model=cache_model, stage=stage,
                    result=stage_result, prompt_version=ANALYSIS_PROMPT_VERSION,
                    schema_version=ANALYSIS_SCHEMA_VERSION,
                )
        for supplied_number, evidence in getattr(result, "image_evidence", {}).items():
            image_number = submitted_image_numbers.get(int(supplied_number))
            if image_number is None:
                continue
            item = db.scalar(select(AnalysisJobImage).where(AnalysisJobImage.job_id == job.id, AnalysisJobImage.image_number == image_number))
            if item and item.source_asset_id:
                asset = db.get(SourceAsset, item.source_asset_id)
                if asset:
                    asset.media_evidence = evidence
        for rejected in result.rejected_images:
            image_number = submitted_image_numbers.get(rejected.image_number)
            if image_number is None:
                continue
            item = db.scalar(select(AnalysisJobImage).where(AnalysisJobImage.job_id == job.id, AnalysisJobImage.image_number == image_number))
            if item:
                item.status = AnalysisImageStatus.REJECTED.value
                item.passed = False
                item.rejection_reason = rejected.reason
        for product in result.products:
            for number in product.image_numbers:
                image_number = submitted_image_numbers.get(number)
                if image_number is None:
                    continue
                item = db.scalar(select(AnalysisJobImage).where(AnalysisJobImage.job_id == job.id, AnalysisJobImage.image_number == image_number))
                if item:
                    item.status = AnalysisImageStatus.ANALYSED.value
                    item.passed = True
                    item.product_number = product.product_number
            analysis = product.analysis
            db.add(ProductAnalysisRecord(
                job_id=job.id,
                product_number=product.product_number,
                product_name=analysis.product_name,
                category=analysis.category.value,
                product_type=analysis.product_type,
                colours=analysis.colours,
                materials=analysis.materials,
                features=analysis.features,
                global_details=(getattr(analysis, "global_details", None).model_dump(mode="json") if getattr(analysis, "global_details", None) else None),
                category_details=(getattr(analysis, "category_details", None).model_dump(mode="json") if hasattr(getattr(analysis, "category_details", None), "model_dump") else getattr(analysis, "category_details", None)),
                confidence_details=(getattr(analysis, "confidence_details", None).model_dump(mode="json") if getattr(analysis, "confidence_details", None) else None),
                description=bound_description(concise_product_description(analysis)),
                confidence=analysis.confidence,
            ))
        job.status = AnalysisJobStatus.AWAITING_CONFIRMATION.value if result.products else AnalysisJobStatus.FAILED.value
        job.error_message = result.reason if not result.products else None
        job.completed_at = _now()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(AnalysisJob, job_id)
        if job:
            job.status = AnalysisJobStatus.FAILED.value
            job.error_message = str(exc)[:1000]
            job.completed_at = _now()
            db.commit()
        raise
    finally:
        if own_session:
            db.close()


def process_generation_job(job_id: str, *, approved: bool | None = None, db: Session | None = None) -> None:
    own_session = db is None
    db = db or SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            raise ValueError("Generation job not found")

        if approved is not None:
            # Review messages are also at-least-once. A duplicate review after
            # completion/cancellation is a harmless no-op. A validating job is
            # resumable if the worker stopped after the approval was recorded.
            if job.status in {"completed", "cancelled"}:
                return
            if job.status not in {"awaiting_review", "validating"}:
                return
            from .generation_graph import resume_persisted_generation
            # Resume compiles against the durable PostgreSQL checkpoint and
            # therefore works after a worker restart. The resume path reads the
            # reviewed preview from MinIO and does not need another provider.
            resume_persisted_generation(db, job_id, approved=approved, storage=MinioGeneratedImageStorage())
            return

        # The graph performs the database-locked claim. This early check avoids
        # constructing SDK clients for duplicate messages that arrive while the
        # first worker is still waiting on the image provider.
        if job.status != "pending":
            return

        provider_name = _ensure_job_provider(job, db)
        while True:
            try:
                provider = _image_generation_provider(provider_name)
                fidelity_validator = None
                try:
                    if _env_flag("OPENAI_IMAGE_FIDELITY_VALIDATION"):
                        fidelity_validator = OpenAIProductFidelityValidator()
                    run_persisted_generation(
                        db,
                        job_id,
                        provider=provider,
                        storage=MinioGeneratedImageStorage(),
                        fidelity_validator=fidelity_validator,
                    )
                finally:
                    provider.close()
                    if fidelity_validator is not None:
                        fidelity_validator.close()
                return
            except Exception as exc:
                job = db.get(GenerationJob, job_id)
                request_id = getattr(exc, "request_id", None)
                if job is not None and request_id:
                    job.provider_request_id = request_id
                    db.commit()
                retryable = (
                    job is not None
                    and job.attempt_count < MAX_GENERATION_ATTEMPTS
                    and not isinstance(exc, ValueError)
                    and getattr(exc, "retryable", True)
                )
                if not retryable:
                    raise
                if job is not None and getattr(exc, "retryable", False) and job.provider_fallback_count == 0:
                    provider_name = _fallback_provider(provider_name)
                    job.provider = provider_name
                    job.provider_model = image_provider_model(provider_name)
                    job.provider_fallback_count += 1
                    db.commit()
                    logger.warning(
                        "Provider-side generation failure; failing over job_id=%s to provider=%s",
                        job_id, provider_name,
                    )
                retry = reschedule_generation_job(db, job_id, str(exc))
                delay = 0.0
                if retry.next_attempt_at is not None:
                    next_attempt = retry.next_attempt_at
                    if next_attempt.tzinfo is None:
                        next_attempt = next_attempt.replace(tzinfo=timezone.utc)
                    delay = max(0.0, (next_attempt - _now()).total_seconds())
                logger.warning(
                    "Generation attempt failed job_id=%s attempt=%s/%s error_type=%s; retrying in %.1fs",
                    job_id, retry.attempt_count, MAX_GENERATION_ATTEMPTS, type(exc).__name__, delay,
                )
                if delay:
                    time.sleep(delay)
    finally:
        if own_session:
            db.close()


def _ensure_groups(redis: Redis) -> None:
    for stream in (QUEUE, GENERATION_QUEUE):
        try:
            redis.xgroup_create(stream, CONSUMER_GROUP, id="0-0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise


def _recover_jobs(redis: Redis) -> None:
    global _RECOVERY_DONE
    if _RECOVERY_DONE:
        return
    lease_seconds = _positive_int_env("GENERATION_RECOVERY_LEASE_SECONDS", GENERATION_RECOVERY_LEASE_SECONDS)
    cutoff = _now() - timedelta(seconds=lease_seconds)
    with SessionLocal() as db:
        # Redis retains the original stream message. Only reset jobs that have
        # been generating longer than the provider lease; blindly adding every
        # pending/generating job here creates duplicate provider requests on
        # every worker restart.
        jobs = db.scalars(select(GenerationJob).where(
            GenerationJob.status == "generating",
            GenerationJob.started_at.is_not(None),
            GenerationJob.started_at < cutoff,
        )).all()
        recovered_runs: set[str] = set()
        for job in jobs:
            job.status = "pending"
            job.next_attempt_at = None
            job.error_message = "Recovered after a worker interruption; retrying generation."
            recovered_runs.add(job.generation_run_id)
        for run_id in recovered_runs:
            recalculate_generation_run(db, run_id)
        pending_jobs = db.scalars(select(GenerationJob).where(GenerationJob.status == "pending")).all()
        for job in pending_jobs:
            redis.xadd(GENERATION_QUEUE, {"type": "generate", "job_id": job.id}, maxlen=10000, approximate=True)
        if jobs or pending_jobs:
            db.commit()
            if jobs:
                logger.warning("Recovered %d stale generation job(s) after a %ss lease.", len(jobs), lease_seconds)
            if pending_jobs:
                logger.info("Requeued %d pending generation job(s) during worker recovery.", len(pending_jobs))
    _RECOVERY_DONE = True


def _positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _claim_stale_message(redis: Redis, stream: str, consumer: str) -> tuple[str, list[tuple[str, dict[str, str]]]] | None:
    """Claim one message abandoned by a worker that has gone away."""
    idle_ms = _positive_int_env("GENERATION_RECOVERY_LEASE_SECONDS", GENERATION_RECOVERY_LEASE_SECONDS) * 1000
    try:
        result = redis.xautoclaim(
            stream,
            CONSUMER_GROUP,
            consumer,
            min_idle_time=idle_ms,
            start_id="0-0",
            count=1,
        )
    except Exception as exc:
        logger.warning("Could not reclaim stale %s message (%s).", stream, type(exc).__name__)
        return None
    entries = result[1] if len(result) > 1 else []
    if entries:
        return stream, entries
    return None


def _next_message(redis: Redis, consumer: str) -> tuple[str, tuple[str, dict[str, str]]] | None:
    for stream in (GENERATION_QUEUE, QUEUE):
        reclaimed = _claim_stale_message(redis, stream, consumer)
        if reclaimed is not None:
            return reclaimed[0], reclaimed[1][0]
    messages = redis.xreadgroup(CONSUMER_GROUP, consumer, {GENERATION_QUEUE: ">", QUEUE: ">"}, count=1, block=100)
    if not messages:
        return None
    stream, entries = messages[0]
    return stream, entries[0]


def run_once() -> bool:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    _ensure_groups(redis)
    _recover_jobs(redis)
    consumer = f"worker-{__import__('os').getpid()}"
    message = _next_message(redis, consumer)
    if message is None:
        redis.close()
        return False
    stream, (message_id, fields) = message
    try:
        if stream == GENERATION_QUEUE:
            process_generation_job(fields["job_id"], approved=(fields.get("approved") == "1") if fields.get("type") == "review" else None)
        elif fields.get("type") == "evidence":
            process_media_evidence(fields["asset_id"])
        else:
            process_job(fields["job_id"])
    except Exception as exc:
        logger.error(
            "Worker message failed stream=%s type=%s job_id=%s error_type=%s; acknowledging message.",
            stream, fields.get("type"), fields.get("job_id") or fields.get("asset_id") or "unknown", type(exc).__name__,
        )
    finally:
        # A failed message has already been recorded in its database job. Ack
        # it here so a stale stream delivery cannot trigger another provider
        # call; explicit bounded retries are handled above.
        redis.xack(stream, CONSUMER_GROUP, message_id)
        redis.close()
    return True
