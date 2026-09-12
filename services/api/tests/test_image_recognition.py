"""Regression coverage for independent image gates and batch ordering.

All model boundaries are replaced, so these tests neither call OpenAI nor need
an API key. Events exercise concurrent work without depending on sleeps.
"""

import base64
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock, get_ident
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from productframe_api import image_recognition as recognition


def image_key(data_url):
    return base64.b64decode(data_url.split(",", 1)[1]).decode()


def screening(*, passed=True, item_count=1, primary_item_clear=True, supporting_clothing_is_styling=False):
    return recognition.ImageScreeningResult(
        passed=passed,
        item_count=item_count,
        primary_item_clear=primary_item_clear,
        supporting_clothing_is_styling=supporting_clothing_is_styling,
        reason="A single cotton shirt is clearly visible." if passed else "The image does not contain a fashion product.",
    )


def test_screening_schema_distinguishes_styling_from_submitted_products():
    result = recognition.ImageScreeningResult(
        passed=True, item_count=1, primary_item_clear=True,
        supporting_clothing_is_styling=True,
        reason="A shirt is the clear subject and the trousers are supporting styling.",
    )

    assert result.supporting_clothing_is_styling is True


def identity(key):
    return recognition.ProductIdentity(
        product_type=f"{key} cotton shirt",
        dominant_colour="navy blue",
        pattern_or_finish="plain cotton",
        visual_signature=f"The {key} shirt has a pointed collar and front buttons.",
    )


def categorization(key):
    return recognition.ProductCategorization(
        category=recognition.ProductCategory.TOPS,
        product_type=f"{key} cotton shirt",
        confidence=0.95,
    )


def analysis(key):
    return recognition.ProductAnalysis(
        product_name=f"{key} cotton shirt",
        category=recognition.ProductCategory.TOPS,
        product_type=f"{key} cotton shirt",
        colours="navy blue",
        colour_details=recognition.ColourDescription(
            primary_colour="Navy blue", secondary_colours=[], pattern="Solid colour",
            colour_distribution="Even across the visible garment", tonal_variation="Slight shadow variation",
            saturation="Deep", brightness="Dark", colour_finish="Matte", visible_uncertainties=[],
        ),
        materials="cotton",
        features=["Pointed collar", "Front buttons"],
        description="A navy blue cotton shirt with a pointed collar and visible front buttons.",
        confidence=0.95,
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
    )


@pytest.fixture
def pipeline(monkeypatch):
    """Provide successful stage defaults, while recording observable boundaries."""
    calls = defaultdict(list)
    lock = Lock()
    client = object()
    openai = Mock(return_value=client)
    monkeypatch.setattr(recognition, "OpenAI", openai)

    def record(key, stage):
        with lock:
            calls[key].append(stage)

    def prescreen(data):
        if data == b"invalid":
            raise ValueError("The upload is not a readable image.")
        return recognition.PrescreenedImage(
            image_bytes=data, content_type="image/jpeg", width=64, height=64, original_format="JPEG",
        )

    def moderate(received_client, data_url):
        assert received_client is client
        record(image_key(data_url), "moderation")
        return SimpleNamespace(results=[SimpleNamespace(flagged=False)])

    def screen(received_client, data_url):
        assert received_client is client
        record(image_key(data_url), "screening")
        return screening()

    def identify(received_client, data_url):
        assert received_client is client
        key = image_key(data_url)
        record(key, "identity")
        return identity(key)

    def categorize(received_client, data_url):
        assert received_client is client
        key = image_key(data_url)
        record(key, "category")
        return categorization(key)

    def group(received_client, data_urls, identities=None, categories=None):
        assert received_client is client
        keys = [image_key(url) for url in data_urls]
        return recognition.BatchScreeningResult(
            passed=True,
            unique_product_count=len(keys),
            groups=[recognition.ProductImageGroup(
                product_number=index, image_numbers=[index], reason=f"The {key} shirt is a separate product.",
            ) for index, key in enumerate(keys, start=1)],
            reason="Each accepted image represents a separate product.",
        )

    synthesis_calls = []

    def synthesize(data, **kwargs):
        synthesis_calls.append((data, kwargs, get_ident()))
        return analysis(data.decode())

    monkeypatch.setattr(recognition, "prescreen_image", prescreen)
    monkeypatch.setattr(recognition, "_moderate_image", moderate)
    monkeypatch.setattr(recognition, "screen_product_image", screen)
    monkeypatch.setattr(recognition, "identify_product_image", identify)
    monkeypatch.setattr(recognition, "categorize_product_image", categorize)
    monkeypatch.setattr(recognition, "group_product_images", group)
    monkeypatch.setattr(recognition, "analyze_product_image", synthesize)
    return SimpleNamespace(
        calls=calls, record=record, moderate=moderate, screen=screen,
        identify=identify, categorize=categorize, group=group,
        synthesize=synthesize, synthesis_calls=synthesis_calls, openai=openai,
    )


