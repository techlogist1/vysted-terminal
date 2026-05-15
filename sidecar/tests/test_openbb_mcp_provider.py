"""Tests for ``services.openbb_mcp_provider`` — MCP client routing + shape mapping.

The openbb-mcp subprocess is never launched live; instead the test installs a
fake :class:`McpClient` whose ``call_tool`` returns canned JSON payloads. The
assertions cover (a) what tool the provider invokes upstream (right name, right
arguments) and (b) what shape it returns to the caller (Vysted
``Quote``/``OHLCVSeries``/``Fundamentals``/...).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import pytest

from services import errors, mcp_client, openbb_mcp_provider
from services.openbb_mcp_provider import ProviderError


class _RecordingClient:
    """Stand-in for :class:`McpClient` — captures every ``call_tool`` invocation."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: dict[str, Any] = {}

    def respond(
        self, tool_name: str, results: list[dict[str, Any]], extra: dict[str, Any] | None = None
    ) -> None:
        body = {"results": list(results), "extra": extra or {}}
        self.responses[tool_name] = body

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"name": name, "arguments": arguments})
        if name not in self.responses:
            raise AssertionError(f"unexpected openbb-mcp tool in test: {name!r}")
        return {
            "isError": False,
            "content": [{"type": "text", "text": json.dumps(self.responses[name])}],
        }


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _RecordingClient:
    """Install a recording fake client + pin the env-var path to 'available'."""
    rec = _RecordingClient()

    async def _fake_get_client(
        server_id: str, *, transport: str, endpoint: str | None = None, **_: Any
    ) -> _RecordingClient:
        return rec

    monkeypatch.setattr(mcp_client, "get_client", _fake_get_client)
    monkeypatch.setenv("VYSTED_OPENBB_MCP_PORT", "9999")
    openbb_mcp_provider._reset_for_tests()
    return rec


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


def test_is_available_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """``is_available`` flips with the env var the Tauri Rust core sets."""
    openbb_mcp_provider._reset_for_tests()
    monkeypatch.delenv("VYSTED_OPENBB_MCP_PORT", raising=False)
    assert openbb_mcp_provider.is_available() is False

    openbb_mcp_provider._reset_for_tests()
    monkeypatch.setenv("VYSTED_OPENBB_MCP_PORT", "9000")
    assert openbb_mcp_provider.is_available() is True


def test_status_returns_endpoint_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    openbb_mcp_provider._reset_for_tests()
    monkeypatch.setenv("VYSTED_OPENBB_MCP_PORT", "9000")
    monkeypatch.setenv("VYSTED_OPENBB_MCP_HOST", "127.0.0.1")
    status = asyncio.run(openbb_mcp_provider.status())
    assert status["available"] is True
    assert status["endpoint"] == "http://127.0.0.1:9000/mcp"
    assert status["provider"] == "openbb-mcp"


def test_status_returns_unavailable_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    openbb_mcp_provider._reset_for_tests()
    monkeypatch.delenv("VYSTED_OPENBB_MCP_PORT", raising=False)
    status = asyncio.run(openbb_mcp_provider.status())
    assert status["available"] is False
    assert status["endpoint"] is None


# ---------------------------------------------------------------------------
# Symbol normalisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("BRK.B", "BRK-B"),
        ("BF.B", "BF-B"),
        ("aapl", "AAPL"),
        ("AAPL", "AAPL"),
    ],
)
def test_normalize_symbol(raw: str, expected: str) -> None:
    assert openbb_mcp_provider._normalize_symbol(raw) == expected


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------


def test_get_quote_normalises_symbol_and_maps_fields(recorder: _RecordingClient) -> None:
    recorder.respond(
        "equity_price_quote",
        [
            {
                "symbol": "BRK-B",
                "last_price": 100.0,
                "prev_close": 99.0,
                "currency": "USD",
                "volume": 1000.0,
                "last_timestamp": "2026-05-15T15:30:00",
            }
        ],
    )
    quote = asyncio.run(openbb_mcp_provider.get_quote("BRK.B"))
    assert recorder.calls[0]["name"] == "equity_price_quote"
    assert recorder.calls[0]["arguments"]["symbol"] == "BRK-B"
    assert recorder.calls[0]["arguments"]["provider"] == "yfinance"
    assert quote.symbol == "BRK-B"
    assert quote.price == 100.0
    assert quote.change == pytest.approx(1.0)
    assert quote.change_percent == pytest.approx(1.0101010101010102)
    assert quote.provider == "openbb-mcp"


