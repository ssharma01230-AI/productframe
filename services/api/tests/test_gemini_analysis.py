import base64
import io
import json
from enum import StrEnum

import httpx
import pytest
from PIL import Image, PngImagePlugin
from pydantic import BaseModel, Field, RootModel, ValidationError

from productframe_api.gemini_analysis import (
    GeminiAPIError,
    GeminiClient,
    GeminiResponseError,
    GeminiSafetyError,
    estimate_gemini_input_tokens,
    gemini_json_schema,
)


class Category(StrEnum):
    SHIRT = "shirt"
    SHOE = "shoe"


class Product(BaseModel):
    name: str = Field(min_length=3, max_length=40)
    category: Category
    confidence: float = Field(ge=0, le=1)


class Result(BaseModel):
    passed: bool
    products: list[Product] = Field(min_length=1)


def png_url(width=32, height=32, padding=""):
    buffer = io.BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("padding", padding)
    Image.new("RGB", (width, height)).save(buffer, format="PNG", pnginfo=metadata)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def response_payload(value=None, *, reason="STOP", parts=None):
    value = value if value is not None else {"passed": True, "products": [{"name": "White shirt", "category": "shirt", "confidence": 0.95}]}
    return {
        "candidates": [{"finishReason": reason, "content": {"parts": parts if parts is not None else [{"text": json.dumps(value)}]}}],
        "usageMetadata": {"promptTokenCount": 1128, "candidatesTokenCount": 50, "thoughtsTokenCount": 2, "totalTokenCount": 1180},
        "modelVersion": "gemini-3.6-flash",
    }


def run_parse(handler, *, model="gemini-3.6-flash", input=None):
    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        client = GeminiClient(api_key="test-gemini-key", client=transport)
        return client.parse(model=model, input=input or [{"role": "user", "content": "Describe the product"}], text_format=Result, max_output_tokens=4096)


def test_one_request_maps_images_schema_roles_and_returns_validated_result():
    calls = []
    image = png_url()

    def handle(request):
        calls.append(request)
        assert str(request.url) == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"
        assert request.headers["x-goog-api-key"] == "test-gemini-key"
        assert "test-gemini-key" not in str(request.url)
        body = json.loads(request.content)
        assert body["systemInstruction"] == {"parts": [{"text": "Use visible evidence only."}]}
        assert body["contents"][0] == {"role": "model", "parts": [{"text": "Previous answer"}]}
        assert body["contents"][1]["parts"] == [
            {"text": "Describe it"},
            {"inlineData": {"mimeType": "image/png", "data": image.split(",", 1)[1]}},
        ]
        config = body["generationConfig"]
        assert config["thinkingConfig"] == {"thinkingLevel": "minimal"}
        assert config["mediaResolution"] == "MEDIA_RESOLUTION_HIGH"
        assert config["maxOutputTokens"] == 4096
        assert config["responseMimeType"] == "application/json"
        assert config["responseJsonSchema"]["$defs"]["Category"]["enum"] == ["shirt", "shoe"]
        assert "safetySettings" not in body
        return httpx.Response(200, json=response_payload(), headers={"x-request-id": "test-request"})

    result = run_parse(handle, input=[
        {"role": "developer", "content": "Use visible evidence only."},
        {"role": "assistant", "content": [{"type": "input_text", "text": "Previous answer"}]},
        {"role": "user", "content": [{"type": "input_text", "text": "Describe it"}, {"type": "input_image", "image_url": image}]},
    ])
    assert len(calls) == 1
    assert isinstance(result.output_parsed, Result)
    assert result.output_parsed.products[0].category is Category.SHIRT
    assert result.usage.input_tokens == 1128
    assert result.usage.output_tokens == 50
    assert result.usage.reasoning_tokens == 2
    assert result.usage.total_tokens == 1180
    assert result.headers["x-request-id"] == "test-request"


