"""Tests for the SearXNG local/private search backend (FR-084, Tier 3).

No test makes a real network call: every request is served by an
``httpx.MockTransport`` handler injected through the backend's ``client`` seam.
The handlers assert the exact request the backend issues (``<base>/search`` with
``format=json`` and the query), and the fake JSON exercises the
``content``→``snippet`` / ``publishedDate``→``published_at`` mapping.
"""

from __future__ import annotations

import httpx
import pytest

from services.search.base import SearchError, SearchResponse
from services.search.searxng import (
    BACKEND_ID,
    DEFAULT_BASE_URL,
    SearxngBackend,
    detect_searxng,
)

_FAKE_SEARCH_JSON = {
    "query": "nvidia earnings",
    "results": [
        {
            "url": "https://example.com/nvda",
            "title": "NVIDIA tops estimates",
            "content": "NVIDIA reported record data-center revenue.",
            "publishedDate": "2026-05-28T00:00:00Z",
        },
        {
            "url": "https://example.org/nvda-2",
            "title": "Analyst reaction",
            "content": "Buy-side desks lifted price targets.",
        },
        # No url → dropped by the mapper.
        {"title": "garbage", "content": "no link"},
    ],
}


def _mock_transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# search() — request shape + result mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_hits_search_endpoint_with_json_format_and_query() -> None:
    seen: dict[str, httpx.Request] = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return httpx.Response(200, json=_FAKE_SEARCH_JSON)

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        backend = SearxngBackend("http://localhost:8080", client=client)
        response = await backend.search("nvidia earnings")

    request = seen["request"]
    assert request.method == "GET"
    assert request.url.path == "/search"
    assert request.url.host == "localhost"
    assert request.url.port == 8080
    # GET hits <base>/search?format=json with the query (no real localhost call).
    params = dict(request.url.params)
    assert params["format"] == "json"
    assert params["q"] == "nvidia earnings"
    assert isinstance(response, SearchResponse)


@pytest.mark.asyncio
async def test_search_maps_results_to_search_response() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_FAKE_SEARCH_JSON)

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        backend = SearxngBackend(client=client)
        response = await backend.search("nvidia earnings")

    assert response.backend == BACKEND_ID
    assert response.query == "nvidia earnings"
    # The url-less third item is dropped; two valid results remain.
    assert len(response.results) == 2

    first = response.results[0]
    assert first.url == "https://example.com/nvda"
    assert first.title == "NVIDIA tops estimates"
    # content -> snippet
    assert first.snippet == "NVIDIA reported record data-center revenue."
    # publishedDate -> published_at
    assert first.published_at == "2026-05-28T00:00:00Z"
    assert first.source == BACKEND_ID

    # A result without publishedDate maps to published_at == None.
    assert response.results[1].published_at is None

    # Top results are promoted to {url, title, excerpt} citations.
    assert len(response.citations) == 2
    assert response.citations[0].url == "https://example.com/nvda"
    assert response.citations[0].excerpt == "NVIDIA reported record data-center revenue."


@pytest.mark.asyncio
async def test_search_forwards_categories_option() -> None:
    seen: dict[str, httpx.Request] = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return httpx.Response(200, json={"results": []})

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        backend = SearxngBackend(client=client)
        await backend.search("fed minutes", options={"categories": "news"})

    assert dict(seen["request"].url.params)["categories"] == "news"


@pytest.mark.asyncio
async def test_search_respects_max_results_citation_cap() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_FAKE_SEARCH_JSON)

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        backend = SearxngBackend(client=client)
        response = await backend.search("nvidia", options={"maxResults": 1})

    assert len(response.results) == 2  # mapping is unaffected
    assert len(response.citations) == 1  # citations capped


# ---------------------------------------------------------------------------
# search() — failure → human SearchError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_connection_error_raises_human_search_error() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        backend = SearxngBackend("http://localhost:8080", client=client)
        with pytest.raises(SearchError) as exc_info:
            await backend.search("anything")

    message = str(exc_info.value)
    assert "no local SearXNG at http://localhost:8080" in message
    assert "start one or pick another search tier" in message


@pytest.mark.asyncio
async def test_search_non_2xx_raises_search_error() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="bad gateway")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        backend = SearxngBackend(client=client)
        with pytest.raises(SearchError):
            await backend.search("anything")


# ---------------------------------------------------------------------------
# detect_searxng() — autodetect probe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_returns_base_url_when_healthz_ok() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/healthz"
        return httpx.Response(200, text="OK")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        found = await detect_searxng("http://localhost:8080", client=client)

    assert found == "http://localhost:8080"


@pytest.mark.asyncio
async def test_detect_falls_back_to_config_when_healthz_missing() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/healthz":
            return httpx.Response(404, text="not found")
        assert request.url.path == "/config"
        return httpx.Response(200, json={"instance_name": "searxng"})

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        found = await detect_searxng(client=client)

    assert found == DEFAULT_BASE_URL


@pytest.mark.asyncio
async def test_detect_returns_none_when_probe_fails() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no instance here")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        found = await detect_searxng("http://localhost:8080", client=client)

    assert found is None


@pytest.mark.asyncio
async def test_detect_returns_none_when_both_probes_non_2xx() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="down")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        found = await detect_searxng(client=client)

    assert found is None
