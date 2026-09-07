"""One-attempt Gemini REST transport for the existing structured analysis inputs.

Admission, retries and provider selection belong to the caller. Safety/content
blocks are deliberately distinct from availability failures and must not trigger
provider fallback. No input, response content or credentials are logged here.

REST/schema: https://ai.google.dev/api/generate-content
Thinking: https://ai.google.dev/gemini-api/docs/generate-content/thinking
Images: https://ai.google.dev/gemini-api/docs/generate-content/media-resolution
"""

from __future__ import annotations

import base64
import binascii
import io
import json
import math
import os
import re
from types import SimpleNamespace
from typing import Any

import httpx
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel


_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
_IMAGE_URL = re.compile(r"^data:(image/(?:jpeg|png|webp|heic|heif));base64,([A-Za-z0-9+/=]+)$")
_BLOCKED_FINISH_REASONS = {
    "SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII",
    "IMAGE_SAFETY", "IMAGE_PROHIBITED_CONTENT", "IMAGE_RECITATION",
}
_SCHEMA_KEYS = {
    "$id", "$defs", "$ref", "$anchor", "type", "format", "title", "description",
    "enum", "items", "prefixItems", "minItems", "maxItems", "minimum", "maximum",
    "anyOf", "oneOf", "properties", "additionalProperties", "required", "propertyOrdering",
}


class GeminiSafetyError(RuntimeError):
    """Terminal content refusal. Do not retry it through another provider."""

    retryable = False
    permanent = True
    code = "content_blocked"

    def __init__(self, *, response: httpx.Response | None = None):
        super().__init__("Gemini declined this content under its safety or content restrictions.")
        self.response = response
        self.status_code = response.status_code if response is not None else None


class GeminiAPIError(RuntimeError):
    """A sanitized transport/provider error with metadata for the caller's policy."""

    def __init__(self, *, code: str, retryable: bool, response: httpx.Response | None = None):
        self.code = code
        self.retryable = retryable
        self.permanent = not retryable
        self.response = response
        self.status_code = response.status_code if response is not None else None
        suffix = f" (HTTP {self.status_code})" if self.status_code is not None else ""
        super().__init__(f"Gemini request failed: {code}{suffix}.")


class GeminiResponseError(ValueError):
    """A successful HTTP response did not contain a complete structured result."""


def _blocked_ratings(ratings: Any) -> bool:
    return isinstance(ratings, list) and any(isinstance(rating, dict) and rating.get("blocked") is True for rating in ratings)


def _image_data(value: Any) -> tuple[str, str, bytes]:
    if isinstance(value, dict):
        value = value.get("url")
    match = _IMAGE_URL.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise ValueError("Gemini image inputs must be base64 image data URLs.")
    mime_type, encoded = match.groups()
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Gemini image input contains invalid base64.") from exc
    if not raw:
        raise ValueError("Gemini image input is empty.")
    return mime_type, encoded, raw


def _content_parts(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"text": content}]
    if not isinstance(content, list) or not content:
        raise ValueError("Gemini messages require nonempty text or image content.")
    parts = []
    for part in content:
        if not isinstance(part, dict):
            raise ValueError("Unsupported Gemini input part.")
        if part.get("type") in {"input_text", "text"} and isinstance(part.get("text"), str):
            parts.append({"text": part["text"]})
        elif part.get("type") in {"input_image", "image_url"}:
            mime_type, encoded, _ = _image_data(part.get("image_url"))
            parts.append({"inlineData": {"mimeType": mime_type, "data": encoded}})
        else:
            raise ValueError("Unsupported Gemini input part.")
    return parts


def _contents(messages: Any) -> dict[str, Any]:
    if not isinstance(messages, list) or not messages:
        raise ValueError("Gemini requires at least one input message.")
    contents = []
    system_parts = []
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("Unsupported Gemini input message.")
        role = message.get("role", "user")
        parts = _content_parts(message.get("content"))
        if role in {"system", "developer"}:
            if any("text" not in part for part in parts):
                raise ValueError("Gemini system instructions support text only.")
            system_parts.extend(parts)
        elif role in {"user", "assistant", "model"}:
            contents.append({"role": "model" if role in {"assistant", "model"} else "user", "parts": parts})
        else:
            raise ValueError("Unsupported Gemini input role.")
    if not contents:
        raise ValueError("Gemini requires a user or model input message.")
    body: dict[str, Any] = {"contents": contents}
    if system_parts:
        body["systemInstruction"] = {"parts": system_parts}
    return body