@pytest.mark.parametrize("explicit_limit,expected_limit", [(None, 3), (2, 2)])
def test_image_pipelines_overlap_within_concurrency_limit(monkeypatch, pipeline, explicit_limit, expected_limit):
    # Hold each first wave at moderation until every permitted slot is in use.
    # A serial pipeline cannot cross the barrier; exceeding the limit fails the
    # active-work assertion before any model stage completes.
    first_wave = Barrier(expected_limit)
    lock = Lock()
    active = 0
    peak = 0
    worker_threads = set()
    coordinator = get_ident()

    def moderate(client, data_url):
        nonlocal active, peak
        key = image_key(data_url)
        with lock:
            active += 1
            peak = max(peak, active)
            worker_threads.add(get_ident())
            assert active <= expected_limit
        if int(key.split("-")[1]) < expected_limit:
            first_wave.wait(timeout=5)
        return pipeline.moderate(client, data_url)

    def categorize(client, data_url):
        nonlocal active
        result = pipeline.categorize(client, data_url)
        with lock:
            active -= 1
        return result

    monkeypatch.setattr(recognition, "_moderate_image", moderate)
    monkeypatch.setattr(recognition, "categorize_product_image", categorize)
    kwargs = {} if explicit_limit is None else {"max_concurrency": explicit_limit}
    result = recognition.analyze_product_images([f"shirt-{n}".encode() for n in range(7)], **kwargs)

    assert result.unique_product_count == 7
    assert peak == expected_limit
    assert active == 0
    assert coordinator not in worker_threads
    assert len(worker_threads) == expected_limit
    synthesis_threads = {thread for _, _, thread in pipeline.synthesis_calls}
    assert coordinator not in synthesis_threads
    assert 1 <= len(synthesis_threads) <= expected_limit


