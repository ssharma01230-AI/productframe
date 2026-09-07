from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from productframe_api import main
from productframe_api.db import Base, get_db
from productframe_api.models import Product, SourceAsset, User, Workspace, WorkspaceMembership


@pytest.fixture
def multi_api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    signer = Mock()
    signer.generate_presigned_url.side_effect = lambda operation, Params, ExpiresIn: f"https://assets.test/{Params['Key']}"
    monkeypatch.setattr(main.boto3, "client", Mock(return_value=signer))
    redis = Mock()
    redis_factory = Mock()
    redis_factory.from_url.return_value = redis
    monkeypatch.setattr(main, "SyncRedis", redis_factory)
    with Session(engine) as db:
        db.add_all([
            User(id="user", clerk_user_id="clerk-user"),
            Workspace(id="workspace", name="Studio"),
            WorkspaceMembership(user_id="user", workspace_id="workspace"),
            Product(id="top", workspace_id="workspace", name="Blue top", category="tops"),
            Product(id="socks", workspace_id="workspace", name="Striped socks", category="socks"),
            SourceAsset(id="top-source", product_id="top", object_key="top/source.jpg", filename="source.jpg", content_type="image/jpeg", media_evidence={"views": ["front_view"]}),
            SourceAsset(id="sock-source", product_id="socks", object_key="socks/source.jpg", filename="source.jpg", content_type="image/jpeg", media_evidence={"views": ["flat_lay"]}),
        ])
        db.commit()

        def database():
            yield db

        previous = main.app.dependency_overrides.copy()
        main.app.dependency_overrides[get_db] = database
        main.app.dependency_overrides[main.current_user] = lambda: {"sub": "clerk-user"}
        try:
            with TestClient(main.app) as client:
                yield client, db, redis
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(previous)
    engine.dispose()


def test_multi_selection_creation_queues_ordered_jobs_and_is_idempotent(multi_api):
    client, db, redis = multi_api
    payload = {
        "selections": [
            {"product_id": "top", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
            {"product_id": "socks", "template_id": "ecommerce-socks-flat-lay", "channel": "ecommerce"},
        ],
        "idempotency_key": "multi-api-request-1",
    }
    first = client.post("/generation-runs", json=payload)
    second = client.post("/generation-runs", json=payload)
    assert first.status_code == second.status_code == 200
    first_payload, second_payload = first.json(), second.json()
    assert second_payload["run_id"] == first_payload["run_id"]
    assert first_payload["total_jobs"] == 2
    assert len(first_payload["jobs"]) == 2
    assert first_payload["jobs"][0]["id"] != first_payload["jobs"][1]["id"]
    assert redis.xadd.call_count == 4
    assert db.query(Product).count() == 2

    snapshot = client.get(f"/generation-runs/{first_payload['run_id']}")
    assert snapshot.status_code == 200
    jobs = snapshot.json()["jobs"]
    assert [job["product"]["id"] for job in jobs] == ["top", "socks"]
    assert snapshot.json()["counts"]["in_progress"] == 2


def test_multi_selection_validation_is_atomic(multi_api):
    client, db, redis = multi_api
    response = client.post("/generation-runs", json={
        "selections": [
            {"product_id": "top", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
            {"product_id": "missing", "template_id": "ecommerce-tops-front-view", "channel": "ecommerce"},
        ],
        "idempotency_key": "multi-api-invalid-1",
    })
    assert response.status_code == 400
    assert db.query(main.GenerationRun).count() == 0
    assert db.query(main.GenerationJob).count() == 0
    assert redis.xadd.call_count == 0
