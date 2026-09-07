from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
import pytest

from productframe_api.db import Base
from productframe_api.generation_persistence import create_single_generation_run
from productframe_api.models import GeneratedAsset, GenerationJob, Product, SourceAsset, Workspace
from productframe_worker.generation_graph import resume_persisted_generation, run_persisted_generation
from productframe_worker.generation_storage import FakeGeneratedImageStorage
from productframe_worker.image_provider import FakeImageGenerationProvider
from productframe_worker.fidelity_validator import ProductFidelityError


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

        review = run_persisted_generation(db, job.id, provider=provider, storage=storage, checkpointer=InMemorySaver())
        assert review["__interrupt__"]
        result = resume_persisted_generation(db, job.id, approved=True)

        saved_job = db.get(GenerationJob, job.id)
        asset = db.query(GeneratedAsset).one()
        assert result["status"] == "completed"
        assert saved_job.status == "completed"
        assert "Blue top" in saved_job.prompt
        assert asset.product_id == "product"
        assert asset.generation_job_id == job.id
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
