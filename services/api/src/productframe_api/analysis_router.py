"""Capacity-aware vision requests; safety decisions are never retried elsewhere."""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import threading
import time
from concurrent.futures import CancelledError
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

from .analysis_limits import AnalysisBudgetError, AnalysisLimits, RateLimiter, estimate_request_tokens, retry_delay
from .gemini_analysis import GeminiClient, GeminiSafetyError, estimate_gemini_input_tokens

logger = logging.getLogger(__name__)
_affinity: ContextVar[str | None] = ContextVar("analysis_provider", default=None)
_gemini_limiters: dict[tuple, RateLimiter] = {}
_gemini_lock = threading.Lock()


class AnalysisSafetyError(ValueError):
    """A terminal refusal; never an invitation to try a different model."""


class DailyAllowance:
    """Persist this application's admissions across restarts, in Pacific days.

    This cannot see requests made by other applications on the same project.
    Only a credential fingerprint, model, day and count are stored.
    """

    def __init__(self, key: str, model: str, limit: int, path: str | None = None):
        self.bucket = hashlib.sha256(key.encode()).hexdigest()[:24] + ":" + model
        self.limit = limit
        self.path = path or os.environ.get("ANALYSIS_QUOTA_DB", str(Path(__file__).resolve().parents[4] / ".cache" / "analysis-quotas.sqlite3"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS daily_admissions (bucket TEXT, day TEXT, count INTEGER NOT NULL, PRIMARY KEY(bucket, day))")

    def acquire(self) -> bool:
        day = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT count FROM daily_admissions WHERE bucket=? AND day=?", (self.bucket, day)).fetchone()
            if row and row[0] >= self.limit:
                return False
            db.execute("INSERT INTO daily_admissions VALUES (?, ?, 1) ON CONFLICT(bucket,day) DO UPDATE SET count=count+1", (self.bucket, day))
            return True


@dataclass
class Route:
    name: str
    model: str
    limiter: RateLimiter
    client: object
    daily: DailyAllowance | None = None
    in_flight: int = 0
    latency: float = 5.0
    disabled: bool = False


def _positive_env(name: str, default: int) -> int:
    value = int(os.environ.get(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


class AnalysisRouter:
    def __init__(self, client, model: str, limiter: RateLimiter, *, routes: list[Route] | None = None):
        self._lock = threading.Lock()
        self.routes = routes if routes is not None else [Route("openai", model, limiter, client)]
        self.events: list[dict] = []
        if routes is None and os.environ.get("GEMINI_API_KEY") and os.environ.get("ANALYSIS_PROVIDER_MODE", "hybrid") == "hybrid":
            key = os.environ["GEMINI_API_KEY"]
            gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
            limits = AnalysisLimits(
                concurrency=limiter.limits.concurrency,
                max_input_tokens=min(limiter.limits.max_input_tokens, _positive_env("GEMINI_MAX_INPUT_TOKENS", 32_000)),
                max_output_tokens=limiter.limits.max_output_tokens,
                tokens_per_minute=_positive_env("GEMINI_TOKENS_PER_MINUTE", 225_000),
                requests_per_minute=_positive_env("GEMINI_REQUESTS_PER_MINUTE", 4),
            )
            fingerprint = hashlib.sha256(key.encode()).hexdigest()
            bucket = (fingerprint, gemini_model, limits)
            with _gemini_lock:
                gemini_limiter = _gemini_limiters.setdefault(bucket, RateLimiter(limits))
            self.routes.append(Route("gemini", gemini_model, gemini_limiter, GeminiClient(api_key=key),
                                     DailyAllowance(key, gemini_model, _positive_env("GEMINI_REQUESTS_PER_DAY", 18))))

    def close(self):
        for route in self.routes:
            if route.name == "gemini":
                route.client.close()

    def parse(self, *, input: list, text_format, output_tokens: int, cancel_event=None, grouping: bool = False):
        """Retry only the current stage. Successful earlier gates stay completed."""
        estimates = {
            route.name: (estimate_gemini_input_tokens(input, text_format=text_format, model=route.model)
                         if route.name == "gemini" else estimate_request_tokens(input, text_format=text_format, model=route.model))
            for route in self.routes if not grouping or route.name == "openai"
        }
        last_error = None
        for attempt in range(8):
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise CancelledError("Image analysis cancelled")
                choices = []
                with self._lock:
                    for route in self.routes:
                        if route.disabled or route.name not in estimates:
                            continue
                        try:
                            delay = route.limiter.availability_delay(estimates[route.name], output_tokens, cancel_event=cancel_event)
                        except AnalysisBudgetError as exc:
                            last_error = exc
                            continue
                        # A pinned image keeps its provider while capacity exists.
                        # Otherwise new work uses capacity and observed completion time.
                        score = delay + route.latency * (route.in_flight + 1)
                        if route.name == _affinity.get() and delay == 0 and not grouping:
                            score *= 0.8
                        choices.append((delay > 0, score, route))
                    choices.sort(key=lambda item: item[:2])
                    chosen = None
                    for waiting, score, route in choices:
                        if waiting:
                            continue
                        if cancel_event is not None and cancel_event.is_set():
                            raise CancelledError("Image analysis cancelled")
                        reservation = route.limiter.try_acquire(estimates[route.name], output_tokens, cancel_event=cancel_event)
                        if reservation is None:
                            continue
                        if route.daily is not None and not route.daily.acquire():
                            route.limiter.observe(reservation)
                            route.disabled = True
                            logger.info("analysis route unavailable provider=%s reason=daily_application_budget", route.name)
                            continue
                        route.in_flight += 1
                        chosen = (route, reservation)
                        break
                if chosen:
                    break
                if not choices:
                    raise RuntimeError("No analysis provider has usable capacity for this stage") from last_error
                if cancel_event is not None:
                    if cancel_event.wait(0.25):
                        raise CancelledError("Image analysis cancelled")
                else:
                    time.sleep(0.25)

            route, reservation = chosen
            started = time.monotonic()
            headers = None
            outcome = "failed"
            usage = None
            try:
                if cancel_event is not None and cancel_event.is_set():
                    raise CancelledError("Image analysis cancelled")
                if route.name == "gemini":
                    response = route.client.parse(model=route.model, input=input, text_format=text_format, max_output_tokens=output_tokens)
                    headers = response.headers
                else:
                    raw = route.client.responses.with_raw_response.parse(model=route.model, input=input, text_format=text_format, max_output_tokens=output_tokens, store=False)
                    headers = raw.headers
                    response = raw.parse()
                    if getattr(getattr(response, "incomplete_details", None), "reason", None) == "content_filter":
                        raise AnalysisSafetyError("Image did not pass the provider safety check.")
                    if any(getattr(part, "type", None) == "refusal" for item in (getattr(response, "output", None) or []) for part in (getattr(item, "content", None) or [])):
                        raise AnalysisSafetyError("Image did not pass the provider safety check.")
                if response.output_parsed is None:
                    raise ValueError("Provider returned no structured analysis")
                usage = getattr(response, "usage", None)
                _affinity.set(route.name)
                outcome = "completed"
                return response
            except CancelledError:
                raise
            except (GeminiSafetyError, AnalysisSafetyError) as exc:
                outcome = "safety_rejected"
                raise AnalysisSafetyError("Image did not pass the provider safety check.") from exc
            except Exception as exc:
                last_error = exc
                headers = headers or getattr(getattr(exc, "response", None), "headers", None)
                permanent = getattr(exc, "permanent", False) or getattr(exc, "status_code", None) in {401, 403, 404}
                if getattr(exc, "code", None) in {"insufficient_quota", "billing_hard_limit_reached"}:
                    permanent = True
                if permanent:
                    with self._lock:
                        route.disabled = True
                else:
                    delay = retry_delay(exc, attempt)
                    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)) or (getattr(exc, "retryable", False) and delay is None):
                        delay = min(60, 2 ** (attempt + 1))
                    if isinstance(exc, (ValidationError, ValueError)) and attempt < 2:
                        delay = 0
                    if delay is None:
                        raise
                    route.limiter.defer(delay)
            finally:
                route.limiter.observe(reservation, headers)
                elapsed = time.monotonic() - started
                with self._lock:
                    route.in_flight -= 1
                    route.latency = route.latency * 0.7 + elapsed * 0.3
                    event = {"provider": route.name, "model": route.model, "stage": text_format.__name__, "attempt": attempt + 1,
                             "seconds": round(elapsed, 3), "outcome": outcome, "estimated_input_tokens": estimates[route.name],
                             "input_tokens": getattr(usage, "input_tokens", None), "output_tokens": getattr(usage, "output_tokens", None)}
                    self.events.append(event)
                logger.info("analysis request %s", event)
        raise RuntimeError("Analysis provider retries exhausted") from last_error
