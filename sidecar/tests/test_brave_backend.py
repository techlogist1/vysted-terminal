"""Tests for the Brave HTML engine adapter (``services.search.brave``)."""

from __future__ import annotations

import asyncio

import pytest

from services.search.base import (
    SEARCH_REASON_RATE_LIMITED,
    SEARCH_REASON_UNREACHABLE,
    SearchError,
)
from services.search.brave import BACKEND_ID, BraveSearchBackend
from services.search.transport import FetchResult, TransportError

# A trimmed Brave SERP: two organic web results (one with rich markup, one
# minimal), an ad-ish self-link that must be skipped, and a duplicate URL.
_FIXTURE = """
<div id="results">
  <div class="snippet" data-type="web" data-pos="1">
    <a href="https://example.com/nvda">
      <div class="title">NVDA <b>Outlook</b> 2026</div>
    </a>
    <div class="snippet-content">
      <div class="snippet-description">Strong datacenter demand drives growth.</div>
    </div>
  </div>
  <div class="snippet" data-type="web" data-pos="2">
    <a href="https://search.brave.com/promoted">Brave promo</a>
  </div>
  <div class="snippet" data-type="web" data-pos="3">
    <a href="https://second.com/page"><div class="title">Second &amp; Source</div></a>
    <div class="snippet-description">A second result.</div>
  </div>
  <div class="snippet" data-type="web" data-pos="4">
    <a href="https://example.com/nvda"><div class="title">Duplicate URL</div></a>
  </div>
</div>
"""

# Drifted markup: no data-type attribute, no .title class — the loose fallback
# must still produce a row from the bare anchor.
_DRIFTED = """
<div id="results">
  <div class="snippet">
    <a href="https://drift.com/article">Drifted result title</a>
  </div>
</div>
"""


def _fetcher(result: FetchResult, calls: list[dict]):
    async def _fetch(url, *, params=None, data=None, headers=None, **kw):  # noqa: ANN001, ANN202
        calls.append({"url": url, "params": params})
        return result

    return _fetch


def _run(coro):
    return asyncio.run(coro)


def test_parses_organic_results_skips_self_links_and_dupes() -> None:
    calls: list[dict] = []
    fetched = FetchResult(status_code=200, text=_FIXTURE, url="https://search.brave.com/search")
    backend = BraveSearchBackend(region="US", fetch=_fetcher(fetched, calls))
    resp = _run(backend.search("nvda datacenter demand"))

    assert resp.backend == BACKEND_ID
    assert [r.url for r in resp.results] == ["https://example.com/nvda", "https://second.com/page"]
    assert resp.results[0].title == "NVDA Outlook 2026"
    assert resp.results[0].snippet == "Strong datacenter demand drives growth."
    assert resp.results[1].title == "Second & Source"
    assert resp.results[0].source == "brave"
    assert resp.citations[0].url == "https://example.com/nvda"
    # Region biases the SERP country param.
    assert calls[0]["params"]["country"] == "us"
    assert calls[0]["params"]["q"] == "nvda datacenter demand"


def test_drifted_markup_still_yields_a_row() -> None:
    fetched = FetchResult(status_code=200, text=_DRIFTED, url="https://search.brave.com/search")
    backend = BraveSearchBackend(fetch=_fetcher(fetched, []))
    resp = _run(backend.search("x"))
    assert len(resp.results) == 1
    assert resp.results[0].url == "https://drift.com/article"
    assert resp.results[0].title == "Drifted result title"


def test_zero_rows_is_empty_success_not_error() -> None:
    fetched = FetchResult(status_code=200, text="<html><body>nothing</body></html>", url="u")
    backend = BraveSearchBackend(fetch=_fetcher(fetched, []))
    resp = _run(backend.search("x"))
    assert resp.results == []
    assert resp.backend == BACKEND_ID


def test_max_results_caps_output() -> None:
    fetched = FetchResult(status_code=200, text=_FIXTURE, url="u")
    backend = BraveSearchBackend(fetch=_fetcher(fetched, []))
    resp = _run(backend.search("x", options={"maxResults": 1}))
    assert len(resp.results) == 1


@pytest.mark.parametrize("status", [403, 429])
def test_block_statuses_raise_typed_rate_limit(status: int) -> None:
    fetched = FetchResult(status_code=status, text="blocked", url="u")
    backend = BraveSearchBackend(fetch=_fetcher(fetched, []))
    with pytest.raises(SearchError) as err:
        _run(backend.search("x"))
    assert err.value.reason == SEARCH_REASON_RATE_LIMITED


def test_server_error_raises_unreachable() -> None:
    fetched = FetchResult(status_code=500, text="oops", url="u")
    backend = BraveSearchBackend(fetch=_fetcher(fetched, []))
    with pytest.raises(SearchError) as err:
        _run(backend.search("x"))
    assert err.value.reason == SEARCH_REASON_UNREACHABLE


def test_transport_failure_raises_unreachable() -> None:
    async def _boom(url, **kw):  # noqa: ANN001, ANN202
        raise TransportError("tls handshake failed")

    backend = BraveSearchBackend(fetch=_boom)
    with pytest.raises(SearchError) as err:
        _run(backend.search("x"))
    assert err.value.reason == SEARCH_REASON_UNREACHABLE


def test_default_transport_is_the_impersonated_lane() -> None:
    from services.search.transport import impersonated_fetch

    # Brave rejects plain httpx TLS — the adapter must default to curl_cffi.
    assert BraveSearchBackend()._fetch is impersonated_fetch
