import base64
import io
import json
import threading
from concurrent.futures import CancelledError, ThreadPoolExecutor

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError
from PIL import Image, PngImagePlugin
from pydantic import BaseModel

from productframe_api.analysis_limits import (
    AnalysisBudgetError,
    AnalysisLimits,
    RateLimiter,
    estimate_request_tokens,
    image_token_cost,
    retry_delay,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []
        self.lock = threading.Lock()

    def __call__(self):
        with self.lock:
            return self.now

    def sleep(self, seconds):
        with self.lock:
            self.sleeps.append(seconds)
            self.now += seconds


def limits(**overrides):
    return AnalysisLimits(**{
        "max_input_tokens": 100,
        "max_output_tokens": 20,
        "tokens_per_minute": 100,
        "requests_per_minute": 10,
        **overrides,
    })


def limiter_for(config=None):
    clock = FakeClock()
    return RateLimiter(config or limits(), clock=clock, sleep=clock.sleep), clock


def png_url(width=32, height=32, padding=""):
    output = io.BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("padding", padding)
    Image.new("RGB", (width, height)).save(output, format="PNG", pnginfo=metadata)
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()


def api_error(status=429, *, headers=None, code=None):
    response = httpx.Response(status, headers=headers, request=httpx.Request("POST", "https://api.test/responses"))
    error_class = RateLimitError if status == 429 else InternalServerError
    return error_class("Request failed", response=response, body={"error": {"code": code}})


def test_settings_defaults_and_environment(monkeypatch):
    for name in AnalysisLimits.__dataclass_fields__:
        monkeypatch.delenv(f"ANALYSIS_{name.upper()}", raising=False)
    assert AnalysisLimits.from_env() == AnalysisLimits(3, 110000, 4096, 180000, 60)
    monkeypatch.setenv("ANALYSIS_CONCURRENCY", "2")
    monkeypatch.setenv("ANALYSIS_TOKENS_PER_MINUTE", "150000")
    assert AnalysisLimits.from_env().concurrency == 2
    assert AnalysisLimits.from_env().tokens_per_minute == 150000


@pytest.mark.parametrize("settings", [
    {"concurrency": 0}, {"concurrency": 9}, {"requests_per_minute": -1},
    {"max_input_tokens": 120001}, {"max_output_tokens": 8001},
    {"tokens_per_minute": 1.5}, {"concurrency": True},
])
def test_settings_reject_unsafe_values(settings):
    with pytest.raises(ValueError):
        AnalysisLimits(**settings)


def test_settings_reject_malformed_environment(monkeypatch):
    monkeypatch.setenv("ANALYSIS_CONCURRENCY", "several")
    with pytest.raises(ValueError, match="ANALYSIS_CONCURRENCY"):
        AnalysisLimits.from_env()


@pytest.mark.parametrize("width,height,expected", [
    (32, 32, 8500), (512, 256, 8500), (512, 512, 8500),
    (1024, 256, 14167), (1024, 1024, 25501),
    (2048, 1024, 36835), (4096, 2048, 36835), (2048, 768, 48169),
])
def test_high_detail_tile_estimates_do_not_upscale(width, height, expected):
    assert image_token_cost(width, height) == expected
    assert image_token_cost(height, width) == expected
    assert image_token_cost(width, height, model="custom-model") == expected


def test_low_detail_and_invalid_dimensions():
    assert image_token_cost(2048, 2048, detail="low") == 2833
    with pytest.raises(ValueError):
        image_token_cost(0, 512)


@pytest.mark.parametrize("width,height,expected", [
    (32, 32, 2), (512, 512, 415), (960, 1200, 1847),
    (1024, 1536, 2489), (2048, 2048, 6636), (4096, 4096, 6636),
])
def test_gpt41_mini_uses_its_patch_profile_for_all_supported_details(width, height, expected):
    for model in ("gpt-4.1-mini", "gpt-4.1-mini-2025-04-14", "openai/gpt-4.1-mini"):
        for detail in ("low", "high", "auto"):
            assert image_token_cost(width, height, model, detail=detail) == expected
            assert image_token_cost(height, width, model, detail=detail) == expected


def test_model_switch_changes_request_image_estimates_and_remote_worst_case():
    inputs = [{"type": "input_image", "image_url": png_url(960, 1200), "detail": "high"}]
    assert estimate_request_tokens(inputs, model="gpt-4o-mini") - estimate_request_tokens(inputs, model="gpt-4.1-mini") == 25501 - 1847
    assert estimate_request_tokens([{"type": "input_image", "image_url": "https://assets.test/image.jpg"}], model="gpt-4.1-mini") > 6636


def test_estimator_counts_image_tiles_not_base64_transport():
    short = png_url()
    long = png_url(padding="x" * 100000)
    assert len(long) > len(short) + 100000
    payload = lambda url: [{"role": "user", "content": [{"type": "input_image", "image_url": url, "detail": "high"}]}]
    estimate = estimate_request_tokens(payload(short))
    assert estimate == estimate_request_tokens(payload(long))
    assert 8500 < estimate < 9000


def test_estimator_counts_utf8_schema_and_all_images():
    class Output(BaseModel):
        description: str

    assert estimate_request_tokens("♥") - estimate_request_tokens("a") == 2
    assert estimate_request_tokens("hello", text_format=Output) >= estimate_request_tokens("hello") + len(json.dumps(Output.model_json_schema()).encode())
    url = png_url(1024, 1024)
    one = {"type": "input_image", "image_url": url}
    assert estimate_request_tokens([one, one]) >= 2 * 25501


def test_unknown_remote_images_use_worst_case_and_bad_data_fails():
    assert estimate_request_tokens([{"type": "input_image", "image_url": "https://assets.test/image.jpg"}]) > 48169
    with pytest.raises(ValueError, match="unreadable"):
        estimate_request_tokens([{"type": "input_image", "image_url": "data:image/png;base64,bad"}])


def test_input_and_output_reservations_share_the_rolling_budget():
    limiter, clock = limiter_for()
    first = limiter.acquire(60, 10)
    limiter.observe(first)
    second = limiter.acquire(30, 10)
    assert first.started_at == 0
    assert second.started_at == 60
    assert clock.sleeps == [60]


def test_only_needed_reservations_expire_before_admission():
    limiter, clock = limiter_for()
    limiter.acquire(60, 0)
    clock.sleep(10)
    limiter.acquire(30, 0)
    assert limiter.acquire(50, 0).started_at == 60
    assert clock.sleeps == [10, 50]


def test_zero_token_moderation_still_reserves_requests():
    limiter, clock = limiter_for(limits(requests_per_minute=2))
    limiter.acquire(0, 0)
    limiter.acquire(0, 0)
    assert limiter.acquire(0, 0).started_at == 60
    assert clock.sleeps == [60]


@pytest.mark.parametrize("input_tokens,output_tokens", [(101, 0), (0, 21), (90, 20)])
def test_oversized_requests_fail_without_waiting(input_tokens, output_tokens):
    limiter, clock = limiter_for()
    with pytest.raises(AnalysisBudgetError):
        limiter.acquire(input_tokens, output_tokens)
    assert clock.sleeps == []


def test_provider_limits_can_only_reduce_configured_budgets():
    limiter, _ = limiter_for()
    first = limiter.acquire(10, 0)
    limiter.observe(first, {"X-Ratelimit-Limit-Tokens": "50", "X-Ratelimit-Limit-Requests": "5"})
    assert limiter.input_budget() == 30
    second = limiter.acquire(10, 0)
    limiter.observe(second, {"x-ratelimit-limit-tokens": "10000", "x-ratelimit-limit-requests": "10000"})
    assert limiter.input_budget() == 30
    with pytest.raises(AnalysisBudgetError):
        limiter.acquire(40, 20)


def test_headers_subtract_other_inflight_requests_and_ignore_stale_increases():
    limiter, clock = limiter_for(limits(max_input_tokens=500, tokens_per_minute=1000))
    first = limiter.acquire(200, 0)
    second = limiter.acquire(200, 0)
    limiter.observe(first, {"x-ratelimit-remaining-tokens": "250", "x-ratelimit-reset-tokens": "10s"})
    assert limiter.availability_delay(60, 0) == 10
    # This older response's larger remaining count must not undo the first guard.
    limiter.observe(second, {"x-ratelimit-remaining-tokens": "800", "x-ratelimit-reset-tokens": "5s"})
    assert limiter.availability_delay(260, 0) == 10
    # Its temporary pending deduction can be released once its headers arrive.
    assert limiter.acquire(60, 0).started_at == 0
    assert clock.sleeps == []


def test_all_completed_responses_release_temporary_inflight_padding():
    limiter, clock = limiter_for(AnalysisLimits())
    pending = [limiter.acquire(32000, 0) for _ in range(3)]
    for reservation in pending:
        limiter.observe(reservation, {"x-ratelimit-remaining-tokens": "84000", "x-ratelimit-reset-tokens": "20s"})
    assert limiter.try_acquire(32000, 0) is not None
    assert clock.sleeps == []


def test_new_reservations_are_accounted_through_out_of_order_responses():
    limiter, _ = limiter_for(limits(max_input_tokens=1000, tokens_per_minute=2000))
    initial = limiter.acquire(10, 0)
    limiter.observe(initial, {"x-ratelimit-remaining-tokens": "500", "x-ratelimit-reset-tokens": "10s"})
    first = limiter.acquire(100, 0)
    second = limiter.acquire(100, 0)
    limiter.observe(second, {"x-ratelimit-remaining-tokens": "300", "x-ratelimit-reset-tokens": "10s"})
    assert limiter.availability_delay(201, 0) == 10
    limiter.observe(first, {"x-ratelimit-remaining-tokens": "400", "x-ratelimit-reset-tokens": "10s"})
    assert limiter.availability_delay(301, 0) == 10
    assert limiter.try_acquire(300, 0) is not None
    assert limiter.try_acquire(1, 0) is None


def test_headerless_completions_do_not_refund_unconfirmed_capacity():
    limiter, _ = limiter_for()
    initial = limiter.acquire(0, 0)
    limiter.observe(initial, {"x-ratelimit-remaining-tokens": "50", "x-ratelimit-reset-tokens": "10s"})
    request = limiter.acquire(40, 0)
    limiter.observe(request)
    assert limiter.try_acquire(11, 0) is None
    assert limiter.availability_delay(11, 0) == 10


def test_provider_remaining_requests_respects_concurrent_reservations():
    limiter, clock = limiter_for()
    first = limiter.acquire(0, 0)
    limiter.acquire(0, 0)
    limiter.observe(first, {"x-ratelimit-remaining-requests": "1", "x-ratelimit-reset-requests": "1500ms"})
    assert limiter.acquire(0, 0).started_at == 1.5
    assert clock.sleeps == [1.5]


def test_project_and_model_token_limits_both_constrain_admission():
    limiter, clock = limiter_for(limits(max_input_tokens=500, tokens_per_minute=1000))
    first = limiter.acquire(100, 0)
    limiter.observe(first, {
        "x-ratelimit-limit-tokens": "900",
        "x-ratelimit-limit-project-tokens": "400",
        "x-ratelimit-remaining-tokens": "800",
        "x-ratelimit-reset-tokens": "5s",
        "x-ratelimit-remaining-project-tokens": "20",
        "x-ratelimit-reset-project-tokens": "1m2s",
    })
    assert limiter.input_budget(20) == 380
    assert limiter.acquire(30, 0).started_at == 62
    assert clock.sleeps == [62]


@pytest.mark.parametrize("constrained_bucket,other_bucket", [("tokens", "project-tokens"), ("project-tokens", "tokens")])
def test_independent_token_buckets_do_not_merge_remaining_with_the_wrong_reset(constrained_bucket, other_bucket):
    limiter, clock = limiter_for(AnalysisLimits())
    first = limiter.acquire(100, 0)
    limiter.observe(first, {
        f"x-ratelimit-remaining-{constrained_bucket}": "0",
        f"x-ratelimit-reset-{constrained_bucket}": "5s",
        f"x-ratelimit-remaining-{other_bucket}": "170000",
        f"x-ratelimit-reset-{other_bucket}": "60s",
    })
    assert limiter.availability_delay(1000, 0) == 5
    assert limiter.acquire(1000, 0).started_at == 5
    assert clock.sleeps == [5]


def test_missing_reset_header_uses_a_conservative_window():
    limiter, _ = limiter_for()
    first = limiter.acquire(0, 0)
    limiter.observe(first, {"x-ratelimit-remaining-requests": "0"})
    assert limiter.acquire(0, 0).started_at == 60


def test_shared_cooldown_cannot_be_shortened_and_lock_is_released_while_waiting():
    clock = FakeClock()
    limiter = None

    def sleep(seconds):
        assert limiter._lock.acquire(blocking=False), "Admission must unlock before sleeping"
        limiter._lock.release()
        clock.sleep(seconds)

    limiter = RateLimiter(limits(), clock=clock, sleep=sleep)
    limiter.defer(5)
    clock.sleep(2)
    limiter.defer(1)
    assert limiter.acquire(10, 0).started_at == 5


def test_simultaneous_callers_cannot_overcommit_a_window():
    limiter, _ = limiter_for(limits(requests_per_minute=100))
    with ThreadPoolExecutor(max_workers=8) as executor:
        reservations = list(executor.map(lambda _: limiter.acquire(10, 0), range(40)))
    assert len({item.number for item in reservations}) == 40
    for reservation in reservations:
        in_window = [item for item in reservations if reservation.started_at <= item.started_at < reservation.started_at + 60]
        assert sum(item.tokens for item in in_window) <= 100


def test_nonblocking_admission_and_delay_preview_never_spend_future_capacity():
    limiter, clock = limiter_for()
    assert limiter.availability_delay(60, 10) == 0
    assert limiter.availability_delay(60, 10) == 0
    first = limiter.try_acquire(60, 10)
    assert first is not None and first.number == 0
    assert limiter.try_acquire(40, 0) is None
    assert limiter.availability_delay(40, 0) == 60
    assert clock.sleeps == []
    second = limiter.try_acquire(30, 0)
    assert second is not None and second.number == 1
    assert limiter.try_acquire(1, 0) is None
    clock.sleep(60)
    assert limiter.availability_delay(100, 0) == 0
    assert limiter.try_acquire(100, 0).number == 2


def test_simultaneous_nonblocking_callers_cannot_overcommit_capacity():
    limiter, clock = limiter_for()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: limiter.try_acquire(20, 0), range(30)))
    reservations = [result for result in results if result is not None]
    assert len(reservations) == 5
    assert len({item.number for item in reservations}) == 5
    assert clock.sleeps == []


