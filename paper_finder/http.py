from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .errors import NotFoundError, ProviderError

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


@dataclass(frozen=True, slots=True)
class RetryConfig:
    max_retries: int = 3
    backoff_seconds: float = 0.5
    max_backoff_seconds: float = 8.0
    jitter_fraction: float = 0.1


class HttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        retry: RetryConfig | None = None,
        transport: httpx.BaseTransport | None = None,
        user_agent: str = "paper-finder/0.2.0",
        sleep: Callable[[float], None] = time.sleep,
        random_fn: Callable[[], float] = random.random,
    ) -> None:
        self._retry = retry or RetryConfig()
        self._sleep = sleep
        self._random_fn = random_fn
        timeout = httpx.Timeout(timeout_seconds)
        self._client = httpx.Client(
            timeout=timeout, transport=transport, headers={"User-Agent": user_agent}
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        url: str,
        *,
        provider: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        for attempt in range(self._retry.max_retries + 1):
            try:
                response = self._client.request(method, url, params=params, headers=headers)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt >= self._retry.max_retries:
                    raise ProviderError(
                        provider,
                        f"{provider} request to {url} failed after {attempt + 1} attempts: {exc}",
                    ) from exc
                self._sleep(self._compute_backoff_seconds(attempt, None))
                continue

            if (
                response.status_code in _RETRYABLE_STATUS_CODES
                and attempt < self._retry.max_retries
            ):
                self._sleep(self._compute_backoff_seconds(attempt, response))
                continue

            if response.status_code == httpx.codes.NOT_FOUND:
                raise NotFoundError(provider, f"{provider} resource not found.", status_code=404)

            if response.is_error:
                body = response.text.strip()
                suffix = f": {body[:300]}" if body else "."
                raise ProviderError(
                    provider,
                    f"{provider} API request to {url} failed with HTTP {response.status_code}{suffix}",
                    status_code=response.status_code,
                )

            return response

        raise ProviderError(provider, f"{provider} request failed for an unknown reason.")

    def get_json(
        self,
        url: str,
        *,
        provider: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = self.request("GET", url, provider=provider, params=params, headers=headers)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError(provider, f"{provider} returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise ProviderError(provider, f"{provider} returned an unexpected response shape.")

        return payload

    def get_text(
        self,
        url: str,
        *,
        provider: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        response = self.request("GET", url, provider=provider, params=params, headers=headers)
        return response.text

    def _compute_backoff_seconds(self, attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            retry_after = self._parse_retry_after(response.headers.get("Retry-After"))
            if retry_after is not None:
                return min(max(0.0, retry_after), self._retry.max_backoff_seconds)

        delay = self._retry.backoff_seconds * (2**attempt)
        delay = float(min(delay, self._retry.max_backoff_seconds))
        jitter_fraction = self._retry.jitter_fraction
        if jitter_fraction <= 0 or delay <= 0:
            return delay

        jitter = delay * jitter_fraction * (self._random_fn() * 2 - 1)
        return float(min(max(0.0, delay + jitter), self._retry.max_backoff_seconds))

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        if value is None:
            return None

        stripped = value.strip()
        if not stripped:
            return None

        try:
            return float(stripped)
        except ValueError:
            pass

        try:
            target = parsedate_to_datetime(stripped)
        except (TypeError, ValueError):
            return None

        now = time.time()
        return target.timestamp() - now
