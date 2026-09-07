from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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
def library(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    signer = Mock()
    signer.generate_presigned_url.side_effect = lambda operation, Params, ExpiresIn: f"https://assets.test/{Params['Key']}"
    monkeypatch.setattr(main.boto3, "client", Mock(return_value=signer))
    with Session(engine) as db:
        db.add_all([
            User(id="user", clerk_user_id="clerk-user"),
            Workspace(id="workspace", name="Studio"),
            Workspace(id="other-workspace", name="Other studio"),
        ])
        db.flush()
        db.add(WorkspaceMembership(user_id="user", workspace_id="workspace"))
        db.add_all([
            Product(id="shirt", workspace_id="workspace", name="Cotton shirt", category="apparel"),
            Product(id="empty", workspace_id="workspace", name="Empty folder"),
            Product(id="declined", workspace_id="workspace", name="Declined product"),
            Product(id="staging", workspace_id="workspace", name="Unconfirmed product upload"),
            Product(id="foreign", workspace_id="other-workspace", name="Other product"),
            AnalysisJob(id="job", workspace_id="workspace"),
        ])
        db.flush()
        db.add_all([
            SourceAsset(id="front", product_id="shirt", filename="front.jpg", content_type="image/jpeg", object_key="shirt/front.jpg", created_at=datetime(2026, 9, 1, tzinfo=timezone.utc)),
            SourceAsset(id="back", product_id="shirt", filename="back.png", content_type="image/png", object_key="shirt/back.png", created_at=datetime(2026, 9, 2, tzinfo=timezone.utc)),
            SourceAsset(id="foreign-source", product_id="foreign", filename="private.jpg", content_type="image/jpeg", object_key="foreign/private.jpg"),
        ])
        for product_number, product_id, status in [(1, "shirt", "approved"), (2, "declined", "rejected")]:
            db.add(ProductAnalysisRecord(
                job_id="job", product_number=product_number, final_product_id=product_id,
                confirmation_status=status, category="apparel", product_type="shirt",
                colours="white", materials="cotton", features=["collar"], description="Cotton shirt", confidence=0.9,
            ))
        db.commit()

        def database():
            yield db

        previous_overrides = main.app.dependency_overrides.copy()
        main.app.dependency_overrides[get_db] = database
        main.app.dependency_overrides[main.current_user] = lambda: {"sub": "clerk-user"}
        try:
            with TestClient(main.app) as client:
                yield client, db, signer
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(previous_overrides)
    engine.dispose()


def test_library_summaries_keep_approval_scope_and_real_asset_counts(library):
    client, _, _ = library
    response = client.get("/products")
    assert response.status_code == 200
    products = {product["id"]: product for product in response.json()}
    assert set(products) == {"shirt", "empty"}
    shirt = products["shirt"]
    assert shirt["name"] == "Cotton shirt"
    assert shirt["category"] == "apparel"
    assert shirt["created_at"]
    assert shirt["image_url"] == "https://assets.test/shirt/back.png"
    assert shirt["upload_count"] == 2
    assert shirt["generated_count"] == 0
    assert [preview["id"] for preview in shirt["preview_images"]] == ["back", "front"]
    assert shirt["preview_images"][0]["image_url"] == shirt["image_url"]
    assert products["empty"]["image_url"] is None
    assert products["empty"]["upload_count"] == 0


def test_folder_contains_only_its_source_uploads_with_signed_urls(library):
    client, _, signer = library
    response = client.get("/products/shirt")
    assert response.status_code == 200
    product = response.json()
    assert product["id"] == "shirt"
    assert product["category"] == "apparel"
    assert product["generated_assets"] == []
    assert [upload["id"] for upload in product["uploads"]] == ["back", "front"]
    assert product["uploads"][0] == {
        "id": "back", "filename": "back.png", "content_type": "image/png",
        "created_at": "2026-09-02T00:00:00", "image_url": "https://assets.test/shirt/back.png",
    }
    assert all(call.kwargs["ExpiresIn"] == 900 for call in signer.generate_presigned_url.call_args_list)


@pytest.mark.parametrize("product_id", ["foreign", "missing", "staging", "declined"])
def test_unavailable_folder_does_not_leak_assets(library, product_id):
    client, _, signer = library
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}
    signer.generate_presigned_url.assert_not_called()


def test_empty_folder_has_no_fabricated_uploads_or_generations(library):
    client, _, _ = library
    product = client.get("/products/empty").json()
    assert product["category"] is None
    assert product["uploads"] == []
    assert product["generated_assets"] == []