@pytest.mark.parametrize("method_name", ["acquire", "try_acquire", "availability_delay"])
def test_all_admission_methods_reject_oversized_or_cancelled_requests(method_name):
    limiter, clock = limiter_for()
    method = getattr(limiter, method_name)
    with pytest.raises(AnalysisBudgetError):
        method(90, 20)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(CancelledError):
        method(10, 0, cancel_event=cancel)
    assert limiter.try_acquire(10, 0).number == 0
    assert clock.sleeps == []


def test_cancelled_batch_exits_admission_wait_without_reserving_another_request():
    clock = FakeClock()
    cancel = threading.Event()

    def sleep(seconds):
        clock.sleep(seconds)
        cancel.set()

    limiter = RateLimiter(limits(), clock=clock, sleep=sleep)
    limiter.acquire(100, 0)
    with pytest.raises(CancelledError):
        limiter.acquire(10, 0, cancel_event=cancel)
    assert clock.sleeps == [0.25]
    assert limiter.acquire(0, 0).number == 1
    with pytest.raises(CancelledError):
        limiter.acquire(0, 0, cancel_event=cancel)
    assert limiter.acquire(0, 0).number == 2


@pytest.mark.parametrize("headers,expected", [
    ({"retry-after": "12.5"}, 12.5),
    ({"retry-after-ms": "2500", "retry-after": "20"}, 2.5),
    ({"retry-after": "Thu, 01 Jan 1970 00:00:20 GMT"}, 20),
])
def test_retry_delays_honor_provider_headers(headers, expected):
    assert retry_delay(api_error(headers=headers), 0, wall_time=lambda: 0) == expected


