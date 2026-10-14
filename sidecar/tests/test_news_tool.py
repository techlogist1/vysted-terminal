"""Tests for the ``news`` agent tool — register/invoke wiring, symbol parsing,
the provider-error envelope, and the §6.5 forbidden-id invariant.

Matches the per-domain test pattern of its v0.6.0 siblings (macro/sec/quant/
earnings/analyst). The ``news`` tool was added when the capability catalog was
projected to the external MCP surface (FR-022) so news is reachable by BOTH the
internal copilot and external MCP clients under the same name.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from models.news import NewsItem
from services import agent_tools
from services.agent_tools import news_tool
from services.errors import ProviderError


@pytest.fixture(autouse=True)
def _isolated_registry() -> None:
    agent_tools.reset_for_tests()
    yield
    agent_tools.reset_for_tests()


def _news_item(item_id: str, title: str, *, symbols: list[str] | None = None) -> NewsItem:
    return NewsItem(
        id=item_id,
        title=title,
        summary=None,
        url=f"https://example.com/{item_id}",
        source="Test",
        published_at=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
        symbols=symbols or [],
        provider="rss",
    )


def test_register_adds_news_to_the_registry() -> None:
    news_tool.register()
    assert agent_tools.is_registered("news")


@pytest.mark.asyncio
async def test_news_returns_ok_envelope_with_mapped_items(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    canned = [
        _news_item("a1", "AAPL headline one"),
        _news_item("a2", "MSFT headline two"),
    ]

    async def _fake_fetch(_client: Any, symbols: list[str], limit: int) -> list[NewsItem]:
        captured["symbols"] = symbols
        captured["limit"] = limit
        return canned

    from services import news_provider

    monkeypatch.setattr(news_provider, "fetch_news", _fake_fetch)
    news_tool.register()

    result = await agent_tools.invoke_tool("news", {"symbols": ["AAPL", "MSFT"], "limit": 5})
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["news"][0]["title"] == "AAPL headline one"
    assert captured["symbols"] == ["AAPL", "MSFT"]
    assert captured["limit"] == 5


@pytest.mark.asyncio
async def test_news_parses_comma_separated_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def _fake_fetch(_client: Any, symbols: list[str], _limit: int) -> list[NewsItem]:
        captured["symbols"] = symbols
        return []

    from services import news_provider

    monkeypatch.setattr(news_provider, "fetch_news", _fake_fetch)
    news_tool.register()

    result = await agent_tools.invoke_tool("news", {"symbols": "AAPL, MSFT ,NVDA"})
    assert result["ok"] is True
    assert result["count"] == 0
    assert captured["symbols"] == ["AAPL", "MSFT", "NVDA"]


@pytest.mark.asyncio
async def test_news_translates_provider_error_to_ok_false(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _boom(_client: Any, _symbols: list[str], _limit: int) -> list[NewsItem]:
        raise ProviderError("news source down")

    from services import news_provider

    monkeypatch.setattr(news_provider, "fetch_news", _boom)
    news_tool.register()

    result = await agent_tools.invoke_tool("news", {})
    assert result["ok"] is False
    assert "news source down" in result["error"]


# --------------------------------------------------------------------------
# R15-AGENT-063: the tool enriches (scores + tags) like the /news route does.
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_news_tool_items_carry_sentiment_and_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    canned = [_news_item("a1", "Company shares soar on record profit")]

    async def _fake_fetch(_client: Any, _symbols: list[str], _limit: int) -> list[NewsItem]:
        return canned

    from services import news_provider

    monkeypatch.setattr(news_provider, "fetch_news", _fake_fetch)
    news_tool.register()

    result = await agent_tools.invoke_tool("news", {})
    assert result["ok"] is True
    assert result["news"][0]["sentiment"] is not None
    assert result["news"][0]["sentiment_label"] == "positive"


@pytest.mark.asyncio
async def test_news_tool_tags_a_crypto_pair_by_its_base_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-063 class pin: BTC/USDT is normalised to BTC for alias
    matching — a headline says "BTC", never the literal pair."""
    canned = [_news_item("c1", "BTC rallies past resistance")]

    async def _fake_fetch(_client: Any, symbols: list[str], _limit: int) -> list[NewsItem]:
        return canned

    from services import news_provider

    monkeypatch.setattr(news_provider, "fetch_news", _fake_fetch)
    news_tool.register()

    result = await agent_tools.invoke_tool("news", {"symbols": ["BTC/USDT"]})
    assert result["ok"] is True
    assert result["news"][0]["symbols"] == ["BTC/USDT"]


def test_news_tool_id_has_no_forbidden_order_substring() -> None:
    """§6.5 mirror — the registered id must stay clear of order-placement verbs."""
    news_tool.register()
    forbidden = {"place_order", "submit_order", "execute_order", "auto_approve"}
    assert set(agent_tools.registered_tools()).isdisjoint(forbidden)
