"""Tests for the keyless DuckDuckGo search floor (``services.search.ddg``)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from services.search import ddg as ddg_module
from services.search.base import (
    SEARCH_REASON_RATE_LIMITED,
    SEARCH_REASON_UNREACHABLE,
    SearchError,
)
from services.search.ddg import BACKEND_ID, DdgSearchBackend, _TokenBucket

# A trimmed DuckDuckGo HTML results page: a uddg-redirect link, a direct link, and
# a protocol-relative link — covering the three href shapes the parser handles.
_FIXTURE = """
<div class="result results_links results_links_deep web-result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fnvda&rut=x">
    NVDA <b>Outlook</b></a>
  <a class="result__snippet">Strong <b>datacenter</b> demand drives growth.</a>
  <a class="result__url">example.com</a>
</div>
<div class="result results_links results_links_deep web-result">
  <a class="result__a" href="https://second.com/page">Second &amp; Source</a>
  <a class="result__snippet">A second result.</a>
  <a class="result__url">second.com</a>
</div>
"""


class _FakeResp:
    def __init__(self, text: str, status: int = 200) -> None:
        self.text = text
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=None)  # type: ignore[arg-type]


class _FakeClient:
    def __init__(self, resp: _FakeResp) -> None:
        self._resp = resp
        self.last: dict = {}

    async def post(self, url, data=None, headers=None):  # noqa: ANN001, ANN201
        self.last = {"url": url, "data": data, "headers": headers}
        return self._resp


def _run(coro):
    return asyncio.run(coro)


def test_parses_results_and_decodes_redirect() -> None:
    client = _FakeClient(_FakeResp(_FIXTURE))
    backend = DdgSearchBackend(region="US", client=client)
    resp = _run(backend.search("nvda datacenter demand"))

    assert resp.backend == BACKEND_ID
    assert len(resp.results) == 2
    first = resp.results[0]
    # uddg redirect decoded to the real target; tags stripped from title/snippet.
    assert first.url == "https://example.com/nvda"
    assert first.title == "NVDA Outlook"
    assert first.snippet == "Strong datacenter demand drives growth."
    assert resp.results[1].url == "https://second.com/page"
    assert resp.results[1].title == "Second & Source"
    # citations mirror the results.
    assert resp.citations[0].url == "https://example.com/nvda"
    # region maps to the DDG kl param.
    assert client.last["data"]["kl"] == "us-en"


def test_max_results_caps_output() -> None:
    client = _FakeClient(_FakeResp(_FIXTURE))
    backend = DdgSearchBackend(client=client)
    resp = _run(backend.search("q", options={"maxResults": 1}))
    assert len(resp.results) == 1


def test_empty_page_is_not_an_error() -> None:
    client = _FakeClient(_FakeResp("<html><body>no results</body></html>"))
    resp = _run(DdgSearchBackend(client=client).search("q"))
    assert resp.results == []  # an empty result set, not a raise


def test_transport_failure_raises_search_error() -> None:
    client = _FakeClient(_FakeResp("", status=503))
    with pytest.raises(SearchError) as excinfo:
        _run(DdgSearchBackend(client=client).search("q"))
    # WS3: a transport/unreachable failure carries the "unreachable" typed reason
    # so the brief reports a genuine no-backend miss, NOT a transient throttle.
    assert excinfo.value.reason == SEARCH_REASON_UNREACHABLE


# --- Track 3 keyless hardening ---------------------------------------------

_LITE_FIXTURE = """
<table>
  <tr><td>
    <a rel="nofollow" href="https://lite-ex.com/nvda"
       class="result-link">NVDA Lite <b>Result</b></a>
  </td></tr>
  <tr><td class="result-snippet">A lite-page snippet about datacenter demand.</td></tr>