def test_out_of_order_completion_preserves_upload_mapping_and_reports_rejections(monkeypatch, pipeline):
    second_done, third_done = Event(), Event()
    completion_order = []
    grouping_inputs = []
    progress = []
    coordinator = get_ident()

    def moderate(client, data_url):
        response = pipeline.moderate(client, data_url)
        response.results[0].flagged = image_key(data_url) == "flagged"
        return response

    def screen(client, data_url):
        pipeline.screen(client, data_url)
        return screening(passed=image_key(data_url) != "unrelated")

    def identify(client, data_url):
        key = image_key(data_url)
        if key == "first":
            assert second_done.wait(timeout=5), "Second image never completed independently"
        elif key == "second":
            assert third_done.wait(timeout=5), "Third image never completed independently"
        return pipeline.identify(client, data_url)

    def categorize(client, data_url):
        result = pipeline.categorize(client, data_url)
        key = image_key(data_url)
        completion_order.append(key)
        if key == "third":
            third_done.set()
        elif key == "second":
            second_done.set()
        return result

    def group(client, data_urls, identities, categories):
        grouping_inputs.append((
            [image_key(url) for url in data_urls],
            [item.visual_signature for item in identities],
            [item.product_type for item in categories],
        ))
        return recognition.BatchScreeningResult(
            passed=True, unique_product_count=2,
            groups=[
                recognition.ProductImageGroup(product_number=1, image_numbers=[1, 3], reason="First and third images show the same shirt."),
                recognition.ProductImageGroup(product_number=2, image_numbers=[2], reason="Second image shows a different shirt."),
            ],
            reason="The accepted images show two different shirts.",
        )

    monkeypatch.setattr(recognition, "_moderate_image", moderate)
    monkeypatch.setattr(recognition, "screen_product_image", screen)
    monkeypatch.setattr(recognition, "identify_product_image", identify)
    monkeypatch.setattr(recognition, "categorize_product_image", categorize)
    monkeypatch.setattr(recognition, "group_product_images", group)
    result = recognition.analyze_product_images(
        [b"invalid", b"first", b"flagged", b"second", b"unrelated", b"third"],
        max_concurrency=3,
        progress_callback=lambda *args: progress.append((get_ident(), args)),
    )

    assert set(completion_order) == {"first", "second", "third"}
    assert len(completion_order) == 3
    assert grouping_inputs == [(
        ["first", "second", "third"],
        [identity(key).visual_signature for key in ["first", "second", "third"]],
        [categorization(key).product_type for key in ["first", "second", "third"]],
    )]
    assert [product.image_numbers for product in result.products] == [[2, 6], [4]]
    assert {item.image_number for item in result.rejected_images} == {1, 3, 5}
    assert sorted(data for data, _, _ in pipeline.synthesis_calls) == [b"first", b"second"]
    for data, kwargs, thread in pipeline.synthesis_calls:
        assert thread != coordinator
        assert kwargs["run_safety_check"] is False
        assert kwargs["screen_already"] is True
        assert kwargs["known_categorization"] == categorization(data.decode())

    assert {thread for thread, _ in progress} == {coordinator}
    completion_reports = [args for _, args in progress if args[0] == "analysis"]
    assert [args[2] for args in completion_reports] == [1, 2, 3, 4, 5]
    assert {args[3] for args in completion_reports} == {5}
    percentages = [args[4] for _, args in progress]
    assert percentages == sorted(percentages)
    assert percentages[-1] == 100


def test_each_image_runs_gates_in_order_and_rejections_short_circuit(monkeypatch, pipeline):
    def moderate(client, data_url):
        response = pipeline.moderate(client, data_url)
        response.results[0].flagged = image_key(data_url) == "flagged"
        return response

    def screen(client, data_url):
        pipeline.screen(client, data_url)
        key = image_key(data_url)
        return screening(
            passed=key not in {"unrelated", "styled"},
            item_count=2 if key in {"multiple", "styled"} else 1,
            primary_item_clear=key not in {"unclear", "multiple"},
            supporting_clothing_is_styling=False,
        )

    monkeypatch.setattr(recognition, "_moderate_image", moderate)
    monkeypatch.setattr(recognition, "screen_product_image", screen)
    result = recognition.analyze_product_images(
        [b"flagged", b"unrelated", b"multiple", b"unclear", b"accepted", b"styled"], max_concurrency=3,
    )

    assert pipeline.calls["flagged"] == ["moderation"]
    for key in ["unrelated", "multiple", "unclear"]:
        assert pipeline.calls[key] == ["moderation", "screening"]
    assert pipeline.calls["accepted"] == ["moderation", "screening", "identity", "category"]
    assert pipeline.calls["styled"] == ["moderation", "screening", "identity", "category"]
    assert [product.image_numbers for product in result.products] == [[5], [6]]
    assert {item.image_number for item in result.rejected_images} == {1, 2, 3, 4}


def test_every_rejected_image_completes_progress_without_grouping(monkeypatch, pipeline):
    progress = []
    grouping = Mock(side_effect=AssertionError("Rejected images must not reach grouping"))

    def reject(client, data_url):
        pipeline.screen(client, data_url)
        return screening(passed=False)

    monkeypatch.setattr(recognition, "screen_product_image", reject)
    monkeypatch.setattr(recognition, "group_product_images", grouping)
    result = recognition.analyze_product_images(
        [b"one", b"two", b"three", b"four"],
        progress_callback=lambda *args: progress.append(args), max_concurrency=3,
    )

    assert result.passed is False
    assert result.unique_product_count == 0
    assert result.products == []
    assert {item.image_number for item in result.rejected_images} == {1, 2, 3, 4}
    assert [args[2] for args in progress if args[0] == "analysis"] == [1, 2, 3, 4]
    assert pipeline.synthesis_calls == []
    grouping.assert_not_called()


