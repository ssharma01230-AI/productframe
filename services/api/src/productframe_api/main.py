import uuid
from typing import Any

import boto3
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import current_user
from .config import Settings, get_settings
from .db import get_db
from .models import MembershipRole, Product, SourceAsset, User, Workspace, WorkspaceMembership

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
    products = db.scalars(select(Product).where(Product.workspace_id == workspace.id).order_by(Product.created_at.desc())).all()
    s3 = boto3.client("s3", endpoint_url=settings.minio_endpoint, aws_access_key_id=settings.minio_access_key, aws_secret_access_key=settings.minio_secret_key, region_name="us-east-1")
    result = []
    for product in products:
        asset = db.scalar(select(SourceAsset).where(SourceAsset.product_id == product.id).order_by(SourceAsset.created_at.desc()))
        image_url = s3.generate_presigned_url("get_object", Params={"Bucket": settings.minio_bucket, "Key": asset.object_key}, ExpiresIn=900) if asset else None
        result.append({"id": product.id, "name": product.name, "image_url": image_url})
    return result


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
