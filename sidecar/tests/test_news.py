"""Tests for the sentiment scorer and the /news router.

The RSS and NewsAPI fetch functions are monkeypatched at the function level —
``news_provider.fetch_rss`` / ``fetch_newsapi`` — so no test makes a live HTTP
call, mirroring the provider-mocking pattern in ``conftest.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from models.news import NewsItem
from services import news_provider, sentiment
from services.errors import ProviderError

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

    def fake_fetch_news(symbols: list[str], limit: int) -> list[NewsItem]:  # noqa: ARG001
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
    def boom(*_args: object, **_kwargs: object) -> list[NewsItem]:
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

    def fake_fetch_rss(feed_url: str, *, fallback_source: str) -> list[NewsItem]:  # noqa: ARG001
        # Same "dup" item returned by every feed — must be de-duplicated.
        return [older, newer]

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    items = news_provider.fetch_news([], limit=50)
    ids = [item.id for item in items]
    assert ids.count("dup") == 1
    # Newest first.
    assert ids == ["fresh", "dup"]


def test_fetch_news_survives_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    good = _news_item("ok", "Working feed item")
    calls = {"n": 0}

    def flaky_fetch_rss(feed_url: str, *, fallback_source: str) -> list[NewsItem]:  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("feed timed out")
        return [good]

    monkeypatch.setattr(news_provider, "fetch_rss", flaky_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    items = news_provider.fetch_news([], limit=50)
    assert [item.id for item in items] == ["ok"]


def test_fetch_news_all_sources_fail_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def dead_fetch_rss(feed_url: str, *, fallback_source: str) -> list[NewsItem]:  # noqa: ARG001
        raise RuntimeError("feed down")

    monkeypatch.setattr(news_provider, "fetch_rss", dead_fetch_rss)
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    with pytest.raises(ProviderError):
        news_provider.fetch_news([], limit=50)


def test_fetch_news_uses_newsapi_when_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    rss_item = _news_item("rss1", "RSS market item")
    api_item = _news_item("api1", "NewsAPI item")
    api_item = api_item.model_copy(update={"provider": news_provider.PROVIDER_NEWSAPI})
    seen: dict[str, object] = {}

    def fake_fetch_rss(feed_url: str, *, fallback_source: str) -> list[NewsItem]:  # noqa: ARG001
        return [rss_item]

    def fake_fetch_newsapi(query: str, *, limit: int, api_key: str) -> list[NewsItem]:
        seen["query"] = query
        seen["api_key"] = api_key
        return [api_item]

    monkeypatch.setattr(news_provider, "fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(news_provider, "fetch_newsapi", fake_fetch_newsapi)
    monkeypatch.setenv("NEWSAPI_KEY", "test-key-123")

    items = news_provider.fetch_news(["NVDA"], limit=10)
    ids = {item.id for item in items}
    assert ids == {"rss1", "api1"}
    assert seen["api_key"] == "test-key-123"
    assert "NVDA" in str(seen["query"])
