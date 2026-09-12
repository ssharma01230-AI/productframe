"""Exercise token-bounded grouping and the actual SDK adapter without network IO."""

import base64
import io
import json
from collections import defaultdict
from types import SimpleNamespace

import httpx
import pytest
from openai import OpenAI
from PIL import Image

from productframe_api import image_recognition as recognition
from productframe_api.analysis_limits import AnalysisBudgetError, AnalysisLimits, RateLimiter, estimate_request_tokens


def image_url(colour, size=(1024, 1536)):
    output = io.BytesIO()
    Image.new("RGB", size, colour).save(output, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode()


def grouping_oracle(monkeypatch, urls, labels, *, expected_model="gpt-4.1-mini"):
    label_for_url = dict(zip(urls, labels))
    requests = []
    limiter = RateLimiter(AnalysisLimits())
    def request_limiter(model):
        assert model == expected_model
        return limiter

    monkeypatch.setattr(recognition, "_request_limiter", request_limiter)

    def parse(client, *, model, input, text_format):
        assert model == expected_model
        tokens = estimate_request_tokens(input, text_format=text_format, model=model)
        assert tokens + 1024 <= limiter.input_budget()
        inputs = [part["image_url"] for part in input[0]["content"] if part["type"] == "input_image"]
        requests.append(inputs)
        by_product = defaultdict(list)
        for number, url in enumerate(inputs, start=1):
            by_product[label_for_url[url]].append(number)
        groups = [recognition.ProductImageGroup(
            product_number=number, image_numbers=numbers, reason="Matching visual evidence for the same product.",
        ) for number, numbers in enumerate(by_product.values(), start=1)]
        return SimpleNamespace(output_parsed=recognition.BatchScreeningResult(
            passed=True, unique_product_count=len(groups), groups=groups,
            reason="Compared every supplied representative image.",
        ))

    monkeypatch.setattr(recognition, "_parse_response", parse)
    return requests


def test_fifteen_images_merge_across_chunks_without_oversized_requests(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    labels = ["navy", "pink", "white", "green", "black"] * 3
    colours = ["navy", "pink", "white", "green", "black"]
    urls = [image_url(colours[index % 5]) for index in range(15)]
    requests = grouping_oracle(monkeypatch, urls, labels, expected_model="gpt-4o-mini")
    assert not recognition._grouping_fits(urls)

    result = recognition.group_product_images(object(), urls)

    assert result.unique_product_count == 5
    assert [group.image_numbers for group in result.groups] == [[1, 6, 11], [2, 7, 12], [3, 8, 13], [4, 9, 14], [5, 10, 15]]
    assert [group.product_number for group in result.groups] == list(range(1, 6))
    assert sorted(number for group in result.groups for number in group.image_numbers) == list(range(1, 16))
    assert all(len(inputs) <= 2 for inputs in requests)
    assert len(requests) > 8  # Both first-level chunks and a bounded representative merge ran.


def test_distinct_products_are_not_lost_when_representatives_do_not_shrink(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    urls = [image_url((index * 20, 100, 150)) for index in range(9)]
    requests = grouping_oracle(monkeypatch, urls, list(range(9)), expected_model="gpt-4o-mini")
    result = recognition.group_product_images(object(), urls)
    assert [group.image_numbers for group in result.groups] == [[number] for number in range(1, 10)]
    assert all(len(inputs) <= 2 for inputs in requests)


def test_small_group_keeps_single_comparison(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    urls = [image_url("navy", (64, 64)), image_url("pink", (64, 64))]
    requests = grouping_oracle(monkeypatch, urls, ["navy", "pink"])
    result = recognition.group_product_images(object(), urls)
    assert result.unique_product_count == 2
    assert requests == [urls]


def test_default_model_groups_fifteen_typical_images_in_one_request(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    colours = ["navy", "pink", "white", "green", "black"]
    urls = [image_url(colours[index % 5]) for index in range(15)]
    requests = grouping_oracle(monkeypatch, urls, colours * 3)

    assert recognition._grouping_fits(urls)
    result = recognition.group_product_images(object(), urls)

    assert requests == [urls]
    assert result.unique_product_count == 5
    assert [group.image_numbers for group in result.groups] == [[1, 6, 11], [2, 7, 12], [3, 8, 13], [4, 9, 14], [5, 10, 15]]
    assert sorted(number for group in result.groups for number in group.image_numbers) == list(range(1, 16))


def test_impossible_input_budget_fails_before_model_call(monkeypatch):
    limiter = RateLimiter(AnalysisLimits(max_input_tokens=1000))
    monkeypatch.setattr(recognition, "_request_limiter", lambda model: limiter)
    monkeypatch.setattr(recognition, "_parse_response", lambda *args, **kwargs: pytest.fail("oversized request was sent"))
    with pytest.raises(AnalysisBudgetError, match="grouping image"):
        recognition.group_product_images(object(), [image_url("navy")])


def test_budget_error_is_not_retried_as_invalid_grouping(monkeypatch):
    attempts = []
    def parse(*args, **kwargs):
        attempts.append(1)
        raise AnalysisBudgetError("Request exceeds token budget")
    monkeypatch.setattr(recognition, "_parse_response", parse)
    with pytest.raises(AnalysisBudgetError, match="token budget"):
        recognition._group_product_images_once(object(), [image_url("navy")])
    assert len(attempts) == 1


@pytest.mark.parametrize("with_identity", [False, True])
def test_grouping_safety_refusal_is_not_retried_or_rephrased(monkeypatch, with_identity):
    attempts = []
    refusal = recognition.AnalysisSafetyError("Image did not pass the provider safety check.")

    def parse(*args, **kwargs):
        attempts.append(kwargs)
        raise refusal

    monkeypatch.setattr(recognition, "_parse_response", parse)
    identities = [recognition.ProductIdentity(
        product_type="Cotton shirt", dominant_colour="navy blue", pattern_or_finish="plain cotton",
        visual_signature="Pointed collar and a row of visible front buttons.",
    )] if with_identity else None

    with pytest.raises(recognition.AnalysisSafetyError) as caught:
        recognition._group_product_images_once(object(), [image_url("navy")], identities)

    assert caught.value is refusal
    assert len(attempts) == 1


@pytest.mark.parametrize("configured_model,expected_model", [(None, "gpt-4.1-mini"), ("gpt-4o-mini", "gpt-4o-mini")])
def test_all_vision_stages_use_default_or_configured_model(monkeypatch, configured_model, expected_model):
    if configured_model is None:
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
    else:
        monkeypatch.setenv("OPENAI_MODEL", configured_model)
    client = object()
    calls = []
    category = recognition.ProductCategorization(category="tops", product_type="Navy cotton shirt", confidence=0.95)
    results = {
        recognition.ImageScreeningResult: recognition.ImageScreeningResult(
            passed=True, detected_item="shirt", item_count=1, primary_item_clear=True,
            reason="One clearly identifiable cotton shirt is visible.",
        ),
        recognition.ProductIdentity: recognition.ProductIdentity(
            product_type="Cotton shirt", dominant_colour="navy blue", pattern_or_finish="plain cotton",
            visual_signature="Pointed collar and a row of visible front buttons.",
        ),
        recognition.ProductCategorization: category,
        recognition.BatchScreeningResult: recognition.BatchScreeningResult(
            passed=True, unique_product_count=1,
            groups=[recognition.ProductImageGroup(product_number=1, image_numbers=[1], reason="The image contains one distinct cotton shirt.")],
            reason="One product was identified in the submitted image.",
        ),
        recognition.ProductAnalysis: recognition.ProductAnalysis(
            product_name="Navy cotton shirt", category="tops", product_type="Navy cotton shirt",
            colours="navy blue",
            colour_details=recognition.ColourDescription(
                primary_colour="Navy blue", secondary_colours=[], pattern="Solid colour",
                colour_distribution="Even across the visible garment", tonal_variation="Slight shadow variation",
                saturation="Deep", brightness="Dark", colour_finish="Matte", visible_uncertainties=[],
            ),
            materials="cotton", features=["Pointed collar", "Front buttons"],
            description="A navy blue cotton shirt with a pointed collar and visible front buttons.", confidence=0.95,
            global_details=recognition.GlobalProductDetails(
                colour=recognition.ColourDescription(
                    primary_colour="Navy blue", secondary_colours=[], pattern="Solid colour",
                    colour_distribution="Even across the visible garment", tonal_variation="Slight shadow variation",
                    saturation="Deep", brightness="Dark", colour_finish="Matte", visible_uncertainties=[],
                ),
                materials=recognition.MaterialDescription(
                    appearance="Smooth cotton fabric", weight="Medium-weight", thickness="Medium",
                    texture="Smooth", finish="Matte", stretch_or_flexibility="Not visible",
                    drape_or_rigidity="Soft drape", visible_condition="No visible damage", visible_uncertainties=[],
                ),
                construction=recognition.ConstructionDescription(
                    silhouette="Regular", shape="Straight", proportions="Regular", construction_details=["Pointed collar", "Front buttons"],
                    functional_details=[], callouts=[], visible_uncertainties=[],
                ),
                branding=recognition.BrandingDescription(graphics=[], logos=[]),
                gender=recognition.GenderDescription(assumed="not_determinable", confidence=0.1, evidence=["Gender is not visible"], basis="unclear", user_confirmed=None),
            ),
            category_details={
                "subtype": "shirt", "neckline_type": "pointed collar", "neckline_depth": "shallow",
                "collar_type": "pointed collar", "sleeve_type": "set-in", "sleeve_length": "short",
                "sleeve_width": "regular", "shoulder_shape": "natural", "cuff_details": "plain",
                "hem_shape": "straight", "fit_and_silhouette": "regular", "garment_length": "regular",
                "closure_details": ["front buttons"], "pocket_details": [], "hood_details": [],
                "visible_uncertainties": [],
            },
            tops_details=recognition.TopGarmentDetails(
                neckline_type="Pointed collar", neckline_depth="Shallow", sleeve_type="Short sleeves",
                sleeve_length="Short", sleeve_width="Regular", shoulder_shape="Natural",
                collar_or_neck_binding="Pointed collar", hem_shape="Straight",
                fit_and_silhouette="Regular fit", garment_length="Regular",
                material_appearance="Smooth cotton fabric", apparent_weight="Medium-weight",
                surface_texture="Smooth", surface_finish="Matte",
                construction_details=["Front buttons", "Side seams"], visible_uncertainties=[],
            ),
        ),
    }

    def parse(received_client, *, model, input, text_format):
        assert received_client is client
        calls.append((text_format, model))
        return SimpleNamespace(output_parsed=results[text_format])

    monkeypatch.setattr(recognition, "OpenAI", lambda **kwargs: client)
    monkeypatch.setattr(recognition, "_parse_response", parse)
    url = image_url("navy", (64, 64))
    recognition.screen_product_image(client, url)
    recognition.identify_product_image(client, url)
    recognition.categorize_product_image(client, url)
    recognition._group_product_images_once(client, [url])
    recognition.analyze_product_image(
        base64.b64decode(url.split(",", 1)[1]), api_key="test-key",
        run_safety_check=False, screen_already=True, known_categorization=category,
    )

    assert calls == [(stage, expected_model) for stage in [
        recognition.ImageScreeningResult, recognition.ProductIdentity, recognition.ProductCategorization,
        recognition.BatchScreeningResult, recognition.ProductAnalysis,
    ]]


def test_sdk_adapter_caps_output_and_admits_each_retry(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    now = [0.0]
    sleeps = []
    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds
    limiter = RateLimiter(AnalysisLimits(), clock=lambda: now[0], sleep=sleep)
    monkeypatch.setattr(recognition, "_request_limiter", lambda model: limiter)
    calls = []
    admissions = []
    acquire = limiter.acquire
    def reserve(*args, **kwargs):
        reservation = acquire(*args, **kwargs)
        admissions.append(reservation)
        return reservation
    monkeypatch.setattr(limiter, "acquire", reserve)

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert body["model"] == "gpt-4.1-mini"
        assert body["max_output_tokens"] == 4096
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "2"}, json={"error": {"message": "temporary rate limit", "type": "tokens", "code": "rate_limit_exceeded"}})
        decision = {"passed": True, "detected_item": "shirt", "item_count": 1, "primary_item_clear": True, "reason": "One clearly identifiable cotton shirt is visible."}
        return httpx.Response(200, json={
            "id": "resp_test", "object": "response", "created_at": 1, "status": "completed", "model": "gpt-4.1-mini",
            "output": [{"id": "msg_test", "type": "message", "status": "completed", "role": "assistant",
                        "content": [{"type": "output_text", "text": json.dumps(decision), "annotations": []}]}],
            "parallel_tool_calls": True, "tool_choice": "auto", "tools": [],
        })

    with OpenAI(api_key="test-not-a-real-key", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        decision = recognition.screen_product_image(client, image_url("navy", (64, 64)))
    assert decision.passed
    assert len(calls) == len(admissions) == 2
    assert sleeps == [2]
    assert all(reservation.tokens > 4096 for reservation in admissions)