def test_get_quote_raises_on_empty_results(recorder: _RecordingClient) -> None:
    recorder.respond("equity_price_quote", [])
    with pytest.raises(ProviderError):
        asyncio.run(openbb_mcp_provider.get_quote("AAPL"))


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_get_history_maps_bars(recorder: _RecordingClient) -> None:
    recorder.respond(
        "equity_price_historical",
        [
            {
                "date": "2026-05-12",
                "open": 188.0,
                "high": 191.0,
                "low": 187.0,
                "close": 190.0,
                "volume": 48_000_000,
            },
            {
                "date": "2026-05-13",
                "open": 190.0,
                "high": 192.0,
                "low": 189.0,
                "close": 191.0,
                "volume": 49_500_000,
            },
        ],
    )
    series = asyncio.run(openbb_mcp_provider.get_history("AAPL", "1d"))
    assert recorder.calls[0]["name"] == "equity_price_historical"
    assert recorder.calls[0]["arguments"]["interval"] == "1d"
    assert series.symbol == "AAPL"
    assert series.timeframe == "1d"
    assert series.provider == "openbb-mcp"
    assert len(series.bars) == 2
    assert series.bars[0].close == 190.0
    assert series.bars[0].timestamp == datetime(2026, 5, 12, tzinfo=UTC)


def test_get_history_passes_iso_range_through(recorder: _RecordingClient) -> None:
    recorder.respond("equity_price_historical", [])
    asyncio.run(openbb_mcp_provider.get_history("AAPL", "1d", range_="2025-01-01"))
    assert recorder.calls[0]["arguments"]["start_date"] == "2025-01-01"


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------


def test_get_fundamentals_combines_profile_and_metrics(recorder: _RecordingClient) -> None:
    recorder.respond(
        "equity_profile",
        [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
            }
        ],
    )
    recorder.respond(
        "equity_fundamental_metrics",
        [
            {
                "symbol": "AAPL",
                "market_cap": 3_000_000_000_000,
                "pe_ratio": 31.2,
                "forward_pe": 28.4,
                "peg_ratio": 2.1,
                "price_to_book": 47.0,
                "dividend_yield": 0.0044,
                "eps": 6.17,
                "beta": 1.25,
                "fifty_two_week_high": 220.0,
                "fifty_two_week_low": 160.0,
            }
        ],
    )
    fundamentals = asyncio.run(openbb_mcp_provider.get_fundamentals("AAPL"))
    assert fundamentals.symbol == "AAPL"
    assert fundamentals.name == "Apple Inc."
    assert fundamentals.market_cap == 3_000_000_000_000
    assert fundamentals.dividend_yield == pytest.approx(0.0044)
    assert fundamentals.provider == "openbb-mcp"


# ---------------------------------------------------------------------------
# Financial statements
# ---------------------------------------------------------------------------


def test_get_income_statement_pivots_periods(recorder: _RecordingClient) -> None:
    recorder.respond(
        "equity_fundamental_income",
        [
            {
                "symbol": "AAPL",
                "period_ending": "2025-09-30",
                "revenue": 400_000.0,
                "net_income": 100_000.0,
            },
            {
                "symbol": "AAPL",
                "period_ending": "2024-09-30",
                "revenue": 380_000.0,
                "net_income": 95_000.0,
            },
        ],
    )
    statement = asyncio.run(openbb_mcp_provider.get_income_statement("AAPL"))
    assert statement.symbol == "AAPL"
    assert statement.periods == ["2025-09-30", "2024-09-30"]
    labels = {line.label for line in statement.lines}
    assert "revenue" in labels
    assert "net_income" in labels


def test_get_balance_sheet_uses_balance_tool(recorder: _RecordingClient) -> None:
    recorder.respond(
        "equity_fundamental_balance",
        [{"symbol": "AAPL", "period_ending": "2025-09-30", "total_assets": 500_000.0}],
    )
    sheet = asyncio.run(openbb_mcp_provider.get_balance_sheet("AAPL"))
    assert sheet.periods == ["2025-09-30"]
    assert recorder.calls[0]["name"] == "equity_fundamental_balance"


def test_get_cash_flow_uses_cash_tool(recorder: _RecordingClient) -> None:
    recorder.respond(
        "equity_fundamental_cash",
        [{"symbol": "AAPL", "period_ending": "2025-09-30", "operating_cash_flow": 120_000.0}],
    )
    flow = asyncio.run(openbb_mcp_provider.get_cash_flow("AAPL"))
    assert flow.periods == ["2025-09-30"]
    assert recorder.calls[0]["name"] == "equity_fundamental_cash"


