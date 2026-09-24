"""Tests for the ``compare_symbols`` agent tool.

The tool fans out to ``provider_registry.get_quote`` / ``get_history`` /
``get_fundamentals`` per symbol; these tests monkeypatch those three
accessors (mirroring ``test_provider_registry.py``) so no network or real
provider is touched. They assert: a two-symbol compare returns ``ok`` with
both symbols and a ``return_pct_window`` each; a one-symbol input is rejected
with ``ok=False``; and a single failing symbol is reported (not raised),
falling below the two-resolved floor.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from models.fundamentals import Fundamentals
from models.market import OHLCVBar, OHLCVSeries, Quote
from services.agent_tools.compare_symbols import _compare_one, _compare_symbols


@pytest.fixture(autouse=True)
def _no_live_resolver_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """A symbol with no quote is run through the resolver; keep its one network
    rung (the live yfinance.Search) out of the tests — the bundled masters answer."""
    from services import symbol_resolver

    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: [])


def _quote(symbol: str, price: float = 100.0, provider: str = "yfinance") -> Quote:
    return Quote(
        symbol=symbol,
        price=price,
        change=1.0,
        change_percent=1.0,
        currency="USD",
        timestamp=datetime.now(tz=UTC),
        provider=provider,
    )


def _series(symbol: str, first: float, last: float, provider: str = "yfinance") -> OHLCVSeries:
    def _bar(close: float) -> OHLCVBar:
        return OHLCVBar(
            timestamp=datetime.now(tz=UTC),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1_000.0,
        )

    return OHLCVSeries(
        symbol=symbol,
        timeframe="1d",
        bars=[_bar(first), _bar((first + last) / 2), _bar(last)],
        provider=provider,
    )


def _fundamentals(symbol: str) -> Fundamentals:
    return Fundamentals(symbol=symbol, market_cap=1.0e12, pe_ratio=25.0, provider="yfinance")


def _patch_registry(
    monkeypatch: pytest.MonkeyPatch,
    *,
    quotes: dict[str, Quote] | None = None,
    series: dict[str, OHLCVSeries] | None = None,
    fundamentals: dict[str, Fundamentals] | None = None,
    quote_errors: set[str] | None = None,
) -> None:
    from services import provider_registry
    from services.errors import ProviderError

    quotes = quotes or {}
    series = series or {}
    fundamentals = fundamentals or {}
    quote_errors = quote_errors or set()

    def fake_quote(symbol: str, asset_class: str = "equity", region: str | None = None) -> Quote:
        if symbol in quote_errors:
            raise ProviderError(f"no quote for {symbol}")
        return quotes[symbol]

    def fake_history(
        symbol: str,
        timeframe: str,
        range_: str | None = None,
        asset_class: str = "equity",
        region: str | None = None,
    ) -> OHLCVSeries:
        return series[symbol]

    async def fake_fundamentals(symbol: str, region: str | None = None) -> Fundamentals:
        return fundamentals[symbol]

    monkeypatch.setattr(provider_registry, "get_quote", fake_quote)
    monkeypatch.setattr(provider_registry, "get_history", fake_history)
    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)


def test_two_symbol_compare_returns_ok_with_both_and_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_registry(
        monkeypatch,
        quotes={"AAPL": _quote("AAPL"), "MSFT": _quote("MSFT")},
        series={
            "AAPL": _series("AAPL", first=100.0, last=120.0),  # +20%
            "MSFT": _series("MSFT", first=100.0, last=110.0),  # +10%
        },
        fundamentals={"AAPL": _fundamentals("AAPL"), "MSFT": _fundamentals("MSFT")},
    )

    result = asyncio.run(_compare_symbols({"symbols": ["AAPL", "MSFT"]}))

    assert result["ok"] is True
    assert result["timeframe"] == "1d"
    by_symbol = {entry["symbol"]: entry for entry in result["symbols"]}
    assert set(by_symbol) == {"AAPL", "MSFT"}
    assert by_symbol["AAPL"]["return_pct_window"] == pytest.approx(20.0)
    assert by_symbol["MSFT"]["return_pct_window"] == pytest.approx(10.0)
    assert by_symbol["AAPL"]["fundamentals"]["pe_ratio"] == 25.0
    assert by_symbol["AAPL"]["quote"]["price"] == 100.0
    # AAPL (+20%) is best, MSFT (+10%) is worst.
    assert result["relative"] == {"best": "AAPL", "worst": "MSFT"}


def test_single_symbol_input_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_registry(monkeypatch, quotes={"AAPL": _quote("AAPL")})
    result = asyncio.run(_compare_symbols({"symbols": ["AAPL"]}))
    assert result["ok"] is False
    assert "between 2 and 4" in result["error"]


def test_non_list_symbols_is_rejected() -> None:
    result = asyncio.run(_compare_symbols({"symbols": "AAPL"}))
    assert result["ok"] is False
    assert "list of non-empty strings" in result["error"]


def test_failing_symbol_is_reported_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    # AAPL resolves; FAKE errors on the quote. Only one symbol resolves, so the
    # tool degrades to ok=False — but the failing symbol is reported, not raised.
    _patch_registry(
        monkeypatch,
        quotes={"AAPL": _quote("AAPL")},
        series={"AAPL": _series("AAPL", first=100.0, last=105.0)},
        fundamentals={"AAPL": _fundamentals("AAPL")},
        quote_errors={"FAKE"},
    )

    result = asyncio.run(_compare_symbols({"symbols": ["AAPL", "FAKE"]}))

    # Fewer than two resolved → ok=False with a human message (no exception).
    assert result["ok"] is False
    assert "fewer than two symbols resolved" in result["message"]


def test_failing_symbol_listed_with_error_when_others_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Three symbols, one (FAKE) errors. Two resolve → ok=True, and FAKE is
    # present in the symbols list carrying an error field.
    _patch_registry(
        monkeypatch,
        quotes={"AAPL": _quote("AAPL"), "MSFT": _quote("MSFT")},
        series={
            "AAPL": _series("AAPL", first=100.0, last=130.0),
            "MSFT": _series("MSFT", first=100.0, last=90.0),
        },
        fundamentals={"AAPL": _fundamentals("AAPL"), "MSFT": _fundamentals("MSFT")},
        quote_errors={"FAKE"},
    )

    result = asyncio.run(_compare_symbols({"symbols": ["AAPL", "MSFT", "FAKE"]}))

    assert result["ok"] is True
    by_symbol = {entry["symbol"]: entry for entry in result["symbols"]}
    assert "FAKE" in by_symbol
    assert "error" in by_symbol["FAKE"]
    assert "note" in by_symbol["FAKE"]
    # AAPL (+30%) best, MSFT (-10%) worst; FAKE excluded from the ranking.
    assert result["relative"] == {"best": "AAPL", "worst": "MSFT"}


def test_invalid_timeframe_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    result = asyncio.run(_compare_symbols({"symbols": ["AAPL", "MSFT"], "timeframe": "5m"}))
    assert result["ok"] is False
    assert "timeframe" in result["error"]


def test_crypto_skips_fundamentals(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_registry(
        monkeypatch,
        quotes={
            "BTC/USDT": _quote("BTC/USDT", provider="ccxt"),
            "ETH/USDT": _quote("ETH/USDT", provider="ccxt"),
        },
        series={
            "BTC/USDT": _series("BTC/USDT", first=100.0, last=150.0, provider="ccxt"),
            "ETH/USDT": _series("ETH/USDT", first=100.0, last=80.0, provider="ccxt"),
        },
    )

    result = asyncio.run(
        _compare_symbols({"symbols": ["BTC/USDT", "ETH/USDT"], "asset_class": "crypto"})
    )

    assert result["ok"] is True
    by_symbol = {entry["symbol"]: entry for entry in result["symbols"]}
    # Crypto never calls get_fundamentals → fundamentals stays None.
    assert by_symbol["BTC/USDT"]["fundamentals"] is None
    assert result["relative"] == {"best": "BTC/USDT", "worst": "ETH/USDT"}


def _daily_series(symbol: str, days_back: int, first: float, last: float) -> OHLCVSeries:
    """Daily bars from ``days_back`` days ago to today, first/last closes as given."""
    today = datetime(2026, 9, 18, tzinfo=UTC)
    stamps = [today - timedelta(days=d) for d in range(days_back, -1, -1)]
    closes = [first] * (len(stamps) - 1) + [last]
    return OHLCVSeries(
        symbol=symbol,
        timeframe="1d",
        bars=[
            OHLCVBar(timestamp=t, open=c, high=c, low=c, close=c, volume=1_000.0)
            for t, c in zip(stamps, closes, strict=True)
        ],
        provider="yfinance",
    )


def test_new_listing_is_not_ranked_against_a_six_month_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # R15-DATA-041: a 2-bar listing's +30% outranked a 6-month +5% series.
    _patch_registry(
        monkeypatch,
        quotes={"ESTABLISHED": _quote("ESTABLISHED"), "NEWLY_LISTED": _quote("NEWLY_LISTED")},
        series={
            "ESTABLISHED": _daily_series("ESTABLISHED", 182, first=100.0, last=105.0),
            "NEWLY_LISTED": _daily_series("NEWLY_LISTED", 1, first=100.0, last=130.0),
        },
        fundamentals={
            "ESTABLISHED": _fundamentals("ESTABLISHED"),
            "NEWLY_LISTED": _fundamentals("NEWLY_LISTED"),
        },
    )

    result = asyncio.run(_compare_symbols({"symbols": ["ESTABLISHED", "NEWLY_LISTED"]}))

    assert result["relative"]["best"] is None
    assert result["relative"]["worst"] is None
    assert "NEWLY_LISTED has 2 bars since 2026-09-17" in result["relative"]["note"]
    new = next(s for s in result["symbols"] if s["symbol"] == "NEWLY_LISTED")
    assert (new["bars"], new["window_start"], new["window_end"]) == (2, "2026-09-17", "2026-09-18")


def test_history_gap_mid_window_is_excluded_from_the_ranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A long-listed name whose provider history starts mid-window measured a
    # shorter period too; the full-window names still rank against each other.
    _patch_registry(
        monkeypatch,
        quotes={s: _quote(s) for s in ("AAA", "BBB", "GAPPY")},
        series={
            "AAA": _daily_series("AAA", 182, first=100.0, last=110.0),
            "BBB": _daily_series("BBB", 180, first=100.0, last=104.0),
            "GAPPY": _daily_series("GAPPY", 90, first=100.0, last=150.0),
        },
        fundamentals={s: _fundamentals(s) for s in ("AAA", "BBB", "GAPPY")},
    )

    result = asyncio.run(_compare_symbols({"symbols": ["AAA", "BBB", "GAPPY"]}))

    assert result["relative"]["best"] == "AAA"
    assert result["relative"]["worst"] == "BBB"
    assert "GAPPY has 91 bars since" in result["relative"]["note"]


def test_invented_ticker_reads_unresolved_not_no_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    # R15-AGENT-045: the model compared COCHINSHIP with an invented MAZAGONDOCK
    # (the listing is MAZDOCK). The resolver matches no listing for it (live
    # Search included), so the tool must say the name is unresolved, never
    # "no quote available".
    _patch_registry(monkeypatch, quote_errors={"MAZAGONDOCK"})

    invented = asyncio.run(_compare_one("MAZAGONDOCK", "1d", "equity"))

    assert invented["error"].startswith("unresolved name: 'MAZAGONDOCK' is not a known ticker")
    assert "no quote" not in invented["note"]


def test_company_name_is_compared_under_its_resolved_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Not the case the fix was written against: a company name ("Mazagon Dock")
    # binds through the one policy to MAZDOCK.NS and is compared under it.
    _patch_registry(
        monkeypatch,
        quotes={"COCHINSHIP": _quote("COCHINSHIP"), "MAZDOCK.NS": _quote("MAZDOCK.NS")},
        series={
            "COCHINSHIP": _series("COCHINSHIP", first=100.0, last=120.0),
            "MAZDOCK.NS": _series("MAZDOCK.NS", first=100.0, last=110.0),
        },
        fundamentals={
            "COCHINSHIP": _fundamentals("COCHINSHIP"),
            "MAZDOCK.NS": _fundamentals("MAZDOCK.NS"),
        },
        quote_errors={"Mazagon Dock"},
    )

    result = asyncio.run(_compare_symbols({"symbols": ["COCHINSHIP", "Mazagon Dock"]}))

    assert result["ok"] is True
    mazdock = next(s for s in result["symbols"] if s["symbol"] == "MAZDOCK.NS")
    assert mazdock["requested"] == "Mazagon Dock"
    assert mazdock["note"] == "resolved 'Mazagon Dock' → 'MAZDOCK.NS'"
