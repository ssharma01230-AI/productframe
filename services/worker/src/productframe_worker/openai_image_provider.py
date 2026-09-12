"""OpenAI GPT Image provider for product and template references."""
from __future__ import annotations

import base64
import binascii
import logging
import os
import time
from typing import Any

import boto3
from openai import APIConnectionError, APIResponseValidationError, APIStatusError, APITimeoutError, OpenAI

from productframe_api.config import get_settings
from productframe_api.generation_prompts import GenerationPrompt
from productframe_api.image_processing import normalize_image_orientation

from .image_provider import GeneratedImage

logger = logging.getLogger(__name__)
DEFAULT_IMAGE_MODEL = "gpt-image-2.5-flare"
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_IMAGE_REQUEST_SIZE = "1024x1024"
DEFAULT_IMAGE_QUALITY = "medium"


class OpenAIImageGenerationError(RuntimeError):
    """A safe image-provider error without request content or credentials."""

    def __init__(self, message: str, *, retryable: bool = True, request_id: str | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.request_id = request_id


def _positive_float_env(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _request_id(response: Any) -> str | None:
    return (
        getattr(response, "_request_id", None)
        or getattr(response, "request_id", None)
        or getattr(response, "id", None)
    )


def _status_error_details(exc: APIStatusError) -> tuple[str, bool, str | None]:
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    error_body = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), dict) else body
    provider_message = error_body.get("message") if isinstance(error_body, dict) else None
    code = error_body.get("code") if isinstance(error_body, dict) else getattr(exc, "code", None)
    parts = [f"OpenAI image generation failed (HTTP {status})"]
    if code:
        parts.append(f"code={code}")
    if isinstance(provider_message, str) and provider_message.strip():
        parts.append("reason=" + " ".join(provider_message.split())[:320])
    request_id = getattr(exc, "request_id", None)
    if request_id:
        parts.append(f"request_id={request_id}")
    retryable = status in {408, 409, 429} or (isinstance(status, int) and status >= 500)
    return "; ".join(parts), retryable, request_id


def _provider_error_details(exc: Exception, timeout_seconds: float) -> tuple[str, bool, str | None]:
    if isinstance(exc, APITimeoutError):
        return f"OpenAI image generation timed out after {timeout_seconds:g}s", True, None
    if isinstance(exc, APIConnectionError):
        return "OpenAI image generation could not reach the provider", True, None
    if isinstance(exc, APIStatusError):
        return _status_error_details(exc)
    if isinstance(exc, APIResponseValidationError):
        return "OpenAI returned an invalid image response", False, getattr(exc, "request_id", None)
    if isinstance(exc, (IndexError, KeyError, TypeError, ValueError, binascii.Error)):
        return "OpenAI returned no usable image data", False, None
    return f"OpenAI image generation failed ({type(exc).__name__})", True, None


class OpenAIImageGenerationProvider:
    def __init__(self, *, client: Any | None = None, object_client: Any | None = None):
        settings = get_settings()
        self.model = os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)
        self.timeout_seconds = _positive_float_env("OPENAI_IMAGE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
        self._owns_client = client is None
        self.client = client or OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            timeout=self.timeout_seconds,
            max_retries=0,
        )
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
        started_at = time.perf_counter()
        logger.info(
            "OpenAI image generation started model=%s template_id=%s references=%d timeout_seconds=%g",
            self.model, request.template_id, len(request.reference_images), self.timeout_seconds,
        )
        try:
            files = [self._reference_file(image.role, image.object_key, request.reference_rotation_degrees) for image in request.reference_images]
        except Exception as exc:
            elapsed = time.perf_counter() - started_at
            logger.error(
                "OpenAI image generation reference load failed model=%s template_id=%s elapsed_seconds=%.1f error_type=%s",
                self.model, request.template_id, elapsed, type(exc).__name__,
            )
            if isinstance(exc, OpenAIImageGenerationError):
                raise
            raise OpenAIImageGenerationError("Product reference image could not be loaded", retryable=False) from exc
        prompt = request.prompt + "\n\nNegative prompt:\n" + request.negative_prompt
        try:
            response = self.client.images.edit(
                model=self.model,
                image=files,
                prompt=prompt,
                size=DEFAULT_IMAGE_REQUEST_SIZE,
                quality=DEFAULT_IMAGE_QUALITY,
            )
            encoded = response.data[0].b64_json
            content = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            elapsed = time.perf_counter() - started_at
            message, retryable, request_id = _provider_error_details(exc, self.timeout_seconds)
            logger.error(
                "OpenAI image generation failed model=%s template_id=%s elapsed_seconds=%.1f retryable=%s request_id=%s error=%s",
                self.model, request.template_id, elapsed, retryable, request_id or "none", message,
            )
            raise OpenAIImageGenerationError(message, retryable=retryable, request_id=request_id) from exc
        if not content:
            message = "OpenAI returned an empty image"
            logger.error("OpenAI image generation failed model=%s template_id=%s error=%s", self.model, request.template_id, message)
            raise OpenAIImageGenerationError(message, retryable=False, request_id=_request_id(response))
        request_id = _request_id(response)
        logger.info(
            "OpenAI image generation completed model=%s template_id=%s elapsed_seconds=%.1f bytes=%d request_id=%s",
            self.model, request.template_id, time.perf_counter() - started_at, len(content), request_id or "none",
        )
        return GeneratedImage(
            content=content,
            content_type="image/png",
            filename=f"{request.template_id}.png",
            provider=self.model,
            request_id=request_id,
        )
