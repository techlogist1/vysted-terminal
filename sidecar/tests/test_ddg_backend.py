"""Tests for the keyless DuckDuckGo search floor (``services.search.ddg``)."""

from __future__ import annotations

import asyncio
from unittest import mock

import httpx
import pytest

from services.search.base import (
    SEARCH_REASON_RATE_LIMITED,
    SEARCH_REASON_UNREACHABLE,
    SearchError,
)
from services.search.ddg import BACKEND_ID, DdgSearchBackend

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


def test_ddg_makes_one_request_the_keyless_tier_owns_retry() -> None:
    """R15-RESEARCH-008: no private retry loop stacked under keyless's own."""

    class _CountingClient(_FakeClient):
        def __init__(self, resp: _FakeResp) -> None:
            super().__init__(resp)
            self.posts = 0

        async def post(self, url, data=None, headers=None):  # noqa: ANN001, ANN201
            self.posts += 1
            if "lite." in url:
                raise AssertionError("a failed HTML fetch must not fall through to Lite")
            return await super().post(url, data=data, headers=headers)

    for status in (503, 202):
        client = _CountingClient(_FakeResp("", status=status))
        with pytest.raises(SearchError):
            _run(DdgSearchBackend(client=client).search("q"))
        assert client.posts == 1, status


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


def test_403_then_429_reports_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-RESEARCH-039: the impersonated 403 fallback used to return text-or-
    None on a 2xx-only check, discarding a 429 the SAME way the plain lane's
    own status check catches — a hard-throttled engine read as 'unreachable'
    instead of 'rate-limited'. The impersonated lane's status must feed the
    same rate-limit gate."""
    from services.search import transport as transport_module
    from services.search.transport import FetchResult

    async def _impersonated_429(url, *, params=None, data=None, headers=None, **kw):  # noqa: ANN001, ANN202
        return FetchResult(status_code=429, text="too many", url=url)

    monkeypatch.setattr(transport_module, "impersonated_fetch", _impersonated_429)
    client = _FakeClient(_FakeResp("denied", status=403))
    with pytest.raises(SearchError) as excinfo:
        _run(DdgSearchBackend(client=client).search("nvda"))
    assert excinfo.value.reason == SEARCH_REASON_RATE_LIMITED


# --- R15-CODE-RESEARCH-009: pacing moved out of ddg.py to the caller --------
#
# The WS7 proactive token-bucket rate-limiter (`_TokenBucket`/`_get_bucket`,
# paced from inside `DdgSearchBackend._search_with`) is DELETED: it double-
# spent a budget the keyless tier's own `pacing.RequestQueue` already metered
# around each engine turn, plus double-paced the Lite fallback within one
# search. Pacing is now entirely the caller's job (keyless's rotation, or the
# registry's `_PacedBackend` for the bare "ddg" id) — this module no longer
# defines, imports, or calls any pacing primitive at all, which this test pins
# structurally (no bucket/pacing symbol survives on the module).


def test_no_internal_pacing_symbols_survive_on_the_module() -> None:
    from services.search import ddg as ddg_module

    for name in ("_TokenBucket", "_get_bucket", "_BUCKET", "_RATE_PER_MIN", "_RATE_PER_SEC"):
        assert not hasattr(ddg_module, name), name


def test_lite_fallback_makes_exactly_two_requests_no_pacing_wait() -> None:
    """A zero-row HTML answer falls through to Lite with no bucket/queue wait
    in between — ddg.py itself no longer paces anything (that is the caller's
    job now)."""
    client = _MapClient(
        {
            "html.duckduckgo.com": _FakeResp("<html><body>no results</body></html>"),
            "lite.duckduckgo.com": _FakeResp(_LITE_FIXTURE),
        }
    )
    resp = _run(DdgSearchBackend(client=client).search("nvda"))
    assert len(resp.results) == 1
    assert len(client.calls) == 2


def test_one_search_with_lite_fallback_takes_one_pacing_slot() -> None:
    """The bare ``"ddg"`` registry lane (the non-rotation path, paced by
    `registry._PacedBackend` since ddg.py no longer paces itself) acquires
    exactly ONE pacing slot for a whole `search()` call, even when it
    internally falls through HTML -> Lite — never one slot per internal hit."""
    from services.search import pacing
    from services.search.registry import _PacedBackend

    pacing.reset_queue()
    acquires: list[str] = []
    original_acquire = pacing.RequestQueue.acquire

    async def _counting_acquire(self, engine_id):  # noqa: ANN001
        acquires.append(engine_id)
        return await original_acquire(self, engine_id)

    client = _MapClient(
        {
            "html.duckduckgo.com": _FakeResp("<html><body>no results</body></html>"),
            "lite.duckduckgo.com": _FakeResp(_LITE_FIXTURE),
        }
    )
    backend = _PacedBackend(DdgSearchBackend(client=client), engine_id="ddg")
    with mock.patch.object(pacing.RequestQueue, "acquire", _counting_acquire):
        resp = _run(backend.search("nvda"))
    pacing.reset_queue()

    assert len(resp.results) == 1
    assert acquires == ["ddg"]