# ---------------------------------------------------------------------------
# Analyst ratings + macro
# ---------------------------------------------------------------------------


def test_get_analyst_rating_maps_consensus_and_targets(recorder: _RecordingClient) -> None:
    recorder.respond(
        "equity_estimates_price_target",
        [
            {
                "symbol": "AAPL",
                "consensus": "buy",
                "target_mean": 225.0,
                "target_high": 260.0,
                "target_low": 170.0,
                "strong_buy": 12,
                "buy": 20,
                "hold": 8,
                "sell": 1,
                "strong_sell": 0,
            }
        ],
    )
    rating = asyncio.run(openbb_mcp_provider.get_analyst_rating("AAPL"))
    assert rating.symbol == "AAPL"
    assert rating.consensus == "buy"
    assert rating.target_mean == 225.0
    assert rating.strong_buy == 12


def test_get_macro_series_maps_observations(recorder: _RecordingClient) -> None:
    recorder.respond(
        "economy_fred_series",
        [
            {"date": "2025-01-01", "value": 5.5},
            {"date": "2025-02-01", "value": 5.6},
            {"date": "2025-03-01", "value": 5.7},
        ],
        extra={"results_metadata": {"DGS10": {"title": "10-Year Treasury Yield"}}},
    )
    series = asyncio.run(openbb_mcp_provider.get_macro_series("DGS10"))
    assert series.series_id == "DGS10"
    assert series.title == "10-Year Treasury Yield"
    assert len(series.observations) == 3
    assert series.observations[0].value == 5.5
    assert series.provider == "openbb-mcp"
    # Provider choice must be FRED by default for macro data.
    assert recorder.calls[0]["arguments"]["provider"] == "fred"


def test_get_macro_series_accepts_provider_override(recorder: _RecordingClient) -> None:
    recorder.respond("economy_fred_series", [{"date": "2025-01-01", "value": 1.0}])
    asyncio.run(openbb_mcp_provider.get_macro_series("GDP", provider="econdb"))
    assert recorder.calls[0]["arguments"]["provider"] == "econdb"


# ---------------------------------------------------------------------------
# MCP tool failure -> ProviderError
# ---------------------------------------------------------------------------


def test_mcp_tool_exception_translated_to_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Boom:
        async def call_tool(self, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("upstream 503")

    async def _fake_get_client(*_args: Any, **_kwargs: Any) -> _Boom:
        return _Boom()

    monkeypatch.setattr(mcp_client, "get_client", _fake_get_client)
    monkeypatch.setenv("VYSTED_OPENBB_MCP_PORT", "9999")
    openbb_mcp_provider._reset_for_tests()
    with pytest.raises(errors.ProviderError, match="503"):
        asyncio.run(openbb_mcp_provider.get_quote("AAPL"))


def test_mcp_call_without_endpoint_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the env-var endpoint, the provider declines rather than hangs."""
    openbb_mcp_provider._reset_for_tests()
    monkeypatch.delenv("VYSTED_OPENBB_MCP_PORT", raising=False)
    with pytest.raises(ProviderError, match="VYSTED_OPENBB_MCP_PORT"):
        asyncio.run(openbb_mcp_provider.get_quote("AAPL"))


# ---------------------------------------------------------------------------
# Provider registry fallback — confirms the new provider plugs in cleanly.
# ---------------------------------------------------------------------------


def test_registry_falls_back_to_yfinance_when_openbb_mcp_unavailable(
    monkeypatch: pytest.MonkeyPatch, mock_yfinance: object
) -> None:
    """When openbb-mcp is unavailable, the registry uses yfinance instead."""
    from services import provider_registry

    monkeypatch.delenv("VYSTED_OPENBB_MCP_PORT", raising=False)
    openbb_mcp_provider._reset_for_tests()
    result = asyncio.run(provider_registry.get_fundamentals("AAPL"))
    assert result.provider == "yfinance"


def test_registry_uses_openbb_mcp_when_available(
    monkeypatch: pytest.MonkeyPatch, recorder: _RecordingClient, mock_yfinance: object
) -> None:
    """When openbb-mcp is available, the registry routes through it."""
    from services import provider_registry

    recorder.respond(
        "equity_profile",
        [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
            }
        ],
    )
    recorder.respond(
        "equity_fundamental_metrics",
        [{"symbol": "AAPL", "pe_ratio": 31.2}],
    )
    result = asyncio.run(provider_registry.get_fundamentals("AAPL"))
    assert result.provider == "openbb-mcp"
    assert result.pe_ratio == 31.2
