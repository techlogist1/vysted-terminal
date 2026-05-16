"""Tests for the v0.6.0 macro agent tools (Teammate M).

Covers register/invoke wiring, argument validation, provider whitelist
enforcement, and provider-error translation into the ``ok=False`` envelope.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from models.macro_extended import MacroSearchResult, MacroSeriesExtended
from models.market import MacroObservation
from services import agent_tools, data_cache
from services.agent_tools import macro_tools
from services.errors import ProviderError
from services.macro import fred_provider


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    data_cache.reset_for_tests(tmp_path / "tools_cache.db")
    yield
    data_cache.reset_for_tests(None)


@pytest.fixture(autouse=True)
def _isolated_registry() -> None:
    agent_tools.reset_for_tests()
    yield
    agent_tools.reset_for_tests()


def _series_stub() -> MacroSeriesExtended:
    return MacroSeriesExtended(
        series_id="DGS10",
        title="10-Year",
        units="Percent",
        observations=[MacroObservation(date=datetime(2026, 5, 14, tzinfo=UTC), value=4.25)],
        provider="fred",
        frequency="daily",
        last_updated=None,
        seasonal_adjustment=None,
        source_url=None,
        notes=None,
    )


@pytest.mark.asyncio
async def test_register_installs_two_tools() -> None:
    macro_tools.register()
    assert agent_tools.is_registered("macro_series")
    assert agent_tools.is_registered("macro_search")


@pytest.mark.asyncio
async def test_macro_series_returns_ok_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fred_provider, "get_series", lambda sid: _series_stub())
    macro_tools.register()
    result = await agent_tools.invoke_tool(
        "macro_series", {"series_id": "DGS10", "provider": "fred"}
    )
    assert result["ok"] is True
    assert result["series"]["provider"] == "fred"


@pytest.mark.asyncio
async def test_macro_series_rejects_missing_series_id() -> None:
    macro_tools.register()
    result = await agent_tools.invoke_tool("macro_series", {"provider": "fred"})
    assert result["ok"] is False
    assert "series_id" in result["error"]


@pytest.mark.asyncio
async def test_macro_series_rejects_unknown_provider() -> None:
    macro_tools.register()
    result = await agent_tools.invoke_tool("macro_series", {"series_id": "X", "provider": "yodlee"})
    assert result["ok"] is False


@pytest.mark.asyncio
async def test_macro_series_wraps_provider_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_sid: str) -> MacroSeriesExtended:
        raise ProviderError("no key")

    monkeypatch.setattr(fred_provider, "get_series", boom)
    macro_tools.register()
    result = await agent_tools.invoke_tool(
        "macro_series", {"series_id": "DGS10", "provider": "fred"}
    )
    assert result["ok"] is False
    assert "provider error" in result["error"]


@pytest.mark.asyncio
async def test_macro_search_returns_results(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        MacroSearchResult(
            provider="fred",
            series_id="DGS10",
            title="10-Year",
            frequency="daily",
            units="Percent",
            score=0.9,
        )
    ]
    monkeypatch.setattr(fred_provider, "search", lambda q, limit=25: rows)
    macro_tools.register()
    result = await agent_tools.invoke_tool(
        "macro_search", {"q": "treasury", "provider": "fred", "limit": 5}
    )
    assert result["ok"] is True
    assert result["results"][0]["series_id"] == "DGS10"


@pytest.mark.asyncio
async def test_macro_search_rejects_missing_query() -> None:
    macro_tools.register()
    result = await agent_tools.invoke_tool("macro_search", {"provider": "fred"})
    assert result["ok"] is False


@pytest.mark.asyncio
async def test_macro_tools_do_not_contain_placement_words() -> None:
    """§6.5 hygiene — no broker / order-placement tool ids."""
    macro_tools.register()
    for tool_id in agent_tools.registered_tools():
        for banned in ("place_order", "submit_order", "execute_order", "auto_approve"):
            assert banned not in tool_id
