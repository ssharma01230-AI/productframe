from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from productframe_api import main
from productframe_api.db import Base, get_db
from productframe_api.generation_persistence import create_single_generation_run, save_generation_result
from productframe_api.models import Product, SourceAsset, User, Workspace, WorkspaceMembership


@pytest.fixture
def generation_api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    signer = Mock()
    signer.generate_presigned_url.side_effect = lambda operation, Params, ExpiresIn: f"https://assets.test/{Params['Key']}"
    monkeypatch.setattr(main.boto3, "client", Mock(return_value=signer))
    redis = Mock()
    monkeypatch.setattr(main, "SyncRedis", Mock(return_value=redis))
    with Session(engine) as db:
        db.add_all([
            User(id="user", clerk_user_id="clerk-user"),
            Workspace(id="workspace", name="Studio"),
            Product(id="product", workspace_id="workspace", name="Blue top", category="tops"),
            Product(id="socks", workspace_id="workspace", name="Striped socks", category="socks"),
        ])
        db.flush()
        db.add_all([
            WorkspaceMembership(user_id="user", workspace_id="workspace"),
            SourceAsset(
                id="source", product_id="product", object_key="products/product/source.jpg",
                filename="source.jpg", content_type="image/jpeg",
                media_evidence={"views": ["front_view"], "evidence": []},
            ),
            SourceAsset(
                id="sock-source", product_id="socks", object_key="products/socks/source.jpg",
                filename="source.jpg", content_type="image/jpeg",
                media_evidence={"views": ["flat_lay"], "evidence": []},
            ),
        ])
        db.commit()
        run, job = create_single_generation_run(
            db,
            workspace_id="workspace",
            product_id="product",
            template_id="ecommerce-tops-front-view",
        )
        job.preview_object_key = "workspaces/workspace/products/product/generations/job/preview/output.png"
        asset = save_generation_result(
            db,
            job_id=job.id,
            object_key=job.preview_object_key,
            filename="output.png",
            content_type="image/png",
        )

        def database():
            yield db

        previous = main.app.dependency_overrides.copy()
        main.app.dependency_overrides[get_db] = database
        main.app.dependency_overrides[main.current_user] = lambda: {"sub": "clerk-user"}
        try:
            with TestClient(main.app) as client:
                yield client, db, run, job, asset, redis
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(previous)
    engine.dispose()


def test_run_snapshot_returns_stable_card_and_review_counts(generation_api):
    client, _, run, job, _, _ = generation_api
    response = client.get(f"/generation-runs/{run.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"] == {
        "products": 1,
        "in_progress": 0,
        "ready": 1,
        "reviewed": 0,
        "approved": 0,
        "rejected": 0,
        "failed": 0,
    }
    assert payload["jobs"][0]["id"] == job.id
    assert payload["jobs"][0]["template_name"] == "Front View"
    assert payload["jobs"][0]["product"]["name"] == "Blue top"
    assert payload["jobs"][0]["preview_url"].endswith("/preview/output.png")
    assert payload["jobs"][0]["asset"]["status"] == "ready"


def test_approval_is_synchronous_idempotent_and_visible_in_library(generation_api):
    client, db, _, job, asset, _ = generation_api

    first = client.put(f"/generation-jobs/{job.id}/decision", json={"decision": "approved"})
    second = client.put(f"/generation-jobs/{job.id}/decision", json={"decision": "approved"})

    assert first.status_code == second.status_code == 200
    assert first.json()["decision"] == second.json()["decision"] == "approved"
    db.expire_all()
    assert db.get(type(job), job.id).review_decision == "approved"
    assert db.get(type(job), job.id).reviewed_at is not None
    assert db.get(type(asset), asset.id).status == "approved"
    assert client.get("/products").json()[0]["generated_count"] == 1
    assert client.get("/products/product").json()["generated_assets"][0]["status"] == "approved"

    conflict = client.put(f"/generation-jobs/{job.id}/decision", json={"decision": "rejected"})
    assert conflict.status_code == 409


def test_rejected_generation_is_kept_but_hidden_from_product_library(generation_api):
    client, db, run, job, asset, _ = generation_api
    response = client.put(f"/generation-jobs/{job.id}/decision", json={"decision": "rejected"})

    assert response.status_code == 200
    db.expire_all()
    assert db.get(type(asset), asset.id).status == "rejected"
    assert client.get("/products").json()[0]["generated_count"] == 0
    assert client.get("/products/product").json()["generated_assets"] == []
    counts = client.get(f"/generation-runs/{run.id}").json()["counts"]
    assert counts["reviewed"] == counts["rejected"] == 1
    assert counts["approved"] == 0


def test_legacy_cancelled_preview_is_treated_as_an_idempotent_rejection(generation_api):
    client, db, run, job, asset, _ = generation_api
    db.delete(asset)
    job.status = "cancelled"
    job.review_decision = None
    db.commit()

    snapshot = client.get(f"/generation-runs/{run.id}").json()
    assert snapshot["counts"]["ready"] == 1
    assert snapshot["counts"]["reviewed"] == 1
    assert snapshot["counts"]["rejected"] == 1
    assert snapshot["jobs"][0]["review_decision"] == "rejected"

    repeated = client.put(f"/generation-jobs/{job.id}/decision", json={"decision": "rejected"})
    assert repeated.status_code == 200
    db.expire_all()
    assert db.get(type(job), job.id).review_decision == "rejected"
