from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_

import boto3
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from productframe_api.config import get_settings
from productframe_api.db import SessionLocal
from productframe_api.description_utils import concise_product_description
from productframe_api.generation_persistence import mark_generation_job_failed, reschedule_generation_job
from productframe_api.image_recognition import analyze_product_images
from productframe_api.models import AnalysisJob, AnalysisJobImage, AnalysisImageStatus, AnalysisJobStatus, GenerationJob, ProductAnalysisRecord, SourceAsset

from .generation_graph import run_persisted_generation
from .generation_storage import MinioGeneratedImageStorage
from .fidelity_validator import OpenAIProductFidelityValidator
from .openai_image_provider import OpenAIImageGenerationProvider

QUEUE = "productframe:analysis"
GENERATION_QUEUE = "productframe:generation"
CONSUMER_GROUP = "productframe-workers"
MAX_GENERATION_ATTEMPTS = 3
_RECOVERY_DONE = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def process_job(job_id: str, db: Session | None = None) -> None:
    own_session = db is None
    db = db or SessionLocal()
    settings = get_settings()
    try:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            return
        job.status = AnalysisJobStatus.SCREENING.value
        job.started_at = _now()
        db.commit()
        job_images = db.scalars(select(AnalysisJobImage).where(AnalysisJobImage.job_id == job.id).order_by(AnalysisJobImage.image_number)).all()
        s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
        image_bytes: list[bytes] = []
        submitted_image_numbers: dict[int, int] = {}
        for item in job_images:
            asset = db.get(SourceAsset, item.source_asset_id) if item.source_asset_id else None
            if asset is None:
                item.status = AnalysisImageStatus.REJECTED.value
                item.passed = False
                item.rejection_reason = "Source image record was not found."
                continue
            image_bytes.append(s3.get_object(Bucket=settings.minio_bucket, Key=asset.object_key)["Body"].read())
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
        result = analyze_product_images(image_bytes, progress_callback=report_progress)
        job.status = AnalysisJobStatus.ANALYSING.value
        job.progress_stage = "complete"
        job.progress_message = "Analysis complete — ready for review"
        job.progress_completed = job.total_images
        job.progress_total = job.total_images
        job.progress_percent = 100
        job.processed_images = job.total_images
        job.unique_product_count = result.unique_product_count
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
                description=concise_product_description(analysis),
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
        provider = OpenAIImageGenerationProvider()
        fidelity_validator = OpenAIProductFidelityValidator()
        try:
            if approved is None:
                run_persisted_generation(
                    db,
                    job_id,
                    provider=provider,
                    storage=MinioGeneratedImageStorage(),
                    fidelity_validator=fidelity_validator,
                )
            else:
                from .generation_graph import resume_persisted_generation
                # Resume compiles against the durable PostgreSQL checkpoint and
                # therefore works after a worker restart.
                resume_persisted_generation(db, job_id, approved=approved, provider=provider, storage=MinioGeneratedImageStorage())
        finally:
            provider.close()
            fidelity_validator.close()
    except Exception as exc:
        job = db.get(GenerationJob, job_id)
        retryable = not isinstance(exc, ValueError) and job is not None and job.attempt_count < MAX_GENERATION_ATTEMPTS
        if retryable:
            reschedule_generation_job(db, job_id, str(exc))
        raise
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
    with SessionLocal() as db:
        jobs = db.scalars(select(GenerationJob).where(GenerationJob.status.in_(["pending", "generating", "validating"]))).all()
        for job in jobs:
            redis.xadd(GENERATION_QUEUE, {"type": "generate", "job_id": job.id}, maxlen=10000, approximate=True)
    _RECOVERY_DONE = True


def run_once() -> bool:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    _ensure_groups(redis)
    _recover_jobs(redis)
    consumer = f"worker-{__import__('os').getpid()}"
    messages = redis.xreadgroup(CONSUMER_GROUP, consumer, {GENERATION_QUEUE: ">", QUEUE: ">"}, count=1, block=100)
    if not messages:
        redis.close()
        return False
    stream, entries = messages[0]
    message_id, fields = entries[0]
    try:
        if stream == GENERATION_QUEUE:
            process_generation_job(fields["job_id"], approved=(fields.get("approved") == "1") if fields.get("type") == "review" else None)
        else:
            process_job(fields["job_id"])
        redis.xack(stream, CONSUMER_GROUP, message_id)
    finally:
        redis.close()
    return True