def test_retry_backoff_is_bounded_with_jitter():
    assert retry_delay(api_error(), 0, random_value=lambda: 0.5) == 2.5
    assert retry_delay(api_error(), 1, random_value=lambda: 0.5) == 4.5
    assert retry_delay(api_error(), 99, random_value=lambda: 0.5) == 60.5


def test_quota_exhaustion_and_permanent_errors_do_not_retry():
    assert retry_delay(api_error(code="insufficient_quota"), 0) is None
    assert retry_delay(api_error(code="billing_hard_limit_reached"), 0) is None
    assert retry_delay(ValueError("Invalid image"), 0) is None
    assert retry_delay(api_error(status=400), 0) is None


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503])
def test_transient_http_failures_keep_retry_behavior(status):
    assert retry_delay(api_error(status), 0, random_value=lambda: 0) == 2


def test_connection_and_timeout_failures_keep_retry_behavior():
    request = httpx.Request("POST", "https://api.test/responses")
    assert retry_delay(APIConnectionError(request=request), 0, random_value=lambda: 0) == 2
    assert retry_delay(APITimeoutError(request=request), 0, random_value=lambda: 0) == 2


def test_provider_adapter_permanent_flags_take_precedence_over_http_status():
    class AdapterError(RuntimeError):
        status_code = 429
        permanent = True
        retryable = False

    assert retry_delay(AdapterError("Daily quota exhausted"), 0) is None


def test_provider_adapter_can_mark_transport_error_retryable():
    class AdapterError(RuntimeError):
        retryable = True

    assert retry_delay(AdapterError("Network timeout"), 0, random_value=lambda: 0) == 2