@pytest.mark.parametrize("model,thinking", [
    ("gemini-2.5-flash", {"thinkingBudget": 0}),
    ("models/gemini-2.5-flash-lite", {"thinkingBudget": 0}),
    ("gemini-3.6-flash", {"thinkingLevel": "minimal"}),
    ("gemini-3.7-flash", {"thinkingLevel": "low"}),
    ("gemini-3.8-flash", {"thinkingLevel": "low"}),
    ("gemini-3.1-pro-preview", {"thinkingLevel": "low"}),
])
def test_model_specific_thinking_controls(model, thinking):
    def handle(request):
        assert json.loads(request.content)["generationConfig"]["thinkingConfig"] == thinking
        return httpx.Response(200, json=response_payload())
    run_parse(handle, model=model)


def test_schema_drops_unsupported_keywords_but_keeps_nested_constraints():
    schema = gemini_json_schema(Result)
    name = schema["$defs"]["Product"]["properties"]["name"]
    assert "minLength" not in name and "maxLength" not in name
    assert schema["$defs"]["Product"]["properties"]["confidence"]["minimum"] == 0
    assert schema["properties"]["products"]["minItems"] == 1
    assert "minLength" in Product.model_json_schema()["properties"]["name"]


def test_root_reference_retains_its_definitions():
    class ProductRoot(RootModel[Product]):
        pass

    schema = gemini_json_schema(ProductRoot)
    assert schema["$ref"] == "#/$defs/Product"
    assert schema["$defs"]["Product"]["properties"]["category"]["$ref"] == "#/$defs/Category"
    assert "Category" in schema["$defs"]


@pytest.mark.parametrize("bad", [
    {"passed": "true", "products": [{"name": "White shirt", "category": "shirt", "confidence": 0.9}]},
    {"passed": True, "products": [{"name": "x", "category": "shirt", "confidence": 0.9}]},
    {"passed": True, "products": [{"name": "White shirt", "category": "unknown", "confidence": 0.9}]},
    {"passed": True, "products": [{"name": "White shirt", "category": "shirt", "confidence": 2.0}]},
    {"passed": True, "products": []},
])
def test_response_is_strictly_validated_without_coercion(bad):
    with pytest.raises(ValidationError):
        run_parse(lambda request: httpx.Response(200, json=response_payload(bad)))


@pytest.mark.parametrize("payload", [
    {"promptFeedback": {"blockReason": "SAFETY"}},
    {"promptFeedback": {"blockReason": "OTHER"}},
    {"promptFeedback": {"safetyRatings": [{"blocked": True}]}},
    response_payload(reason="SAFETY"),
    response_payload(reason="RECITATION"),
    response_payload(reason="BLOCKLIST"),
    response_payload(reason="PROHIBITED_CONTENT"),
    response_payload(reason="SPII"),
    {"candidates": [{"finishReason": "STOP", "safetyRatings": [{"blocked": True}]}]},
    response_payload(parts=[{"refusal": "Cannot answer this content."}]),
])
def test_safety_and_content_blocks_are_terminal_distinct_errors(payload):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=payload)
    with pytest.raises(GeminiSafetyError) as failure:
        run_parse(handle)
    assert not isinstance(failure.value, GeminiAPIError)
    assert not isinstance(failure.value, ValueError)
    assert failure.value.permanent and not failure.value.retryable
    assert len(calls) == 1


def test_explicit_http_content_refusal_is_not_an_availability_error():
    payload = {"error": {"status": "INVALID_ARGUMENT", "details": [{"reason": "PROHIBITED_CONTENT"}]}}
    with pytest.raises(GeminiSafetyError):
        run_parse(lambda request: httpx.Response(400, json=payload))


@pytest.mark.parametrize("payload", [
    {}, [], {"candidates": [{}]}, response_payload(reason="MAX_TOKENS"),
    response_payload(parts=[]), {"candidates": [{"finishReason": "STOP", "content": []}]},
])
def test_incomplete_envelopes_do_not_become_successful_results(payload):
    with pytest.raises(GeminiResponseError):
        run_parse(lambda request: httpx.Response(200, json=payload))