def test_library_reads_require_authentication(library):
    client, _, signer = library
    del main.app.dependency_overrides[main.current_user]
    assert client.get("/products").status_code == 401
    assert client.get("/products/shirt").status_code == 401
    assert client.get("/products/shirt/download").status_code == 401
    signer.generate_presigned_url.assert_not_called()


def test_approval_moves_only_accepted_product_uploads_into_folder(library):
    client, db, _ = library
    db.add_all([
        SourceAsset(id="accepted", product_id="staging", filename="accepted.jpg", content_type="image/jpeg", object_key="staging/accepted.jpg"),
        SourceAsset(id="rejected", product_id="staging", filename="rejected.jpg", content_type="image/jpeg", object_key="staging/rejected.jpg"),
        ProductAnalysisRecord(job_id="job", product_number=3, category="apparel", product_type="shirt", colours="blue", materials="cotton", features=["pocket"], description="Blue shirt", confidence=0.9),
    ])
    db.flush()
    db.add_all([
        AnalysisJobImage(job_id="job", image_number=1, source_asset_id="accepted", product_number=3, passed=True),
        AnalysisJobImage(job_id="job", image_number=2, source_asset_id="rejected", product_number=3, passed=False),
    ])
    db.commit()
    response = client.patch("/analysis-jobs/job/products/3", json={
        "status": "approved", "product_name": "Blue shirt", "product_type": "shirt",
        "colours": "blue", "materials": "cotton", "features": ["pocket"], "description": "Blue shirt",
    })
    assert response.status_code == 200
    product = next(product for product in client.get("/products").json() if product["name"] == "Blue shirt")
    assert product["upload_count"] == 1
    folder = client.get(f"/products/{product['id']}").json()
    assert [upload["id"] for upload in folder["uploads"]] == ["accepted"]
    assert db.get(SourceAsset, "rejected").product_id == "staging"


def approved_product_decision(status="cancelled"):
    return {
        "status": status, "product_name": "Cotton shirt", "product_type": "shirt",
        "colours": "white", "materials": "cotton", "features": ["collar"], "description": "Cotton shirt",
    }


def test_cancel_approved_product_hides_library_access_but_preserves_uploads_and_history(library):
    client, db, storage = library
    db.add_all([
        AnalysisJobImage(job_id="job", image_number=1, source_asset_id="front", product_number=1, passed=True, status="analysed"),
        AnalysisJobImage(job_id="job", image_number=2, source_asset_id="back", product_number=1, passed=True, status="analysed"),
    ])
    db.commit()
    assert "shirt" in {item["id"] for item in client.get("/products").json()}
    assert client.get("/products/shirt").status_code == 200

    for _ in range(2):
        storage.reset_mock()
        response = client.patch("/analysis-jobs/job/products/1", json=approved_product_decision())
        assert response.status_code == 200
        assert response.json() == {"status": "cancelled", "product_number": "1"}
        # Read again from the database after the request commits, rather than
        # trusting the request's response or an existing ORM identity.
        db.expire_all()
        record = db.scalar(select(ProductAnalysisRecord).where(ProductAnalysisRecord.job_id == "job", ProductAnalysisRecord.product_number == 1))
        assert record.confirmation_status == "cancelled"
        assert record.final_product_id == "shirt"
        assert db.get(Product, "shirt").name == "Cotton shirt"
        assert [(asset.id, asset.object_key) for asset in db.scalars(select(SourceAsset).where(SourceAsset.product_id == "shirt").order_by(SourceAsset.id))] == [
            ("back", "shirt/back.png"), ("front", "shirt/front.jpg"),
        ]
        assert [image.source_asset_id for image in db.scalars(select(AnalysisJobImage).where(AnalysisJobImage.job_id == "job").order_by(AnalysisJobImage.image_number))] == ["front", "back"]

        assert {item["id"] for item in client.get("/products").json()} == {"empty"}
        assert client.get("/products/shirt").status_code == 404
        assert client.get("/products/shirt/download").status_code == 404
        storage.delete_object.assert_not_called()
        storage.get_object.assert_not_called()
        storage.generate_presigned_url.assert_not_called()

    results = client.get("/analysis-jobs/job/results").json()
    cancelled = next(item for item in results["products"] if item["product_number"] == 1)
    assert cancelled["confirmation_status"] == "cancelled"
    assert cancelled["final_product_id"] == "shirt"
    assert {item["filename"] for item in results["images"]} == {"front.jpg", "back.png"}


