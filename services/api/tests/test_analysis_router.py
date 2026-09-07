import logging
from concurrent.futures import CancelledError, ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event
from types import SimpleNamespace

import httpx
import pytest
from pydantic import BaseModel

from productframe_api import analysis_router as routing
from productframe_api.analysis_limits import AnalysisLimits, RateLimiter
from productframe_api.gemini_analysis import GeminiAPIError, GeminiSafetyError


class Decision(BaseModel):
    passed: bool


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeClient:
    def __init__(self, provider, operation=None):
        self.provider = provider
        self.operation = operation
        self.calls = []
        self.responses = SimpleNamespace(with_raw_response=SimpleNamespace(parse=self.parse))

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        response = self.operation() if self.operation else SimpleNamespace(
            output_parsed=Decision(passed=True), output=[], headers={},
            usage=SimpleNamespace(input_tokens=123, output_tokens=7),
        )
        if self.provider == "openai":
            return SimpleNamespace(headers=response.headers, parse=lambda: response)
        return response

    def close(self):
        pass


@pytest.fixture
def clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(routing.time, "monotonic", clock)
    monkeypatch.setattr(routing.time, "sleep", clock.sleep)
    monkeypatch.setattr(routing, "estimate_request_tokens", lambda *args, **kwargs: 10)
    monkeypatch.setattr(routing, "estimate_gemini_input_tokens", lambda *args, **kwargs: 12)
    token = routing._affinity.set(None)
    yield clock
    routing._affinity.reset(token)


def route(clock, provider, *, rpm=10, latency=1.0, operation=None, daily=None):
    limiter = RateLimiter(AnalysisLimits(
        concurrency=3, max_input_tokens=80, max_output_tokens=20,
        tokens_per_minute=1000, requests_per_minute=rpm,
    ), clock=clock, sleep=clock.sleep)
    model = "gemini-3.6-flash" if provider == "gemini" else "gpt-4.1-mini"
    return routing.Route(provider, model, limiter, FakeClient(provider, operation), daily=daily, latency=latency)


def router_for(*routes):
    first = routes[0]
    return routing.AnalysisRouter(first.client, first.model, first.limiter, routes=list(routes))


def parse(router, **kwargs):
    return router.parse(input=[{"role": "user", "content": [{"type": "input_text", "text": "private product details"}]}], text_format=Decision, output_tokens=20, **kwargs)


def test_available_gemini_capacity_avoids_waiting_for_openai(clock):
    openai = route(clock, "openai", rpm=1)
    reservation = openai.limiter.try_acquire(10, 20)
    openai.limiter.observe(reservation)
    gemini = route(clock, "gemini")
    router = router_for(openai, gemini)

    assert parse(router).output_parsed.passed is True
    assert not openai.client.calls
    assert len(gemini.client.calls) == 1
    assert not clock.sleeps
    assert router.events[0]["provider"] == "gemini"


def test_both_busy_routes_wait_until_capacity_is_available(clock):
    openai, gemini = route(clock, "openai"), route(clock, "gemini")
    openai.limiter.defer(2)
    gemini.limiter.defer(3)
    assert parse(router_for(openai, gemini)).output_parsed.passed is True
    assert clock.now == 2
    assert len(openai.client.calls) == 1
    assert not gemini.client.calls


def test_transient_failure_falls_back_without_repeating_the_whole_pipeline(clock, monkeypatch):
    def unavailable():
        raise GeminiAPIError(code="provider_error", retryable=True, response=httpx.Response(503))
    gemini = route(clock, "gemini", operation=unavailable)
    openai = route(clock, "openai", latency=2)
    monkeypatch.setattr(routing, "retry_delay", lambda error, attempt: 4)
    router = router_for(gemini, openai)

    assert parse(router).output_parsed.passed is True
    assert len(gemini.client.calls) == len(openai.client.calls) == 1
    assert gemini.limiter.availability_delay(12, 20) == 4
    assert not clock.sleeps
    assert [event["outcome"] for event in router.events] == ["failed", "completed"]
    assert all(event["stage"] == "Decision" for event in router.events)


def test_retryable_gemini_transport_error_can_use_other_provider(clock):
    def timeout():
        raise GeminiAPIError(code="transport_error", retryable=True)
    gemini = route(clock, "gemini", operation=timeout)
    openai = route(clock, "openai", latency=2)
    assert parse(router_for(gemini, openai)).output_parsed.passed is True
    assert len(gemini.client.calls) == len(openai.client.calls) == 1
    assert not gemini.disabled


@pytest.mark.parametrize("provider,refusal", [
    ("gemini", "safety"), ("openai", "refusal_part"), ("openai", "content_filter"),
])
def test_safety_refusal_is_terminal_with_no_alternate_provider(clock, provider, refusal):
    def blocked():
        if provider == "gemini":
            raise GeminiSafetyError(response=httpx.Response(200))
        return SimpleNamespace(
            output_parsed=None, headers={}, usage=None,
            output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])] if refusal == "refusal_part" else [],
            incomplete_details=SimpleNamespace(reason="content_filter") if refusal == "content_filter" else None,
        )
    primary = route(clock, provider, operation=blocked)
    alternate = route(clock, "gemini" if provider == "openai" else "openai", latency=2)
    router = router_for(primary, alternate)

    with pytest.raises(routing.AnalysisSafetyError):
        parse(router)
    assert len(primary.client.calls) == 1
    assert not alternate.client.calls
    assert len(router.events) == 1
    assert router.events[0]["outcome"] == "safety_rejected"
    assert primary.in_flight == 0


