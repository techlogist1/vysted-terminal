"""Tests for the sentiment scorer and the /news router.

The RSS and NewsAPI fetch functions are monkeypatched at the function level —
``news_provider.fetch_rss`` / ``fetch_newsapi`` — so no test makes a live HTTP
call, mirroring the provider-mocking pattern in ``conftest.py``.

``fetch_news`` (and the source fetchers) are now ``async`` and take a shared
``httpx.AsyncClient``. The provider-level tests drive the coroutine via
``asyncio.run(...)`` — NOT ``asyncio.get_event_loop()``, which raises on Python
3.13 outside a running loop — and pass a throwaway client the mocked fetchers
ignore.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from models.news import NewsItem
from services import news_provider, sentiment
from services.errors import ProviderError

# A real (never-used-for-IO) client object; the mocked fetchers ignore it. Kept
# module-level so provider-level tests share one instance.
_CLIENT = httpx.AsyncClient()

# --------------------------------------------------------------------------
# sentiment scorer — tested directly
# --------------------------------------------------------------------------


def test_sentiment_positive_headline() -> None:
    result = sentiment.score_text("Company shares soar on record profit and stellar growth")
    assert result.score > 0
    assert result.label == "positive"


def test_sentiment_negative_headline() -> None:
    result = sentiment.score_text("Stock crashes amid disastrous losses and bankruptcy fears")
    assert result.score < 0
    assert result.label == "negative"


def test_sentiment_neutral_headline() -> None:
    result = sentiment.score_text("Company to hold annual shareholder meeting on Tuesday")
    assert -1.0 <= result.score <= 1.0
    assert result.label == "neutral"


def test_sentiment_empty_text_is_neutral() -> None:
    for text in (None, "", "   "):
        result = sentiment.score_text(text)
        assert result.score == 0.0
        assert result.label == "neutral"


def test_sentiment_score_bounded() -> None:
    result = sentiment.score_text("amazing fantastic incredible wonderful great superb excellent")
    assert -1.0 <= result.score <= 1.0


def test_label_for_score_thresholds() -> None:
    assert sentiment.label_for_score(0.5) == "positive"
    assert sentiment.label_for_score(0.05) == "positive"
    assert sentiment.label_for_score(0.0) == "neutral"
    assert sentiment.label_for_score(-0.04) == "neutral"
    assert sentiment.label_for_score(-0.05) == "negative"
    assert sentiment.label_for_score(-0.8) == "negative"


# --------------------------------------------------------------------------
# /news router — provider fetch functions mocked at the function level
# --------------------------------------------------------------------------


def _news_item(item_id: str, title: str, summary: str | None = None) -> NewsItem:
    """Build a canned NewsItem the way the provider layer would emit one."""
    return NewsItem(
        id=item_id,
        title=title,
        summary=summary,
        url=f"https://example.com/{item_id}",
        source="Test Feed",
        published_at=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
        symbols=[],
        provider=news_provider.PROVIDER_RSS,
    )


@pytest.fixture
def mock_news(monkeypatch: pytest.MonkeyPatch) -> list[NewsItem]:
    """Patch ``fetch_news`` with canned articles; no network, no NewsAPI key."""
    canned = [
        _news_item("a1", "NVDA shares soar on record profit", "Strong demand lifts NVDA."),
        _news_item("b2", "AAPL stock crashes amid disastrous quarter", "Losses pile up at AAPL."),
        _news_item("c3", "Federal Reserve to hold meeting next week", "Routine policy review."),
    ]

    async def fake_fetch_news(
        client: httpx.AsyncClient,  # noqa: ARG001
        symbols: list[str],  # noqa: ARG001
        limit: int,  # noqa: ARG001
        *,
        newsapi_key: str | None = None,  # noqa: ARG001
        source_status: dict[str, str] | None = None,
    ) -> list[NewsItem]:
        if source_status is not None:
            source_status["newsapi"] = "absent"
        return list(canned)

    monkeypatch.setattr(news_provider, "fetch_news", fake_fetch_news)
    return canned


def test_get_news_scores_every_item(client: TestClient, mock_news: list[NewsItem]) -> None:
    body = client.get("/news").json()
    assert len(body) == 3
    for item in body:
        assert item["sentiment"] is not None
        assert -1.0 <= item["sentiment"] <= 1.0
        assert item["sentiment_label"] in {"positive", "neutral", "negative"}


def test_get_news_sentiment_direction(client: TestClient, mock_news: list[NewsItem]) -> None:
    by_id = {item["id"]: item for item in client.get("/news").json()}
    assert by_id["a1"]["sentiment_label"] == "positive"
    assert by_id["b2"]["sentiment_label"] == "negative"


def test_get_news_tags_default_watchlist(client: TestClient, mock_news: list[NewsItem]) -> None:
    by_id = {item["id"]: item for item in client.get("/news").json()}
    # Default watchlist includes NVDA and AAPL — they should be tagged.
    assert by_id["a1"]["symbols"] == ["NVDA"]
    assert by_id["b2"]["symbols"] == ["AAPL"]
    # The Fed item mentions no watchlist ticker.
    assert by_id["c3"]["symbols"] == []


def test_get_news_filters_to_requested_symbols(
    client: TestClient, mock_news: list[NewsItem]
) -> None:
    body = client.get("/news", params={"symbols": "NVDA"}).json()
    assert [item["id"] for item in body] == ["a1"]
    assert body[0]["symbols"] == ["NVDA"]


def test_get_news_respects_limit(client: TestClient, mock_news: list[NewsItem]) -> None:
    body = client.get("/news", params={"limit": 2}).json()
    assert len(body) == 2


def test_get_news_limit_out_of_range_is_422(client: TestClient, mock_news: list[NewsItem]) -> None:
    assert client.get("/news", params={"limit": 0}).status_code == 422
    assert client.get("/news", params={"limit": 9999}).status_code == 422


def test_get_news_provider_error_is_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*_args: object, **_kwargs: object) -> list[NewsItem]:
        raise ProviderError("all news sources failed")

    monkeypatch.setattr(news_provider, "fetch_news", boom)
    response = client.get("/news")
    assert response.status_code == 502
    assert response.json()["detail"] == "The data provider returned an unexpected response."


# --------------------------------------------------------------------------
# Symbol tagging by alias set and provenance (R15-DATA-030)
# --------------------------------------------------------------------------


def _news_for(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, item: NewsItem, symbols: str
) -> list[dict]:
    async def fake_fetch_news(client, symbols, limit, *, newsapi_key=None, source_status=None):  # noqa: ANN001, ANN202, ARG001
        return [item]

    monkeypatch.setattr(news_provider, "fetch_news", fake_fetch_news)
    return client.get("/news", params={"symbols": symbols}).json()


def test_company_name_tags_a_suffixed_india_symbol(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = _news_item("r1", "Reliance Industries Q2 profit rises 10%", "RIL beats estimates")
    body = _news_for(client, monkeypatch, item, "RELIANCE.NS")
    assert [i["symbols"] for i in body] == [["RELIANCE.NS"]]


def test_one_letter_ticker_never_matches_the_article_a(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = _news_item("n1", "Nvidia unveils a new chip", "A report from a bank")
    assert _news_for(client, monkeypatch, item, "A") == []


def test_company_name_tags_a_bare_nse_ticker(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = _news_item("s1", "State Bank of India raises rates")
    body = _news_for(client, monkeypatch, item, "SBIN")
    assert [i["symbols"] for i in body] == [["SBIN"]]


def test_btc_usdt_tags_a_bitcoin_headline(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-AGENT-063 residual: news_provider._aliases used to yield only
    ["BTC/USDT", "BTC"] with no company-name alias, so a headline that never
    says the literal pair or bare base ("BTC") went untagged."""
    item = _news_item("btc1", "Bitcoin options expiry looms as volatility spikes")
    body = _news_for(client, monkeypatch, item, "BTC/USDT")
    assert [i["symbols"] for i in body] == [["BTC/USDT"]]


