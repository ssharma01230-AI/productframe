import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import PurePosixPath
from typing import Annotated, Any

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
from .generation_persistence import create_single_generation_run
from .models import AnalysisJob, AnalysisJobImage, GenerationJob, MembershipRole, Product, ProductAnalysisRecord, SourceAsset, User, Workspace, WorkspaceMembership

app = FastAPI(title="ProductFrame API", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


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


class GenerationRunCreate(BaseModel):
    product_id: str = Field(min_length=1, max_length=36)
    template_id: str = Field(min_length=1, max_length=160)
    channel: str = Field(default="ecommerce", min_length=1, max_length=30)


class GenerationReview(BaseModel):
    approved: bool


class ProductReviewDraft(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_name: str = Field(min_length=1, max_length=160)
    product_type: str = Field(min_length=1, max_length=160)
    colours: str = Field(min_length=1, max_length=300)
    materials: str = Field(min_length=1, max_length=300)
    features: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]] = Field(min_length=1, max_length=30)
    description: str = Field(min_length=1, max_length=320)


class ProductDecision(ProductReviewDraft):
    status: str = Field(pattern=r"^(suggested|approved|rejected|cancelled)$")


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
        run, job = create_single_generation_run(
            db,
            workspace_id=workspace.id,
            product_id=payload.product_id,
            template_id=payload.template_id,
            channel=payload.channel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)
        redis.xadd("productframe:generation", {"type": "generate", "job_id": job.id}, maxlen=10000, approximate=True)
        redis.close()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Generation could not be queued") from exc
    return {"run_id": run.id, "job_id": job.id, "status": run.status, "total_jobs": run.total_jobs, "graph_thread_id": job.graph_thread_id}


@app.post("/generation-jobs/{job_id}/review")
def review_generation_job(
    job_id: str,
    payload: GenerationReview,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    job = db.scalar(select(GenerationJob).where(GenerationJob.id == job_id, GenerationJob.workspace_id == workspace.id).with_for_update())
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    if job.status != "awaiting_review":
        raise HTTPException(status_code=409, detail="Generation job is not awaiting review")
    redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)
    redis.xadd("productframe:generation", {"type": "review", "job_id": job.id, "approved": "1" if payload.approved else "0"}, maxlen=10000, approximate=True)
    redis.close()
    return {"job_id": job.id, "status": job.status, "approved": payload.approved}


@app.get("/generation-jobs/{job_id}")
def get_generation_job(job_id: str, user: dict[str, Any] = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    job = db.scalar(select(GenerationJob).where(GenerationJob.id == job_id, GenerationJob.workspace_id == workspace.id))
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    preview_url = None
    if job.preview_object_key:
        client = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
        preview_url = client.generate_presigned_url("get_object", Params={"Bucket": settings.minio_bucket, "Key": job.preview_object_key}, ExpiresIn=900)
    asset = job.generated_asset
    return {"id": job.id, "run_id": job.generation_run_id, "status": job.status, "template_id": job.template_id, "graph_thread_id": job.graph_thread_id, "attempt_count": job.attempt_count, "preview_object_key": job.preview_object_key, "preview_url": preview_url, "error_message": job.error_message, "asset": {"id": asset.id, "object_key": asset.object_key, "filename": asset.filename} if asset else None}


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
        "products": [{"id": analysis.id, "final_product_id": analysis.final_product_id, "product_number": analysis.product_number, "product_name": analysis.product_name, "category": analysis.category, "product_type": analysis.product_type, "colours": analysis.colours, "materials": analysis.materials, "features": analysis.features, "description": analysis.description, "confidence": analysis.confidence, "confirmation_status": analysis.confirmation_status} for analysis in analyses],
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
        .options(selectinload(Product.source_assets))
        .order_by(Product.created_at.desc(), Product.id)
    ).all()
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    result = []
    for product in products:
        previews = [{
            "id": asset.id,
            "filename": asset.filename,
            "image_url": s3.generate_presigned_url("get_object", Params={"Bucket": settings.minio_bucket, "Key": asset.object_key}, ExpiresIn=900),
        } for asset in sorted(product.source_assets, key=lambda source: (source.created_at, source.id), reverse=True)[:4]]
        result.append({
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "created_at": product.created_at.isoformat(),
            "image_url": previews[0]["image_url"] if previews else None,
            "preview_images": previews,
            "upload_count": len(product.source_assets),
            # Generated outputs will be counted when generation persistence is connected.
            "generated_count": 0,
        })
    return result


@app.get("/products/{product_id}")
def get_product(
    product_id: str,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = _workspace_for_user(db, user["sub"])
    product = db.scalar(_library_products_query(workspace.id).where(Product.id == product_id))
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
        "created_at": product.created_at.isoformat(),
        "uploads": [{
            "id": asset.id,
            "filename": asset.filename,
            "content_type": asset.content_type,
            "created_at": asset.created_at.isoformat(),
            "image_url": s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.minio_bucket, "Key": asset.object_key},
                ExpiresIn=900,
            ),
        } for asset in assets],
        # Reserved for generated outputs with review status; source uploads are never outputs.
        "generated_assets": [],
    }


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


@app.delete("/products/{product_id}")
def delete_product(product_id: str, user: dict[str, Any] = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    workspace = _workspace_for_user(db, user["sub"])
    product = db.scalar(select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    for asset in list(product.source_assets):
        try:
            s3.delete_object(Bucket=settings.minio_bucket, Key=asset.object_key)
        except Exception:
            pass
    db.delete(product)
    db.commit()
    return {"id": product_id, "status": "deleted"}


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
