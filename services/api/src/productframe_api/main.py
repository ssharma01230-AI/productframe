import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from redis import Redis as SyncRedis
from redis.asyncio import Redis
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .auth import current_user
from .config import Settings, get_settings
from .db import get_db
from .generation_persistence import create_generation_run as create_generation_run_persistence
from .generation_templates import get_generation_template, list_generation_templates
from .output_readiness import evaluate_template
from .models import AnalysisJob, AnalysisJobImage, GeneratedAssetStatus, GenerationJob, GenerationRun, GenerationRunStatus, MembershipRole, Product, ProductAnalysisRecord, SourceAsset, User, Workspace, WorkspaceMembership

app = FastAPI(title="ProductFrame API", version="0.1.0")
ANALYSIS_QUEUE = "productframe:analysis"

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


_GENERATION_PROGRESS_STAGES: dict[str, tuple[int, str, str]] = {
    "pending": (8, "in_progress", "Preparing your image"),
    "generating": (58, "in_progress", "Creating the product image"),
    "awaiting_review": (100, "ready", "Image ready for your review"),
    "validating": (96, "in_progress", "Finalising your approved image"),
    "completed": (100, "ready", "Image ready for your review"),
    "failed": (100, "failed", "Generation stopped"),
    "cancelled": (100, "cancelled", "Generation cancelled"),
}


def _generation_progress(jobs: list[GenerationJob]) -> dict[str, Any]:
    """Return a run-level progress snapshot that also works for fan-out runs."""
    if not jobs:
        return {
            "stage": "in_progress",
            "message": "Preparing your image",
            "completed": 0,
            "total": 0,
            "percent": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "active_jobs": 0,
        }

    statuses = [job.status or "pending" for job in jobs]
    stage_order = ("generating", "validating", "pending", "awaiting_review", "failed", "cancelled", "completed")
    representative = next((status for status in stage_order if status in statuses), "pending")
    percent = round(sum(_GENERATION_PROGRESS_STAGES.get(status, _GENERATION_PROGRESS_STAGES["pending"])[0] for status in statuses) / len(statuses))
    completed_jobs = statuses.count("completed")
    failed_jobs = statuses.count("failed")
    active_jobs = len(statuses) - completed_jobs - failed_jobs - statuses.count("cancelled")
    message = _GENERATION_PROGRESS_STAGES[representative][2]
    if representative == "pending" and any(job.attempt_count > 1 for job in jobs if (job.status or "pending") == "pending"):
        message = "Retrying the generation"
    return {
        "stage": _GENERATION_PROGRESS_STAGES[representative][1],
        "message": message,
        "completed": completed_jobs,
        "total": len(jobs),
        "percent": percent,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "active_jobs": active_jobs,
    }


def _signed_generation_url(client: Any, object_key: str | None) -> str | None:
    if not object_key:
        return None
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": object_key},
        ExpiresIn=900,
    )


def _generation_decision(job: GenerationJob) -> str | None:
    if job.review_decision in {"approved", "rejected"}:
        return job.review_decision
    asset = job.generated_asset
    if asset is not None and asset.status in {GeneratedAssetStatus.APPROVED.value, GeneratedAssetStatus.REJECTED.value}:
        return asset.status
    # The previous interrupt-based graph represented rejection by cancelling
    # the job after a preview had been produced, without creating an asset.
    if job.status == "cancelled" and job.preview_object_key:
        return "rejected"
    return None


