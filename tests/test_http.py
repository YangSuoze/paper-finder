import httpx
import pytest
from paper_finder.errors import ProviderError
from paper_finder.http import HttpClient, RetryConfig


def test_http_client_retries_on_retryable_status() -> None:
    calls = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True})

    sleeps: list[float] = []
    with HttpClient(
        retry=RetryConfig(max_retries=2, backoff_seconds=0.5),
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    ) as client:
        payload = client.get_json("https://example.org/test", provider="example")

    assert payload == {"ok": True}
    assert calls["count"] == 2
    assert len(sleeps) == 1
    assert sleeps[0] == pytest.approx(0.0)


def test_http_client_raises_after_exhausting_retries() -> None:
    calls = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(503, text="temporarily unavailable")

    with (
        HttpClient(
            retry=RetryConfig(max_retries=2, backoff_seconds=0.1),
            transport=httpx.MockTransport(handler),
            sleep=lambda _: None,
        ) as client,
        pytest.raises(ProviderError) as exc,
    ):
        client.get_json("https://example.org/test", provider="example")

    assert calls["count"] == 3
    assert exc.value.status_code == 503
    assert "HTTP 503" in str(exc.value)


def test_http_client_retries_transport_errors() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"ok": True})

    with HttpClient(
        retry=RetryConfig(max_retries=3, backoff_seconds=0.1),
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    ) as client:
        payload = client.get_json("https://example.org/test", provider="example")

    assert payload == {"ok": True}
    assert calls["count"] == 3


def test_http_client_applies_jitter_to_exponential_backoff() -> None:
    calls = {"count": 0}
    sleeps: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, text="retry")
        return httpx.Response(200, json={"ok": True})

    with HttpClient(
        retry=RetryConfig(max_retries=1, backoff_seconds=0.5, jitter_fraction=0.2),
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        random_fn=lambda: 1.0,  # max positive jitter
    ) as client:
        payload = client.get_json("https://example.org/test", provider="example")

    assert payload == {"ok": True}
    assert sleeps == [pytest.approx(0.6)]