def test_safety_opt_out_skips_only_moderation(monkeypatch, pipeline):
    moderation = Mock(side_effect=AssertionError("Moderation was explicitly disabled"))
    monkeypatch.setattr(recognition, "_moderate_image", moderation)

    result = recognition.analyze_product_images([b"accepted"], run_safety_check=False, max_concurrency=1)

    assert result.passed is True
    assert pipeline.calls["accepted"] == ["screening", "identity", "category"]
    moderation.assert_not_called()


@pytest.mark.parametrize("blocked_stage", ["moderation", "screening", "identity"])
def test_fatal_error_stops_other_image_before_its_next_gate(monkeypatch, pipeline, blocked_stage):
    other_in_flight = Event()
    grouping = Mock(side_effect=AssertionError("A failed batch must not reach grouping"))

    def stage(name, original):
        def run(client, data_url):
            key = image_key(data_url)
            if key == "other" and name == blocked_stage:
                # Keep one dispatched operation in flight until the coordinator
                # sees the other image's error. Its next gate must never run.
                signal = recognition._analysis_cancel.get()
                assert signal is not None
                other_in_flight.set()
                assert signal.wait(timeout=5), "The coordinator did not cancel the failed batch"
            result = original(client, data_url)
            if key == "fatal" and name == "screening":
                assert other_in_flight.wait(timeout=5), "The independent image did not start"
                raise RuntimeError("Fatal screening service failure")
            return result

        return run

    monkeypatch.setattr(recognition, "_moderate_image", stage("moderation", pipeline.moderate))
    monkeypatch.setattr(recognition, "screen_product_image", stage("screening", pipeline.screen))
    monkeypatch.setattr(recognition, "identify_product_image", stage("identity", pipeline.identify))
    monkeypatch.setattr(recognition, "group_product_images", grouping)

    with pytest.raises(RuntimeError, match="Fatal screening service failure"):
        recognition.analyze_product_images([b"fatal", b"other"], max_concurrency=2)

    gates = ["moderation", "screening", "identity", "category"]
    if blocked_stage == "identity":
        assert set(pipeline.calls["other"]) == set(gates)
    else:
        assert pipeline.calls["other"] == gates[:gates.index(blocked_stage) + 1]
    assert pipeline.calls["fatal"] == ["moderation", "screening"]
    assert pipeline.synthesis_calls == []
    assert recognition._analysis_cancel.get() is None
    grouping.assert_not_called()


def test_simultaneous_first_requests_share_one_model_limiter(monkeypatch):
    start = Barrier(4)
    constructor_started, duplicate_constructor, release_constructor = Event(), Event(), Event()
    construction_lock = Lock()
    constructed = []
    monkeypatch.setattr(recognition, "_limiters", {})

    def construct(limits):
        limiter = object()
        with construction_lock:
            constructed.append(limiter)
            if len(constructed) > 1:
                duplicate_constructor.set()
        constructor_started.set()
        assert release_constructor.wait(timeout=5)
        return limiter

    def request_limiter():
        start.wait(timeout=5)
        return recognition._request_limiter("shared-first-wave")

    monkeypatch.setattr(recognition, "RateLimiter", construct)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(request_limiter) for _ in range(4)]
        try:
            assert constructor_started.wait(timeout=5)
            # The constructor deliberately remains in progress while concurrent
            # callers arrive. A cache that permits duplicate initialization fails.
            duplicate_seen = duplicate_constructor.wait(timeout=0.15)
        finally:
            release_constructor.set()
        results = [future.result(timeout=5) for future in futures]

    assert not duplicate_seen
    assert len(constructed) == 1
    assert all(result is constructed[0] for result in results)


