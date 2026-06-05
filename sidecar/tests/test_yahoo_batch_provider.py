"""Tests for the Yahoo v7 batch quote provider (FR-126 / SC-034).

Every test mocks the HTTP transport (``httpx.MockTransport``) so nothing hits
the network — the v7 chunking, cookie+crumb bootstrap, field mapping, and the
skip-reason vocabulary are exercised against synthetic Yahoo responses.
"""

from __future__ import annotations

import json

import httpx
import pytest

from services import yahoo_batch_provider as yb


@pytest.fixture(autouse=True)
def _reset_session() -> None:
    """Each test starts with a cold session (no leaked crumb/client)."""
    yield
    yb.reset_for_tests(None)


def _quote_row(symbol: str, **fields: object) -> dict[str, object]:
    row: dict[str, object] = {"symbol": symbol}
    row.update(fields)
    return row


def _install(handler) -> None:
    yb.reset_for_tests(httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# Cookie + crumb bootstrap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crumb_bootstrap_seeds_cookie_then_mints_crumb() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "getcrumb" in request.url.path:
            assert "crumb" not in request.url.params  # crumb req itself is crumbless
            return httpx.Response(200, text="ABC123crumb")
        if "/v7/finance/quote" in request.url.path:
            assert request.url.params.get("crumb") == "ABC123crumb"
            return httpx.Response(
                200,
                json={"quoteResponse": {"result": [_quote_row("AAPL", regularMarketPrice=200.0)]}},
            )
        # cookie bootstrap pages
        return httpx.Response(200, text="ok")

    _install(handler)
    rows, failures = await yb.fetch_quotes_batch(["AAPL"])
    assert "AAPL" in rows
    assert failures == {}
    # The crumb was minted before the quote call.
    assert any("getcrumb" in u for u in seen)
    assert any("/v7/finance/quote" in u for u in seen)


@pytest.mark.asyncio
async def test_invalid_crumb_triggers_one_refresh_then_succeeds() -> None:
    crumb_calls = {"n": 0}
    quote_calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            crumb_calls["n"] += 1
            return httpx.Response(200, text=f"crumb{crumb_calls['n']}")
        if "/v7/finance/quote" in request.url.path:
            quote_calls["n"] += 1
            if quote_calls["n"] == 1:
                # First attempt rejected as an invalid crumb.
                return httpx.Response(401, json={"quoteResponse": {"error": "Invalid Crumb"}})
            return httpx.Response(
                200,
                json={"quoteResponse": {"result": [_quote_row("MSFT", regularMarketPrice=400.0)]}},
            )
        return httpx.Response(200, text="ok")

    _install(handler)
    rows, failures = await yb.fetch_quotes_batch(["MSFT"])
    assert "MSFT" in rows
    assert failures == {}
    assert quote_calls["n"] == 2  # one reject + one success
    assert crumb_calls["n"] >= 2  # crumb re-minted after invalidation


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def test_chunk_count_sp500_is_about_eleven() -> None:
    assert yb.chunk_count(506) == 11
    assert yb.chunk_count(50) == 1
    assert yb.chunk_count(51) == 2
    assert yb.chunk_count(0) == 0


@pytest.mark.asyncio
async def test_batch_chunks_at_fifty_symbols() -> None:
    chunk_sizes: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if "/v7/finance/quote" in request.url.path:
            syms = request.url.params.get("symbols", "").split(",")
            chunk_sizes.append(len(syms))
            return httpx.Response(
                200,
                json={
                    "quoteResponse": {
                        "result": [_quote_row(s, regularMarketPrice=10.0) for s in syms]
                    }
                },
            )
        return httpx.Response(200, text="ok")

    _install(handler)
    symbols = [f"S{i:03d}" for i in range(120)]
    rows, failures = await yb.fetch_quotes_batch(symbols)
    assert len(rows) == 120
    assert failures == {}
    # 120 symbols → 50 + 50 + 20.
    assert sorted(chunk_sizes, reverse=True) == [50, 50, 20]


# ---------------------------------------------------------------------------
# Skip-reason vocabulary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unreturned_symbol_is_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if "/v7/finance/quote" in request.url.path:
            # Only AAPL comes back; BOGUS is dropped by Yahoo.
            return httpx.Response(
                200,
                json={"quoteResponse": {"result": [_quote_row("AAPL", regularMarketPrice=1.0)]}},
            )
        return httpx.Response(200, text="ok")

    _install(handler)
    rows, failures = await yb.fetch_quotes_batch(["AAPL", "BOGUS"])
    assert "AAPL" in rows
    assert failures == {"BOGUS": "not_found"}


@pytest.mark.asyncio
async def test_http_429_is_rate_limited() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if "/v7/finance/quote" in request.url.path:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, text="ok")

    _install(handler)
    rows, failures = await yb.fetch_quotes_batch(["AAPL", "MSFT"])
    assert rows == {}
    assert failures == {"AAPL": "rate_limited", "MSFT": "rate_limited"}