def _generation_run_payload(db: Session, run: GenerationRun) -> dict[str, Any]:
    jobs = sorted(run.jobs, key=lambda item: (item.job_index, item.created_at, item.id))
    product_ids = {job.product_id for job in jobs}
    products = db.scalars(
        select(Product)
        .where(Product.id.in_(product_ids), Product.workspace_id == run.workspace_id)
        .options(selectinload(Product.source_assets))
    ).all() if product_ids else []
    products_by_id = {product.id: product for product in products}
    client = boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name="us-east-1",
    )
    payload_jobs: list[dict[str, Any]] = []
    ready = approved = rejected = failed = 0
    for job in jobs:
        product = products_by_id.get(job.product_id)
        asset = job.generated_asset
        decision = _generation_decision(job)
        output_key = asset.object_key if asset is not None else job.preview_object_key
        is_ready = bool(output_key) and job.status != "failed"
        if is_ready:
            ready += 1
        if decision == "approved":
            approved += 1
        elif decision == "rejected":
            rejected += 1
        if job.status == "failed":
            failed += 1
        template = get_generation_template(job.template_id)
        source = None
        if product is not None and product.source_assets:
            source = max(product.source_assets, key=lambda item: (item.created_at, item.id))
        payload_jobs.append({
            "id": job.id,
            "run_id": job.generation_run_id,
            "status": job.status,
            "template_id": job.template_id,
            "template_name": template.name if template is not None else job.template_id,
            "template_channel": template.channel if template is not None else "ecommerce",
            "attempt_count": job.attempt_count,
            "preview_url": _signed_generation_url(client, output_key),
            "error_message": job.error_message,
            "review_decision": decision,
            "product": {
                "id": product.id if product is not None else job.product_id,
                "name": product.name if product is not None else "Product",
                "category": product.category if product is not None else None,
                "image_url": _signed_generation_url(client, source.object_key) if source is not None else None,
            },
            "asset": ({
                "id": asset.id,
                "filename": asset.filename,
                "content_type": asset.content_type,
                "status": asset.status,
                "image_url": _signed_generation_url(client, asset.object_key),
            } if asset is not None else None),
        })
    reviewed = approved + rejected
    in_progress = max(0, len(jobs) - ready - failed)
    return {
        "id": run.id,
        "status": run.status,
        "total_jobs": len(jobs),
        "created_at": run.created_at.isoformat(),
        "progress": _generation_progress(jobs),
        "counts": {
            "products": len(product_ids),
            "in_progress": in_progress,
            "ready": ready,
            "reviewed": reviewed,
            "approved": approved,
            "rejected": rejected,
            "failed": failed,
        },
        "jobs": payload_jobs,
    }


@app.middleware("http")
async def request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready(db: Session = Depends(get_db), config: Settings = Depends(get_settings)) -> dict[str, Any]:
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "not_ready"
    try:
        redis = Redis.from_url(config.redis_url)
        await redis.ping()
        await redis.aclose()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "not_ready"
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            result = await client.get(f"{config.minio_endpoint}/minio/health/live")
            checks["minio"] = "ok" if result.is_success else "not_ready"
    except Exception:
        checks["minio"] = "not_ready"
    status = "ready" if all(value == "ok" for value in checks.values()) else "not_ready"
    return {"status": status, "checks": checks}


@app.get("/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {"id": user["sub"], "claims": user}


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class AssetUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(pattern=r"^image/")


class AnalysisJobCreate(BaseModel):
    source_asset_ids: list[str] = Field(min_length=1, max_length=50)


class GenerationSelection(BaseModel):
    product_id: str = Field(min_length=1, max_length=36)
    template_id: str = Field(min_length=1, max_length=160)
    channel: str = Field(default="ecommerce", min_length=1, max_length=30)


class GenerationRunCreate(BaseModel):
    # Legacy fields remain accepted while the frontend migrates to selections.
    product_id: str | None = Field(default=None, min_length=1, max_length=36)
    template_id: str | None = Field(default=None, min_length=1, max_length=160)
    channel: str = Field(default="ecommerce", min_length=1, max_length=30)
    selections: list[GenerationSelection] | None = Field(default=None, min_length=1, max_length=100)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=255)

    @field_validator("selections")
    @classmethod
    def unique_selections(cls, selections: list[GenerationSelection] | None) -> list[GenerationSelection] | None:
        if selections is not None and not selections:
            raise ValueError("At least one generation selection is required")
        return selections

    def normalized_selections(self) -> list[dict[str, str]]:
        if self.selections is not None:
            return [selection.model_dump() for selection in self.selections]
        if self.product_id is None or self.template_id is None:
            raise ValueError("Either selections or the legacy product_id and template_id fields are required")
        return [{"product_id": self.product_id, "template_id": self.template_id, "channel": self.channel}]


class GenerationReview(BaseModel):
    approved: bool


class GenerationDecision(BaseModel):
    decision: Literal["approved", "rejected"]


class ProductReviewDraft(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    gender: Literal["male", "female", "unisex"] = "unisex"
    product_name: str = Field(min_length=1, max_length=160)

    @field_validator("product_name")
    @classmethod
    def product_name_max_five_words(cls, value: str) -> str:
        return " ".join(value.split()[:5])
    product_type: str = Field(min_length=1, max_length=160)
    colours: str = Field(min_length=1, max_length=300)
    materials: str = Field(min_length=1, max_length=300)
    features: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]] = Field(min_length=1, max_length=30)
    description: str = Field(min_length=1, max_length=320)


class ProductDecision(ProductReviewDraft):
    status: str = Field(pattern=r"^(suggested|approved|rejected|cancelled)$")


def assumed_gender(global_details: Any) -> str:
    gender = global_details.get("gender") if isinstance(global_details, dict) else None
    value = gender.get("user_confirmed") or gender.get("assumed") if isinstance(gender, dict) else gender
    text = str(value or "").lower()
    if any(word in text for word in ("female", "woman", "women", "womens", "girl")):
        return "female"
    if any(word in text for word in ("male", "man", "men", "mens", "boy")):
        return "male"
    return "unisex"