</table>
"""


class _MapClient:
    """Returns a different response per endpoint (keyed by URL substring)."""

    def __init__(self, by_url: dict[str, _FakeResp]) -> None:
        self._by_url = by_url
        self.calls: list[str] = []

    async def post(self, url, data=None, headers=None):  # noqa: ANN001, ANN201
        self.calls.append(url)
        for needle, resp in self._by_url.items():
            if needle in url:
                return resp
        raise AssertionError(f"unexpected url {url}")


def test_rate_limit_status_raises_honest_error() -> None:
    """A 202 anomaly/soft-block surfaces a clear rate-limit SearchError (not a
    silent empty result the loop would read as 'no web data')."""
    client = _FakeClient(_FakeResp("<html>anomaly</html>", status=202))
    with pytest.raises(SearchError, match="rate-limit") as excinfo:
        _run(DdgSearchBackend(client=client).search("q"))
    # WS3: a transient throttle carries the typed "rate_limited" reason so the
    # brief banner says "rate-limited, retrying" — NOT the false "no backend".
    assert excinfo.value.reason == SEARCH_REASON_RATE_LIMITED


def test_rate_limit_429_also_tagged_transient() -> None:
    """429 (the other rate-limit status) is also tagged transient, not no-backend."""
    client = _FakeClient(_FakeResp("<html>too many</html>", status=429))
    with pytest.raises(SearchError) as excinfo:
        _run(DdgSearchBackend(client=client).search("q"))
    assert excinfo.value.reason == SEARCH_REASON_RATE_LIMITED


def test_lite_fallback_when_html_empty() -> None:
    """Zero rows from the HTML endpoint → fall back to the DDG Lite page."""
    client = _MapClient(
        {
            "html.duckduckgo.com": _FakeResp("<html><body>no results</body></html>"),
            "lite.duckduckgo.com": _FakeResp(_LITE_FIXTURE),
        }
    )
    resp = _run(DdgSearchBackend(client=client).search("nvda"))
    assert len(resp.results) == 1
    assert resp.results[0].url == "https://lite-ex.com/nvda"
    assert resp.results[0].title == "NVDA Lite Result"
    assert "datacenter demand" in resp.results[0].snippet
    # The HTML endpoint was tried first, then Lite.
    assert any("html.duckduckgo.com" in u for u in client.calls)
    assert any("lite.duckduckgo.com" in u for u in client.calls)


def test_403_falls_back_to_impersonated_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """R7 T1 hardening: a DDG 403 (TLS-fingerprint block) gets ONE retry over
    the curl_cffi Chrome-impersonation lane before counting as a failure."""
    from services.search import transport as transport_module
    from services.search.transport import FetchResult

    impersonated_calls: list[str] = []

    async def _fake_impersonated(url, *, params=None, data=None, headers=None, **kw):  # noqa: ANN001, ANN202
        impersonated_calls.append(url)
        return FetchResult(status_code=200, text=_FIXTURE, url=url)

    monkeypatch.setattr(transport_module, "impersonated_fetch", _fake_impersonated)
    client = _FakeClient(_FakeResp("denied", status=403))
    resp = _run(DdgSearchBackend(client=client).search("nvda"))
    assert len(resp.results) == 2
    assert resp.results[0].url == "https://example.com/nvda"
    assert impersonated_calls and "duckduckgo.com" in impersonated_calls[0]


def test_403_with_failed_impersonation_raises_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.search import transport as transport_module
    from services.search.transport import FetchResult

    async def _still_blocked(url, *, params=None, data=None, headers=None, **kw):  # noqa: ANN001, ANN202
        return FetchResult(status_code=403, text="denied", url=url)

    monkeypatch.setattr(transport_module, "impersonated_fetch", _still_blocked)
    client = _FakeClient(_FakeResp("denied", status=403))
    with pytest.raises(SearchError) as excinfo:
        _run(DdgSearchBackend(client=client).search("nvda"))
    assert excinfo.value.reason == SEARCH_REASON_UNREACHABLE


# --- WS7: proactive token-bucket rate-limiter ------------------------------
#
# These tests drive the bucket LOGIC with an INJECTED clock — no real-time
# sleeps — so they are deterministic, never wall-clock-flaky. Token accounting
# (refill maths + "how long must we wait") is asserted directly; we never block
# on a real `asyncio.sleep`.


class _FakeClock:
    """A monotonic clock whose value is advanced explicitly by the test."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, secs: float) -> None:
        self.now += secs


