from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class MembershipRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class AnalysisJobStatus(StrEnum):
    PENDING = "pending"
    SCREENING = "screening"
    GROUPING = "grouping"
    ANALYSING = "analysing"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisImageStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ANALYSED = "analysed"


class AnalysisConfirmationStatus(StrEnum):
    SUGGESTED = "suggested"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    clerk_user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    memberships: Mapped[list["WorkspaceMembership"]] = relationship(back_populates="user")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    memberships: Mapped[list["WorkspaceMembership"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(40), default=AnalysisJobStatus.PENDING.value, index=True)
    total_images: Mapped[int] = mapped_column(default=0)
    processed_images: Mapped[int] = mapped_column(default=0)
    unique_product_count: Mapped[int] = mapped_column(default=0)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    progress_stage: Mapped[str] = mapped_column(String(40), default="queued")
    progress_message: Mapped[str | None] = mapped_column(String(240))
    progress_completed: Mapped[int] = mapped_column(default=0)
    progress_total: Mapped[int] = mapped_column(default=0)
    progress_percent: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    images: Mapped[list["AnalysisJobImage"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    analyses: Mapped[list["ProductAnalysisRecord"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class AnalysisJobImage(Base):
    __tablename__ = "analysis_job_images"
    __table_args__ = (UniqueConstraint("job_id", "image_number", name="uq_analysis_job_image_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    source_asset_id: Mapped[str | None] = mapped_column(ForeignKey("source_assets.id", ondelete="SET NULL"), index=True)
    image_number: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default=AnalysisImageStatus.PENDING.value)
    passed: Mapped[bool | None] = mapped_column()
    product_number: Mapped[int | None] = mapped_column()
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[AnalysisJob] = relationship(back_populates="images")


class ProductAnalysisRecord(Base):
    __tablename__ = "product_analysis_records"
    __table_args__ = (UniqueConstraint("job_id", "product_number", name="uq_analysis_job_product_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    product_number: Mapped[int] = mapped_column()
    product_name: Mapped[str] = mapped_column(String(160), default="Unconfirmed product")
    category: Mapped[str] = mapped_column(String(30))
    product_type: Mapped[str] = mapped_column(String(160))
    colours: Mapped[str] = mapped_column(String(300))
    materials: Mapped[str] = mapped_column(String(300))
    features: Mapped[list[str]] = mapped_column(JSON)
    global_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    category_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str] = mapped_column(String(320))
    confidence: Mapped[float] = mapped_column()
    confirmation_status: Mapped[str] = mapped_column(String(20), default=AnalysisConfirmationStatus.SUGGESTED.value)
    final_product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[AnalysisJob] = relationship(back_populates="analyses")


class GenerationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_FAILED = "partially_failed"
    CANCELLED = "cancelled"


class GenerationJobStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    AWAITING_REVIEW = "awaiting_review"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GeneratedAssetStatus(StrEnum):
    READY = "ready"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class GenerationRun(Base):
    __tablename__ = "generation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default=GenerationRunStatus.PENDING.value, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    total_jobs: Mapped[int] = mapped_column(default=0)
    completed_jobs: Mapped[int] = mapped_column(default=0)
    failed_jobs: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jobs: Mapped[list["GenerationJob"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (UniqueConstraint("generation_run_id", "product_id", "template_id", name="uq_generation_job_selection"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    generation_run_id: Mapped[str] = mapped_column(ForeignKey("generation_runs.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[str] = mapped_column(String(160))
    template_version: Mapped[int] = mapped_column(default=1)
    job_index: Mapped[int] = mapped_column(default=0)
    graph_thread_id: Mapped[str] = mapped_column(String(120), unique=True)
    preview_object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=GenerationJobStatus.PENDING.value, index=True)
    attempt_count: Mapped[int] = mapped_column(default=0)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    aspect_ratio: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    review_decision: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run: Mapped[GenerationRun] = relationship(back_populates="jobs")
    generated_asset: Mapped["GeneratedAsset | None"] = relationship(back_populates="job", uselist=False, cascade="all, delete-orphan")


class GeneratedAsset(Base):
    __tablename__ = "generated_assets"
    __table_args__ = (UniqueConstraint("generation_job_id", name="uq_generated_asset_job"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    generation_run_id: Mapped[str] = mapped_column(ForeignKey("generation_runs.id", ondelete="CASCADE"), index=True)
    generation_job_id: Mapped[str] = mapped_column(ForeignKey("generation_jobs.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[str] = mapped_column(String(160))
    object_key: Mapped[str] = mapped_column(String(500), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default=GeneratedAssetStatus.READY.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[GenerationJob] = relationship(back_populates="generated_asset")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    colours: Mapped[str | None] = mapped_column(String(300), nullable=True)
    materials: Mapped[str | None] = mapped_column(String(300), nullable=True)
    features: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    global_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    category_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    source_assets: Mapped[list["SourceAsset"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    generated_assets: Mapped[list["GeneratedAsset"]] = relationship(foreign_keys="GeneratedAsset.product_id", cascade="all, delete-orphan")


class SourceAsset(Base):
    __tablename__ = "source_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    object_key: Mapped[str] = mapped_column(String(500), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    # Model-derived visual coverage for output-template readiness. This is
    # source-media evidence, not product identity data.
    media_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    product: Mapped[Product] = relationship(back_populates="source_assets")


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default=MembershipRole.MEMBER.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship(back_populates="memberships")
    workspace: Mapped[Workspace] = relationship(back_populates="memberships")