def test_eth_usdt_tags_an_ethereum_headline(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Class pin, not written against: the same residual on a different base."""
    item = _news_item("eth1", "Ethereum upgrade activates on mainnet")
    body = _news_for(client, monkeypatch, item, "ETH/USDT")
    assert [i["symbols"] for i in body] == [["ETH/USDT"]]


def test_items_from_a_symbols_own_feed_are_tagged_by_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_rss(client, feed_url, *, fallback_source):  # noqa: ANN001, ANN202, ARG001
        # The same story on a market feed and on HDFCBANK's own feed.
        return [_news_item("h1", "Lender posts record quarter")]

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    items = asyncio.run(news_provider.fetch_news(_CLIENT, ["HDFCBANK"], limit=10))
    assert [i.symbols for i in items] == [["HDFCBANK"]]


# --------------------------------------------------------------------------
# news_provider.fetch_news — RSS/NewsAPI fetchers mocked at the function level
# --------------------------------------------------------------------------


def test_fetch_news_dedupes_and_sorts(monkeypatch: pytest.MonkeyPatch) -> None:
    older = _news_item("dup", "Same story")
    older = older.model_copy(update={"published_at": datetime(2026, 5, 10, tzinfo=UTC)})
    newer = _news_item("fresh", "Newer story")
    newer = newer.model_copy(update={"published_at": datetime(2026, 5, 14, tzinfo=UTC)})

    async def fake_fetch_rss(
        client: httpx.AsyncClient,  # noqa: ARG001
        feed_url: str,  # noqa: ARG001
        *,
        fallback_source: str,  # noqa: ARG001
    ) -> list[NewsItem]:
        # Same "dup" item returned by every feed — must be de-duplicated.
        return [older, newer]

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    items = asyncio.run(news_provider.fetch_news(_CLIENT, [], limit=50))
    ids = [item.id for item in items]
    assert ids.count("dup") == 1
    # Newest first.
    assert ids == ["fresh", "dup"]


def test_undated_rss_item_has_no_date_and_sorts_last(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-DATA-070: an RSS entry with no pubDate is served with published_at None
    and sorted after every dated story — never stamped now() and put on top."""
    rss = (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>Feed</title>'
        "<item><title>Undated story</title><link>https://example.com/u</link></item>"
        "<item><title>Dated story</title><link>https://example.com/d</link>"
        "<pubDate>Thu, 14 May 2026 12:00:00 GMT</pubDate></item>"
        "</channel></rss>"
    )
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=rss))
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    async def run() -> list[NewsItem]:
        async with httpx.AsyncClient(transport=transport) as client:
            return await news_provider.fetch_news(client, [], limit=50)

    items = asyncio.run(run())
    assert [item.title for item in items] == ["Dated story", "Undated story"]
    assert items[0].published_at == datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    assert items[1].published_at is None


