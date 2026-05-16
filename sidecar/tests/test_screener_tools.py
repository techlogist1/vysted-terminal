"""Tests for the ``screener_run`` agent tool."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from services import agent_tools, data_cache
from services.agent_tools import screener_tools


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    data_cache.reset_for_tests(tmp_path / "tools_test_cache.db")
    yield
    data_cache.reset_for_tests(None)


def _make_fundamentals(symbol: str, **overrides: Any) -> Fundamentals:
    payload: dict[str, Any] = {
        "symbol": symbol,
        "name": f"{symbol} Inc.",
        "sector": "Technology",
        "industry": "Software",
        "market_cap": 500_000_000_000.0,
        "pe_ratio": 15.0,
        "provider": "test",
    }
    payload.update(overrides)
    return Fundamentals(**payload)


def _make_quote(symbol: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=100.0,
        change=1.5,
        change_percent=1.5,
        volume=1_000_000.0,
        currency="USD",
        market_state="open",
        timestamp=datetime.now(tz=UTC),
        provider="test",
    )


def test_register_adds_screener_run_to_registry() -> None:
    """``screener_tools.register()`` adds the id to the package registry."""
    # The package import runs in conftest's app build; assert the tool id
    # is already registered (which it is after :func:`register_v0_6_0_tools`).
    assert agent_tools.is_registered("screener_run")


@pytest.mark.asyncio
async def test_screener_run_invokes_engine_and_returns_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return _make_fundamentals(symbol)

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr(
        "services.provider_registry.get_fundamentals", fake_get_fundamentals
    )
    monkeypatch.setattr(
        "services.provider_registry.get_quote", fake_get_quote
    )

    response = await screener_tools._screener_run(
        {
            "universe": "custom",
            "custom_symbols": ["AAA", "BBB"],
            "criteria": [
                {"field": "sector", "operator": "eq", "value": "Technology"},
            ],
            "limit": 10,
        }
    )
    assert response["ok"] is True
    assert response["result"]["result_count"] == 2


@pytest.mark.asyncio
async def test_screener_run_invalid_payload_returns_error() -> None:
    response = await screener_tools._screener_run(
        {"universe": "nope", "criteria": []}
    )
    assert response["ok"] is False
    assert "invalid screener request" in response["error"]


@pytest.mark.asyncio
async def test_screener_run_tool_id_safe_for_safety_audit() -> None:
    """§6.5 audit greps for ``place_order|submit_order|execute_order`` tool ids.

    The ``screener_run`` id must not appear in that pattern — this is a
    belt-and-braces check (the v0.5.0 audit test does the real grep).
    """
    tool_id = "screener_run"
    for forbidden in ("place_order", "submit_order", "execute_order", "auto_approve"):
        assert forbidden not in tool_id
