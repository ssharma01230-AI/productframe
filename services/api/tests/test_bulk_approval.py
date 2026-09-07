"""Review API transactions against an isolated database; no service or AI calls."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from productframe_api import main
from productframe_api.db import Base, get_db
from productframe_api.models import (
    AnalysisJob,
    AnalysisJobImage,
    Product,
    ProductAnalysisRecord,
    SourceAsset,
    User,
    Workspace,
    WorkspaceMembership,
)


@pytest.fixture
def review():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            User(id="user", clerk_user_id="clerk-user"),
            Workspace(id="workspace", name="Studio"),
            Workspace(id="foreign-workspace", name="Other studio"),
        ])
        db.flush()
        db.add_all([
            WorkspaceMembership(user_id="user", workspace_id="workspace"),
            AnalysisJob(id="job", workspace_id="workspace", status="awaiting_confirmation"),
            AnalysisJob(id="foreign-job", workspace_id="foreign-workspace", status="awaiting_confirmation"),
            Product(id="staging", workspace_id="workspace", name="Unconfirmed product upload"),
            Product(id="approved-product", workspace_id="workspace", name="Saved shirt", category="tops"),
            Product(id="foreign-product", workspace_id="foreign-workspace", name="Private product"),
        ])
        db.flush()
        for number, status in [(1, "suggested"), (2, "suggested"), (3, "approved"), (4, "rejected"), (5, "cancelled"), (6, "pending")]:
            db.add(ProductAnalysisRecord(
                id=f"record-{number}", job_id="job", product_number=number,
                product_name=f"Original product {number}", category="tops", product_type="shirt",
                colours="blue", materials="cotton", features=["collar"],
                description=f"Original description {number}", confidence=0.9,
                confirmation_status=status,
                final_product_id="approved-product" if number == 3 else None,
            ))
            db.add(SourceAsset(
                id=f"source-{number}", product_id="approved-product" if number == 3 else "staging",
                filename=f"image-{number}.jpg", content_type="image/jpeg", object_key=f"staging/image-{number}.jpg",
            ))
        db.add_all([
            ProductAnalysisRecord(
                id="foreign-record", job_id="foreign-job", product_number=1,
                product_name="Private suggestion", category="tops", product_type="shirt",
                colours="white", materials="cotton", features=["pocket"],
                description="Private suggestion description", confidence=0.8,
            ),
            SourceAsset(id="rejected-image", product_id="staging", filename="rejected.jpg", content_type="image/jpeg", object_key="staging/rejected.jpg"),
        ])
        db.flush()
        for number in range(1, 7):
            db.add(AnalysisJobImage(
                job_id="job", image_number=number, source_asset_id=f"source-{number}",
                product_number=number, passed=True, status="analysed",
            ))
        db.add(AnalysisJobImage(job_id="job", image_number=7, source_asset_id="rejected-image", product_number=1, passed=False, status="rejected"))
        db.commit()

        def database():
            yield db

        previous_overrides = main.app.dependency_overrides.copy()
        main.app.dependency_overrides[get_db] = database
        main.app.dependency_overrides[main.current_user] = lambda: {"sub": "clerk-user"}
        try:
            with TestClient(main.app, raise_server_exceptions=False) as client:
                yield client, db
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(previous_overrides)
    engine.dispose()


def draft(number, **changes):
    return {
        "product_number": number, "product_name": f"Edited product {number}", "product_type": "Edited shirt",
        "colours": "navy", "materials": "linen", "features": ["button cuffs", "pocket"],
        "description": f"Edited description {number}", **changes,
    }


def approve(client, *drafts, job_id="job"):
    return client.post(f"/analysis-jobs/{job_id}/products/approve-all", json={"products": list(drafts)})


def assert_original_pending(db):
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Product)) == 3
    for number in (1, 2):
        record = db.get(ProductAnalysisRecord, f"record-{number}")
        assert record.confirmation_status == "suggested"
        assert record.product_name == f"Original product {number}"
        assert record.final_product_id is None
        assert db.get(SourceAsset, f"source-{number}").product_id == "staging"


def test_batch_saves_edited_pending_fields_and_moves_only_accepted_sources(review):
    client, db = review
    response = approve(client, draft(2), draft(1, product_name="  Reviewed shirt  ", features=[" collar "]), draft(6))

    assert response.status_code == 200
    results = response.json()["products"]
    assert [row["product_number"] for row in results] == [2, 1, 6]
    assert len({row["final_product_id"] for row in results}) == 3
    assert all(row["status"] == row["confirmation_status"] == "approved" for row in results)
    for row in results:
        number = row["product_number"]
        record = db.get(ProductAnalysisRecord, f"record-{number}")
        product = db.get(Product, row["final_product_id"])
        assert row == {
            "id": record.id, "product_number": number, "product_name": record.product_name,
            "category": "tops", "product_type": "Edited shirt", "colours": "navy",
            "materials": "linen", "features": record.features, "description": f"Edited description {number}",
            "confidence": 0.9, "status": "approved", "confirmation_status": "approved", "final_product_id": product.id,
        }
        assert product.name == record.product_name
        assert product.category == "tops"
        assert product.product_type == "Edited shirt"
        assert product.colours == "navy"
        assert product.materials == "linen"
        assert product.features == record.features
        assert product.description == f"Edited description {number}"
        asset = db.get(SourceAsset, f"source-{number}")
        assert asset.product_id == product.id
        assert asset.object_key == f"staging/image-{number}.jpg"
    assert results[1]["product_name"] == "Reviewed shirt"
    assert results[1]["features"] == ["collar"]
    assert db.get(SourceAsset, "rejected-image").product_id == "staging"
    assert db.get(ProductAnalysisRecord, "record-3").confirmation_status == "approved"


def test_batch_preserves_decided_records_and_returns_canonical_metadata(review):
    client, db = review
    response = approve(client, *(draft(number, product_name="Stale unsaved edit") for number in (1, 3, 4, 5)))

    assert response.status_code == 200
    results = {row["product_number"]: row for row in response.json()["products"]}
    for number, status in [(3, "approved"), (4, "rejected"), (5, "cancelled")]:
        row = results[number]
        assert row["status"] == row["confirmation_status"] == status
        assert row["product_name"] == f"Original product {number}"
        assert row["description"] == f"Original description {number}"
        assert row["features"] == ["collar"]
        assert row["final_product_id"] == ("approved-product" if number == 3 else None)
        assert db.get(SourceAsset, f"source-{number}").product_id == ("approved-product" if number == 3 else "staging")
    assert db.get(Product, "approved-product").name == "Saved shirt"
    assert db.scalar(select(func.count()).select_from(Product)) == 4
    assert db.get(ProductAnalysisRecord, "record-2").confirmation_status == "suggested"


def test_batch_retry_does_not_duplicate_products_or_overwrite_first_approval(review):
    client, db = review
    first = approve(client, draft(1), draft(2))
    retry = approve(client, draft(1, product_name="New stale value"), draft(2))

    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    assert db.scalar(select(func.count()).select_from(Product)) == 5


@pytest.mark.parametrize("changes", [
    {"product_name": " \t "}, {"product_type": " "}, {"colours": " "}, {"materials": " "},
    {"description": " "}, {"features": [" "]}, {"features": []}, {"features": ["x"] * 31},
    {"product_name": "x" * 161}, {"product_type": "x" * 161}, {"colours": "x" * 301},
    {"materials": "x" * 301}, {"description": "x" * 321}, {"product_number": 0}, {"product_number": True},
])
def test_invalid_second_draft_cannot_partially_approve_first(review, changes):
    client, db = review
    response = approve(client, draft(1), draft(2, **changes))
    assert response.status_code == 422
    assert_original_pending(db)


@pytest.mark.parametrize("products", [[], [draft(1), draft(1)], [draft(number) for number in range(1, 52)]])
def test_invalid_batch_shape_is_rejected_before_mutation(review, products):
    client, db = review
    assert approve(client, *products).status_code == 422
    assert_original_pending(db)


def test_all_requested_records_must_exist_before_any_approval(review):
    client, db = review
    response = approve(client, draft(1), draft(99))
    assert response.status_code == 404
    assert_original_pending(db)


def test_failure_after_first_product_flush_rolls_back_entire_batch(review):
    client, db = review
    flushed_names = []

    def fail_on_second_product(session, flush_context, instances):
        for item in session.new:
            if isinstance(item, Product):
                flushed_names.append(item.name)
                if item.name == "Edited product 2":
                    raise RuntimeError("Injected database failure after first product was flushed")

    event.listen(db, "before_flush", fail_on_second_product)
    try:
        response = approve(client, draft(1), draft(2))
    finally:
        event.remove(db, "before_flush", fail_on_second_product)
    assert response.status_code == 500
    assert flushed_names == ["Edited product 1", "Edited product 2"]
    assert_original_pending(db)
    assert approve(client, draft(1), draft(2)).status_code == 200


@pytest.mark.parametrize("job_id", ["foreign-job", "missing-job"])
def test_batch_respects_workspace_scope(review, job_id):
    client, db = review
    assert approve(client, draft(1), job_id=job_id).status_code == 404
    assert_original_pending(db)
    assert db.get(ProductAnalysisRecord, "foreign-record").confirmation_status == "suggested"


def test_batch_requires_authentication(review):
    client, db = review
    del main.app.dependency_overrides[main.current_user]
    assert approve(client, draft(1)).status_code == 401
    assert_original_pending(db)


@pytest.mark.parametrize("status", ["pending", "screening", "analysing", "failed"])
def test_unfinished_or_failed_job_cannot_be_bulk_approved(review, status):
    client, db = review
    db.get(AnalysisJob, "job").status = status
    db.commit()
    assert approve(client, draft(1)).status_code == 409
    assert_original_pending(db)


def test_completed_job_can_be_bulk_approved(review):
    client, db = review
    db.get(AnalysisJob, "job").status = "completed"
    db.commit()
    assert approve(client, draft(1)).status_code == 200


def test_single_approval_can_edit_an_approved_product_without_changing_category(review):
    client, db = review
    before = db.scalar(select(func.count()).select_from(Product))
    response = client.patch("/analysis-jobs/job/products/3", json={
        **draft(3, product_name="  Updated approved shirt  ", category="shoes"), "status": "approved",
    })
    assert response.status_code == 200
    assert response.json() == {"status": "approved", "product_number": "3"}
    product = db.get(Product, "approved-product")
    assert product.name == "Updated approved shirt"
    assert product.category == "tops"
    assert db.scalar(select(func.count()).select_from(Product)) == before
    assert db.get(ProductAnalysisRecord, "record-3").final_product_id == "approved-product"


def test_single_and_bulk_mutations_request_same_postgres_job_lock_before_reading_records(review):
    # SQLite exercises transaction rollback above; compile the actual statements
    # for PostgreSQL to check that both API paths request its row lock.
    client, db = review
    statements = []

    def capture_statement(state):
        if state.is_select:
            statements.append(str(state.statement.compile(dialect=postgresql.dialect())))

    event.listen(db, "do_orm_execute", capture_statement)
    try:
        assert approve(client, draft(1)).status_code == 200
        first_statements = statements[:]
        statements.clear()
        assert client.patch("/analysis-jobs/job/products/2", json={**draft(2), "status": "approved"}).status_code == 200
        second_statements = statements[:]
    finally:
        event.remove(db, "do_orm_execute", capture_statement)

    for path_statements in (first_statements, second_statements):
        lock_index = next(index for index, sql in enumerate(path_statements) if "FROM analysis_jobs " in sql and "FOR UPDATE" in sql)
        first_record_index = next(index for index, sql in enumerate(path_statements) if "FROM product_analysis_records " in sql)
        assert "analysis_jobs.workspace_id =" in path_statements[lock_index]
        assert lock_index < first_record_index