def test_fetch_news_survives_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """One source fails its retries; the other succeeds → partial success (no raise)."""
    good = _news_item("ok", "Working feed item")

    async def flaky_fetch_rss(
        client: httpx.AsyncClient,  # noqa: ARG001
        feed_url: str,
        *,
        fallback_source: str,  # noqa: ARG001
    ) -> list[NewsItem]:
        # The first market feed always fails (even on retry); the second works.
        if "marketwatch" in feed_url:
            raise RuntimeError("feed timed out")
        return [good]

    # Zero retries/backoff so the failing source doesn't slow the test.
    monkeypatch.setattr(news_provider, "_MAX_RETRIES", 0)
    monkeypatch.setattr(news_provider, "fetch_rss", flaky_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    items = asyncio.run(news_provider.fetch_news(_CLIENT, [], limit=50))
    assert [item.id for item in items] == ["ok"]


def test_fetch_news_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """A transient first-fetch failure is retried and recovers — models #38."""
    good = _news_item("recovered", "Recovered after retry")
    calls = {"n": 0}

    async def transient_fetch_rss(
        client: httpx.AsyncClient,  # noqa: ARG001
        feed_url: str,  # noqa: ARG001
        *,
        fallback_source: str,  # noqa: ARG001
    ) -> list[NewsItem]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("cold-start TLS timeout")
        return [good]

    monkeypatch.setattr(news_provider, "_RETRY_BACKOFF_SECONDS", 0.0)
    monkeypatch.setattr(news_provider, "fetch_rss", transient_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    items = asyncio.run(news_provider.fetch_news(_CLIENT, [], limit=50))
    assert any(item.id == "recovered" for item in items)
    assert calls["n"] >= 2  # at least one retry happened


def test_fetch_news_all_sources_fail_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only raise when NOTHING was collected from any source."""

    async def dead_fetch_rss(
        client: httpx.AsyncClient,  # noqa: ARG001
        feed_url: str,  # noqa: ARG001
        *,
        fallback_source: str,  # noqa: ARG001
    ) -> list[NewsItem]:
        raise RuntimeError("feed down")

    monkeypatch.setattr(news_provider, "_MAX_RETRIES", 0)
    monkeypatch.setattr(news_provider, "fetch_rss", dead_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    with pytest.raises(ProviderError):
        asyncio.run(news_provider.fetch_news(_CLIENT, [], limit=50))


def test_fetch_news_empty_collected_raises_even_when_no_source_errored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every source returns an empty list (no exception) → still a 502-worthy raise."""

    async def empty_fetch_rss(
        client: httpx.AsyncClient,  # noqa: ARG001
        feed_url: str,  # noqa: ARG001
        *,
        fallback_source: str,  # noqa: ARG001
    ) -> list[NewsItem]:
        return []

    monkeypatch.setattr(news_provider, "fetch_rss", empty_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    with pytest.raises(ProviderError):
        asyncio.run(news_provider.fetch_news(_CLIENT, [], limit=50))


def test_fetch_news_uses_newsapi_when_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    rss_item = _news_item("rss1", "RSS market item")
    api_item = _news_item("api1", "NewsAPI item")
    api_item = api_item.model_copy(update={"provider": news_provider.PROVIDER_NEWSAPI})
    seen: dict[str, object] = {}

    async def fake_fetch_rss(
        client: httpx.AsyncClient,  # noqa: ARG001
        feed_url: str,  # noqa: ARG001
        *,
        fallback_source: str,  # noqa: ARG001
    ) -> list[NewsItem]:
        return [rss_item]

    async def fake_fetch_newsapi(
        client: httpx.AsyncClient,  # noqa: ARG001
        query: str,
        *,
        limit: int,  # noqa: ARG001
        api_key: str,
    ) -> list[NewsItem]:
        seen["query"] = query
        seen["api_key"] = api_key
        return [api_item]

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(news_provider, "fetch_newsapi", fake_fetch_newsapi)
    monkeypatch.setenv("NEWSAPI_KEY", "test-key-123")

    items = asyncio.run(news_provider.fetch_news(_CLIENT, ["NVDA"], limit=10))
    ids = {item.id for item in items}
    assert ids == {"rss1", "api1"}
    assert seen["api_key"] == "test-key-123"
    assert "NVDA" in str(seen["query"])


def test_fetch_news_request_key_takes_precedence_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-036: the request-supplied (keychain) key wins over the env var."""
    rss_item = _news_item("rss1", "RSS market item")
    api_item = _news_item("api1", "NewsAPI item").model_copy(
        update={"provider": news_provider.PROVIDER_NEWSAPI}
    )
    seen: dict[str, object] = {}

    async def fake_fetch_rss(client, feed_url, *, fallback_source):  # noqa: ANN001, ANN202, ARG001
        return [rss_item]

    async def fake_fetch_newsapi(client, query, *, limit, api_key):  # noqa: ANN001, ANN202, ARG001
        seen["api_key"] = api_key
        return [api_item]

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(news_provider, "fetch_newsapi", fake_fetch_newsapi)
    # Env var present, but the request-supplied key must win.
    monkeypatch.setenv("NEWSAPI_KEY", "env-key")

    items = asyncio.run(
        news_provider.fetch_news(_CLIENT, ["NVDA"], limit=10, newsapi_key="keychain-key")
    )
    assert {item.id for item in items} == {"rss1", "api1"}
    assert seen["api_key"] == "keychain-key"


def test_fetch_news_env_key_is_last_resort_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """No request key → the NEWSAPI_KEY env var is the dev fallback."""
    api_item = _news_item("api1", "NewsAPI item").model_copy(
        update={"provider": news_provider.PROVIDER_NEWSAPI}
    )
    seen: dict[str, object] = {}

    async def fake_fetch_rss(client, feed_url, *, fallback_source):  # noqa: ANN001, ANN202, ARG001
        return [_news_item("rss1", "RSS market item")]

    async def fake_fetch_newsapi(client, query, *, limit, api_key):  # noqa: ANN001, ANN202, ARG001
        seen["api_key"] = api_key
        return [api_item]

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(news_provider, "fetch_newsapi", fake_fetch_newsapi)
    monkeypatch.setenv("NEWSAPI_KEY", "env-key")

    items = asyncio.run(news_provider.fetch_news(_CLIENT, ["NVDA"], limit=10))
    assert {item.id for item in items} == {"rss1", "api1"}
    assert seen["api_key"] == "env-key"


def test_get_news_passes_header_key_to_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-036: the /news route reads the BYOK key from a HEADER and passes it on;
    the key is never echoed in the response."""
    seen: dict[str, object] = {}

    async def fake_fetch_news(
        client_: httpx.AsyncClient,  # noqa: ARG001
        symbols: list[str],  # noqa: ARG001
        limit: int,  # noqa: ARG001
        *,
        newsapi_key: str | None = None,
        source_status: dict[str, str] | None = None,
    ) -> list[NewsItem]:
        seen["newsapi_key"] = newsapi_key
        if source_status is not None:
            source_status["newsapi"] = "ok"
        return [_news_item("a1", "NVDA shares soar")]

    monkeypatch.setattr(news_provider, "fetch_news", fake_fetch_news)
    response = client.get("/news", headers={"X-Vysted-Newsapi-Key": "keychain-key"})
    assert response.status_code == 200
    assert seen["newsapi_key"] == "keychain-key"
    # The key must never appear in the response payload.
    assert "keychain-key" not in response.text


# --------------------------------------------------------------------------
# R15-DATA-094: NewsAPI 401 is reported, not silently swallowed
# --------------------------------------------------------------------------


def test_fetch_news_reports_unauthorized_status_on_a_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """A rejected NewsAPI key still returns the RSS items, but ``source_status``
    names the 401 instead of it reading as merely "NewsAPI had nothing new"."""
    request = httpx.Request("GET", "https://newsapi.org/v2/everything")
    unauthorized = httpx.HTTPStatusError(
        "401", request=request, response=httpx.Response(401, request=request)
    )

    async def fake_fetch_rss(client, feed_url, *, fallback_source):  # noqa: ANN001, ANN202, ARG001
        return [_news_item("rss1", "RSS market item")]

    async def failing_fetch_newsapi(client, query, *, limit, api_key):  # noqa: ANN001, ANN202, ARG001
        raise unauthorized

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(news_provider, "fetch_newsapi", failing_fetch_newsapi)

    status: dict[str, str] = {}
    items = asyncio.run(
        news_provider.fetch_news(_CLIENT, [], limit=10, newsapi_key="bad-key", source_status=status)
    )
    assert {item.id for item in items} == {"rss1"}
    assert status == {"newsapi": "unauthorized"}


def test_fetch_news_reports_absent_status_with_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_rss(client, feed_url, *, fallback_source):  # noqa: ANN001, ANN202, ARG001
        return [_news_item("rss1", "RSS market item")]

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    status: dict[str, str] = {}
    asyncio.run(news_provider.fetch_news(_CLIENT, [], limit=10, source_status=status))
    assert status == {"newsapi": "absent"}


def test_get_news_sets_the_x_news_sources_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_fetch_news(
        client_,  # noqa: ANN001, ARG001
        symbols,  # noqa: ANN001, ARG001
        limit,  # noqa: ANN001, ARG001
        *,
        newsapi_key=None,  # noqa: ANN001, ARG001
        source_status=None,  # noqa: ANN001
    ):
        if source_status is not None:
            source_status["newsapi"] = "unauthorized"
        return [_news_item("a1", "headline")]

    monkeypatch.setattr(news_provider, "fetch_news", fake_fetch_news)
    response = client.get("/news", headers={"X-Vysted-Newsapi-Key": "bad-key"})
    assert response.status_code == 200
    assert response.headers["X-News-Sources"] == "rss=ok;newsapi=unauthorized"


def test_news_sources_status_probes_the_header_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    async def fake_probe(client_, api_key):  # noqa: ANN001, ARG001
        seen["api_key"] = api_key
        return "unauthorized"

    monkeypatch.setattr(news_provider, "probe_newsapi_key", fake_probe)
    response = client.get("/news/sources/status", headers={"X-Vysted-Newsapi-Key": "bad-key"})
    assert response.status_code == 200
    assert response.json() == {"newsapi": "unauthorized"}
    assert seen["api_key"] == "bad-key"
    assert "bad-key" not in response.text


def test_news_sources_status_with_no_key_is_absent(client: TestClient) -> None:
    response = client.get("/news/sources/status")
    assert response.status_code == 200
    assert response.json() == {"newsapi": "absent"}


def test_probe_newsapi_key_ok_and_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "https://newsapi.org/v2/everything")

    async def ok_fetch(client, query, *, limit, api_key):  # noqa: ANN001, ANN202, ARG001
        return [_news_item("a1", "headline")]

    monkeypatch.setattr(news_provider, "fetch_newsapi", ok_fetch)
    assert asyncio.run(news_provider.probe_newsapi_key(_CLIENT, "good-key")) == "ok"

    async def unauthorized_fetch(client, query, *, limit, api_key):  # noqa: ANN001, ANN202, ARG001
        raise httpx.HTTPStatusError(
            "401", request=request, response=httpx.Response(401, request=request)
        )

    monkeypatch.setattr(news_provider, "fetch_newsapi", unauthorized_fetch)
    assert asyncio.run(news_provider.probe_newsapi_key(_CLIENT, "bad-key")) == "unauthorized"


def test_bare_nse_symbol_in_an_in_session_fetches_its_ns_feed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-029: bare BDL in IN must hit BDL.NS, not Flanigan's (US BDL)."""
    import config

    urls: list[str] = []

    async def fake_fetch_rss(client, feed_url, *, fallback_source):  # noqa: ANN001, ANN202, ARG001
        urls.append(feed_url)
        return [_news_item("x", "headline")]

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    token = config.set_request_region("IN")
    try:
        asyncio.run(news_provider.fetch_news(_CLIENT, ["BDL"], limit=10))
    finally:
        config.reset_request_region(token)
    symbol_feeds = [u for u in urls if "headline?s=" in u]
    assert len(symbol_feeds) == 1
    assert "s=BDL.NS&" in symbol_feeds[0]


# --------------------------------------------------------------------------
# Shared httpx.AsyncClient lifespan wiring
# --------------------------------------------------------------------------


def test_shared_httpx_client_created_at_build() -> None:
    """``create_app`` puts a shared AsyncClient on app.state for the news route."""
    from app import create_app

    app = create_app()
    assert isinstance(app.state.httpx_client, httpx.AsyncClient)


def test_shared_httpx_client_closed_in_lifespan() -> None:
    """The lifespan closes the shared client on shutdown (no leaked connections)."""
    from app import create_app

    app = create_app()
    client = app.state.httpx_client
    assert not client.is_closed
    # Entering+exiting the TestClient context runs the lifespan startup+shutdown.
    with TestClient(app):
        pass
    assert client.is_closed
