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


def test_one_raising_quote_yields_one_error_row(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-AGENT-069: ``_quote_one`` already catches every known failure, but
    the inner ``gather`` used to omit ``return_exceptions=True`` — a truly
    unexpected exception from one index's task would raise out of ``gather``
    and crash the whole overview instead of degrading to that one index."""

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

    async def fake_news(client: Any, symbols: list[str], limit: int) -> list[Any]:
        return []

    real_quote_one = market_overview._quote_one

    async def _boom_for_bsesn(symbol: str, region: str) -> dict:
        if symbol == "^BSESN":
            raise RuntimeError("totally unexpected blowup")
        return await real_quote_one(symbol, region)

    monkeypatch.setattr(provider_registry, "get_quote", fake_quote)
    monkeypatch.setattr(news_provider, "fetch_news", fake_news)
    monkeypatch.setattr(market_overview, "_quote_one", _boom_for_bsesn)

    result = asyncio.run(market_overview._market_overview({"region": "IN"}))

    assert result["ok"] is True
    by_symbol = {idx["symbol"]: idx for idx in result["indices"]}
    assert "totally unexpected blowup" in by_symbol["^BSESN"]["error"]
    assert "error" not in by_symbol["^NSEI"]


def test_global_region_carries_us_proxy_note(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-DATA-101: region 'GLOBAL' silently reused the US index set with no
    note, so the model read "GLOBAL" as its own benchmark."""

    def fake_quote(symbol: str, asset_class: str, region: str) -> Any:
        return SimpleNamespace(
            symbol=symbol,
            price=100.0,
            change=1.0,
            change_percent=1.0,
            currency="USD",
            market_state="REGULAR",
            provider="yfinance",
        )

    async def fake_news(client: Any, symbols: list[str], limit: int) -> list[Any]:
        return []

    monkeypatch.setattr(provider_registry, "get_quote", fake_quote)
    monkeypatch.setattr(news_provider, "fetch_news", fake_news)

    result = asyncio.run(market_overview._market_overview({"region": "GLOBAL"}))

    assert result["ok"] is True
    assert [idx["symbol"] for idx in result["indices"]] == ["^GSPC", "^IXIC", "^DJI", "SPY", "QQQ"]
    assert "note" in result
    assert "GLOBAL" in result["note"]
    assert "US" in result["note"]


def test_us_region_carries_no_note(monkeypatch: pytest.MonkeyPatch) -> None:
    """A region with its own index set (US) never gets the substitution note."""

    def fake_quote(symbol: str, asset_class: str, region: str) -> Any:
        return SimpleNamespace(
            symbol=symbol,
            price=100.0,
            change=1.0,
            change_percent=1.0,
            currency="USD",
            market_state="REGULAR",
            provider="yfinance",
        )

    async def fake_news(client: Any, symbols: list[str], limit: int) -> list[Any]:
        return []

    monkeypatch.setattr(provider_registry, "get_quote", fake_quote)
    monkeypatch.setattr(news_provider, "fetch_news", fake_news)

    result = asyncio.run(market_overview._market_overview({"region": "US"}))

    assert "note" not in result


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
