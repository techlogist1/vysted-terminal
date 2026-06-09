"""Tests for the Mojeek HTML engine adapter (``services.search.mojeek``)."""

from __future__ import annotations

import asyncio

import pytest

from services.search.base import (
    SEARCH_REASON_RATE_LIMITED,
    SEARCH_REASON_UNREACHABLE,
    SearchError,
)
from services.search.mojeek import BACKEND_ID, MojeekSearchBackend
from services.search.transport import FetchResult, TransportError

# A trimmed Mojeek SERP: standard results list with title anchor + p.s snippet,
# a mojeek self-link to skip, and a duplicate URL.
_FIXTURE = """
<ul class="results-standard">
  <li>
    <h2><a class="title" href="https://example.com/nvda">NVDA <b>Outlook</b></a></h2>
    <p class="s">Strong datacenter demand drives growth.</p>
    <p class="i">example.com</p>
  </li>
  <li>
    <h2><a class="title" href="https://www.mojeek.com/about">About Mojeek</a></h2>
    <p class="s">Self link.</p>
  </li>
  <li>
    <h2><a class="title" href="https://second.com/page">Second &amp; Source</a></h2>
    <p class="s">A second result.</p>
  </li>
  <li>
    <h2><a class="title" href="https://example.com/nvda">Duplicate</a></h2>
  </li>
</ul>
"""

# Drifted markup: no results-standard class, no a.title — loose fallback path.
_DRIFTED = """
<ul class="results">
  <li><a href="https://drift.com/article">Drifted result title</a></li>
</ul>
"""


def _fetcher(result: FetchResult, calls: list[dict]):
    async def _fetch(url, *, params=None, data=None, headers=None, **kw):  # noqa: ANN001, ANN202
        calls.append({"url": url, "params": params})
        return result

    return _fetch


def _run(coro):
    return asyncio.run(coro)


def test_parses_results_skips_self_links_and_dupes() -> None:
    calls: list[dict] = []
    fetched = FetchResult(status_code=200, text=_FIXTURE, url="https://www.mojeek.com/search")
    backend = MojeekSearchBackend(region="IN", fetch=_fetcher(fetched, calls))
    resp = _run(backend.search("nvda datacenter demand"))

    assert resp.backend == BACKEND_ID
    assert [r.url for r in resp.results] == ["https://example.com/nvda", "https://second.com/page"]
    assert resp.results[0].title == "NVDA Outlook"
    assert resp.results[0].snippet == "Strong datacenter demand drives growth."
    assert resp.results[1].title == "Second & Source"
    assert resp.results[0].source == "mojeek"
    assert resp.citations[1].url == "https://second.com/page"
    # Region biases the arc param.
    assert calls[0]["params"]["arc"] == "in"


def test_drifted_markup_still_yields_a_row() -> None:
    fetched = FetchResult(status_code=200, text=_DRIFTED, url="u")
    backend = MojeekSearchBackend(fetch=_fetcher(fetched, []))
    resp = _run(backend.search("x"))
    assert len(resp.results) == 1
    assert resp.results[0].url == "https://drift.com/article"


def test_zero_rows_is_empty_success_not_error() -> None:
    fetched = FetchResult(status_code=200, text="<html><body>none</body></html>", url="u")
    backend = MojeekSearchBackend(fetch=_fetcher(fetched, []))
    resp = _run(backend.search("x"))
    assert resp.results == []


def test_max_results_caps_output() -> None:
    fetched = FetchResult(status_code=200, text=_FIXTURE, url="u")
    backend = MojeekSearchBackend(fetch=_fetcher(fetched, []))
    resp = _run(backend.search("x", options={"numResults": 1}))
    assert len(resp.results) == 1


@pytest.mark.parametrize("status", [403, 429])
def test_block_statuses_raise_typed_rate_limit(status: int) -> None:
    fetched = FetchResult(status_code=status, text="blocked", url="u")
    backend = MojeekSearchBackend(fetch=_fetcher(fetched, []))
    with pytest.raises(SearchError) as err:
        _run(backend.search("x"))
    assert err.value.reason == SEARCH_REASON_RATE_LIMITED


def test_server_error_raises_unreachable() -> None:
    fetched = FetchResult(status_code=503, text="oops", url="u")
    backend = MojeekSearchBackend(fetch=_fetcher(fetched, []))
    with pytest.raises(SearchError) as err:
        _run(backend.search("x"))
    assert err.value.reason == SEARCH_REASON_UNREACHABLE


def test_transport_failure_raises_unreachable() -> None:
    async def _boom(url, **kw):  # noqa: ANN001, ANN202
        raise TransportError("connect timeout")

    backend = MojeekSearchBackend(fetch=_boom)
    with pytest.raises(SearchError) as err:
        _run(backend.search("x"))
    assert err.value.reason == SEARCH_REASON_UNREACHABLE


def test_default_transport_is_the_friendly_httpx_lane() -> None:
    from services.search.transport import httpx_fetch

    assert MojeekSearchBackend()._fetch is httpx_fetch
