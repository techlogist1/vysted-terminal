"""Tests for ``services.openbb_provider`` — normalisation + shape mapping.

The OpenBB SDK is not exercised live; instead the test patches the cached
``CommandRunner`` with a recorder that captures every ``sync_run`` call and
returns a canned response. The assertions cover both *what the provider sent
upstream* (route, provider choice, normalised symbol) and *what shape it
returned to the caller* (Vysted ``Quote``/``OHLCVSeries``/``Fundamentals`` etc).
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from services import openbb_provider

# ---------------------------------------------------------------------------
# Recorder fixture — replaces the cached CommandRunner instance.
# ---------------------------------------------------------------------------


class _Recorder:
    """Captures every ``sync_run`` call and returns canned ``OBBject``s."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: dict[str, Any] = {}

    def respond(
        self, route: str, results: list[dict[str, Any]], extra: dict[str, Any] | None = None
    ) -> None:
        self.responses[route] = SimpleNamespace(results=list(results), extra=extra or {})

    def sync_run(
        self,
        route: str,
        *,
        user: str = "",
        provider_choices: dict[str, Any] | None = None,
        standard_params: dict[str, Any] | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> Any:
        self.calls.append(
            {
                "route": route,
                "user": user,
                "provider_choices": provider_choices or {},
                "standard_params": standard_params or {},
                "extra_params": extra_params or {},
            }
        )
        if route not in self.responses:
            raise AssertionError(f"unexpected OpenBB route in test: {route!r}")
        return self.responses[route]


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    """Install a fresh recorder as the cached :class:`CommandRunner`."""
    rec = _Recorder()
    monkeypatch.setattr(openbb_provider, "_runner", rec)
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    return rec


# ---------------------------------------------------------------------------
# Symbol normalisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("BRK.B", "BRK-B"),
        ("BF.B", "BF-B"),
        ("RDS.A", "RDS-A"),
        ("aapl", "AAPL"),
        ("AAPL", "AAPL"),
    ],
)
def test_normalize_symbol(raw: str, expected: str) -> None:
    """Dot-tickers are dashed and case is normalised to upper."""
    assert openbb_provider._normalize_symbol(raw) == expected


# ---------------------------------------------------------------------------
# is_available + graceful degradation
# ---------------------------------------------------------------------------


def test_is_available_reports_module_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    assert openbb_provider.is_available() is True
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", False)
    assert openbb_provider.is_available() is False


