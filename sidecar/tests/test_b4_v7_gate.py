"""R15-DATA-034 / R15-DATA-082: every served path runs the correctness gate.

The v7 batch mapping (screener + warm store) validates at its one mapping site,
so an implausible yield is withheld there, never matched by a screen; the crypto
lane is gated too, and ccxt never serves a 0.0 price.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from models.screener import NumericThresholdCriterion, ScreenerRequest, ScreenerUniverse
from services import (
    ccxt_provider,
    data_cache,
    fundamentals_store,
    provider_registry,
    screener,
)
from services import yahoo_batch_provider as yb
from services.errors import ProviderError


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    data_cache.reset_for_tests(tmp_path / "cache.db")
    fundamentals_store.reset_for_tests(tmp_path / "fundamentals.db")
    yb.reset_for_tests()
    yield
    data_cache.reset_for_tests(None)
    fundamentals_store.reset_for_tests(None)
    yb.reset_for_tests()


def _v7_row(symbol: str, dividend_yield: float) -> dict[str, object]:
    return {
        "symbol": symbol,
        "longName": f"{symbol} Inc.",
        "regularMarketPrice": 150.0,
        "regularMarketTime": 1_700_000_000,
        "currency": "USD",
        "trailingPE": 20.0,
        "epsTrailingTwelveMonths": 7.5,
        "fiftyTwoWeekHigh": 199.0,
        "fiftyTwoWeekLow": 124.0,
        "trailingAnnualDividendYield": dividend_yield,
    }


def test_v7_row_with_an_implausible_yield_is_withheld_with_its_reason() -> None:
    fund = yb.fundamentals_from_v7(_v7_row("AAA", 1.5))
    assert fund.dividend_yield is None
    meta = fund.field_meta["dividend_yield"]
    assert meta.status == "withheld"
    assert "150.00%" in meta.reason
    assert yb.fundamentals_from_v7(_v7_row("BBB", 0.03)).dividend_yield == pytest.approx(0.03)


@pytest.mark.asyncio
async def test_screener_never_matches_a_withheld_v7_yield(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = {"AAA": _v7_row("AAA", 1.5), "BBB": _v7_row("BBB", 0.03)}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            wanted = (request.url.params.get("symbols") or "").split(",")
            result = [rows[s] for s in wanted if s in rows]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))

    async def universe(universe_id, custom_symbols=None):  # noqa: ANN001, ARG001
        return ScreenerUniverse(
            id="sp500", label="S&P 500", symbols=list(rows), asset_class="equity"
        )

    monkeypatch.setattr(screener, "resolve_universe", universe)
    request = ScreenerRequest(
        universe="sp500",
        criteria=[NumericThresholdCriterion(field="dividend_yield", operator="gt", value=0.5)],
        limit=100,
    )
    result = await screener.run_screener(request)
    assert [r.symbol for r in result.rows] == []


def test_ccxt_ticker_without_a_price_raises_and_the_registry_serves_no_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticker = {"symbol": "BTC/USDT", "last": None, "close": None, "timestamp": 1_700_000_000_000}
    with pytest.raises(ProviderError, match="no last or close"):
        ccxt_provider._ticker_to_quote(ticker, "binance", "BTC/USDT")

    class _Exchange:
        def fetch_ticker(self, symbol: str) -> dict[str, object]:
            return ticker

    monkeypatch.setattr(ccxt_provider, "_sync_exchange", lambda exchange: _Exchange())
    with pytest.raises(ProviderError):
        provider_registry.get_quote("BTC/USDT", asset_class="crypto")


def test_crypto_quote_and_series_are_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime

    from models.market import OHLCVBar, OHLCVSeries, Quote

    # A zero price and a wrong-instrument series are rejected like any other lane.
    zero = Quote(
        symbol="BTC/USDT",
        price=0.0,
        change=0.0,
        change_percent=0.0,
        timestamp=datetime.now(tz=UTC),
        provider="ccxt:binance",
    )
    monkeypatch.setattr(ccxt_provider, "get_ticker", lambda exchange, symbol: zero)
    with pytest.raises(ProviderError, match="non-positive price"):
        provider_registry.get_quote("BTC/USDT", asset_class="crypto")

    bar = OHLCVBar(
        timestamp=datetime.now(tz=UTC), open=1.0, high=2.0, low=1.0, close=1.5, volume=9.0
    )
    wrong = OHLCVSeries(symbol="ETH/USDT", timeframe="1d", bars=[bar], provider="ccxt:binance")
    monkeypatch.setattr(ccxt_provider, "get_ohlcv", lambda exchange, symbol, timeframe: wrong)
    with pytest.raises(ProviderError, match="symbol mismatch"):
        provider_registry.get_history("BTC/USDT", "1d", asset_class="crypto")

    # An old crypto quote is not judged against an exchange session calendar.
    old = zero.model_copy(update={"price": 60_000.0, "timestamp": datetime(2026, 1, 3, tzinfo=UTC)})
    monkeypatch.setattr(ccxt_provider, "get_ticker", lambda exchange, symbol: old)
    assert provider_registry.get_quote("BTC/USDT", asset_class="crypto").price == 60_000.0
