"""Tests for the keyless DuckDuckGo search floor (``services.search.ddg``)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from services.search.base import SearchError
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
    with pytest.raises(SearchError):
        _run(DdgSearchBackend(client=client).search("q"))