@pytest.mark.parametrize("explicit_limit,expected_limit", [(None, 3), (2, 2)])
def test_product_synthesis_overlaps_within_limit_only_after_grouping(monkeypatch, pipeline, explicit_limit, expected_limit):
    grouped = Event()
    first_wave = Barrier(expected_limit)
    lock = Lock()
    active = 0
    peak = 0
    coordinator = get_ident()

    def group(*args, **kwargs):
        result = pipeline.group(*args, **kwargs)
        assert len(pipeline.calls) == 7
        assert all(stages[-1] == "category" for stages in pipeline.calls.values())
        grouped.set()
        return result

    def synthesize(data, **kwargs):
        nonlocal active, peak
        assert grouped.is_set(), "Product synthesis started before grouping completed"
        with lock:
            active += 1
            peak = max(peak, active)
            assert active <= expected_limit
        try:
            if int(data.decode().split("-")[1]) < expected_limit:
                first_wave.wait(timeout=5)
            return pipeline.synthesize(data, **kwargs)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(recognition, "group_product_images", group)
    monkeypatch.setattr(recognition, "analyze_product_image", synthesize)
    kwargs = {} if explicit_limit is None else {"max_concurrency": explicit_limit}
    result = recognition.analyze_product_images([f"shirt-{n}".encode() for n in range(7)], **kwargs)

    assert result.unique_product_count == 7
    assert peak == expected_limit
    assert active == 0
    threads = {thread for _, _, thread in pipeline.synthesis_calls}
    assert len(threads) == expected_limit
    assert coordinator not in threads


def test_synthesis_completion_order_preserves_products_categories_and_coordinator_progress(monkeypatch, pipeline):
    second_done, third_done = Event(), Event()
    completion_order = []
    progress = []
    coordinator = get_ident()

    def group(*args, **kwargs):
        return recognition.BatchScreeningResult(
            passed=True, unique_product_count=3,
            groups=[
                recognition.ProductImageGroup(product_number=1, image_numbers=[1, 4], reason="First and fourth images show the same shirt."),
                recognition.ProductImageGroup(product_number=2, image_numbers=[2], reason="Second image shows a different shirt."),
                recognition.ProductImageGroup(product_number=3, image_numbers=[3], reason="Third image shows another separate shirt."),
            ],
            reason="The accepted images show three different shirts.",
        )

    def synthesize(data, **kwargs):
        key = data.decode()
        if key == "first":
            assert second_done.wait(timeout=5), "Second product did not synthesize independently"
        elif key == "second":
            assert third_done.wait(timeout=5), "Third product did not synthesize independently"
        result = pipeline.synthesize(data, **kwargs)
        # Group consensus remains authoritative if synthesis returns another category.
        result.category = recognition.ProductCategory.FOOTWEAR
        completion_order.append(key)
        if key == "third":
            third_done.set()
        elif key == "second":
            second_done.set()
        return result

    monkeypatch.setattr(recognition, "group_product_images", group)
    monkeypatch.setattr(recognition, "analyze_product_image", synthesize)
    result = recognition.analyze_product_images(
        [b"invalid", b"first", b"second", b"third", b"fourth"],
        api_key="test-key", model="requested-synthesis-model", max_concurrency=3,
        progress_callback=lambda *args: progress.append((get_ident(), args)),
    )

    assert completion_order == ["third", "second", "first"]
    assert [product.product_number for product in result.products] == [1, 2, 3]
    assert [product.image_numbers for product in result.products] == [[2, 5], [3], [4]]
    assert [product.analysis.product_name for product in result.products] == [f"{key} cotton shirt" for key in ["first", "second", "third"]]
    assert all(product.analysis.category == recognition.ProductCategory.TOPS for product in result.products)
    assert [item.image_number for item in result.rejected_images] == [1]
    for data, kwargs, thread in pipeline.synthesis_calls:
        assert thread != coordinator
        assert kwargs == {
            "api_key": "test-key", "model": "requested-synthesis-model",
            "run_safety_check": False, "screen_already": True,
            "known_categorization": categorization(data.decode()),
            "prepared_data_url": "data:image/jpeg;base64," + __import__('base64').b64encode(data).decode("ascii"),
        }
    assert {thread for thread, _ in progress} == {coordinator}
    synthesis_reports = [args for _, args in progress if args[0] == "synthesis"]
    assert [args[2] for args in synthesis_reports] == [0, 1, 2, 3]
    assert {args[3] for args in synthesis_reports} == {3}
    percentages = [args[4] for _, args in progress]
    assert percentages == sorted(percentages)
    assert percentages[-1] == 100


