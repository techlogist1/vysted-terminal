"""Tests for the Yahoo v7 batch quote provider — the screener fast path (FR-126).

No test makes a live Yahoo call: ``httpx`` is mocked at the transport level
(:class:`httpx.MockTransport`) installed on a cold session via
:func:`yahoo_batch_provider.reset_for_tests`, so the v7 endpoint, the cookie
bootstrap, and the crumb mint are all deterministic.

Surfaces under test:
  - the v7 row → ``Quote`` / ``Fundamentals`` field mapping (incl. the dividend
    yield + 52-week-change unit normalisation);
  - ``fetch_quotes_batch`` chunking + the itemized failure ledger (zero silent
    drops) for not_found / rate_limited / timeout / no_data;
  - the cookie + crumb bootstrap (single mint under a fan-out) + the
    401/"Invalid Crumb" invalidate-and-retry-once path;
  - ``field_needs_enrichment`` / ``chunk_count`` field-coverage helpers.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from services import yahoo_batch_provider as yb


def _v7_row(symbol: str, **overrides: object) -> dict[str, object]:
    """A realistic v7 quote row for ``symbol`` with sane defaults."""
    row: dict[str, object] = {
        "symbol": symbol,
        "longName": f"{symbol} Inc.",
        "shortName": symbol,
        "regularMarketPrice": 150.0,
        "regularMarketChange": 1.5,
        "regularMarketChangePercent": 1.0,
        "regularMarketVolume": 1_000_000,
        "regularMarketTime": 1_700_000_000,
        "marketState": "REGULAR",
        "currency": "USD",
        "marketCap": 2_500_000_000_000,
        "trailingPE": 28.5,
        "forwardPE": 25.1,
        "priceToBook": 45.0,
        "bookValue": 4.2,
        "epsTrailingTwelveMonths": 6.1,
        "fiftyTwoWeekHigh": 199.0,
        "fiftyTwoWeekLow": 124.0,
        "fiftyTwoWeekChangePercent": 21.4,
        "trailingAnnualDividendYield": 0.0044,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Field mapping — v7 row → (Quote, Fundamentals)
# ---------------------------------------------------------------------------


def test_quote_from_v7_maps_price_change_volume_currency() -> None:
    quote = yb.quote_from_v7(_v7_row("AAPL"))
    assert isinstance(quote, Quote)
    assert quote.symbol == "AAPL"
    assert quote.price == 150.0
    assert quote.change == 1.5
    assert quote.change_percent == 1.0
    assert quote.volume == 1_000_000
    assert quote.currency == "USD"
    assert quote.provider == yb.PROVIDER


def test_quote_from_v7_drops_priceless_row() -> None:
    # No usable price ⇒ never fabricate; the caller itemizes it as no_data.
    assert yb.quote_from_v7(_v7_row("BAD", regularMarketPrice=None)) is None
    assert yb.quote_from_v7(_v7_row("BAD", regularMarketPrice=0)) is None


def test_fundamentals_from_v7_maps_valuation_and_units() -> None:
    fund = yb.fundamentals_from_v7(_v7_row("AAPL"))
    assert isinstance(fund, Fundamentals)
    assert fund.symbol == "AAPL"
    assert fund.name == "AAPL Inc."
    assert fund.currency == "USD"
    assert fund.market_cap == 2_500_000_000_000
    assert fund.pe_ratio == 28.5
    assert fund.forward_pe == 25.1
    assert fund.price_to_book == 45.0
    assert fund.book_value == 4.2
    assert fund.eps == 6.1
    assert fund.fifty_two_week_high == 199.0
    assert fund.fifty_two_week_low == 124.0
    # 52-week change normalised from percent (21.4) to fraction (0.214).
    assert fund.fifty_two_week_change == pytest.approx(0.214)
    # trailingAnnualDividendYield is already a fraction → preserved as-is.
    assert fund.dividend_yield == pytest.approx(0.0044)
    # v7 carries none of these → left None (enrichment territory).
    assert fund.sector is None
    assert fund.peg_ratio is None
    assert fund.beta is None
    assert fund.roe is None


def test_dividend_yield_fallback_divides_percent_form() -> None:
    # Only the percent-form ``dividendYield`` present → divide by 100.
    row = _v7_row("VZ")
    row.pop("trailingAnnualDividendYield")
    row["dividendYield"] = 6.01
    fund = yb.fundamentals_from_v7(row)
    assert fund.dividend_yield == pytest.approx(0.0601)


def test_dividend_yield_rejects_absurd_value() -> None:
    row = _v7_row("X")
    row["trailingAnnualDividendYield"] = 5.0  # 500% — implausible, rejected
    assert yb.fundamentals_from_v7(row).dividend_yield is None


def test_num_rejects_nan_inf_and_non_numeric() -> None:
    assert yb._num(float("nan")) is None
    assert yb._num(float("inf")) is None
    assert yb._num("12.5") is None  # strings are not coerced (v7 numerics are real)
    assert yb._num({"raw": 1}) is None
    assert yb._num(12.5) == 12.5


def test_field_coverage_helpers() -> None:
    # Batch-covered fields do NOT need enrichment.
    for field in (
        "price",
        "market_cap",
        "pe_ratio",
        "forward_pe",
        "price_to_book",
        "book_value",
        "dividend_yield",
        "eps",
        "fifty_two_week_high",
        "fifty_two_week_low",
        "fifty_two_week_change",
        "volume",
        "change_percent_1d",
    ):
        assert not yb.field_needs_enrichment(field), field
    # v7-omitted fields DO need enrichment.
    for field in (
        "sector",
        "industry",
        "peg_ratio",
        "beta",
        "price_to_sales",
        "ev_to_ebitda",
        "roe",
        "roa",
        "gross_margin",
        "operating_margin",
        "profit_margin",
        "debt_to_equity",
        "current_ratio",
        "quick_ratio",
        "revenue_growth",
        "earnings_growth",
        "held_percent_insiders",
        "held_percent_institutions",
    ):
        assert yb.field_needs_enrichment(field), field


def test_chunk_count() -> None:
    assert yb.chunk_count(0) == 0
    assert yb.chunk_count(1) == 1
    assert yb.chunk_count(50) == 1
    assert yb.chunk_count(51) == 2
    assert yb.chunk_count(506) == 11  # the S&P 500 → ~11 calls


# ---------------------------------------------------------------------------
# fetch_quotes_batch — chunking + itemized failure ledger
# ---------------------------------------------------------------------------


def _ok_transport(rows_by_symbol: dict[str, dict[str, object]]) -> httpx.MockTransport:
    """A transport that serves the crumb + a v7 quoteResponse for known symbols."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="test-crumb-123")
        if request.url.path.endswith("/v7/finance/quote"):
            requested = (request.url.params.get("symbols") or "").split(",")
            result = [rows_by_symbol[s] for s in requested if s in rows_by_symbol]
            return httpx.Response(200, json={"quoteResponse": {"result": result, "error": None}})
        # Cookie bootstrap GETs (fc.yahoo.com / finance.yahoo.com).
        return httpx.Response(200, text="ok")

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_quotes_batch_returns_rows_for_known_symbols() -> None:
    rows = {s: _v7_row(s) for s in ("AAPL", "MSFT", "NVDA")}
    yb.reset_for_tests(_ok_transport(rows))
    try:
        out, failures = await yb.fetch_quotes_batch(["AAPL", "MSFT", "NVDA"])
        assert set(out) == {"AAPL", "MSFT", "NVDA"}
        assert failures == {}
    finally:
        await yb.aclose()
        yb.reset_for_tests()


