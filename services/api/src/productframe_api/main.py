import uuid
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from redis.asyncio import Redis
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .auth import current_user
from .config import Settings, get_settings
from .db import get_db
from .models import MembershipRole, User, Workspace, WorkspaceMembership

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
        db.flush()
        db.add(WorkspaceMembership(user_id=local_user.id, workspace_id=workspace.id, role=MembershipRole.OWNER.value))
        db.commit()
        return {"id": workspace.id, "name": workspace.name, "owner_id": clerk_user_id, "role": MembershipRole.OWNER.value}

    membership = db.scalar(select(WorkspaceMembership).where(WorkspaceMembership.user_id == local_user.id).order_by(WorkspaceMembership.created_at))
    if membership is None:
        raise HTTPException(status_code=404, detail="No workspace membership found")
    workspace = db.get(Workspace, membership.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"id": workspace.id, "name": workspace.name, "owner_id": clerk_user_id, "role": membership.role}