def test_approve_all_cannot_restore_a_previously_approved_then_cancelled_product(library):
    client, db, storage = library
    db.get(AnalysisJob, "job").status = "awaiting_confirmation"
    db.commit()
    assert client.patch("/analysis-jobs/job/products/1", json=approved_product_decision()).status_code == 200
    stale_draft = approved_product_decision("approved")
    del stale_draft["status"]
    response = client.post("/analysis-jobs/job/products/approve-all", json={
        "products": [{**stale_draft, "product_number": 1, "product_name": "Stale pending draft"}],
    })

    assert response.status_code == 200
    result = response.json()["products"][0]
    assert result["status"] == result["confirmation_status"] == "cancelled"
    assert result["product_name"] == "Cotton shirt"
    assert result["final_product_id"] == "shirt"
    db.expire_all()
    assert db.get(Product, "shirt").name == "Cotton shirt"
    assert db.get(SourceAsset, "front").product_id == "shirt"
    assert db.get(SourceAsset, "back").product_id == "shirt"
    assert {item["id"] for item in client.get("/products").json()} == {"empty"}
    assert client.get("/products/shirt").status_code == 404
    assert client.get("/products/shirt/download").status_code == 404
    storage.delete_object.assert_not_called()


def test_cancellation_cannot_mutate_another_workspaces_approved_product(library):
    client, db, storage = library
    db.add(AnalysisJob(id="foreign-job", workspace_id="other-workspace", status="awaiting_confirmation"))
    db.flush()
    db.add(ProductAnalysisRecord(
        id="foreign-analysis", job_id="foreign-job", product_number=1, final_product_id="foreign",
        confirmation_status="approved", category="apparel", product_name="Private shirt", product_type="shirt",
        colours="white", materials="cotton", features=["collar"], description="Private shirt", confidence=0.9,
    ))
    db.commit()

    response = client.patch("/analysis-jobs/foreign-job/products/1", json=approved_product_decision())
    assert response.status_code == 404
    db.expire_all()
    record = db.get(ProductAnalysisRecord, "foreign-analysis")
    assert record.confirmation_status == "approved"
    assert record.product_name == "Private shirt"
    assert record.final_product_id == "foreign"
    assert db.get(SourceAsset, "foreign-source").product_id == "foreign"
    storage.delete_object.assert_not_called()


def test_cancellation_requires_authentication(library):
    client, db, _ = library
    del main.app.dependency_overrides[main.current_user]
    assert client.patch("/analysis-jobs/job/products/1", json=approved_product_decision()).status_code == 401
    db.expire_all()
    record = db.scalar(select(ProductAnalysisRecord).where(ProductAnalysisRecord.job_id == "job", ProductAnalysisRecord.product_number == 1))
    assert record.confirmation_status == "approved"
    assert record.final_product_id == "shirt"


def test_folder_preview_uses_at_most_four_distinct_uploads(library):
    client, db, _ = library
    for number in range(5):
        db.add(SourceAsset(id=f"extra-{number}", product_id="shirt", filename=f"extra-{number}.jpg", content_type="image/jpeg", object_key=f"shirt/extra-{number}.jpg"))
    db.commit()
    product = next(product for product in client.get("/products").json() if product["id"] == "shirt")
    assert product["upload_count"] == 7
    assert len(product["preview_images"]) == 4
    assert len({preview["id"] for preview in product["preview_images"]}) == 4


def test_download_contains_actual_upload_bytes_with_safe_unique_names(library):
    client, db, storage = library
    db.get(SourceAsset, "front").filename = "../../photo.jpg"
    db.get(SourceAsset, "back").filename = "C:\\folder\\photo.jpg"
    db.commit()
    storage.get_object.side_effect = lambda Bucket, Key: {"Body": BytesIO(Key.encode())}
    response = client.get("/products/shirt/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == 'attachment; filename="Cotton-shirt-uploads.zip"'
    assert response.headers["cache-control"] == "private, no-store"
    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.namelist() == ["photo.jpg", "photo (2).jpg"]
        assert archive.read("photo.jpg") == b"shirt/front.jpg"
        assert archive.read("photo (2).jpg") == b"shirt/back.png"
    assert {call.kwargs["Key"] for call in storage.get_object.call_args_list} == {"shirt/front.jpg", "shirt/back.png"}


@pytest.mark.parametrize("product_id,expected_status", [("foreign", 404), ("missing", 404), ("staging", 404), ("declined", 404), ("empty", 409)])
def test_download_rejects_unavailable_or_empty_folder(library, product_id, expected_status):
    client, _, storage = library
    assert client.get(f"/products/{product_id}/download").status_code == expected_status
    storage.get_object.assert_not_called()


def test_storage_failure_does_not_return_an_incomplete_archive(library):
    client, _, storage = library
    storage.get_object.side_effect = ClientError({"Error": {"Code": "NoSuchKey", "Message": "Missing"}}, "GetObject")
    response = client.get("/products/shirt/download")
    assert response.status_code == 502
    assert response.json()["detail"] == "Could not retrieve product uploads. Please try again."