@pytest.mark.asyncio
async def test_fetch_quotes_batch_itemizes_not_found() -> None:
    # Yahoo returns AAPL but not GHOST → GHOST is itemized not_found (no silent drop).
    rows = {"AAPL": _v7_row("AAPL")}
    yb.reset_for_tests(_ok_transport(rows))
    try:
        out, failures = await yb.fetch_quotes_batch(["AAPL", "GHOST"])
        assert set(out) == {"AAPL"}
        assert failures == {"GHOST": "not_found"}
    finally:
        await yb.aclose()
        yb.reset_for_tests()


@pytest.mark.asyncio
async def test_fetch_quotes_batch_itemizes_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A SUSTAINED 429 (every attempt throttled) exhausts the bounded in-fetch
    # retry and only THEN concedes ``rate_limited``. ``asyncio.sleep`` is stubbed
    # so the retry backoff adds no real latency to the suite.
    quote_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal quote_calls
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if request.url.path.endswith("/v7/finance/quote"):
            quote_calls += 1
            return httpx.Response(429, text="Too Many Requests")
        return httpx.Response(200, text="ok")

    sleeps: list[float] = []

    async def fake_sleep(secs: float) -> None:
        sleeps.append(secs)

    monkeypatch.setattr(yb.asyncio, "sleep", fake_sleep)
    yb.reset_for_tests(httpx.MockTransport(handler))
    try:
        out, failures = await yb.fetch_quotes_batch(["AAPL", "MSFT"])
        assert out == {}
        assert failures == {"AAPL": "rate_limited", "MSFT": "rate_limited"}
        # One initial attempt + _RETRY_MAX_ATTEMPTS retries, then it gives up.
        assert quote_calls == 1 + yb._RETRY_MAX_ATTEMPTS
        assert len(sleeps) == yb._RETRY_MAX_ATTEMPTS
    finally:
        await yb.aclose()
        yb.reset_for_tests()


