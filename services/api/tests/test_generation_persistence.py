import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from productframe_api.db import Base
from productframe_api.generation_persistence import (
    claim_generation_job,
    create_generation_run,
    create_single_generation_run,
    mark_generation_job_failed,
    recalculate_generation_run,
    reschedule_generation_job,
    mark_generation_job_generating,
    save_generation_result,
)
from productframe_api.models import GeneratedAsset, GenerationJob, GenerationRun, Product, SourceAsset, Workspace


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Workspace(id="workspace", name="Studio"))
        session.add(Product(id="product", workspace_id="workspace", name="Blue top", category="tops"))
        session.add(Product(id="outerwear", workspace_id="workspace", name="Coat", category="outerwear"))
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


def test_create_run_creates_multiple_ordered_jobs_and_deduplicates_selections(db):
    run, jobs = create_generation_run(
        db,
        workspace_id="workspace",
        selections=[
            {"product_id": "product", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
            {"product_id": "outerwear", "template_id": "ecommerce-outerwear-front-medium", "channel": "ecommerce"},
            {"product_id": "product", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
        ],
    )
    assert run.total_jobs == 2
    assert [job.product_id for job in jobs] == ["product", "outerwear"]
    assert [job.template_id for job in jobs] == ["ecommerce-tops-front-view", "ecommerce-outerwear-front-medium"]
    assert len({job.graph_thread_id for job in jobs}) == 2


def test_multiple_selection_validation_is_atomic(db):
    with pytest.raises(ValueError, match="Product not found"):
        create_generation_run(
            db,
            workspace_id="workspace",
            selections=[
                {"product_id": "product", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
                {"product_id": "missing", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
            ],
        )
    assert db.query(GenerationRun).count() == 0
    assert db.query(GenerationJob).count() == 0


def test_repeated_multi_generation_request_reuses_same_run_and_jobs(db):
    selections = [
        {"product_id": "product", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
        {"product_id": "outerwear", "template_id": "ecommerce-outerwear-front-medium", "channel": "ecommerce"},
    ]
    first_run, first_jobs = create_generation_run(db, workspace_id="workspace", selections=selections, idempotency_key="request-key-multi")
    second_run, second_jobs = create_generation_run(db, workspace_id="workspace", selections=selections, idempotency_key="request-key-multi")
    assert second_run.id == first_run.id
    assert [(job.product_id, job.template_id) for job in second_jobs] == [(job.product_id, job.template_id) for job in first_jobs]
    assert db.query(GenerationRun).count() == 1
    assert db.query(GenerationJob).count() == 2


def test_repeated_generation_request_reuses_the_same_run_and_job(db):
    first_run, first_job = create_single_generation_run(
        db,
        workspace_id="workspace",
        product_id="product",
        template_id="ecommerce-tops-front-view",
        idempotency_key="request-key-123",
    )
    second_run, second_job = create_single_generation_run(
        db,
        workspace_id="workspace",
        product_id="product",
        template_id="ecommerce-tops-front-view",
        idempotency_key="request-key-123",
    )
    assert second_run.id == first_run.id
    assert second_job.id == first_job.id


def test_evidence_is_required_for_api_generation_requests(db):
    with pytest.raises(ValueError, match="source assets"):
        create_single_generation_run(
            db,
            workspace_id="workspace",
            product_id="product",
            template_id="ecommerce-tops-front-view",
            enforce_evidence=True,
        )

    db.add(SourceAsset(
        id="front-source",
        product_id="product",
        object_key="products/product/front.jpg",
        filename="front.jpg",
        content_type="image/jpeg",
        media_evidence={"views": ["front_view"], "evidence": []},
    ))
    db.commit()
    run, job = create_single_generation_run(
        db,
        workspace_id="workspace",
        product_id="product",
        template_id="ecommerce-tops-front-view",
        enforce_evidence=True,
    )
    assert run.total_jobs == 1
    assert job.template_id == "ecommerce-tops-front-view"


def test_run_status_is_derived_for_partial_success_and_failure(db):
    run, jobs = create_generation_run(
        db,
        workspace_id="workspace",
        selections=[
            {"product_id": "product", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
            {"product_id": "outerwear", "template_id": "ecommerce-outerwear-front-medium", "channel": "ecommerce"},
        ],
    )
    claim_generation_job(db, jobs[0].id)
    claim_generation_job(db, jobs[1].id)
    mark_generation_job_failed(db, job_id=jobs[1].id, error_message="provider failed")
    assert run.status == "running"
    # A generated job is represented by completion, independently of its sibling.
    db.get(GenerationJob, jobs[0].id).status = "completed"
    recalculate_generation_run(db, run.id)
    db.commit()
    assert run.status == "partially_failed"
    assert run.completed_jobs == 1
    assert run.failed_jobs == 1


def test_run_failure_accounting_is_idempotent_and_retry_reopens_run(db):
    run, jobs = create_generation_run(
        db,
        workspace_id="workspace",
        selections=[{"product_id": "product", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"}],
    )
    claim_generation_job(db, jobs[0].id)
    mark_generation_job_failed(db, job_id=jobs[0].id, error_message="provider failed")
    mark_generation_job_failed(db, job_id=jobs[0].id, error_message="duplicate delivery")
    assert run.failed_jobs == 1
    reschedule_generation_job(db, jobs[0].id, "retrying")
    assert run.status == "pending"
    assert run.failed_jobs == 0


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


def test_duplicate_generation_delivery_only_claims_one_attempt(db):
    _, job = create_single_generation_run(
        db,
        workspace_id="workspace",
        product_id="product",
        template_id="ecommerce-tops-front-view",
    )

    first, first_claimed = claim_generation_job(db, job.id)
    second, second_claimed = claim_generation_job(db, job.id)

    assert first_claimed is True
    assert second_claimed is False
    assert first.attempt_count == 1
    assert second.attempt_count == 1
    assert second.status == "generating"


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


def test_small_generation_runs_always_use_openai():
    from productframe_api.generation_persistence import planned_image_provider

    for total_jobs in (1, 2, 9):
        assert planned_image_provider(total_jobs=total_jobs, job_index=0) == "openai"
        assert planned_image_provider(total_jobs=total_jobs, job_index=8) == "openai"


def test_large_generation_runs_split_between_providers():
    from productframe_api.generation_persistence import planned_image_provider

    assert [planned_image_provider(total_jobs=10, job_index=index) for index in range(4)] == [
        "openai", "gemini", "openai", "gemini",
    ]