def test_get_quote_raises_when_openbb_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without OpenBB present, every accessor raises ProviderError cleanly."""
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", False)
    monkeypatch.setattr(openbb_provider, "_runner", None)
    with pytest.raises(openbb_provider.ProviderError):
        openbb_provider.get_quote("AAPL")


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------


def test_get_quote_normalises_symbol_and_maps_fields(recorder: _Recorder) -> None:
    recorder.respond(
        "/equity/price/quote",
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
    quote = openbb_provider.get_quote("BRK.B")
    assert recorder.calls[0]["route"] == "/equity/price/quote"
    assert recorder.calls[0]["provider_choices"] == {"provider": "yfinance"}
    assert recorder.calls[0]["standard_params"] == {"symbol": "BRK-B"}
    assert quote.symbol == "BRK-B"
    assert quote.price == 100.0
    assert quote.change == pytest.approx(1.0)
    assert quote.change_percent == pytest.approx(1.0101010101010102)
    assert quote.provider == "openbb"


def test_get_quote_falls_back_to_close_when_last_price_missing(recorder: _Recorder) -> None:
    recorder.respond(
        "/equity/price/quote",
        [{"symbol": "AAPL", "close": 192.5, "previous_close": 190.0}],
    )
    quote = openbb_provider.get_quote("AAPL")
    assert quote.price == 192.5
    assert quote.change == pytest.approx(2.5)


def test_get_quote_raises_on_empty_results(recorder: _Recorder) -> None:
    recorder.respond("/equity/price/quote", [])
    with pytest.raises(openbb_provider.ProviderError):
        openbb_provider.get_quote("AAPL")


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_get_history_maps_bars(recorder: _Recorder) -> None:
    recorder.respond(
        "/equity/price/historical",
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
    series = openbb_provider.get_history("AAPL", "1d")
    assert recorder.calls[0]["extra_params"] == {"interval": "1d"}
    assert series.symbol == "AAPL"
    assert series.timeframe == "1d"
    assert series.provider == "openbb"
    assert len(series.bars) == 2
    assert series.bars[0].close == 190.0
    assert series.bars[0].timestamp == datetime(2026, 5, 12, tzinfo=UTC)


def test_get_history_passes_iso_range_through(recorder: _Recorder) -> None:
    recorder.respond("/equity/price/historical", [])
    openbb_provider.get_history("AAPL", "1d", range_="2025-01-01")
    assert recorder.calls[0]["extra_params"]["start_date"] == "2025-01-01"


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------


def test_get_fundamentals_combines_profile_and_metrics(recorder: _Recorder) -> None:
    recorder.respond(
        "/equity/profile",
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
        "/equity/fundamental/metrics",
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
    fundamentals = openbb_provider.get_fundamentals("AAPL")
    assert fundamentals.symbol == "AAPL"
    assert fundamentals.name == "Apple Inc."
    assert fundamentals.market_cap == 3_000_000_000_000
    # OpenBB returns dividend_yield as a fraction already; no /100 expected.
    assert fundamentals.dividend_yield == pytest.approx(0.0044)
    assert fundamentals.provider == "openbb"


def test_get_fundamentals_recovers_when_profile_route_empty(recorder: _Recorder) -> None:
    recorder.respond("/equity/profile", [])
    recorder.respond(
        "/equity/fundamental/metrics",
        [{"symbol": "AAPL", "pe_ratio": 31.2}],
    )
    fundamentals = openbb_provider.get_fundamentals("AAPL")
    assert fundamentals.symbol == "AAPL"
    assert fundamentals.pe_ratio == 31.2


# ---------------------------------------------------------------------------
# Financial statements
# ---------------------------------------------------------------------------


def test_get_income_statement_pivots_periods(recorder: _Recorder) -> None:
    recorder.respond(
        "/equity/fundamental/income",
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
    statement = openbb_provider.get_income_statement("AAPL")
    assert statement.symbol == "AAPL"
    assert statement.periods == ["2025-09-30", "2024-09-30"]
    labels = {line.label for line in statement.lines}
    assert "revenue" in labels
    assert "net_income" in labels
    by_label = {line.label: line.values for line in statement.lines}
    assert by_label["revenue"]["2025-09-30"] == 400_000.0


def test_get_balance_sheet_uses_balance_route(recorder: _Recorder) -> None:
    recorder.respond(
        "/equity/fundamental/balance",
        [{"symbol": "AAPL", "period_ending": "2025-09-30", "total_assets": 500_000.0}],
    )
    sheet = openbb_provider.get_balance_sheet("AAPL")
    assert sheet.periods == ["2025-09-30"]
    assert recorder.calls[0]["route"] == "/equity/fundamental/balance"


def test_get_cash_flow_uses_cash_route(recorder: _Recorder) -> None:
    recorder.respond(
        "/equity/fundamental/cash",
        [{"symbol": "AAPL", "period_ending": "2025-09-30", "operating_cash_flow": 120_000.0}],
    )
    flow = openbb_provider.get_cash_flow("AAPL")
    assert flow.periods == ["2025-09-30"]
    assert recorder.calls[0]["route"] == "/equity/fundamental/cash"


# ---------------------------------------------------------------------------
# Analyst ratings
# ---------------------------------------------------------------------------


def test_get_analyst_rating_maps_consensus_and_targets(recorder: _Recorder) -> None:
    recorder.respond(
        "/equity/estimates/price_target",
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
    rating = openbb_provider.get_analyst_rating("AAPL")
    assert rating.symbol == "AAPL"
    assert rating.consensus == "buy"
    assert rating.target_mean == 225.0
    assert rating.strong_buy == 12
    assert rating.buy == 20


# ---------------------------------------------------------------------------
# Macro
# ---------------------------------------------------------------------------


def test_get_macro_series_maps_observations(recorder: _Recorder) -> None:
    recorder.respond(
        "/economy/fred_series",
        [
            {"date": "2025-01-01", "value": 5.5},
            {"date": "2025-02-01", "value": 5.6},
            {"date": "2025-03-01", "value": 5.7},
        ],
        extra={"results_metadata": {"DGS10": {"title": "10-Year Treasury Yield"}}},
    )
    series = openbb_provider.get_macro_series("DGS10")
    assert series.series_id == "DGS10"
    assert series.title == "10-Year Treasury Yield"
    assert len(series.observations) == 3
    assert series.observations[0].value == 5.5
    assert series.provider == "openbb"
    # Provider choice must be FRED by default for macro data.
    assert recorder.calls[0]["provider_choices"] == {"provider": "fred"}


def test_get_macro_series_accepts_provider_override(recorder: _Recorder) -> None:
    recorder.respond("/economy/fred_series", [{"date": "2025-01-01", "value": 1.0}])
    openbb_provider.get_macro_series("GDP", provider="econdb")
    assert recorder.calls[0]["provider_choices"] == {"provider": "econdb"}


# ---------------------------------------------------------------------------
# CommandRunner failure -> ProviderError
# ---------------------------------------------------------------------------


def test_command_runner_exception_translated_to_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Boom:
        def sync_run(self, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("upstream 503")

    monkeypatch.setattr(openbb_provider, "_runner", _Boom())
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    with pytest.raises(openbb_provider.ProviderError, match="503"):
        openbb_provider.get_quote("AAPL")