@pytest.mark.asyncio
async def test_fetch_quotes_batch_429_self_heals_on_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A SINGLE transient 429 then a 200 → the bounded retry self-heals; the chunk
    # resolves with NO ``rate_limited`` failure (the blip never reaches the loop).
    quote_calls = 0
    rows = {"AAPL": _v7_row("AAPL"), "MSFT": _v7_row("MSFT")}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal quote_calls
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if request.url.path.endswith("/v7/finance/quote"):
            quote_calls += 1
            if quote_calls == 1:
                return httpx.Response(429, text="Too Many Requests")
            requested = (request.url.params.get("symbols") or "").split(",")
            result = [rows[s] for s in requested if s in rows]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    sleeps: list[float] = []

    async def fake_sleep(secs: float) -> None:
        sleeps.append(secs)

    monkeypatch.setattr(yb.asyncio, "sleep", fake_sleep)
    yb.reset_for_tests(httpx.MockTransport(handler))
    try:
        out, failures = await yb.fetch_quotes_batch(["AAPL", "MSFT"])
        assert set(out) == {"AAPL", "MSFT"}
        assert failures == {}
        assert quote_calls == 2  # initial 429 + one successful retry
        assert len(sleeps) == 1  # exactly one bounded backoff
    finally:
        await yb.aclose()
        yb.reset_for_tests()


@pytest.mark.asyncio
async def test_fetch_quotes_batch_429_honours_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A ``Retry-After: 2`` header drives the (clamped) backoff sleep on the retry.
    quote_calls = 0
    rows = {"AAPL": _v7_row("AAPL")}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal quote_calls
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if request.url.path.endswith("/v7/finance/quote"):
            quote_calls += 1
            if quote_calls == 1:
                return httpx.Response(429, headers={"Retry-After": "2"}, text="slow down")
            result = [
                rows[s] for s in (request.url.params.get("symbols") or "").split(",") if s in rows
            ]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    sleeps: list[float] = []

    async def fake_sleep(secs: float) -> None:
        sleeps.append(secs)

    monkeypatch.setattr(yb.asyncio, "sleep", fake_sleep)
    yb.reset_for_tests(httpx.MockTransport(handler))
    try:
        out, failures = await yb.fetch_quotes_batch(["AAPL"])
        assert set(out) == {"AAPL"}
        assert failures == {}
        # The one retry slept around Retry-After=2 (±20% jitter), never above cap.
        assert len(sleeps) == 1
        assert 1.6 <= sleeps[0] <= 2.4
        assert sleeps[0] <= yb._RETRY_BACKOFF_CAP_SECONDS
    finally:
        await yb.aclose()
        yb.reset_for_tests()


def test_parse_retry_after_forms_and_clamp() -> None:
    # Bare delta-seconds, clamped to the cap.
    assert yb._parse_retry_after("2") == pytest.approx(2.0)
    assert yb._parse_retry_after(str(int(yb._RETRY_BACKOFF_CAP_SECONDS + 100))) == pytest.approx(
        yb._RETRY_BACKOFF_CAP_SECONDS
    )
    # Negative / absent / garbage → None or floored.
    assert yb._parse_retry_after(None) is None
    assert yb._parse_retry_after("") is None
    assert yb._parse_retry_after("not-a-date") is None
    # A past HTTP-date floors to 0.
    assert yb._parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0


def test_retry_sleep_seconds_grows_jittered_and_capped() -> None:
    # Exponential growth (base × 2**(attempt-1)) within ±20% jitter, capped.
    for attempt in (1, 2):
        expected = yb._RETRY_BASE_SECONDS * (2 ** (attempt - 1))
        for _ in range(50):
            s = yb._retry_sleep_seconds(attempt)
            assert (expected * 0.8) - 1e-9 <= s <= (expected * 1.2) + 1e-9
    # A huge attempt is capped (±jitter around the cap).
    for _ in range(50):
        s = yb._retry_sleep_seconds(20)
        assert s <= yb._RETRY_BACKOFF_CAP_SECONDS * 1.2 + 1e-9
    # An explicit retry_after overrides the computed base.
    for _ in range(50):
        s = yb._retry_sleep_seconds(1, retry_after=3.0)
        assert (3.0 * 0.8) - 1e-9 <= s <= (3.0 * 1.2) + 1e-9


@pytest.mark.asyncio
async def test_fetch_quotes_batch_itemizes_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if request.url.path.endswith("/v7/finance/quote"):
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))
    try:
        out, failures = await yb.fetch_quotes_batch(["AAPL"])
        assert out == {}
        assert failures == {"AAPL": "timeout"}
    finally:
        await yb.aclose()
        yb.reset_for_tests()