def test_fatal_synthesis_error_cancels_other_products_before_another_request(monkeypatch, pipeline):
    other_in_flight = Event()
    admission = Mock(side_effect=AssertionError("Cancelled synthesis must not reserve another request"))
    operation = Mock(side_effect=AssertionError("Cancelled synthesis must not send another request"))
    monkeypatch.setattr(recognition, "_request_limiter", lambda model: SimpleNamespace(acquire=admission))

    def synthesize(data, **kwargs):
        if data == b"fatal":
            assert other_in_flight.wait(timeout=5), "The independent product did not start"
            raise RuntimeError("Fatal synthesis service failure")
        signal = recognition._analysis_cancel.get()
        assert signal is not None
        other_in_flight.set()
        assert signal.wait(timeout=5), "Synthesis failure did not cancel the other product"
        recognition._openai_call(operation, model="cancelled-synthesis-model", input_tokens=100, output_tokens=100)
        raise AssertionError("Cancelled synthesis unexpectedly continued")

    monkeypatch.setattr(recognition, "analyze_product_image", synthesize)

    with pytest.raises(RuntimeError, match="Fatal synthesis service failure"):
        recognition.analyze_product_images([b"fatal", b"other"], max_concurrency=2)

    admission.assert_not_called()
    operation.assert_not_called()
    assert recognition._analysis_cancel.get() is None


@pytest.mark.parametrize("configured_model,explicit_model,expected_model", [
    (None, None, "gpt-4.1-mini"),
    ("gpt-4o-mini", None, "gpt-4o-mini"),
    ("gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1-mini"),
])
def test_model_selection_reaches_every_batch_stage_and_worker(monkeypatch, pipeline, configured_model, explicit_model, expected_model):
    if configured_model is None:
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
    else:
        monkeypatch.setenv("OPENAI_MODEL", configured_model)
    calls = []
    coordinator = get_ident()

    def stage(name, original):
        def run(*args, **kwargs):
            calls.append((name, recognition._vision_model(), get_ident()))
            return original(*args, **kwargs)
        return run

    for attribute, name, original in [
        ("screen_product_image", "screening", pipeline.screen),
        ("identify_product_image", "identity", pipeline.identify),
        ("categorize_product_image", "category", pipeline.categorize),
        ("group_product_images", "grouping", pipeline.group),
        ("analyze_product_image", "synthesis", pipeline.synthesize),
    ]:
        monkeypatch.setattr(recognition, attribute, stage(name, original))
    kwargs = {} if explicit_model is None else {"model": explicit_model}
    result = recognition.analyze_product_images([b"accepted"], api_key="test-key", max_concurrency=1, **kwargs)

    assert result.passed
    assert [(name, model) for name, model, _ in calls] == [(stage_name, expected_model) for stage_name in [
        "screening", "identity", "category", "grouping", "synthesis",
    ]]
    assert all(thread != coordinator for name, _, thread in calls if name != "grouping")
    assert next(thread for name, _, thread in calls if name == "grouping") == coordinator
    # A per-call override must not become the default of the next batch.
    assert recognition._vision_model() == (configured_model or "gpt-4.1-mini")


@pytest.mark.parametrize("invalid_input", ["empty_batch", "invalid_batch", "invalid_single"])
def test_invalid_inputs_are_resolved_before_provider_initialization(monkeypatch, invalid_input):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = Mock(side_effect=AssertionError("Invalid input must not initialize an API client"))
    router = Mock(side_effect=AssertionError("Invalid input must not initialize routing or quota storage"))
    monkeypatch.setattr(recognition, "OpenAI", client)
    monkeypatch.setattr(recognition, "AnalysisRouter", router)

    if invalid_input == "empty_batch":
        with pytest.raises(ValueError, match="at least one image is required"):
            recognition.analyze_product_images([])
    elif invalid_input == "invalid_single":
        with pytest.raises(ValueError, match="not a readable image"):
            recognition.analyze_product_image(b"not an image")
    else:
        result = recognition.analyze_product_images([b"not an image", b""])
        assert result.passed is False
        assert result.products == []
        assert result.unique_product_count == 0
        assert [item.image_number for item in result.rejected_images] == [1, 2]
        assert "not a readable image" in result.rejected_images[0].reason
        assert "empty" in result.rejected_images[1].reason

    client.assert_not_called()
    router.assert_not_called()
