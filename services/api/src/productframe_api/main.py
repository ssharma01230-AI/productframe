import uuid
from typing import Any

import boto3
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from redis import Redis as SyncRedis
from redis.asyncio import Redis
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import current_user
from .config import Settings, get_settings
from .db import get_db
from .models import AnalysisJob, AnalysisJobImage, MembershipRole, Product, ProductAnalysisRecord, SourceAsset, User, Workspace, WorkspaceMembership

app = FastAPI(title="ProductFrame API", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


class ProductDecision(BaseModel):
    status: str = Field(pattern=r"^(suggested|approved|rejected|cancelled)$")
    product_name: str = Field(min_length=1, max_length=160)
    product_type: str = Field(min_length=1, max_length=160)
    colours: str = Field(min_length=1, max_length=300)
    materials: str = Field(min_length=1, max_length=300)
    features: list[str] = Field(min_length=1, max_length=30)
    description: str = Field(min_length=1, max_length=320)


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
    redis = SyncRedis.from_url(settings.redis_url)
    redis.lpush("productframe:analysis", job.id)
    redis.close()
    return {"id": job.id, "status": job.status, "total_images": job.total_images}


@app.patch("/analysis-jobs/{job_id}/products/{product_number}")
def decide_analysis_product(
    job_id: str,
    product_number: int,
    payload: ProductDecision,
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    workspace = _workspace_for_user(db, user["sub"])
    job = db.scalar(select(AnalysisJob).where(AnalysisJob.id == job_id, AnalysisJob.workspace_id == workspace.id))
    record = db.scalar(select(ProductAnalysisRecord).where(ProductAnalysisRecord.job_id == job_id, ProductAnalysisRecord.product_number == product_number))
    if job is None or record is None:
        raise HTTPException(status_code=404, detail="Analysis product not found")
    record.product_name = payload.product_name.strip()
    record.product_type = payload.product_type.strip()
    record.colours = payload.colours.strip()
    record.materials = payload.materials.strip()
    record.features = payload.features
    record.description = payload.description.strip()
    record.confirmation_status = payload.status
    if payload.status == "approved" and record.final_product_id is None:
        final_product = Product(workspace_id=workspace.id, name=record.product_name, category=record.category, product_type=record.product_type, colours=record.colours, materials=record.materials, features=record.features, description=record.description)
        db.add(final_product)
        db.flush()
        record.final_product_id = final_product.id
        image_rows = db.scalars(select(AnalysisJobImage).where(AnalysisJobImage.job_id == job_id, AnalysisJobImage.product_number == product_number, AnalysisJobImage.passed.is_(True))).all()
        for image in image_rows:
            if image.source_asset_id:
                asset = db.get(SourceAsset, image.source_asset_id)
                if asset:
                    asset.product_id = final_product.id
    elif payload.status == "approved" and record.final_product_id:
        final_product = db.get(Product, record.final_product_id)
        if final_product:
            final_product.name = record.product_name
            final_product.category = record.category
            final_product.product_type = record.product_type
            final_product.colours = record.colours
            final_product.materials = record.materials
            final_product.features = record.features
            final_product.description = record.description
    db.commit()
    return {"status": record.confirmation_status, "product_number": str(record.product_number)}


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


@app.get("/products")
def list_products(
    user: dict[str, Any] = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, str | None]]:
    workspace = _workspace_for_user(db, user["sub"])
    linked_ids = set(db.scalars(select(ProductAnalysisRecord.final_product_id).where(ProductAnalysisRecord.final_product_id.is_not(None))).all())
    approved_ids = set(db.scalars(select(ProductAnalysisRecord.final_product_id).where(ProductAnalysisRecord.confirmation_status == "approved", ProductAnalysisRecord.final_product_id.is_not(None))).all())
    products = db.scalars(select(Product).where(Product.workspace_id == workspace.id, Product.name != "Unconfirmed product upload", or_(Product.id.not_in(linked_ids or ["00000000-0000-0000-0000-000000000000"]), Product.id.in_(approved_ids or ["00000000-0000-0000-0000-000000000000"]))).order_by(Product.created_at.desc())).all()
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    result = []
    for product in products:
        asset = db.scalar(select(SourceAsset).where(SourceAsset.product_id == product.id).order_by(SourceAsset.created_at.desc()))
        image_url = s3.generate_presigned_url("get_object", Params={"Bucket": settings.minio_bucket, "Key": asset.object_key}, ExpiresIn=900) if asset else None
        result.append({"id": product.id, "name": product.name, "image_url": image_url})
    return result


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
