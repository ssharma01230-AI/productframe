"""Storage adapters for generated images."""
from typing import Protocol

import boto3

from productframe_api.config import get_settings

from .image_provider import GeneratedImage


class GeneratedImageStorage(Protocol):
    def put(self, object_key: str, image: GeneratedImage) -> None:
        """Store one generated image at the given object key."""
        ...

    def get(self, object_key: str) -> GeneratedImage:
        """Retrieve an image previously stored outside the graph checkpoint."""
        ...

    def presign(self, object_key: str, expires: int = 900) -> str:
        """Create a short-lived URL for a stored image."""
        ...


class MinioGeneratedImageStorage:
    def __init__(self, client=None) -> None:
        settings = get_settings()
        self.bucket = settings.minio_bucket
        self.client = client or boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name="us-east-1",
        )

    def put(self, object_key: str, image: GeneratedImage) -> None:
        self.client.put_object(Bucket=self.bucket, Key=object_key, Body=image.content, ContentType=image.content_type)

    def get(self, object_key: str) -> GeneratedImage:
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        body = response["Body"]
        try:
            content = body.read()
        finally:
            body.close()
        return GeneratedImage(content=content, content_type=response.get("ContentType", "image/png"), filename=object_key.rsplit("/", 1)[-1], provider="stored")

    def presign(self, object_key: str, expires: int = 900) -> str:
        return self.client.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": object_key}, ExpiresIn=expires)


class FakeGeneratedImageStorage:
    """In-memory storage for persistence tests."""

    def __init__(self) -> None:
        self.objects: dict[str, GeneratedImage] = {}

    def put(self, object_key: str, image: GeneratedImage) -> None:
        self.objects[object_key] = image

    def get(self, object_key: str) -> GeneratedImage:
        return self.objects[object_key]

    def presign(self, object_key: str, expires: int = 900) -> str:
        return f"memory://{object_key}"