@pytest.mark.asyncio
async def test_fetch_quotes_batch_chunks_large_universe() -> None:
    """120 symbols → 3 chunks (≤50 each); all resolve, no silent drop."""
    symbols = [f"S{i:03d}" for i in range(120)]
    rows = {s: _v7_row(s) for s in symbols}
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if request.url.path.endswith("/v7/finance/quote"):
            requested = (request.url.params.get("symbols") or "").split(",")
            calls.append(len(requested))
            result = [rows[s] for s in requested if s in rows]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))
    try:
        out, failures = await yb.fetch_quotes_batch(symbols)
        assert len(out) == 120
        assert failures == {}
        assert len(calls) == 3  # 50 + 50 + 20
        assert max(calls) <= 50
    finally:
        await yb.aclose()
        yb.reset_for_tests()


# ---------------------------------------------------------------------------
# Cookie + crumb bootstrap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crumb_minted_once_under_fanout() -> None:
    """A concurrent fan-out mints the crumb ONCE (lock-guarded), not per chunk."""
    crumb_mints = 0
    symbols = [f"S{i:03d}" for i in range(150)]  # 3 chunks, fanned out concurrently
    rows = {s: _v7_row(s) for s in symbols}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal crumb_mints
        if "getcrumb" in request.url.path:
            crumb_mints += 1
            return httpx.Response(200, text="crumb-xyz")
        if request.url.path.endswith("/v7/finance/quote"):
            requested = (request.url.params.get("symbols") or "").split(",")
            # The crumb must have been threaded onto the request.
            assert request.url.params.get("crumb") == "crumb-xyz"
            result = [rows[s] for s in requested if s in rows]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))
    try:
        out, failures = await yb.fetch_quotes_batch(symbols)
        assert len(out) == 150
        assert failures == {}
        assert crumb_mints == 1, f"expected a single crumb mint, got {crumb_mints}"
    finally:
        await yb.aclose()
        yb.reset_for_tests()


@pytest.mark.asyncio
async def test_invalid_crumb_invalidates_and_retries_once() -> None:
    """A 401 invalidates the crumb and the chunk retries once with a fresh one."""
    attempts: dict[str, int] = {"quote": 0, "crumb": 0}
    rows = {"AAPL": _v7_row("AAPL")}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            attempts["crumb"] += 1
            return httpx.Response(200, text=f"crumb-{attempts['crumb']}")
        if request.url.path.endswith("/v7/finance/quote"):
            attempts["quote"] += 1
            if attempts["quote"] == 1:
                return httpx.Response(401, text="Invalid Crumb")
            result = [
                rows[s] for s in (request.url.params.get("symbols") or "").split(",") if s in rows
            ]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))
    try:
        out, failures = await yb.fetch_quotes_batch(["AAPL"])
        assert set(out) == {"AAPL"}
        assert failures == {}
        assert attempts["quote"] == 2  # initial 401 + retry
        assert attempts["crumb"] == 2  # initial mint + re-mint after invalidate
    finally:
        await yb.aclose()
        yb.reset_for_tests()


@pytest.mark.asyncio
async def test_bootstrap_failure_still_attempts_request() -> None:
    """If the crumb mint fails, the request still goes out cookieless (best-effort)."""
    rows = {"AAPL": _v7_row("AAPL")}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(500, text="oops")
        if request.url.path.endswith("/v7/finance/quote"):
            # Served without a crumb param in some regions.
            assert "crumb" not in request.url.params
            result = [
                rows[s] for s in (request.url.params.get("symbols") or "").split(",") if s in rows
            ]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))
    try:
        out, failures = await yb.fetch_quotes_batch(["AAPL"])
        assert set(out) == {"AAPL"}
        assert failures == {}
    finally:
        await yb.aclose()
        yb.reset_for_tests()


@pytest.mark.asyncio
async def test_empty_symbol_list_no_network() -> None:
    # A guard before any client/transport touch — must not raise.
    out, failures = await yb.fetch_quotes_batch([])
    assert out == {}
    assert failures == {}


@pytest.mark.asyncio
async def test_concurrent_chunks_respect_semaphore() -> None:
    """The fan-out never exceeds the batch concurrency cap of 8 in flight."""
    symbols = [f"S{i:03d}" for i in range(500)]  # 10 chunks
    rows = {s: _v7_row(s) for s in symbols}
    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, peak
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if request.url.path.endswith("/v7/finance/quote"):
            async with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            async with lock:
                in_flight -= 1
            requested = (request.url.params.get("symbols") or "").split(",")
            result = [rows[s] for s in requested if s in rows]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))
    try:
        out, _failures = await yb.fetch_quotes_batch(symbols)
        assert len(out) == 500
        assert peak <= yb._BATCH_CONCURRENCY
    finally:
        await yb.aclose()
        yb.reset_for_tests()
