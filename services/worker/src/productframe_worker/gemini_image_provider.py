"""Gemini image-generation provider for product and template references."""
from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any

import boto3
import httpx

from productframe_api.config import get_settings
from productframe_api.generation_prompts import GenerationPrompt

from .image_provider import GeneratedImage


logger = logging.getLogger(__name__)


class GeminiImageGenerationError(RuntimeError):
    """A safe error without response bodies, prompts or credentials."""

    def __init__(self, message: str, *, retryable: bool = True, request_id: str | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.request_id = request_id


class GeminiImageGenerationProvider:
    def __init__(self, *, client: httpx.Client | None = None, object_client: Any | None = None):
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise GeminiImageGenerationError("GEMINI_API_KEY is not configured", retryable=False)
        self.model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-lite-image")
        try:
            self.timeout_seconds = float(os.environ.get("GEMINI_IMAGE_TIMEOUT_SECONDS", "300"))
        except (TypeError, ValueError):
            self.timeout_seconds = 300.0
        if self.timeout_seconds <= 0:
            self.timeout_seconds = 300.0
        settings = get_settings()
        self.bucket = settings.minio_bucket
        self.object_client = object_client or boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name="us-east-1",
        )
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=self.timeout_seconds, follow_redirects=False)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _reference_part(self, role: str, object_key: str) -> tuple[dict[str, str], dict[str, Any]]:
        stored = self.object_client.get_object(Bucket=self.bucket, Key=object_key)
        body = stored["Body"]
        try:
            raw = body.read()
        finally:
            body.close()
        if not raw:
            raise GeminiImageGenerationError(f"Reference image is empty: {role}")
        content_type = stored.get("ContentType") or "image/jpeg"
        if not content_type.startswith("image/"):
            raise GeminiImageGenerationError(f"Reference is not an image: {role}")
        return {"text": f"{role.replace('_', ' ').title()} reference:"}, {
            "inlineData": {"mimeType": content_type, "data": base64.b64encode(raw).decode("ascii")}
        }

    def generate(self, request: GenerationPrompt) -> GeneratedImage:
        started_at = time.perf_counter()
        logger.info(
            "Gemini image generation started model=%s template_id=%s references=%d",
            self.model, request.template_id, len(request.reference_images),
        )
        parts: list[dict[str, Any]] = [{"text": request.prompt + "\n\nNegative prompt:\n" + request.negative_prompt}]
        for reference in request.reference_images:
            label, image = self._reference_part(reference.role, reference.object_key)
            parts.extend([label, image])
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": request.aspect_ratio},
            },
        }
        try:
            response = self.client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                json=body,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            )
        except httpx.TimeoutException as exc:
            raise GeminiImageGenerationError(
                f"Gemini image generation timed out after {self.timeout_seconds:g}s",
                retryable=True,
            ) from exc
        except httpx.TransportError as exc:
            raise GeminiImageGenerationError("Gemini image request could not be sent", retryable=True) from exc
        request_id = response.headers.get("x-request-id") or response.headers.get("x-goog-request-id")
        if not response.is_success:
            retryable = response.status_code in {408, 409, 429} or response.status_code >= 500
            raise GeminiImageGenerationError(
                f"Gemini image request failed (HTTP {response.status_code})",
                retryable=retryable,
                request_id=request_id,
            )
        try:
            payload = response.json()
            candidates = payload.get("candidates") or []
            parts = candidates[0]["content"]["parts"]
            image_part = next(part for part in parts if isinstance(part, dict) and part.get("inlineData"))
            inline = image_part["inlineData"]
            content = base64.b64decode(inline["data"], validate=True)
            content_type = inline.get("mimeType", "image/png")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise GeminiImageGenerationError("Gemini returned no usable image", retryable=False, request_id=request_id) from exc
        if not content or not content_type.startswith("image/"):
            raise GeminiImageGenerationError("Gemini returned an invalid image", retryable=False, request_id=request_id)
        logger.info(
            "Gemini image generation completed model=%s template_id=%s elapsed_seconds=%.1f bytes=%d request_id=%s",
            self.model, request.template_id, time.perf_counter() - started_at, len(content), request_id or "none",
        )
        extension = content_type.split("/", 1)[1].split(";", 1)[0]
        return GeneratedImage(
            content=content,
            content_type=content_type,
            filename=f"{request.template_id}.{extension}",
            provider=self.model,
            request_id=request_id,
        )
