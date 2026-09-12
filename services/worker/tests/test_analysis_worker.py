from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image

from productframe_api.models import (
    AnalysisImageStatus,
    AnalysisJob,
    AnalysisJobImage,
    AnalysisJobStatus,
    ProductAnalysisRecord,
    SourceAsset,
)
from productframe_worker import worker


def test_source_image_orientation_is_normalized_for_preview():
    source = BytesIO()
    image = Image.new("RGB", (40, 80), "red")
    exif = Image.Exif()
    exif[274] = 6
    image.save(source, format="JPEG", exif=exif)
    asset = SimpleNamespace(object_key="source.jpg", content_type="image/jpeg")
    storage = Mock()
    storage.get_object.return_value = {"Body": BytesIO(source.getvalue())}

    normalized_bytes = worker._read_upright_source_image(storage, "bucket", asset)

    storage.put_object.assert_called_once()
    persisted = storage.put_object.call_args.kwargs["Body"]
    assert persisted == normalized_bytes
    assert asset.content_type == "image/jpeg"
    with Image.open(BytesIO(persisted)) as normalized:
        assert normalized.size == (80, 40)
        assert normalized.getexif().get(274) is None


def test_missing_middle_source_preserves_original_image_associations(monkeypatch):
    job = SimpleNamespace(id="job", total_images=4, status=AnalysisJobStatus.PENDING.value)
    images = {
        number: SimpleNamespace(
            image_number=number,
            source_asset_id=f"source-{number}",
            status=AnalysisImageStatus.PENDING.value,
            passed=None,
            rejection_reason=None,
            product_number=None,
        )
        for number in range(1, 5)
    }
    sources = {
        f"source-{number}": SimpleNamespace(object_key=f"image-{number}.jpg")
        for number in (1, 3, 4)
    }
    db = Mock()

    def get_record(model, record_id):
        if model is AnalysisJob:
            return job if record_id == job.id else None
        assert model is SourceAsset
        return sources.get(record_id)

    def get_image(query):
        if query.column_descriptions[0]["entity"].__name__ == "ImageAnalysisCache":
            return None
        assert query.column_descriptions[0]["entity"] is AnalysisJobImage
        parameters = query.compile().params
        assert parameters["job_id_1"] == job.id
        return images.get(parameters["image_number_1"])

    db.get.side_effect = get_record
    def get_records(query):
        result = Mock()
        entity = query.column_descriptions[0]["entity"]
        result.all.return_value = [] if entity is ProductAnalysisRecord else list(images.values())
        return result

    db.scalars.side_effect = get_records
    db.scalar.side_effect = get_image
    storage = Mock()
    storage.get_object.side_effect = lambda Bucket, Key: {"Body": BytesIO(Key.encode())}
    monkeypatch.setattr(worker.boto3, "client", Mock(return_value=storage))
    monkeypatch.setattr(worker, "SessionLocal", Mock(side_effect=AssertionError("A real database session must not be opened")))
    monkeypatch.setattr(worker, "get_settings", lambda: SimpleNamespace(
        minio_endpoint="https://storage.test", minio_access_key="test", minio_secret_key="test", minio_bucket="test",
    ))
    analysis = SimpleNamespace(
        product_name="Cotton shirt", category=SimpleNamespace(value="tops"), product_type="shirt",
        colours="white", materials="cotton", features=["collar"], description="A white cotton shirt", confidence=0.9,
    )

    def analyze(image_bytes, progress_callback, cached_stage_results=None, stage_result_callback=None, cached_stage_state=None, stage_state_callback=None):
        assert image_bytes == [b"image-1.jpg", b"image-3.jpg", b"image-4.jpg"]
        progress_callback("screening", "Screening images", 3, 3, 40)
        return SimpleNamespace(
            unique_product_count=1,
            products=[SimpleNamespace(product_number=1, image_numbers=[1, 2], analysis=analysis)],
            rejected_images=[SimpleNamespace(image_number=3, reason="No identifiable product.")],
            reason="One product was identified.",
        )

    monkeypatch.setattr(worker, "analyze_product_images", analyze)
    worker.process_job(job.id, db=db)

    assert images[2].status == AnalysisImageStatus.REJECTED.value
    assert images[2].passed is False
    assert images[2].rejection_reason == "Source image record was not found."
    assert images[2].product_number is None
    for number in (1, 3):
        assert images[number].status == AnalysisImageStatus.ANALYSED.value
        assert images[number].passed is True
        assert images[number].product_number == 1
    assert images[4].status == AnalysisImageStatus.REJECTED.value
    assert images[4].passed is False
    assert images[4].rejection_reason == "No identifiable product."
    assert images[4].product_number is None
    assert job.status == AnalysisJobStatus.AWAITING_CONFIRMATION.value
    assert job.processed_images == 4
    assert job.progress_completed == 4
    assert job.progress_percent == 100
    db.add.assert_called_once()
    assert db.add.call_args.args[0].product_name == "Cotton shirt"
    db.rollback.assert_not_called()
    db.close.assert_not_called()