def test_invalid_structured_output_has_three_attempt_bound(clock):
    def invalid():
        raise ValueError("Invalid structured output")
    gemini = route(clock, "gemini", operation=invalid)
    router = router_for(gemini)
    with pytest.raises(ValueError, match="Invalid structured output"):
        parse(router)
    assert len(gemini.client.calls) == len(router.events) == 3
    assert not clock.sleeps
    assert gemini.in_flight == 0


def test_actual_usage_is_logged_without_prompt_or_credential_data(clock, caplog):
    openai = route(clock, "openai")
    router = router_for(openai)
    with caplog.at_level(logging.INFO, logger=routing.__name__):
        parse(router)
    event = router.events[0]
    assert event["estimated_input_tokens"] == 10
    assert event["input_tokens"] == 123
    assert event["output_tokens"] == 7
    assert "private product details" not in caplog.text
    assert "x-goog-api-key" not in caplog.text
    assert openai.client.calls[0]["store"] is False


def test_grouping_uses_openai_even_when_gemini_is_faster(clock):
    gemini = route(clock, "gemini", latency=0.1)
    openai = route(clock, "openai", latency=10)
    assert parse(router_for(gemini, openai), grouping=True).output_parsed.passed is True
    assert len(openai.client.calls) == 1
    assert not gemini.client.calls


def test_daily_allowance_persists_and_resets_at_pacific_midnight(tmp_path, monkeypatch):
    class WallClock:
        instant = datetime(2026, 9, 5, 6, 59, tzinfo=timezone.utc)

        @classmethod
        def now(cls, zone):
            return cls.instant.astimezone(zone)

    monkeypatch.setattr(routing, "datetime", WallClock)
    ledger = str(tmp_path / "quota.sqlite3")
    allowance = routing.DailyAllowance("test-key-never-store", "gemini-3.6-flash", 2, path=ledger)
    assert allowance.acquire() is True
    assert allowance.acquire() is True
    reopened = routing.DailyAllowance("test-key-never-store", "gemini-3.6-flash", 2, path=ledger)
    assert reopened.acquire() is False
    assert b"test-key-never-store" not in (tmp_path / "quota.sqlite3").read_bytes()
    WallClock.instant = datetime(2026, 9, 5, 7, 0, tzinfo=timezone.utc)
    assert reopened.acquire() is True


def test_daily_allowance_is_atomic_across_independent_instances(tmp_path):
    path = str(tmp_path / "atomic.sqlite3")
    allowances = [routing.DailyAllowance("test-key", "gemini-3.6-flash", 3, path=path) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda index: allowances[index % 2].acquire(), range(12)))
    assert sum(results) == 3
    assert allowances[0].acquire() is False


def test_exhausted_daily_allowance_skips_gemini_without_sending(clock, tmp_path):
    daily = routing.DailyAllowance("test-key", "gemini-3.6-flash", 1, path=str(tmp_path / "quota.sqlite3"))
    assert daily.acquire() is True
    gemini = route(clock, "gemini", daily=daily)
    openai = route(clock, "openai", latency=2)
    assert parse(router_for(gemini, openai)).output_parsed.passed is True
    assert gemini.disabled
    assert not gemini.client.calls
    assert len(openai.client.calls) == 1


def test_provider_daily_quota_failure_disables_route_and_falls_back(clock):
    def exhausted():
        raise GeminiAPIError(code="daily_quota_exhausted", retryable=False, response=httpx.Response(429))
    gemini = route(clock, "gemini", operation=exhausted)
    openai = route(clock, "openai", latency=2)
    router = router_for(gemini, openai)
    assert parse(router).output_parsed.passed is True
    assert parse(router).output_parsed.passed is True
    assert gemini.disabled
    assert len(gemini.client.calls) == 1
    assert len(openai.client.calls) == 2


def test_cancellation_before_admission_does_not_send(clock):
    event = Event()
    event.set()
    openai = route(clock, "openai")
    with pytest.raises(CancelledError):
        parse(router_for(openai), cancel_event=event)
    assert not openai.client.calls
    assert not clock.sleeps


def test_cancellation_after_admission_prevents_network_dispatch(clock, monkeypatch):
    event = Event()
    openai = route(clock, "openai")
    real_acquire = openai.limiter.try_acquire

    def cancel_after_reserving(*args, **kwargs):
        reservation = real_acquire(*args, **kwargs)
        event.set()
        return reservation

    monkeypatch.setattr(openai.limiter, "try_acquire", cancel_after_reserving)
    router = router_for(openai)
    with pytest.raises(CancelledError):
        parse(router, cancel_event=event)
    assert not openai.client.calls
    assert openai.in_flight == 0
    assert len(router.events) == 1
