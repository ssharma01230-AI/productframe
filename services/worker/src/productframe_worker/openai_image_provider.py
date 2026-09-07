"""OpenAI GPT Image provider for product and template references."""
from __future__ import annotations

import base64
import os
from typing import Any

import boto3
from openai import OpenAI

from productframe_api.config import get_settings
from productframe_api.generation_prompts import GenerationPrompt
from productframe_api.image_processing import normalize_image_orientation

from .image_provider import GeneratedImage


class OpenAIImageGenerationError(RuntimeError):
    """A safe image-provider error without request content or credentials."""


class OpenAIImageGenerationProvider:
    def __init__(self, *, client: Any | None = None, object_client: Any | None = None):
        settings = get_settings()
        self.model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
        self._owns_client = client is None
        self.client = client or OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=120)
        self.bucket = settings.minio_bucket
        self.object_client = object_client or boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name="us-east-1",
        )

    def close(self) -> None:
        if self._owns_client and hasattr(self.client, "close"):
            self.client.close()

    def _reference_file(self, role: str, object_key: str, rotation_degrees: int = 0) -> tuple[str, bytes, str]:
        stored = self.object_client.get_object(Bucket=self.bucket, Key=object_key)
        body = stored["Body"]
        try:
            content = body.read()
        finally:
            body.close()
        content_type = stored.get("ContentType") or "image/jpeg"
        if not content or not content_type.startswith("image/"):
            raise OpenAIImageGenerationError(f"Invalid {role} reference image")
        try:
            normalized = normalize_image_orientation(content, rotation_degrees=rotation_degrees)
        except ValueError as exc:
            raise OpenAIImageGenerationError(f"Invalid {role} reference image") from exc
        suffix = "png" if normalized.content_type == "image/png" else "jpg"
        return f"{role}.{suffix}", normalized.content, normalized.content_type

    def generate(self, request: GenerationPrompt) -> GeneratedImage:
        files = [self._reference_file(image.role, image.object_key, request.reference_rotation_degrees) for image in request.reference_images]
        prompt = request.prompt + "\n\nNegative prompt:\n" + request.negative_prompt
        try:
            response = self.client.images.edit(
                model=self.model,
                image=files,
                prompt=prompt,
                size="1024x1024",
                quality="high",
            )
            encoded = response.data[0].b64_json
            content = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise OpenAIImageGenerationError("OpenAI image generation failed") from exc
        if not content:
            raise OpenAIImageGenerationError("OpenAI returned an empty image")
        return GeneratedImage(
            content=content,
            content_type="image/png",
            filename=f"{request.template_id}.png",
            provider=self.model,
            request_id=getattr(response, "id", None),
        )
