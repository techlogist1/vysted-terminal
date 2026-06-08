"""Tests for the keyless DuckDuckGo search floor (``services.search.ddg``)."""

from __future__ import annotations

import asyncio

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
