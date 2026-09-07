import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from productframe_api.db import Base
from productframe_api.generation_persistence import (
    create_single_generation_run,
    mark_generation_job_generating,
    save_generation_result,
)
from productframe_api.models import GeneratedAsset, GenerationJob, Product, Workspace


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Workspace(id="workspace", name="Studio"))
        session.add(Product(id="product", workspace_id="workspace", name="Blue top", category="tops"))
        session.commit()
        yield session
    engine.dispose()


def test_create_single_run_creates_one_pending_job(db):
    run, job = create_single_generation_run(
        db,
        workspace_id="workspace",
        product_id="product",
        template_id="ecommerce-tops-front-view",
    )

    assert run.total_jobs == 1
    assert run.status == "pending"
    assert job.generation_run_id == run.id
    assert job.product_id == "product"
    assert job.status == "pending"


def test_save_result_completes_job_and_run(db):
    run, job = create_single_generation_run(
        db,
        workspace_id="workspace",
        product_id="product",
        template_id="ecommerce-tops-front-view",
    )
    mark_generation_job_generating(db, job.id)

    asset = save_generation_result(
        db,
        job_id=job.id,
        object_key="workspaces/workspace/products/product/generations/job/output.png",
        filename="output.png",
        content_type="image/png",
    )

    saved_job = db.get(GenerationJob, job.id)
    saved_run = db.get(type(run), run.id)
    assert asset.status == "ready"
    assert saved_job.status == "completed"
    assert saved_run.status == "completed"
    assert saved_run.completed_jobs == 1


def test_retry_does_not_create_duplicate_asset(db):
    _, job = create_single_generation_run(
        db,
        workspace_id="workspace",
        product_id="product",
        template_id="ecommerce-tops-front-view",
    )
    first = save_generation_result(
        db,
        job_id=job.id,
        object_key="output/one.png",
        filename="one.png",
        content_type="image/png",
    )
    second = save_generation_result(
        db,
        job_id=job.id,
        object_key="output/two.png",
        filename="two.png",
        content_type="image/png",
    )

    assert second.id == first.id
    assert db.scalars(select(GeneratedAsset)).all() == [first]


def test_wrong_template_category_is_rejected(db):
    with pytest.raises(ValueError, match="not available"):
        create_single_generation_run(
            db,
            workspace_id="workspace",
            product_id="product",
            template_id="ecommerce-tops-front-view",
            channel="lifestyle",
        )