def gemini_json_schema(text_format: type[BaseModel]) -> dict[str, Any]:
    """Send the supported JSON-schema subset; validate all constraints locally."""
    def clean(schema: Any) -> Any:
        if not isinstance(schema, dict):
            return schema
        # Gemini permits only $-prefixed siblings next to a $ref.
        if "$ref" in schema:
            result = {key: value for key, value in schema.items() if key in {"$ref", "$id", "$anchor"}}
            if "$defs" in schema:
                result["$defs"] = {name: clean(child) for name, child in schema["$defs"].items()}
            return result
        result: dict[str, Any] = {}
        for key, value in schema.items():
            if key not in _SCHEMA_KEYS:
                continue
            if key in {"properties", "$defs"}:
                result[key] = {name: clean(child) for name, child in value.items()}
            elif key in {"anyOf", "oneOf", "prefixItems"}:
                result[key] = [clean(child) for child in value]
            elif key in {"items", "additionalProperties"}:
                result[key] = clean(value)
            else:
                result[key] = value
        if "const" in schema:
            result["enum"] = [schema["const"]]
        return result

    return clean(text_format.model_json_schema())


def _quota_failure(payload: Any) -> str | None:
    serialized = json.dumps(payload, ensure_ascii=True).lower()
    if re.search(r"per[ _-]?day|daily|\brpd\b", serialized):
        return "daily_quota_exhausted"

    def zero_limit(value: Any) -> bool:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = key.lower().replace("_", "")
                if normalized in {"quotavalue", "quotalimit", "quotalimitvalue", "limit", "limitvalue"} and not isinstance(item, bool) and item in (0, "0"):
                    return True
                if zero_limit(item):
                    return True
        elif isinstance(value, list):
            return any(zero_limit(item) for item in value)
        return False

    if zero_limit(payload) or re.search(r"(?:limit|quota[_ ]?value)\s*[:=]\s*0(?:\D|$)", serialized):
        return "quota_unavailable"
    return None


def _api_error(response: httpx.Response) -> GeminiAPIError | GeminiSafetyError:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    details = error.get("details", []) if isinstance(error, dict) else []
    if isinstance(error, dict) and (
        error.get("status") in _BLOCKED_FINISH_REASONS
        or isinstance(details, list) and any(
            isinstance(detail, dict) and detail.get("reason") in _BLOCKED_FINISH_REASONS for detail in details
        )
    ):
        return GeminiSafetyError(response=response)
    # Google often gives retry timing in the JSON body instead of HTTP headers.
    if "retry-after" not in response.headers and isinstance(details, list):
        for detail in details:
            if not isinstance(detail, dict) or not str(detail.get("@type", "")).endswith("google.rpc.RetryInfo"):
                continue
            delay = detail.get("retryDelay")
            if isinstance(delay, str) and re.fullmatch(r"\d+(?:\.\d+)?s", delay):
                response.headers["retry-after"] = delay[:-1]
                break
    status = response.status_code
    if status == 429 and (quota_code := _quota_failure(payload)):
        return GeminiAPIError(code=quota_code, retryable=False, response=response)
    if status in {401, 403} or (status == 400 and "API_KEY_INVALID" in json.dumps(payload)):
        return GeminiAPIError(code="authentication_error", retryable=False, response=response)
    retryable = status in {408, 409, 429} or 500 <= status <= 599
    return GeminiAPIError(code="rate_limited" if status == 429 else "provider_error", retryable=retryable, response=response)


def _thinking_config(model: str) -> dict[str, Any] | None:
    if re.fullmatch(r"gemini-2\.5-flash(?:-lite)?(?:-.*)?", model):
        return {"thinkingBudget": 0}
    if re.fullmatch(r"gemini-3(?:\.[156])?-flash(?:-lite)?(?:-.*)?", model):
        return {"thinkingLevel": "minimal"}
    if re.fullmatch(r"gemini-3\.[78]-flash(?:-.*)?", model) or model.startswith("gemini-3.1-pro"):
        return {"thinkingLevel": "low"}
    return None


