"""Conservative request sizing and per-process admission for image analysis.

Every network attempt must acquire its own reservation. A completed or failed
attempt keeps its rolling-window charge; provider headers can only tighten it.
Separate model/rate buckets should use separate RateLimiter instances.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
import random
import re
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Mapping
from concurrent.futures import CancelledError
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Any

from openai import APIConnectionError, APITimeoutError
from PIL import Image


class AnalysisBudgetError(ValueError):
    """A request cannot fit the configured or observed capacity."""


@dataclass(frozen=True)
class AnalysisLimits:
    concurrency: int = 3
    max_input_tokens: int = 110_000
    max_output_tokens: int = 4_096
    tokens_per_minute: int = 180_000
    requests_per_minute: int = 60

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"ANALYSIS_{name.upper()} must be a positive integer")
        if self.concurrency > 8:
            raise ValueError("ANALYSIS_CONCURRENCY must not exceed 8")
        if self.max_input_tokens > 120_000 or self.max_output_tokens > 8_000:
            raise ValueError("Analysis input/output limits must not exceed 120000/8000 tokens")
        if self.max_input_tokens + self.max_output_tokens > 128_000:
            raise ValueError("Analysis input and output limits must fit within 128000 tokens")

    @classmethod
    def from_env(cls) -> AnalysisLimits:
        values: dict[str, int] = {}
        for name in cls.__dataclass_fields__:
            raw = os.environ.get(f"ANALYSIS_{name.upper()}")
            if raw is not None:
                try:
                    values[name] = int(raw)
                except ValueError as exc:
                    raise ValueError(f"ANALYSIS_{name.upper()} must be an integer") from exc
        return cls(**values)


@dataclass(frozen=True)
class Reservation:
    number: int
    started_at: float
    tokens: int


@dataclass
class _RemainingGuard:
    # Keep the provider snapshot separate from local reservations. A response
    # reconciles its reservation instead of permanently shrinking the snapshot.
    remaining: int
    resets_at: float
    pending: dict[int, Reservation] = field(default_factory=dict)


def _duration(value: str | None) -> float | None:
    """Read provider reset durations such as 1m2.5s or 1500ms."""
    if value is None:
        return None
    value = value.strip().lower()
    try:
        seconds = float(value)
    except ValueError:
        if not re.fullmatch(r"(?:\d+(?:\.\d+)?(?:ms|s|m|h))+", value):
            return None
        factors = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}
        seconds = sum(float(amount) * factors[unit] for amount, unit in re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h)", value))
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


def _nonnegative_int(value: str | None) -> int | None:
    try:
        number = int(value) if value is not None else -1
        return number if number >= 0 else None
    except (TypeError, ValueError):
        return None


class RateLimiter:
    """Reserve requests/tokens atomically, without holding a lock while waiting."""

    def __init__(
        self,
        limits: AnalysisLimits,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.limits = limits
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._history: deque[Reservation] = deque()
        self._in_flight: dict[int, Reservation] = {}
        self._next_number = 0
        self._token_limit = limits.tokens_per_minute
        self._request_limit = limits.requests_per_minute
        self._guards: dict[str, _RemainingGuard] = {}
        self._cooldown_until = 0.0

    def input_budget(self, output_tokens: int | None = None) -> int:
        output = self.limits.max_output_tokens if output_tokens is None else output_tokens
        with self._lock:
            return max(0, min(self.limits.max_input_tokens, self._token_limit - output))

    def _expire(self, now: float) -> None:
        while self._history and self._history[0].started_at + 60 <= now:
            self._history.popleft()
        self._guards = {kind: guard for kind, guard in self._guards.items() if guard.resets_at > now}

    def _validate_request(self, input_tokens: int, output_tokens: int) -> int:
        for amount in (input_tokens, output_tokens):
            if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
                raise ValueError("Request token estimates must be nonnegative integers")
        if input_tokens > self.limits.max_input_tokens:
            raise AnalysisBudgetError(f"Estimated input ({input_tokens} tokens) exceeds the analysis input limit ({self.limits.max_input_tokens})")
        if output_tokens > self.limits.max_output_tokens:
            raise AnalysisBudgetError(f"Requested output ({output_tokens} tokens) exceeds the analysis output limit ({self.limits.max_output_tokens})")
        return input_tokens + output_tokens

    def _ready_at(self, tokens: int, now: float) -> float:
        """Called under the lock, for both previewing and reserving capacity."""
        self._expire(now)
        if tokens > self._token_limit:
            raise AnalysisBudgetError(f"Estimated request ({tokens} tokens) exceeds the available per-minute token limit ({self._token_limit}); reduce request size or increase the configured capacity")
        ready_at = max(now, self._cooldown_until)
        used_tokens = sum(item.tokens for item in self._history)
        if used_tokens + tokens > self._token_limit:
            for item in self._history:
                used_tokens -= item.tokens
                ready_at = max(ready_at, item.started_at + 60)
                if used_tokens + tokens <= self._token_limit:
                    break
        if len(self._history) + 1 > self._request_limit:
            expires = self._history[len(self._history) - self._request_limit].started_at + 60
            ready_at = max(ready_at, expires)
        for kind, guard in self._guards.items():
            pending = len(guard.pending) if kind == "requests" else sum(item.tokens for item in guard.pending.values())
            requested = 1 if kind == "requests" else tokens
            if requested > max(0, guard.remaining - pending):
                ready_at = max(ready_at, guard.resets_at)
        return ready_at

    def _admission(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        reserve: bool,
        cancel_event: threading.Event | None,
    ) -> tuple[Reservation | None, float]:
        tokens = self._validate_request(input_tokens, output_tokens)
        with self._lock:
            if cancel_event is not None and cancel_event.is_set():
                raise CancelledError("Image analysis was cancelled")
            now = self._clock()
            wait = max(0.0, self._ready_at(tokens, now) - now)
            if wait > 0 or not reserve:
                return None, wait
            reservation = Reservation(self._next_number, now, tokens)
            self._next_number += 1
            self._history.append(reservation)
            self._in_flight[reservation.number] = reservation
            for guard in self._guards.values():
                guard.pending[reservation.number] = reservation
            return reservation, 0.0

    def try_acquire(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        cancel_event: threading.Event | None = None,
    ) -> Reservation | None:
        """Reserve immediately if possible; never sleep or reserve future slots."""
        reservation, _ = self._admission(input_tokens, output_tokens, reserve=True, cancel_event=cancel_event)
        return reservation

    def availability_delay(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        cancel_event: threading.Event | None = None,
    ) -> float:
        """Preview admission delay without reserving capacity for this caller.

        Another caller can reserve first, so a router must still try_acquire.
        Pending responses can release conservative header padding earlier.
        """
        _, wait = self._admission(input_tokens, output_tokens, reserve=False, cancel_event=cancel_event)
        return wait

    def acquire(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        cancel_event: threading.Event | None = None,
    ) -> Reservation:
        while True:
            reservation, wait = self._admission(input_tokens, output_tokens, reserve=True, cancel_event=cancel_event)
            if reservation is not None:
                return reservation
            if cancel_event is not None:
                if cancel_event.is_set():
                    raise CancelledError("Image analysis was cancelled")
                wait = min(wait, 0.25)
            self._sleep(wait)

    def observe(self, reservation: Reservation, headers: Mapping[str, str] | None = None) -> None:
        """Finish one attempt and conservatively apply its provider rate headers.

        A raw remaining snapshot and its reset belong to one provider bucket.
        Keep model, project, and request buckets independent. Other requests may
        not be reflected yet, so retain their pending deductions until their own
        corresponding headers arrive. Older/larger snapshots cannot increase a
        guard, but reconciled reservations stop being subtracted a second time.
        """
        normalized = {key.lower(): value for key, value in (headers or {}).items()}
        with self._lock:
            now = self._clock()
            self._expire(now)
            if self._in_flight.pop(reservation.number, None) is None:
                return
            for suffix in ("tokens", "project-tokens"):
                token_limit = _nonnegative_int(normalized.get(f"x-ratelimit-limit-{suffix}"))
                if token_limit:
                    self._token_limit = min(self._token_limit, token_limit)
            request_limit = _nonnegative_int(normalized.get("x-ratelimit-limit-requests"))
            if request_limit:
                self._request_limit = min(self._request_limit, request_limit)
            for kind in ("tokens", "project-tokens", "requests"):
                remaining = _nonnegative_int(normalized.get(f"x-ratelimit-remaining-{kind}"))
                if remaining is None:
                    continue
                duration = _duration(normalized.get(f"x-ratelimit-reset-{kind}"))
                resets_at = now + (60.0 if duration is None else duration)
                guard = self._guards.get(kind)
                if guard:
                    guard.remaining = min(guard.remaining, remaining)
                    guard.resets_at = max(guard.resets_at, resets_at)
                    guard.pending.pop(reservation.number, None)
                else:
                    self._guards[kind] = _RemainingGuard(remaining, resets_at, dict(self._in_flight))

    def defer(self, seconds: float) -> None:
        """A retry delay blocks new attempts across this shared model bucket."""
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Cooldown must be finite and nonnegative")
        with self._lock:
            self._cooldown_until = max(self._cooldown_until, self._clock() + seconds)


_dimension_cache: OrderedDict[str, tuple[int, int]] = OrderedDict()
_dimension_lock = threading.Lock()
_DIMENSION_CACHE_SIZE = 128


def _image_dimensions(url: str, *, model: str = "gpt-4o-mini") -> tuple[int, int]:
    if not url.startswith("data:"):
        # Reserve the supported model's worst case without fetching remote data.
        return (2048, 2048) if model.removeprefix("openai/").startswith("gpt-4.1-mini") else (2048, 768)
    digest = hashlib.sha256(url.encode()).hexdigest()
    with _dimension_lock:
        if digest in _dimension_cache:
            _dimension_cache.move_to_end(digest)
            return _dimension_cache[digest]
    try:
        header, encoded = url.split(",", 1)
        if ";base64" not in header:
            raise ValueError("Image data URLs must use base64 encoding")
        with Image.open(io.BytesIO(base64.b64decode(encoded, validate=True))) as image:
            dimensions = image.size
    except Exception as exc:
        raise ValueError("Cannot estimate tokens for an unreadable image data URL") from exc
    with _dimension_lock:
        _dimension_cache[digest] = dimensions
        _dimension_cache.move_to_end(digest)
        while len(_dimension_cache) > _DIMENSION_CACHE_SIZE:
            _dimension_cache.popitem(last=False)
    return dimensions


def image_token_cost(width: int, height: int, model: str = "gpt-4o-mini", *, detail: str = "high") -> int:
    """Size supported vision models using their documented patch/tile rules.

    GPT-4.1 mini uses 32px patches, a 2048px maximum dimension, a 6144-patch
    budget, and a 1.62 multiplier for low/high/auto. GPT-4o mini and unknown
    overrides retain the conservative 2833-base / 5667-tile estimate.
    """
    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive")
    if model.removeprefix("openai/").startswith("gpt-4.1-mini"):
        scale = min(1.0, 2048 / max(width, height))
        # Round coverage up when fitting dimensions to avoid under-reserving a
        # fractional edge patch. Existing preprocessed images need no resizing.
        fitted_width = max(1, min(2048, math.ceil(width * scale)))
        fitted_height = max(1, min(2048, math.ceil(height * scale)))
        patches = math.ceil(fitted_width / 32) * math.ceil(fitted_height / 32)
        patch_budget = 6144
        if patches > patch_budget:
            shrink = math.sqrt(32 ** 2 * patch_budget / (fitted_width * fitted_height))
            shrink *= min(
                math.floor(fitted_width * shrink / 32) / (fitted_width * shrink / 32),
                math.floor(fitted_height * shrink / 32) / (fitted_height * shrink / 32),
            )
            fitted_width = max(1, math.floor(fitted_width * shrink))
            fitted_height = max(1, math.floor(fitted_height * shrink))
            patches = math.ceil(fitted_width / 32) * math.ceil(fitted_height / 32)
        return math.ceil(patches * 1.62)
    if detail == "low":
        return 2833
    scale = min(1.0, 2048 / max(width, height), 768 / min(width, height))
    tiles = math.ceil(width * scale / 512) * math.ceil(height * scale / 512)
    return 2833 + 5667 * tiles


def estimate_request_tokens(input: Any, *, text_format: Any = None, model: str = "gpt-4o-mini") -> int:
    """Upper-bound text by UTF-8 bytes, include schema, and size image tiles.

    The base64 transport representation is replaced before counting text, so it
    does not overwhelm the actual visual-token estimate.
    """
    image_tokens = 0

    def without_image_data(value: Any) -> Any:
        nonlocal image_tokens
        if isinstance(value, dict):
            if value.get("type") in {"input_image", "image_url"}:
                url = value.get("image_url")
                if isinstance(url, dict):
                    url = url.get("url")
                if not isinstance(url, str):
                    raise ValueError("Image input must contain an image URL")
                width, height = _image_dimensions(url, model=model)
                image_tokens += image_token_cost(width, height, model, detail=value.get("detail", "high"))
                return {key: "[image]" if key == "image_url" else without_image_data(item) for key, item in value.items()}
            return {key: without_image_data(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [without_image_data(item) for item in value]
        return value

    payload = {"input": without_image_data(input)}
    if text_format is not None:
        payload["schema"] = text_format.model_json_schema() if hasattr(text_format, "model_json_schema") else text_format
    # JSON punctuation/role fields and a fixed message overhead make this more
    # conservative than just counting prompt characters.
    return image_tokens + len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) + 128


def retry_delay(
    error: Exception,
    attempt: int,
    *,
    random_value: Callable[[], float] = random.random,
    wall_time: Callable[[], float] = time.time,
) -> float | None:
    """Return a shared retry delay, or None for a permanent/non-transient error."""
    if getattr(error, "permanent", False) or getattr(error, "retryable", None) is False:
        return None
    body = getattr(error, "body", None)
    code = getattr(error, "code", None)
    if isinstance(body, dict):
        detail = body.get("error", body)
        if isinstance(detail, dict):
            code = code or detail.get("code")
    if code in {"insufficient_quota", "billing_hard_limit_reached"}:
        return None
    status = getattr(error, "status_code", None)
    transient = getattr(error, "retryable", None) is True or status in {408, 409, 429} or (isinstance(status, int) and 500 <= status < 600)
    if not transient and not isinstance(error, (APIConnectionError, APITimeoutError)):
        return None
    response = getattr(error, "response", None)
    headers = {key.lower(): value for key, value in getattr(response, "headers", {}).items()}
    milliseconds = _duration(headers.get("retry-after-ms"))
    if milliseconds is not None:
        return milliseconds / 1000
    seconds = _duration(headers.get("retry-after"))
    if seconds is not None:
        return seconds
    if headers.get("retry-after"):
        try:
            reset_at = parsedate_to_datetime(headers["retry-after"]).timestamp()
            return max(0.0, reset_at - wall_time())
        except (TypeError, ValueError, OverflowError):
            pass
    return min(60.0, 2.0 * (2 ** min(max(attempt, 0), 8))) + random_value()
