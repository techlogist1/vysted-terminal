"""``market_overview``: a news-feed outage is reported, never read as "no news"
(R15-AGENT-058)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from services import news_provider, provider_registry
from services.agent_tools import market_overview
from services.errors import ProviderError


def test_news_outage_sets_headlines_error_and_keeps_indices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_quote(symbol: str, asset_class: str, region: str) -> Any:
        return SimpleNamespace(
            symbol=symbol,
            price=100.0,
            change=1.0,
            change_percent=1.0,
            currency="INR",
            market_state="REGULAR",
            provider="yfinance",
        )

    async def failing_news(client: Any, symbols: list[str], limit: int) -> list[Any]:
        raise ProviderError("all news sources failed")

    monkeypatch.setattr(provider_registry, "get_quote", fake_quote)
    monkeypatch.setattr(news_provider, "fetch_news", failing_news)

    result = asyncio.run(market_overview._market_overview({"region": "IN"}))

    assert result["ok"] is True
    assert [idx["symbol"] for idx in result["indices"]] == ["^NSEI", "^BSESN"]
    assert result["headlines"] == []
    assert "all news sources failed" in result["headlines_error"]