class GeminiClient:
    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None, *, timeout: float = 90.0):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self._api_key:
            raise GeminiAPIError(code="missing_api_key", retryable=False)
        self._owns_client = client is None
        self._client = client if client is not None else httpx.Client(timeout=timeout, follow_redirects=False)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GeminiClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def parse(self, *, model: str, input: list, text_format: type[BaseModel], max_output_tokens: int) -> SimpleNamespace:
        model = model.removeprefix("models/")
        if not re.fullmatch(r"gemini-[a-zA-Z0-9][a-zA-Z0-9._-]*", model):
            raise ValueError("Invalid Gemini model identifier.")
        if not isinstance(max_output_tokens, int) or isinstance(max_output_tokens, bool) or max_output_tokens <= 0:
            raise ValueError("Gemini max_output_tokens must be a positive integer.")
        body = _contents(input)
        config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseJsonSchema": gemini_json_schema(text_format),
            "maxOutputTokens": max_output_tokens,
            "candidateCount": 1,
        }
        if thinking := _thinking_config(model):
            config["thinkingConfig"] = thinking
        if model.startswith("gemini-3"):
            config["mediaResolution"] = "MEDIA_RESOLUTION_HIGH"
        body["generationConfig"] = config
        try:
            response = self._client.post(
                f"{_ENDPOINT}/{model}:generateContent", json=body,
                headers={"x-goog-api-key": self._api_key, "Content-Type": "application/json"},
            )
        except httpx.TransportError as exc:
            raise GeminiAPIError(code="transport_error", retryable=True) from exc
        if not response.is_success:
            raise _api_error(response)
        try:
            payload = response.json()
        except ValueError as exc:
            raise GeminiResponseError("Gemini returned an unreadable response.") from exc
        if not isinstance(payload, dict):
            raise GeminiResponseError("Gemini returned an invalid response envelope.")
        feedback = payload.get("promptFeedback") or {}
        if isinstance(feedback, dict) and (
            feedback.get("blockReason") not in {None, "BLOCK_REASON_UNSPECIFIED"}
            or _blocked_ratings(feedback.get("safetyRatings"))
        ):
            raise GeminiSafetyError(response=response)
        candidates = payload.get("candidates") or []
        if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
            raise GeminiResponseError("Gemini returned no structured response candidate.")
        candidate = candidates[0]
        reason = candidate.get("finishReason")
        if reason in _BLOCKED_FINISH_REASONS or _blocked_ratings(candidate.get("safetyRatings")):
            raise GeminiSafetyError(response=response)
        if reason != "STOP":
            raise GeminiResponseError("Gemini did not complete its structured response.")
        content = candidate.get("content")
        if not isinstance(content, dict) or not isinstance(content.get("parts"), list):
            raise GeminiResponseError("Gemini returned invalid response content.")
        parts = content["parts"]
        if any(isinstance(part, dict) and part.get("refusal") for part in parts):
            raise GeminiSafetyError(response=response)
        text = "".join(part["text"] for part in parts if isinstance(part, dict) and isinstance(part.get("text"), str) and not part.get("thought"))
        if not text:
            raise GeminiResponseError("Gemini returned no structured response text.")
        parsed = text_format.model_validate_json(text, strict=True)
        metadata = payload.get("usageMetadata")
        if not isinstance(metadata, dict):
            metadata = {}
        usage = SimpleNamespace(
            input_tokens=metadata.get("promptTokenCount"),
            output_tokens=metadata.get("candidatesTokenCount"),
            reasoning_tokens=metadata.get("thoughtsTokenCount"),
            total_tokens=metadata.get("totalTokenCount"),
        )
        return SimpleNamespace(output_parsed=parsed, usage=usage, headers=response.headers, model=payload.get("modelVersion", model))


def estimate_gemini_input_tokens(input: list, *, text_format: type[BaseModel] | None = None, model: str | None = None) -> int:
    """Conservative local sizing, excluding base64 transport; no countTokens call.

    Gemini 3 HIGH allocates about 1120 tokens/image; reserve 1536 for headroom.
    For older image models use
    Google's 258-token crop estimate, retaining a 2304-token pan/scan floor.
    Text/schema use UTF-8 bytes as an upper estimate, plus framing headroom.
    """
    body = _contents(input)
    image_tokens = 0

    def text_only(value: Any) -> Any:
        nonlocal image_tokens
        if isinstance(value, dict):
            if "inlineData" in value:
                inline = value["inlineData"]
                _, _, raw = _image_data(f"data:{inline['mimeType']};base64,{inline['data']}")
                try:
                    with Image.open(io.BytesIO(raw)) as image:
                        width, height = image.size
                except (OSError, ValueError, UnidentifiedImageError) as exc:
                    raise ValueError("Gemini image input is unreadable.") from exc
                if model and model.removeprefix("models/").startswith("gemini-3"):
                    image_tokens += 1536
                elif width <= 384 and height <= 384:
                    image_tokens += 258
                else:
                    crop = max(1, min(768, math.floor(min(width, height) / 1.5)))
                    image_tokens += max(2304, math.ceil(width / crop) * math.ceil(height / crop) * 258)
                return {"image": True}
            return {key: text_only(item) for key, item in value.items()}
        if isinstance(value, list):
            return [text_only(item) for item in value]
        return value

    estimate = len(json.dumps(text_only(body), ensure_ascii=False).encode("utf-8")) + image_tokens + 256
    if text_format is not None:
        estimate += len(json.dumps(gemini_json_schema(text_format), ensure_ascii=False).encode("utf-8"))
    return estimate
