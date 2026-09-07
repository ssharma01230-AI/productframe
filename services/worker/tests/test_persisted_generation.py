from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
import pytest

from productframe_api.db import Base
from productframe_api.generation_persistence import create_generation_run, create_single_generation_run
from productframe_api.models import GeneratedAsset, GenerationJob, Product, SourceAsset, Workspace
from productframe_worker.generation_graph import run_persisted_generation
from productframe_worker.generation_storage import FakeGeneratedImageStorage
from productframe_worker.image_provider import FakeImageGenerationProvider
from productframe_worker.fidelity_validator import ProductFidelityError


def test_multi_job_run_processes_children_independently_and_preserves_success():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    provider = FakeImageGenerationProvider()
    storage = FakeGeneratedImageStorage()

    with Session(engine) as db:
        db.add(Workspace(id="workspace", name="Studio"))
        for product_id, category in (("top", "tops"), ("coat", "outerwear")):
            db.add(Product(id=product_id, workspace_id="workspace", name=product_id, category=category, product_type=product_id, colours="Blue", materials="Cotton", features=["Visible construction"], description=product_id))
            db.add(SourceAsset(id=f"source-{product_id}", product_id=product_id, filename="source.png", content_type="image/png", object_key=f"products/{product_id}/source.png"))
        db.commit()
        run, jobs = create_generation_run(db, workspace_id="workspace", selections=[
            {"product_id": "top", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
            {"product_id": "coat", "template_id": "ecommerce-outerwear-front-medium", "channel": "ecommerce"},
        ])
        run_persisted_generation(db, jobs[0].id, provider=provider, storage=storage, checkpointer=InMemorySaver())
        run_persisted_generation(db, jobs[1].id, provider=provider, storage=storage, checkpointer=InMemorySaver())
        assert run.status == "completed"
        assert run.completed_jobs == 2
        assert run.failed_jobs == 0
        assert db.query(GeneratedAsset).count() == 2
        assert len(provider.requests) == 2
        # Re-delivery is a no-op for already completed children.
        run_persisted_generation(db, jobs[0].id, provider=provider, storage=storage, checkpointer=InMemorySaver())
        assert len(provider.requests) == 2

    engine.dispose()


def test_persisted_graph_saves_prompt_asset_and_statuses():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    provider = FakeImageGenerationProvider()
    storage = FakeGeneratedImageStorage()

    with Session(engine) as db:
        db.add(Workspace(id="workspace", name="Studio"))
        db.add(Product(
            id="product",
            workspace_id="workspace",
            name="Blue top",
            category="tops",
            product_type="Short-sleeve crew-neck top",
            colours="Muted blue",
            materials="Cotton",
            features=["Short sleeves", "Round neckline"],
            description="A muted blue short-sleeve top with a round neckline.",
        ))
        db.add(SourceAsset(
            id="source",
            product_id="product",
            filename="source.webp",
            content_type="image/webp",
            object_key="products/product/source.webp",
        ))
        db.commit()
        _, job = create_single_generation_run(
            db,
            workspace_id="workspace",
            product_id="product",
            template_id="ecommerce-tops-front-view",
        )

        result = run_persisted_generation(db, job.id, provider=provider, storage=storage, checkpointer=InMemorySaver())

        saved_job = db.get(GenerationJob, job.id)
        asset = db.query(GeneratedAsset).one()
        assert result["status"] == "completed"
        assert saved_job.status == "completed"
        assert "Blue top" in saved_job.prompt
        assert asset.product_id == "product"
        assert asset.generation_job_id == job.id
        assert asset.status == "ready"
        assert asset.object_key in storage.objects
        assert len(provider.requests) == 1

    engine.dispose()


def test_persisted_graph_does_not_store_preview_when_fidelity_fails():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    provider = FakeImageGenerationProvider()
    storage = FakeGeneratedImageStorage()

    class RejectingValidator:
        def validate(self, prompt, image):
            raise ProductFidelityError("Generated image failed product fidelity validation: artwork changed")

    with Session(engine) as db:
        db.add(Workspace(id="workspace", name="Studio"))
        db.add(Product(
            id="product", workspace_id="workspace", name="Graphic top", category="tops",
            product_type="Graphic t-shirt", colours="Navy", materials="Cotton",
            features=["Printed artwork"],
            description="A navy graphic t-shirt with a prominent printed illustration.",
        ))
        db.add(SourceAsset(
            id="source", product_id="product", filename="source.png",
            content_type="image/png", object_key="products/product/source.png",
        ))
        db.commit()
        _, job = create_single_generation_run(
            db, workspace_id="workspace", product_id="product",
            template_id="ecommerce-tops-front-view",
        )

        with pytest.raises(ProductFidelityError, match="artwork changed"):
            run_persisted_generation(
                db, job.id, provider=provider, storage=storage,
                fidelity_validator=RejectingValidator(), checkpointer=InMemorySaver(),
            )

        assert len(storage.objects) == 1
        assert "/rejected/" in next(iter(storage.objects))
        assert "/preview/" not in next(iter(storage.objects))
        assert db.get(GenerationJob, job.id).status == "failed"

    engine.dispose()


def test_duplicate_generation_delivery_does_not_call_provider_twice():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    provider = FakeImageGenerationProvider()
    storage = FakeGeneratedImageStorage()

    with Session(engine) as db:
        db.add(Workspace(id="workspace", name="Studio"))
        db.add(Product(
            id="product", workspace_id="workspace", name="Blue top", category="tops",
            product_type="Short-sleeve crew-neck top", colours="Muted blue", materials="Cotton",
            features=["Short sleeves"], description="A muted blue short-sleeve top.",
        ))
        db.add(SourceAsset(
            id="source", product_id="product", filename="source.png",
            content_type="image/png", object_key="products/product/source.png",
        ))
        db.commit()
        _, job = create_single_generation_run(
            db, workspace_id="workspace", product_id="product",
            template_id="ecommerce-tops-front-view",
        )

        first = run_persisted_generation(db, job.id, provider=provider, storage=storage, checkpointer=InMemorySaver())
        duplicate = run_persisted_generation(db, job.id, provider=provider, storage=storage, checkpointer=InMemorySaver())

        assert first["status"] == "completed"
        assert duplicate["status"] == "completed"
        assert len(provider.requests) == 1

    engine.dispose()
