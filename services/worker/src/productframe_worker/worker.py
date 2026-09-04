from datetime import datetime, timezone
from typing import Any

import boto3
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from productframe_api.config import get_settings
from productframe_api.db import SessionLocal
from productframe_api.image_recognition import analyze_product_images
from productframe_api.models import AnalysisJob, AnalysisJobImage, AnalysisImageStatus, AnalysisJobStatus, ProductAnalysisRecord, SourceAsset

QUEUE = "productframe:analysis"


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
        for item in job_images:
            asset = db.get(SourceAsset, item.source_asset_id) if item.source_asset_id else None
            if asset is None:
                item.status = AnalysisImageStatus.REJECTED.value
                item.passed = False
                item.rejection_reason = "Source image record was not found."
                continue
            image_bytes.append(s3.get_object(Bucket=settings.minio_bucket, Key=asset.object_key)["Body"].read())
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
            item = db.scalar(select(AnalysisJobImage).where(AnalysisJobImage.job_id == job.id, AnalysisJobImage.image_number == rejected.image_number))
            if item:
                item.status = AnalysisImageStatus.REJECTED.value
                item.passed = False
                item.rejection_reason = rejected.reason
        for product in result.products:
            for number in product.image_numbers:
                item = db.scalar(select(AnalysisJobImage).where(AnalysisJobImage.job_id == job.id, AnalysisJobImage.image_number == number))
                if item:
                    item.status = AnalysisImageStatus.ANALYSED.value
                    item.passed = True
                    item.product_number = product.product_number
            analysis = product.analysis
            db.add(ProductAnalysisRecord(job_id=job.id, product_number=product.product_number, product_name=analysis.product_name, category=analysis.category.value, product_type=analysis.product_type, colours=analysis.colours, materials=analysis.materials, features=analysis.features, description=analysis.description, confidence=analysis.confidence))
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


def run_once() -> bool:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    message = redis.rpop(QUEUE)
    redis.close()
    if not message:
        return False
    process_job(message)
    return True
