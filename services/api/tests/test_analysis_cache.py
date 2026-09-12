from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from productframe_api.analysis_cache import (
    ANALYSIS_PROMPT_VERSION,
    ANALYSIS_SCHEMA_VERSION,
    load_cached_stages,
    normalized_image_hash,
    save_cached_stage,
)
from productframe_api.db import Base


def test_normalized_image_hash_is_stable_and_content_keyed():
    assert normalized_image_hash(b"image") == normalized_image_hash(b"image")
    assert normalized_image_hash(b"image") != normalized_image_hash(b"other")


def test_cache_preserves_independent_stages_and_invalidates_versions():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        image_hash = normalized_image_hash(b"image")
        save_cached_stage(db, image_hash=image_hash, model="vision", stage="screening", result={"passed": True})
        save_cached_stage(db, image_hash=image_hash, model="vision", stage="identity", result={"product_type": "pump"})
        db.commit()
        assert load_cached_stages(db, image_hash=image_hash, model="vision") == {
            "screening": {"passed": True}, "identity": {"product_type": "pump"}
        }
        assert load_cached_stages(db, image_hash=image_hash, model="vision", prompt_version="new") == {}
        assert load_cached_stages(db, image_hash=image_hash, model="other") == {}
    engine.dispose()


def test_cache_rejects_unknown_stage():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        try:
            save_cached_stage(db, image_hash="a" * 64, model="vision", stage="unknown", result={})
        except ValueError as exc:
            assert "Unknown analysis cache stage" in str(exc)
        else:
            raise AssertionError("unknown stages must be rejected")
    engine.dispose()
