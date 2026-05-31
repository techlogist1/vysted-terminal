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
    ) -> list[NewsItem]:
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
    assert "all news sources failed" in response.json()["detail"]


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
    ) -> list[NewsItem]:
        seen["newsapi_key"] = newsapi_key
        return [_news_item("a1", "NVDA shares soar")]

    monkeypatch.setattr(news_provider, "fetch_news", fake_fetch_news)
    response = client.get("/news", headers={"X-Vysted-Newsapi-Key": "keychain-key"})
    assert response.status_code == 200
    assert seen["newsapi_key"] == "keychain-key"
    # The key must never appear in the response payload.
    assert "keychain-key" not in response.text


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
