"""Tests for the ``analysis.screener_query`` workflow node."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from services import data_cache, workflow_engine
from services.workflow_nodes import screener_nodes


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    data_cache.reset_for_tests(tmp_path / "nodes_test_cache.db")
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


def test_register_adds_screener_query_to_workflow_engine() -> None:
    """``register()`` adds ``analysis.screener_query`` to the engine registry."""
    # The conftest's TestClient build triggers ``register_v0_6_0_nodes`` which
    # calls our register helper. Assert the node is in the registry.
    assert "analysis.screener_query" in workflow_engine.registered_node_types()


@pytest.mark.asyncio
async def test_screener_query_runs_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without inputs, config supplies the universe + criteria."""

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return _make_fundamentals(symbol)

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    outputs = await screener_nodes.screener_query(
        inputs={},
        config={
            "universe": "custom",
            "custom_symbols": ["AAA", "BBB"],
            "criteria": [
                {"field": "sector", "operator": "eq", "value": "Technology"},
            ],
        },
    )
    assert outputs["result_count"] == 2
    assert outputs["evaluated_count"] == 2
    assert len(outputs["rows"]) == 2


@pytest.mark.asyncio
async def test_screener_query_inputs_override_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Upstream node outputs (inputs) take precedence over static config."""

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return _make_fundamentals(symbol)

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    outputs = await screener_nodes.screener_query(
        inputs={
            "universe": "custom",
            "custom_symbols": ["INPUT_A"],
            "criteria": [
                {"field": "sector", "operator": "eq", "value": "Technology"},
            ],
        },
        config={
            "universe": "sp500",
            "criteria": [],
        },
    )
    assert outputs["result_count"] == 1
    assert outputs["rows"][0]["symbol"] == "INPUT_A"


@pytest.mark.asyncio
async def test_screener_query_missing_universe_raises_value_error() -> None:
    with pytest.raises(ValueError, match="universe"):
        await screener_nodes.screener_query({}, {})


@pytest.mark.asyncio
async def test_screener_query_invalid_criteria_raises_value_error() -> None:
    with pytest.raises(ValueError):
        await screener_nodes.screener_query(
            {},
            {
                "universe": "custom",
                "custom_symbols": ["X"],
                "criteria": [{"operator": "wat"}],
            },
        )