@pytest.mark.asyncio
async def test_timeout_is_itemized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if "/v7/finance/quote" in request.url.path:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, text="ok")

    _install(handler)
    rows, failures = await yb.fetch_quotes_batch(["AAPL"])
    assert rows == {}
    assert failures == {"AAPL": "timeout"}


@pytest.mark.asyncio
async def test_total_wipeout_returns_empty_for_graceful_degrade() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        raise httpx.ConnectError("network down", request=request)

    _install(handler)
    rows, failures = await yb.fetch_quotes_batch(["AAPL", "MSFT"])
    assert rows == {}
    # Every symbol itemized — the screener degrades to the per-symbol path.
    assert set(failures) == {"AAPL", "MSFT"}


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------


def test_quote_from_v7_maps_common_fields() -> None:
    row = _quote_row(
        "AAPL",
        regularMarketPrice=200.0,
        regularMarketChange=2.5,
        regularMarketChangePercent=1.25,
        regularMarketVolume=50_000_000,
        currency="USD",
        regularMarketTime=1_700_000_000,
        marketState="REGULAR",
    )
    quote = yb.quote_from_v7(row)
    assert quote is not None
    assert quote.symbol == "AAPL"
    assert quote.price == 200.0
    assert quote.change == 2.5
    assert quote.change_percent == 1.25
    assert quote.volume == 50_000_000
    assert quote.currency == "USD"
    assert quote.provider == "yahoo-v7-batch"


def test_quote_from_v7_drops_priceless_row() -> None:
    assert yb.quote_from_v7(_quote_row("AAPL")) is None
    assert yb.quote_from_v7(_quote_row("AAPL", regularMarketPrice=0.0)) is None
    assert yb.quote_from_v7(_quote_row("AAPL", regularMarketPrice=-5.0)) is None


def test_fundamentals_from_v7_maps_valuation_fields() -> None:
    row = _quote_row(
        "AAPL",
        longName="Apple Inc.",
        marketCap=3_000_000_000_000,
        trailingPE=30.0,
        forwardPE=28.0,
        priceToBook=45.0,
        epsTrailingTwelveMonths=6.5,
        fiftyTwoWeekHigh=210.0,
        fiftyTwoWeekLow=160.0,
        trailingAnnualDividendYield=0.0055,
    )
    fund = yb.fundamentals_from_v7(row)
    assert fund.symbol == "AAPL"
    assert fund.name == "Apple Inc."
    assert fund.market_cap == 3_000_000_000_000
    assert fund.pe_ratio == 30.0
    assert fund.forward_pe == 28.0
    assert fund.price_to_book == 45.0
    assert fund.eps == 6.5
    assert fund.fifty_two_week_high == 210.0
    assert fund.fifty_two_week_low == 160.0
    assert fund.dividend_yield == pytest.approx(0.0055)
    # Fields v7 does NOT carry stay None (the engine enriches per-symbol).
    assert fund.sector is None
    assert fund.industry is None
    assert fund.peg_ratio is None
    assert fund.beta is None


def test_dividend_yield_percent_fallback_is_normalised() -> None:
    # No trailingAnnualDividendYield → fall back to the percent-form field.
    fund = yb.fundamentals_from_v7(_quote_row("VZ", dividendYield=6.01))
    assert fund.dividend_yield == pytest.approx(0.0601)


def test_dividend_yield_absurd_value_rejected() -> None:
    fund = yb.fundamentals_from_v7(_quote_row("X", trailingAnnualDividendYield=5.0))
    assert fund.dividend_yield is None


def test_num_rejects_nan_and_inf() -> None:
    nan = float("nan")
    inf = float("inf")
    fund = yb.fundamentals_from_v7(_quote_row("X", marketCap=nan, trailingPE=inf))
    assert fund.market_cap is None
    assert fund.pe_ratio is None


# ---------------------------------------------------------------------------
# Enrichment field coverage
# ---------------------------------------------------------------------------


def test_field_needs_enrichment_coverage() -> None:
    # On the v7 fast path → no enrichment.
    for fast in (
        "price",
        "market_cap",
        "pe_ratio",
        "forward_pe",
        "price_to_book",
        "dividend_yield",
        "eps",
        "fifty_two_week_high",
        "fifty_two_week_low",
        "volume",
        "change_percent_1d",
        "currency",
    ):
        assert not yb.field_needs_enrichment(fast), fast
    # Not on the v7 row → per-symbol enrichment.
    for slow in ("sector", "industry", "peg_ratio", "beta"):
        assert yb.field_needs_enrichment(slow), slow


@pytest.mark.asyncio
async def test_malformed_json_is_no_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if "/v7/finance/quote" in request.url.path:
            return httpx.Response(200, content=b"not json", headers={"content-type": "text/html"})
        return httpx.Response(200, text="ok")

    _install(handler)
    rows, failures = await yb.fetch_quotes_batch(["AAPL"])
    assert rows == {}
    assert failures == {"AAPL": "no_data"}
    # sanity: the malformed body really wasn't JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads("not json")
