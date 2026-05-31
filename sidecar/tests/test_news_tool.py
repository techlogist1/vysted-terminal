"""Tests for the ``news`` agent tool — register/invoke wiring, symbol parsing,
the provider-error envelope, and the §6.5 forbidden-id invariant.

Matches the per-domain test pattern of its v0.6.0 siblings (macro/sec/quant/
earnings/analyst). The ``news`` tool was added when the capability catalog was
projected to the external MCP surface (FR-022) so news is reachable by BOTH the
internal copilot and external MCP clients under the same name.
"""

from __future__ import annotations

from typing import Any

import pytest

from services import agent_tools
from services.agent_tools import news_tool
from services.errors import ProviderError


@pytest.fixture(autouse=True)
def _isolated_registry() -> None:
    agent_tools.reset_for_tests()
    yield
    agent_tools.reset_for_tests()


class _FakeNewsItem:
    """Stands in for a NewsItem — only ``model_dump`` is used by the handler."""

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        return {"title": "Headline", "source": "Test", "sentiment": 0.1}


def test_register_adds_news_to_the_registry() -> None:
    news_tool.register()
    assert agent_tools.is_registered("news")


@pytest.mark.asyncio
async def test_news_returns_ok_envelope_with_mapped_items(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def _fake_fetch(_client: Any, symbols: list[str], limit: int) -> list[_FakeNewsItem]:
        captured["symbols"] = symbols
        captured["limit"] = limit
        return [_FakeNewsItem(), _FakeNewsItem()]

    from services import news_provider

    monkeypatch.setattr(news_provider, "fetch_news", _fake_fetch)
    news_tool.register()

    result = await agent_tools.invoke_tool("news", {"symbols": ["AAPL", "MSFT"], "limit": 5})
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["news"][0]["title"] == "Headline"
    assert captured["symbols"] == ["AAPL", "MSFT"]
    assert captured["limit"] == 5


@pytest.mark.asyncio
async def test_news_parses_comma_separated_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def _fake_fetch(_client: Any, symbols: list[str], _limit: int) -> list[_FakeNewsItem]:
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
    async def _boom(_client: Any, _symbols: list[str], _limit: int) -> list[_FakeNewsItem]:
        raise ProviderError("news source down")

    from services import news_provider

    monkeypatch.setattr(news_provider, "fetch_news", _boom)
    news_tool.register()

    result = await agent_tools.invoke_tool("news", {})
    assert result["ok"] is False
    assert "news source down" in result["error"]


def test_news_tool_id_has_no_forbidden_order_substring() -> None:
    """§6.5 mirror — the registered id must stay clear of order-placement verbs."""
    news_tool.register()
    forbidden = {"place_order", "submit_order", "execute_order", "auto_approve"}
    assert set(agent_tools.registered_tools()).isdisjoint(forbidden)
