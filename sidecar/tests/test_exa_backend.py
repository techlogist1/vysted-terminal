"""Tests for the Exa BYOK search backend (FR-083).

No test makes a live Exa call: ``httpx`` is monkeypatched at the transport
level (``httpx.MockTransport``) or via an injected fake client, so the request
the backend *would* send is captured and a canned Exa JSON body is mapped back
through the real ``services.search.exa`` code. The operator validates against
the real Exa API separately with a real key — these tests are fully offline.

Coverage:
  * the request carries the ``x-api-key`` header + the query, and a fake Exa
    response maps to a ``SearchResponse`` with populated results + citations;
  * an HTTP 401 maps to a human ``SearchError`` (not a crash, no raw JSON);
  * an ``IN`` region applies the locale ``includeDomains`` allow-list;
  * a ``news`` category is forwarded as Exa's ``category``;
  * the key is never echoed in the response or in an error message.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from services.search.base import SearchError, SearchResponse, locale_domains
from services.search.exa import EXA_SEARCH_URL, ExaBackend, ExaSearchBackend

_FAKE_EXA_BODY: dict[str, Any] = {
    "results": [
        {
            "url": "https://reuters.com/markets/aapl-earnings",
            "title": "Apple beats on Q3 earnings",
            "text": "Apple reported revenue above estimates driven by services.",
            "publishedDate": "2026-05-30T12:00:00.000Z",
            "author": "Reuters Staff",
        },
        {
            "url": "https://bloomberg.com/news/aapl-guidance",
            "title": "Apple raises guidance",
            "text": "The company lifted its full-year outlook.",
            "publishedDate": "2026-05-31T09:00:00.000Z",
        },
        # A result with no url must be skipped (unciteable), not crash the map.
        {"title": "No link here", "text": "orphan"},
    ]
}

_SECRET_KEY = "exa-secret-key-do-not-leak"


class _Captured:
    """Records the single request a backend issues so the test can assert on it."""

    def __init__(self) -> None:
        self.request: httpx.Request | None = None


def _mock_client(captured: _Captured, *, status: int = 200) -> httpx.AsyncClient:
    """An ``httpx.AsyncClient`` whose transport records the request + returns canned JSON."""

    def handler(request: httpx.Request) -> httpx.Response:
        captured.request = request
        if status != 200:
            return httpx.Response(status, json={"error": "Unauthorized"})
        return httpx.Response(status, json=_FAKE_EXA_BODY)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Happy path: request shape + response mapping
# ---------------------------------------------------------------------------


def test_search_sends_key_and_query_and_maps_response() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = ExaBackend(api_key=_SECRET_KEY, client=client)

    response = _run(backend.search("AAPL earnings", options={"numResults": 4}))
    _run(client.aclose())

    # --- request assertions -------------------------------------------------
    assert captured.request is not None
    assert str(captured.request.url) == EXA_SEARCH_URL
    assert captured.request.method == "POST"
    # The BYOK key rides as the x-api-key header (never the body).
    assert captured.request.headers["x-api-key"] == _SECRET_KEY
    sent = json.loads(captured.request.content.decode())
    assert sent["query"] == "AAPL earnings"
    assert sent["numResults"] == 4
    assert sent["type"] == "auto"
    assert sent["contents"]["text"]["maxCharacters"] == 512
    assert _SECRET_KEY not in captured.request.content.decode()

    # --- response mapping ---------------------------------------------------
    assert isinstance(response, SearchResponse)
    assert response.backend == "exa"
    assert response.query == "AAPL earnings"
    # Two valid results (the url-less one is dropped).
    assert len(response.results) == 2
    first = response.results[0]
    assert first.url == "https://reuters.com/markets/aapl-earnings"
    assert first.title == "Apple beats on Q3 earnings"
    assert "services" in first.snippet
    assert first.published_at == "2026-05-30T12:00:00.000Z"
    assert first.source == "Reuters Staff"
    # Citations derive from the results — {url, title, excerpt}.
    assert len(response.citations) == 2
    assert response.citations[0].url == first.url
    assert response.citations[0].excerpt == first.snippet


def test_default_num_results_is_six() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = ExaBackend(api_key=_SECRET_KEY, client=client)

    _run(backend.search("market outlook"))
    _run(client.aclose())

    assert captured.request is not None
    sent = json.loads(captured.request.content.decode())
    assert sent["numResults"] == 6


# ---------------------------------------------------------------------------
# Error handling: 401 -> human SearchError (no crash, no raw JSON, no key)
# ---------------------------------------------------------------------------


def test_http_401_maps_to_search_error() -> None:
    captured = _Captured()
    client = _mock_client(captured, status=401)
    backend = ExaBackend(api_key=_SECRET_KEY, client=client)

    with pytest.raises(SearchError) as excinfo:
        _run(backend.search("anything"))
    _run(client.aclose())

    message = str(excinfo.value)
    # Human, finance-operator-readable — not a raw vendor JSON blob.
    assert "Exa" in message
    assert "{" not in message and "Unauthorized" not in message
    # The key must never leak into an error message.
    assert _SECRET_KEY not in message


def test_unparseable_body_maps_to_search_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(200, content=b"not json at all")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    backend = ExaBackend(api_key=_SECRET_KEY, client=client)

    with pytest.raises(SearchError) as excinfo:
        _run(backend.search("anything"))
    _run(client.aclose())
    assert _SECRET_KEY not in str(excinfo.value)


# ---------------------------------------------------------------------------
# Locale: IN region applies includeDomains
# ---------------------------------------------------------------------------


def test_in_region_applies_include_domains() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = ExaBackend(api_key=_SECRET_KEY, region="IN", client=client)

    _run(backend.search("Reliance results"))
    _run(client.aclose())

    assert captured.request is not None
    sent = json.loads(captured.request.content.decode())
    assert sent["includeDomains"] == locale_domains("IN")
    assert "nseindia.com" in sent["includeDomains"]


def test_options_region_overrides_construction_region() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = ExaBackend(api_key=_SECRET_KEY, region="US", client=client)

    _run(backend.search("Reliance results", options={"region": "IN"}))
    _run(client.aclose())

    assert captured.request is not None
    sent = json.loads(captured.request.content.decode())
    assert sent["includeDomains"] == locale_domains("IN")


def test_no_region_omits_include_domains() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = ExaBackend(api_key=_SECRET_KEY, client=client)

    _run(backend.search("global macro"))
    _run(client.aclose())

    assert captured.request is not None
    sent = json.loads(captured.request.content.decode())
    assert "includeDomains" not in sent


def test_explicit_locale_domains_option_wins() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = ExaBackend(api_key=_SECRET_KEY, region="US", client=client)

    _run(backend.search("custom", options={"locale_domains": ["example.com", "test.org"]}))
    _run(client.aclose())

    assert captured.request is not None
    sent = json.loads(captured.request.content.decode())
    assert sent["includeDomains"] == ["example.com", "test.org"]


# ---------------------------------------------------------------------------
# Finance category forwarding
# ---------------------------------------------------------------------------


def test_news_category_is_forwarded() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = ExaBackend(api_key=_SECRET_KEY, client=client)

    _run(backend.search("fed rate", options={"category": "news"}))
    _run(client.aclose())

    assert captured.request is not None
    sent = json.loads(captured.request.content.decode())
    assert sent["category"] == "news"


def test_financial_category_maps_to_financial_report() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = ExaBackend(api_key=_SECRET_KEY, client=client)

    _run(backend.search("AAPL 10-K", options={"category": "financial"}))
    _run(client.aclose())

    assert captured.request is not None
    sent = json.loads(captured.request.content.decode())
    assert sent["category"] == "financial report"


def test_unknown_category_is_omitted() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = ExaBackend(api_key=_SECRET_KEY, client=client)

    _run(backend.search("anything", options={"category": "sports"}))
    _run(client.aclose())

    assert captured.request is not None
    sent = json.loads(captured.request.content.decode())
    assert "category" not in sent


# ---------------------------------------------------------------------------
# Construction + short-lived client path + edge cases
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_search_error() -> None:
    with pytest.raises(SearchError):
        ExaBackend(api_key="   ")


def test_empty_query_raises_search_error() -> None:
    backend = ExaBackend(api_key=_SECRET_KEY, client=httpx.AsyncClient())
    with pytest.raises(SearchError):
        _run(backend.search("   "))


def test_exa_backend_alias_is_exa_search_backend() -> None:
    assert ExaBackend is ExaSearchBackend


def test_short_lived_client_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no injected client, the backend opens its own client — still mocked."""
    captured = _Captured()

    def handler(request: httpx.Request) -> httpx.Response:
        captured.request = request
        return httpx.Response(200, json=_FAKE_EXA_BODY)

    real_init = httpx.AsyncClient.__init__

    def patched_init(self: httpx.AsyncClient, *args: Any, **kwargs: Any) -> None:
        kwargs["transport"] = httpx.MockTransport(handler)
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)

    backend = ExaBackend(api_key=_SECRET_KEY)  # no client -> short-lived path
    response = _run(backend.search("self-managed client"))

    assert captured.request is not None
    assert captured.request.headers["x-api-key"] == _SECRET_KEY
    assert len(response.results) == 2