def test_thought_parts_are_excluded_from_structured_json():
    body = response_payload()
    body["candidates"][0]["content"]["parts"].insert(0, {"thought": True, "text": "Intermediate reasoning"})
    assert run_parse(lambda request: httpx.Response(200, json=body)).output_parsed.passed is True


@pytest.mark.parametrize("status,payload,code,retryable", [
    (429, {"error": {"message": "Quota exceeded for metric, limit: 0"}}, "quota_unavailable", False),
    (429, {"error": {"details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel"}]}]}}, "daily_quota_exhausted", False),
    (429, {"error": {"details": [{"violations": [{"quotaValue": "0"}]}]}}, "quota_unavailable", False),
    (429, {"error": {"message": "Requests per minute exceeded"}}, "rate_limited", True),
    (401, {"error": {"message": "secret-key-must-not-leak"}}, "authentication_error", False),
    (403, {"error": {"message": "Permission denied"}}, "authentication_error", False),
    (400, {"error": {"details": [{"reason": "API_KEY_INVALID"}]}}, "authentication_error", False),
    (400, {"error": {"message": "Invalid parameter"}}, "provider_error", False),
    (404, {"error": {"message": "Model not available"}}, "provider_error", False),
    (503, {"error": {"message": "Unavailable"}}, "provider_error", True),
])
def test_http_error_classification_is_safe_and_never_retries(status, payload, code, retryable):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(status, json=payload)
    with pytest.raises(GeminiAPIError) as failure:
        run_parse(handle)
    error = failure.value
    assert (error.status_code, error.code, error.retryable, error.permanent) == (status, code, retryable, not retryable)
    assert error.response is not None
    assert "secret-key-must-not-leak" not in str(error)
    assert "test-gemini-key" not in str(error)
    assert len(calls) == 1


def test_retry_info_is_exposed_as_header_for_caller():
    body = {"error": {"details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "12.5s"}]}}
    with pytest.raises(GeminiAPIError) as failure:
        run_parse(lambda request: httpx.Response(429, json=body))
    assert failure.value.response.headers["retry-after"] == "12.5"


def test_transport_failure_is_retryable_without_internal_retry():
    calls = []
    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout("Timed out", request=request)
    with pytest.raises(GeminiAPIError) as failure:
        run_parse(handle)
    assert failure.value.retryable is True
    assert failure.value.status_code is None
    assert len(calls) == 1


def test_missing_key_fails_without_creating_transport(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(GeminiAPIError, match="missing_api_key"):
        GeminiClient()


@pytest.mark.parametrize("image", ["https://example.test/private.jpg", "data:image/png;base64,bad", "data:text/plain;base64,YQ=="])
def test_unsupported_images_never_make_a_network_request(image):
    def handle(request):
        pytest.fail("Invalid image must fail before transport")
    with pytest.raises(ValueError):
        run_parse(handle, input=[{"role": "user", "content": [{"type": "input_image", "image_url": image}]}])


def test_estimate_ignores_base64_padding_and_reserves_gemini3_high_image_budget():
    inputs = lambda image: [{"role": "user", "content": [{"type": "input_image", "image_url": image}]}]
    short, padded = png_url(), png_url(padding="x" * 100000)
    estimate = estimate_gemini_input_tokens(inputs(short), model="gemini-3.6-flash")
    assert estimate == estimate_gemini_input_tokens(inputs(padded), model="gemini-3.6-flash")
    assert 1536 < estimate < 2000
    assert estimate_gemini_input_tokens(inputs(short), model="gemini-3.6-flash", text_format=Result) > estimate
    doubled = inputs(short) + inputs(short)
    assert estimate_gemini_input_tokens(doubled, model="gemini-3.6-flash") >= 2 * 1536


def test_legacy_image_estimate_respects_crop_dimensions():
    inputs = lambda image: [{"role": "user", "content": [{"type": "input_image", "image_url": image}]}]
    small = estimate_gemini_input_tokens(inputs(png_url()), model="gemini-2.5-flash")
    large = estimate_gemini_input_tokens(inputs(png_url(2048, 2048)), model="gemini-2.5-flash")
    assert 258 < small < 800
    assert large > small + 2000
