"""Tests for the ``screener_run`` agent tool."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from services import agent_tools, data_cache, fundamentals_store
from services.agent_tools import screener_tools


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    data_cache.reset_for_tests(tmp_path / "tools_test_cache.db")
    fundamentals_store.reset_for_tests(tmp_path / "fundamentals_test.db")
    yield
    data_cache.reset_for_tests(None)
    fundamentals_store.reset_for_tests(None)


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

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

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
async def test_screener_run_accepts_formula_and_filters_server_side(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The agent can pass ``formula`` TODAY (the tool revalidates through
    ScreenerRequest, which carries the field) — R7 Pillar 3. The catalog
    schema advertisement is the lead's wiring (INTEGRATION_NOTES_R7_HACK)."""
    # Fictional bare tickers: pin US so the region-aware custom-symbol
    # canonicalisation (R15-DATA-093) keeps them literal.
    monkeypatch.setenv("VYSTED_REGION", "US")

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return _make_fundamentals(symbol, pe_ratio=10.0 if symbol == "AAA" else 40.0, roe=0.3)

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    response = await screener_tools._screener_run(
        {
            "universe": "custom",
            "custom_symbols": ["AAA", "BBB"],
            "criteria": [],
            "formula": "pe < 15 and roe > 0.2",
            "limit": 10,
        }
    )
    assert response["ok"] is True
    assert [row["symbol"] for row in response["result"]["rows"]] == ["AAA"]
    assert response["result"]["evaluated_count"] == 2


@pytest.mark.asyncio
async def test_screener_run_bad_formula_is_clean_tool_error() -> None:
    """An unparseable formula is a recovery-first ``{"ok": False}`` return
    carrying the caret column — never a crash out of the tool surface."""
    response = await screener_tools._screener_run(
        {
            "universe": "sp500",
            "criteria": [],
            "formula": "pe << 15",
        }
    )
    assert response["ok"] is False
    assert "invalid formula" in response["error"]
    assert "col" in response["error"]


@pytest.mark.asyncio
async def test_screener_run_invalid_payload_returns_error() -> None:
    response = await screener_tools._screener_run({"universe": "nope", "criteria": []})
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


@pytest.mark.asyncio
async def test_screener_run_counts_skips_instead_of_listing_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-009: a partial india-all run skipped ~5,000 symbols and every
    {symbol, reason} row went into the model's context."""
    import json

    from models.screener import ScreenerResult, SkipDetail
    from services import screener

    reasons = ["timeout", "not_found", "missing_field:pe_ratio"]
    skips = [SkipDetail(symbol=f"SYM{i}.NS", reason=reasons[i % 3]) for i in range(5000)]

    async def fake_run(_request: Any) -> ScreenerResult:
        return ScreenerResult(
            universe="india-all",
            evaluated_count=100,
            skipped_count=5000,
            skip_details=skips,
            result_count=0,
            rows=[],
            duration_ms=1.0,
            partial=True,
        )

    monkeypatch.setattr(screener, "run_screener", fake_run)
    response = await screener_tools._screener_run(
        {
            "universe": "india-all",
            "criteria": [{"field": "pe_ratio", "operator": "lt", "value": 15}],
        }
    )
    result = response["result"]
    assert len(json.dumps(response)) < 2_000
    assert "skip_details" not in result
    assert result["skipped_count"] == 5000
    assert result["skip_summary"] == {
        "timeout": 1667,
        "not_found": 1667,
        "missing_field:pe_ratio": 1666,
    }
    assert len(result["skip_examples"]) == 5