class ProductApprovalDraft(ProductReviewDraft):
    product_number: int = Field(ge=1, strict=True)


class ProductsApproveAll(BaseModel):
    products: list[ProductApprovalDraft] = Field(min_length=1, max_length=50)

    @field_validator("products")
    @classmethod
    def unique_product_numbers(cls, products: list[ProductApprovalDraft]) -> list[ProductApprovalDraft]:
        if len({product.product_number for product in products}) != len(products):
            raise ValueError("Each product number must appear only once")
        return products


@app.post("/generation-runs")
def create_generation_run(
    payload: GenerationRunCreate,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    try:
        run, jobs = create_generation_run_persistence(
            db,
            workspace_id=workspace.id,
            selections=payload.normalized_selections(),
            idempotency_key=payload.idempotency_key,
            enforce_evidence=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)
        for job in jobs:
            redis.xadd("productframe:generation", {"type": "generate", "job_id": job.id}, maxlen=10000, approximate=True)
        redis.close()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Generation could not be queued") from exc
    return {
        "run_id": run.id,
        "job_id": jobs[0].id if len(jobs) == 1 else None,
        "status": run.status,
        "total_jobs": run.total_jobs,
        "graph_thread_id": jobs[0].graph_thread_id if len(jobs) == 1 else None,
        "progress": _generation_progress(jobs),
        "jobs": [{"id": job.id, "graph_thread_id": job.graph_thread_id} for job in jobs],
    }


@app.get("/generation-runs/{run_id}")
def get_generation_run(
    run_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    run = db.scalar(
        select(GenerationRun)
        .where(GenerationRun.id == run_id, GenerationRun.workspace_id == workspace.id)
        .options(selectinload(GenerationRun.jobs).selectinload(GenerationJob.generated_asset))
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Generation run not found")
    return _generation_run_payload(db, run)


def _record_generation_decision(
    *,
    job_id: str,
    decision: Literal["approved", "rejected"],
    clerk_user_id: str,
    db: Session,
) -> tuple[GenerationJob, bool]:
    workspace = _workspace_for_user(db, clerk_user_id)
    local_user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    job = db.scalar(
        select(GenerationJob)
        .where(GenerationJob.id == job_id, GenerationJob.workspace_id == workspace.id)
        .with_for_update()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    asset = job.generated_asset
    existing = _generation_decision(job)
    if existing is not None and existing != decision:
        raise HTTPException(status_code=409, detail=f"Generation job was already {existing}")
    if existing == decision:
        if job.review_decision != decision:
            job.review_decision = decision
            job.reviewed_at = job.reviewed_at or datetime.now(timezone.utc)
            job.reviewed_by_user_id = job.reviewed_by_user_id or (local_user.id if local_user is not None else None)
            db.commit()
            db.refresh(job)
        return job, False
    legacy_review = asset is None and job.status in {"awaiting_review", "validating"}
    if asset is None and not legacy_review:
        raise HTTPException(status_code=409, detail="Generated image is not ready for review")
    if asset is not None and job.status == "failed":
        raise HTTPException(status_code=409, detail="Failed generation cannot be reviewed")
    if asset is not None and asset.status in {"approved", "rejected"} and asset.status != decision:
        raise HTTPException(status_code=409, detail=f"Generated image was already {asset.status}")

    job.review_decision = decision
    job.reviewed_at = job.reviewed_at or datetime.now(timezone.utc)
    job.reviewed_by_user_id = job.reviewed_by_user_id or (local_user.id if local_user is not None else None)
    if asset is not None:
        asset.status = decision
    db.commit()
    db.refresh(job)
    return job, legacy_review and job.status in {"awaiting_review", "validating"}


def _queue_legacy_generation_review(job: GenerationJob, approved: bool) -> None:
    redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)
    try:
        redis.xadd("productframe:generation", {"type": "review", "job_id": job.id, "approved": "1" if approved else "0"}, maxlen=10000, approximate=True)
    finally:
        redis.close()


@app.put("/generation-jobs/{job_id}/decision")
def decide_generation_job(
    job_id: str,
    payload: GenerationDecision,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    job, queue_legacy = _record_generation_decision(
        job_id=job_id,
        decision=payload.decision,
        clerk_user_id=user["sub"],
        db=db,
    )
    if queue_legacy:
        try:
            _queue_legacy_generation_review(job, payload.decision == "approved")
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Decision was saved, but legacy finalisation could not be queued. Retry this action.") from exc
    return {"job_id": job.id, "status": job.status, "decision": job.review_decision}


@app.post("/generation-jobs/{job_id}/review")
def review_generation_job(
    job_id: str,
    payload: GenerationReview,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Backward-compatible review route for an in-flight old frontend."""
    decision: Literal["approved", "rejected"] = "approved" if payload.approved else "rejected"
    job, queue_legacy = _record_generation_decision(
        job_id=job_id,
        decision=decision,
        clerk_user_id=user["sub"],
        db=db,
    )
    if queue_legacy:
        try:
            _queue_legacy_generation_review(job, payload.approved)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Decision was saved, but legacy finalisation could not be queued. Retry this action.") from exc
    return {"job_id": job.id, "status": job.status, "approved": payload.approved, "decision": job.review_decision}


@app.delete("/generation-jobs/{job_id}")
def delete_generation_job(
    job_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete one generated output without deleting its product or siblings."""
    workspace = _workspace_for_user(db, user["sub"])
    job = db.scalar(
        select(GenerationJob)
        .where(GenerationJob.id == job_id, GenerationJob.workspace_id == workspace.id)
        .with_for_update()
    )
    if job is None:
        asset = db.scalar(
            select(GeneratedAsset)
            .where(GeneratedAsset.id == job_id, GeneratedAsset.workspace_id == workspace.id)
            .with_for_update()
        )
        job = asset.job if asset is not None else None
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    if job.status == GenerationJobStatus.GENERATING.value:
        raise HTTPException(status_code=409, detail="This image is still generating. Try again when it is ready.")
    asset_key = job.generated_asset.object_key if job.generated_asset else None
    run = job.run
    if asset_key:
        s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
        try:
            s3.delete_object(Bucket=settings.minio_bucket, Key=asset_key)
        except Exception:
            pass
    db.delete(job)
    db.flush()
    run.total_jobs = max(0, run.total_jobs - 1)
    recalculate_generation_run(db, run.id)
    db.commit()
    return {"job_id": job_id, "run_id": run.id, "status": "deleted"}


@app.post("/generation-jobs/{job_id}/retry")
def retry_generation_job(
    job_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    job = db.scalar(
        select(GenerationJob)
        .where(GenerationJob.id == job_id, GenerationJob.workspace_id == workspace.id)
        .with_for_update()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    if job.status != "failed" or job.generated_asset is not None:
        raise HTTPException(status_code=409, detail="Only a failed generation without an image can be retried")
    job.status = "pending"
    job.attempt_count = 0
    job.error_message = None
    job.next_attempt_at = None
    job.started_at = None
    job.completed_at = None
    job.provider_request_id = None
    job.graph_thread_id = f"generation-job-{job.id}-retry-{uuid.uuid4()}"
    job.run.failed_jobs = max(0, job.run.failed_jobs - 1)
    job.run.status = GenerationRunStatus.PENDING.value
    job.run.completed_at = None
    db.commit()
    try:
        redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)
        redis.xadd("productframe:generation", {"type": "generate", "job_id": job.id}, maxlen=10000, approximate=True)
        redis.close()
    except Exception as exc:
        job.status = "failed"
        job.error_message = "Retry could not be queued"
        job.run.failed_jobs += 1
        job.run.status = GenerationRunStatus.FAILED.value
        job.run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=503, detail="Generation retry could not be queued") from exc
    return {"job_id": job.id, "status": job.status}


@app.get("/generation-jobs/{job_id}")
def get_generation_job(job_id: str, user: dict[str, Any] = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    job = db.scalar(select(GenerationJob).where(GenerationJob.id == job_id, GenerationJob.workspace_id == workspace.id))
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    run_jobs = db.scalars(select(GenerationJob).where(
        GenerationJob.generation_run_id == job.generation_run_id,
        GenerationJob.workspace_id == workspace.id,
    )).all()
    preview_url = None
    if job.preview_object_key:
        client = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
        preview_url = client.generate_presigned_url("get_object", Params={"Bucket": settings.minio_bucket, "Key": job.preview_object_key}, ExpiresIn=900)
    asset = job.generated_asset
    return {"id": job.id, "run_id": job.generation_run_id, "status": job.status, "template_id": job.template_id, "graph_thread_id": job.graph_thread_id, "attempt_count": job.attempt_count, "preview_object_key": job.preview_object_key, "preview_url": preview_url, "error_message": job.error_message, "review_decision": _generation_decision(job), "progress": _generation_progress(run_jobs), "asset": {"id": asset.id, "object_key": asset.object_key, "filename": asset.filename, "status": asset.status} if asset else None}


@app.post("/analysis-jobs")
def create_analysis_job(
    payload: AnalysisJobCreate,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    assets = db.scalars(select(SourceAsset).join(Product).where(SourceAsset.id.in_(payload.source_asset_ids), Product.workspace_id == workspace.id)).all()
    if len(assets) != len(set(payload.source_asset_ids)):
        raise HTTPException(status_code=400, detail="One or more source images were not found in this workspace")
    job = AnalysisJob(workspace_id=workspace.id, total_images=len(assets))
    db.add(job)
    db.flush()
    for number, asset in enumerate(assets, start=1):
        db.add(AnalysisJobImage(job_id=job.id, source_asset_id=asset.id, image_number=number))
    db.commit()
    redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)
    redis.xadd("productframe:analysis", {"type": "analyse", "job_id": job.id}, maxlen=10000, approximate=True)
    redis.close()
    return {"id": job.id, "status": job.status, "total_images": job.total_images}


def _lock_analysis_job(db: Session, workspace_id: str, job_id: str) -> AnalysisJob:
    # Every review mutation shares this lock, including individual decisions, so
    # a concurrent approval cannot create a second final product for a record.
    job = db.scalar(select(AnalysisJob).where(
        AnalysisJob.id == job_id, AnalysisJob.workspace_id == workspace_id,
    ).with_for_update().execution_options(populate_existing=True))
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return job


def _apply_product_decision(
    db: Session, workspace_id: str, record: ProductAnalysisRecord,
    payload: ProductReviewDraft, status: str,
) -> None:
    record.product_name = payload.product_name
    gender_details = record.global_details.get("gender", {}) if isinstance(record.global_details, dict) else {}
    if not isinstance(gender_details, dict): gender_details = {}
    record.global_details = {**(record.global_details or {}), "gender": {**gender_details, "user_confirmed": payload.gender}}
    record.product_type = payload.product_type
    record.colours = payload.colours
    record.materials = payload.materials
    record.features = payload.features
    record.description = payload.description
    record.confirmation_status = status
    if status == "approved" and record.final_product_id is None:
        final_product = Product(workspace_id=workspace_id, name=record.product_name, category=record.category, product_type=record.product_type, colours=record.colours, materials=record.materials, features=record.features, global_details=record.global_details, category_details=record.category_details, confidence_details=record.confidence_details, description=record.description)
        db.add(final_product)
        db.flush()
        record.final_product_id = final_product.id
        image_rows = db.scalars(select(AnalysisJobImage).where(AnalysisJobImage.job_id == record.job_id, AnalysisJobImage.product_number == record.product_number, AnalysisJobImage.passed.is_(True))).all()
        for image in image_rows:
            if image.source_asset_id:
                asset = db.get(SourceAsset, image.source_asset_id)
                if asset:
                    asset.product_id = final_product.id
    elif status == "approved" and record.final_product_id:
        final_product = db.get(Product, record.final_product_id)
        if final_product:
            final_product.name = record.product_name
            final_product.category = record.category
            final_product.product_type = record.product_type
            final_product.colours = record.colours
            final_product.materials = record.materials
            final_product.features = record.features
            final_product.global_details = record.global_details
            final_product.category_details = record.category_details
            final_product.confidence_details = record.confidence_details
            final_product.description = record.description


@app.patch("/analysis-jobs/{job_id}/products/{product_number}")
def decide_analysis_product(
    job_id: str,
    product_number: int,
    payload: ProductDecision,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        workspace = _workspace_for_user(db, user["sub"])
        _lock_analysis_job(db, workspace.id, job_id)
        record = db.scalar(select(ProductAnalysisRecord).where(
            ProductAnalysisRecord.job_id == job_id, ProductAnalysisRecord.product_number == product_number,
        ).execution_options(populate_existing=True))
        if record is None:
            raise HTTPException(status_code=404, detail="Analysis product not found")
        _apply_product_decision(db, workspace.id, record, payload, payload.status)
        result = {"status": record.confirmation_status, "product_number": str(record.product_number)}
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


@app.post("/analysis-jobs/{job_id}/products/approve-all")
def approve_all_analysis_products(
    job_id: str,
    payload: ProductsApproveAll,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        workspace = _workspace_for_user(db, user["sub"])
        job = _lock_analysis_job(db, workspace.id, job_id)
        if job.status not in {"awaiting_confirmation", "completed"}:
            raise HTTPException(status_code=409, detail="Analysis job is not ready for approval")
        requested_numbers = [product.product_number for product in payload.products]
        records = db.scalars(select(ProductAnalysisRecord).where(
            ProductAnalysisRecord.job_id == job_id,
            ProductAnalysisRecord.product_number.in_(requested_numbers),
        ).execution_options(populate_existing=True)).all()
        records_by_number = {record.product_number: record for record in records}
        if len(records_by_number) != len(requested_numbers):
            raise HTTPException(status_code=404, detail="One or more analysis products were not found")

        results = []
        for draft in payload.products:
            record = records_by_number[draft.product_number]
            # Stale browser state and retries must never overwrite a decision.
            if record.confirmation_status in {"suggested", "pending"}:
                _apply_product_decision(db, workspace.id, record, draft, "approved")
            results.append({
                "id": record.id,
                "product_number": record.product_number,
                "product_name": record.product_name,
                "category": record.category,
                "product_type": record.product_type,
                "colours": record.colours,
                "materials": record.materials,
                "features": record.features,
                "description": record.description,
                "confidence": record.confidence,
                "confirmation_status": record.confirmation_status,
                "status": record.confirmation_status,
                "final_product_id": record.final_product_id,
            })
        db.commit()
        return {"products": results}
    except Exception:
        db.rollback()
        raise


@app.get("/analysis-jobs/{job_id}/results")
def get_analysis_results(
    job_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    job = db.scalar(select(AnalysisJob).where(AnalysisJob.id == job_id, AnalysisJob.workspace_id == workspace.id))
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    images = db.scalars(select(AnalysisJobImage).where(AnalysisJobImage.job_id == job.id).order_by(AnalysisJobImage.image_number)).all()
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    analyses = db.scalars(select(ProductAnalysisRecord).where(ProductAnalysisRecord.job_id == job.id).order_by(ProductAnalysisRecord.product_number)).all()
    return {
        "id": job.id, "status": job.status, "total_images": job.total_images, "processed_images": job.processed_images,
        "unique_product_count": job.unique_product_count,
        "progress": {"stage": job.progress_stage, "message": job.progress_message, "completed": job.progress_completed, "total": job.progress_total, "percent": job.progress_percent},
        "images": [{"id": image.id, "image_number": image.image_number, "filename": (db.get(SourceAsset, image.source_asset_id).filename if image.source_asset_id and db.get(SourceAsset, image.source_asset_id) else None), "image_url": (s3.generate_presigned_url("get_object", Params={"Bucket": settings.minio_bucket, "Key": db.get(SourceAsset, image.source_asset_id).object_key}, ExpiresIn=900) if image.source_asset_id and db.get(SourceAsset, image.source_asset_id) else None), "status": image.status, "passed": image.passed, "product_number": image.product_number, "rejection_reason": image.rejection_reason} for image in images],
        "products": [{"id": analysis.id, "final_product_id": analysis.final_product_id, "product_number": analysis.product_number, "product_name": analysis.product_name, "category": analysis.category, "product_type": analysis.product_type, "colours": analysis.colours, "materials": analysis.materials, "features": analysis.features, "description": analysis.description, "confidence": analysis.confidence, "confirmation_status": analysis.confirmation_status, "gender": assumed_gender(analysis.global_details)} for analysis in analyses],
    }


@app.get("/analysis-jobs/{job_id}")
def get_analysis_job(
    job_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    job = db.scalar(select(AnalysisJob).where(AnalysisJob.id == job_id, AnalysisJob.workspace_id == workspace.id))
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return {"id": job.id, "status": job.status, "total_images": job.total_images, "processed_images": job.processed_images, "unique_product_count": job.unique_product_count, "error_message": job.error_message, "progress": {"stage": job.progress_stage, "message": job.progress_message, "completed": job.progress_completed, "total": job.progress_total, "percent": job.progress_percent}}


@app.post("/products")
def create_product(
    payload: ProductCreate,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    workspace = _workspace_for_user(db, user["sub"])
    product = Product(name=payload.name.strip(), workspace_id=workspace.id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return {"id": product.id, "name": product.name, "workspace_id": workspace.id}


def _library_products_query(workspace_id: str):
    linked = select(ProductAnalysisRecord.id).where(ProductAnalysisRecord.final_product_id == Product.id).exists()
    approved = select(ProductAnalysisRecord.id).where(
        ProductAnalysisRecord.final_product_id == Product.id,
        ProductAnalysisRecord.confirmation_status == "approved",
    ).exists()
    return select(Product).where(
        Product.workspace_id == workspace_id,
        Product.name != "Unconfirmed product upload",
        or_(~linked, approved),
    )


@app.get("/products")
def list_products(
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    workspace = _workspace_for_user(db, user["sub"])
    products = db.scalars(
        _library_products_query(workspace.id)
        .options(selectinload(Product.source_assets), selectinload(Product.generated_assets))
        .order_by(Product.created_at.desc(), Product.id)
    ).all()
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    result = []
    for product in products:
        approved_assets = [asset for asset in product.generated_assets if asset.status == GeneratedAssetStatus.APPROVED.value]
        previews = [{
            "id": asset.id,
            "filename": asset.filename,
            **({"media_evidence": asset.media_evidence} if asset.media_evidence else {}),
            "image_url": s3.generate_presigned_url("get_object", Params={"Bucket": settings.minio_bucket, "Key": asset.object_key}, ExpiresIn=900),
        } for asset in sorted(product.source_assets, key=lambda source: (source.created_at, source.id), reverse=True)[:4]]
        result.append({
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "product_family": (product.category_details or {}).get("family") if isinstance(product.category_details, dict) else None,
            "created_at": product.created_at.isoformat(),
            "image_url": previews[0]["image_url"] if previews else None,
            "preview_images": previews,
            "media_evidence": [asset.media_evidence for asset in sorted(product.source_assets, key=lambda source: (source.created_at, source.id), reverse=True) if asset.media_evidence],
            "upload_count": len(product.source_assets),
            "generated_count": len(approved_assets),
        })
    return result


@app.get("/products/{product_id}")
def get_product(
    product_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    product = db.scalar(_library_products_query(workspace.id).where(Product.id == product_id).options(selectinload(Product.generated_assets)))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    assets = db.scalars(
        select(SourceAsset)
        .where(SourceAsset.product_id == product.id)
        .order_by(SourceAsset.created_at.desc(), SourceAsset.id)
    ).all()
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "product_family": (product.category_details or {}).get("family") if isinstance(product.category_details, dict) else None,
        "created_at": product.created_at.isoformat(),
        "uploads": [{
            "id": asset.id,
            "filename": asset.filename,
            "content_type": asset.content_type,
            "created_at": asset.created_at.isoformat(),
            **({"media_evidence": asset.media_evidence} if asset.media_evidence else {}),
            "image_url": s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.minio_bucket, "Key": asset.object_key},
                ExpiresIn=900,
            ),
        } for asset in assets],
        "generated_assets": [{
            "id": asset.id,
            "name": asset.filename,
            "filename": asset.filename,
            "content_type": asset.content_type,
            "created_at": asset.created_at.isoformat(),
            "status": asset.status,
            "image_url": s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.minio_bucket, "Key": asset.object_key},
                ExpiresIn=900,
            ),
        } for asset in sorted(
            (item for item in product.generated_assets if item.status == GeneratedAssetStatus.APPROVED.value),
            key=lambda item: (item.created_at, item.id),
            reverse=True,
        )],
    }


@app.get("/products/{product_id}/output-readiness")
def get_output_readiness(
    product_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    product = db.scalar(_library_products_query(workspace.id).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    evidence = [asset.media_evidence for asset in product.source_assets]
    category_details = product.category_details if isinstance(product.category_details, dict) else {}
    family = category_details.get("family")
    templates = [] if product.category == "underwear" and not family else list_generation_templates(
        category=product.category,
        channel="ecommerce",
        product_family=family,
    ) if product.category else []
    return {"product_id": product.id, "templates": [evaluate_template(template, evidence) for template in templates]}


@app.get("/products/{product_id}/download")
def download_product_uploads(
    product_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    workspace = _workspace_for_user(db, user["sub"])
    product = db.scalar(_library_products_query(workspace.id).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    assets = db.scalars(select(SourceAsset).where(SourceAsset.product_id == product.id).order_by(SourceAsset.created_at, SourceAsset.id)).all()
    if not assets:
        raise HTTPException(status_code=409, detail="This product has no uploads to download")
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    archive = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
    used_names: set[str] = set()
    try:
        with zipfile.ZipFile(archive, "w") as zipped:
            for asset in assets:
                # Uploaded filenames are untrusted and must remain plain ZIP entries.
                name = re.sub(r"[\x00-\x1f\x7f]", "", PurePosixPath(asset.filename.replace("\\", "/")).name).strip()
                if name in {"", ".", ".."}:
                    name = f"upload-{asset.id}"
                original = PurePosixPath(name)
                duplicate = 2
                while name.casefold() in used_names:
                    name = f"{original.stem} ({duplicate}){original.suffix}"
                    duplicate += 1
                used_names.add(name.casefold())
                body = s3.get_object(Bucket=settings.minio_bucket, Key=asset.object_key)["Body"]
                try:
                    with zipped.open(name, "w") as target:
                        shutil.copyfileobj(body, target, length=64 * 1024)
                finally:
                    body.close()
        content_length = archive.tell()
        archive.seek(0)
    except (BotoCoreError, ClientError, OSError) as exc:
        archive.close()
        raise HTTPException(status_code=502, detail="Could not retrieve product uploads. Please try again.") from exc
    except Exception:
        archive.close()
        raise

    def stream_archive():
        try:
            while chunk := archive.read(64 * 1024):
                yield chunk
        finally:
            archive.close()

    download_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", product.name).strip("-") or "product"
    return StreamingResponse(
        stream_archive(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}-uploads.zip"',
            "Content-Length": str(content_length),
            "Cache-Control": "private, no-store",
        },
    )


@app.delete("/products/{product_id}/source-assets/{asset_id}")
def delete_source_asset(
    product_id: str,
    asset_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    workspace = _workspace_for_user(db, user["sub"])
    asset = db.scalar(select(SourceAsset).join(Product).where(SourceAsset.id == asset_id, SourceAsset.product_id == product_id, Product.workspace_id == workspace.id))
    if asset is None:
        raise HTTPException(status_code=404, detail="Source image not found")
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    try:
        s3.delete_object(Bucket=settings.minio_bucket, Key=asset.object_key)
    except Exception:
        pass
    db.delete(asset)
    db.commit()
    return {"asset_id": asset_id, "status": "deleted"}


@app.delete("/products/{product_id}")
def delete_product(product_id: str, user: dict[str, Any] = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    workspace = _workspace_for_user(db, user["sub"])
    product = db.scalar(select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    for asset in list(product.source_assets) + list(product.generated_assets):
        try:
            s3.delete_object(Bucket=settings.minio_bucket, Key=asset.object_key)
        except Exception:
            pass
    db.delete(product)
    db.commit()
    return {"id": product_id, "status": "deleted"}


@app.post("/products/{product_id}/source-assets/{asset_id}/evidence")
def queue_evidence_analysis(
    product_id: str,
    asset_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    workspace = _workspace_for_user(db, user["sub"])
    asset = db.scalar(select(SourceAsset).join(Product).where(
        SourceAsset.id == asset_id,
        SourceAsset.product_id == product_id,
        Product.workspace_id == workspace.id,
    ))
    if asset is None:
        raise HTTPException(status_code=404, detail="Source image not found")
    redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)
    try:
        redis.xadd(ANALYSIS_QUEUE, {"type": "evidence", "product_id": product_id, "asset_id": asset_id}, maxlen=10000, approximate=True)
    finally:
        redis.close()
    return {"asset_id": asset_id, "status": "queued"}


@app.post("/products/{product_id}/source-assets/upload-url")
def create_upload_url(
    product_id: str,
    payload: AssetUploadRequest,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    workspace = _workspace_for_user(db, user["sub"])
    product = db.scalar(select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    object_key = f"workspaces/{workspace.id}/products/{product.id}/sources/{uuid.uuid4()}-{payload.filename}"
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    upload_url = s3.generate_presigned_url("put_object", Params={"Bucket": settings.minio_bucket, "Key": object_key, "ContentType": payload.content_type}, ExpiresIn=900, HttpMethod="PUT")
    asset = SourceAsset(product_id=product.id, object_key=object_key, filename=payload.filename, content_type=payload.content_type)
    db.add(asset)
    db.commit()
    return {"asset_id": asset.id, "object_key": object_key, "upload_url": upload_url}


def _workspace_for_user(db: Session, clerk_user_id: str) -> Workspace:
    local_user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    if local_user is None:
        raise HTTPException(status_code=404, detail="User workspace not initialized")
    membership = db.scalar(select(WorkspaceMembership).where(WorkspaceMembership.user_id == local_user.id).order_by(WorkspaceMembership.created_at))
    if membership is None:
        raise HTTPException(status_code=404, detail="No workspace membership found")
    workspace = db.get(Workspace, membership.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@app.get("/workspaces/current")
def current_workspace(
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Return the user's current workspace, creating the local record on first login."""
    clerk_user_id = user["sub"]
    local_user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    if local_user is None:
        local_user = User(clerk_user_id=clerk_user_id, email=user.get("email"))
        workspace = Workspace(name="Studio")
        db.add_all([local_user, workspace])
        try:
            db.flush()
            db.add(WorkspaceMembership(user_id=local_user.id, workspace_id=workspace.id, role=MembershipRole.OWNER.value))
            db.commit()
            return {"id": workspace.id, "name": workspace.name, "owner_id": clerk_user_id, "role": MembershipRole.OWNER.value}
        except IntegrityError:
            # Two browser requests can arrive during first login. Re-read the winner.
            db.rollback()
            local_user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
            if local_user is None:
                raise HTTPException(status_code=409, detail="Could not create local user")

    membership = db.scalar(select(WorkspaceMembership).where(WorkspaceMembership.user_id == local_user.id).order_by(WorkspaceMembership.created_at))
    if membership is None:
        raise HTTPException(status_code=404, detail="No workspace membership found")
    workspace = db.get(Workspace, membership.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"id": workspace.id, "name": workspace.name, "owner_id": clerk_user_id, "role": membership.role}