def test_token_bucket_first_request_is_immediate() -> None:
    """A fresh bucket starts FULL, so the very first acquire never sleeps."""
    clock = _FakeClock()
    bucket = _TokenBucket(rate_per_sec=0.4, capacity=5, clock=clock)

    # No token deficit at the start → zero wait, and the awaitable returns 0.0
    # WITHOUT a real-time sleep (the immediate path takes no asyncio.sleep).
    assert bucket.time_until_available() == 0.0
    assert _run(bucket.acquire()) == 0.0
    # ... and a single call must not have advanced wall-clock at all.
    assert clock.now == 1000.0


def test_token_bucket_paces_a_sustained_burst() -> None:
    """Once the initial tokens drain, the bucket reports a per-request WAIT —
    asserted via the pure `time_until_available` accounting, NOT by sleeping."""
    clock = _FakeClock()
    # capacity 3, refill 0.5 tok/sec → one new token every 2.0s.
    bucket = _TokenBucket(rate_per_sec=0.5, capacity=3, clock=clock)

    # Drain the full bucket: 3 immediate (zero-wait) acquires (no time elapses).
    assert _run(bucket.acquire()) == 0.0
    assert _run(bucket.acquire()) == 0.0
    assert _run(bucket.acquire()) == 0.0

    # Empty now (no time elapsed): the next request must wait a full refill
    # interval (2.0s). Asserted on the PURE accounting — no real sleep.
    assert bucket.time_until_available() == pytest.approx(2.0)
    # Halfway to a token (advance 1.0s at 0.5 tok/s = 0.5 token) → ~1.0s left.
    clock.advance(1.0)
    assert bucket.time_until_available() == pytest.approx(1.0)


def test_token_bucket_refills_over_time() -> None:
    """Tokens accrue with elapsed (injected) time and re-enable immediate
    acquires; refill saturates at capacity (no unbounded build-up). All asserted
    on the pure `time_until_available` accounting — deterministic, no real sleep."""
    clock = _FakeClock()
    bucket = _TokenBucket(rate_per_sec=1.0, capacity=2, clock=clock)

    # Drain both tokens (immediate).
    assert _run(bucket.acquire()) == 0.0
    assert _run(bucket.acquire()) == 0.0
    # Empty now: a request would wait 1.0s.
    assert bucket.time_until_available() == pytest.approx(1.0)

    # Advance 1s → exactly one token refilled → no wait.
    clock.advance(1.0)
    assert bucket.time_until_available() == 0.0
    assert _run(bucket.acquire()) == 0.0  # consume the refilled token

    # Advance well past capacity → bucket saturates at `capacity`, not beyond:
    # two tokens available (two immediate acquires), then a wait reappears.
    clock.advance(100.0)
    assert _run(bucket.acquire()) == 0.0
    assert _run(bucket.acquire()) == 0.0
    assert bucket.time_until_available() == pytest.approx(1.0)


def test_module_bucket_is_lazy_and_process_global() -> None:
    """The DDG floor's bucket is a module-level singleton, lazily built on first
    use (never an asyncio primitive at import time)."""
    # Reset any state a prior test left, to assert the lazy-init path.
    ddg_module._BUCKET = None
    first = ddg_module._get_bucket()
    second = ddg_module._get_bucket()
    assert first is second  # process-global singleton
    assert isinstance(first, _TokenBucket)


def test_limiter_does_not_delay_a_single_search() -> None:
    """End-to-end: the limiter sits in front of the fetch but the FIRST search
    passes immediately (full bucket) — existing single-call tests stay fast."""
    # Fresh bucket → full → no pacing wait on the one request.
    ddg_module._BUCKET = None
    client = _FakeClient(_FakeResp(_FIXTURE))
    backend = DdgSearchBackend(region="US", client=client)
    resp = _run(backend.search("nvda"))
    assert len(resp.results) == 2
