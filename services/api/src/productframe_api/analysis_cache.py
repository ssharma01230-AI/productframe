"""Versioned, image-content keyed storage for reusable analysis stages."""
from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ImageAnalysisCache

# Increment these when prompts or structured response contracts change.
ANALYSIS_PROMPT_VERSION = "2026-09-12-v3"
ANALYSIS_SCHEMA_VERSION = "product-analysis-v1"

_STAGE_COLUMNS = {
    "moderation": "moderation_result",
    "screening": "screening_result",
    "identity": "identity_result",
    "classification": "classification_result",
    "media_evidence": "media_evidence",
}


def normalized_image_hash(image_bytes: bytes) -> str:
    """Return the stable content key for already-normalized image bytes."""
    return hashlib.sha256(image_bytes).hexdigest()


def load_cached_stages(
    db: Session,
    *,
    image_hash: str,
    model: str,
    prompt_version: str = ANALYSIS_PROMPT_VERSION,
    schema_version: str = ANALYSIS_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Load only completed stage values for the exact analysis contract."""
    entry = db.scalar(select(ImageAnalysisCache).where(
        ImageAnalysisCache.image_hash == image_hash,
        ImageAnalysisCache.model == model,
        ImageAnalysisCache.prompt_version == prompt_version,
        ImageAnalysisCache.schema_version == schema_version,
    ))
    if entry is None:
        return {}
    return {
        stage: getattr(entry, column)
        for stage, column in _STAGE_COLUMNS.items()
        if getattr(entry, column) is not None
    }


def save_cached_stage(
    db: Session,
    *,
    image_hash: str,
    model: str,
    stage: str,
    result: Any,
    prompt_version: str = ANALYSIS_PROMPT_VERSION,
    schema_version: str = ANALYSIS_SCHEMA_VERSION,
) -> ImageAnalysisCache:
    """Upsert one completed stage without replacing other cached stages."""
    column = _STAGE_COLUMNS.get(stage)
    if column is None:
        raise ValueError(f"Unknown analysis cache stage: {stage}")
    entry = db.scalar(select(ImageAnalysisCache).where(
        ImageAnalysisCache.image_hash == image_hash,
        ImageAnalysisCache.model == model,
        ImageAnalysisCache.prompt_version == prompt_version,
        ImageAnalysisCache.schema_version == schema_version,
    ))
    if entry is None:
        entry = ImageAnalysisCache(
            image_hash=image_hash,
            model=model,
            prompt_version=prompt_version,
            schema_version=schema_version,
        )
        db.add(entry)
    setattr(entry, column, result)
    db.flush()
    return entry
