"""Tests for the NSE UDiFF bhavcopy fetcher (D54 — one-request whole-NSE EOD).

No test makes a live NSE call: ``httpx`` is mocked at the transport level
(:class:`httpx.MockTransport`) installed on a cold session via
:func:`nse_bhavcopy.reset_for_tests` — the same seam as
``test_yahoo_batch_provider``. The fixture CSV is a verbatim trim of the real
``BhavCopy_NSE_CM_0_0_0_20260702_F_0000.csv`` downloaded live from
nsearchives (fixtures/nse convention: verbatim trims, never hand-built data).

Surfaces under test:
  - UDiFF parse: EQ/BE/BZ kept, SM/GS/N1/IV excluded, keyed by bare symbol;
  - the legacy ``sec_bhavdata_full`` fallback parse (padded headers/cells);
  - weekend/holiday walk-back → the newest published file, correct trade_date;
  - blocked (403 on primary AND fallback) → ``None`` with no retry storm;
  - the data_cache round-trip: a second same-day fetch does zero HTTP calls;
  - ``derive_market_cap`` math incl. the ``None``/non-positive shares cases.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date
from pathlib import Path

import httpx
import pytest

from services import data_cache
from services import nse_bhavcopy as nb

_FIXTURE = Path(__file__).parent / "fixtures" / "nse" / "bhavcopy_udiff_20260702_trimmed.csv"

# A verbatim two-row trim of the legacy security-wise full bhavcopy
# (sec_bhavdata_full_01072026.csv, downloaded live 2026-07-02) — note the
# space-padded header names and cells the parser must strip.
_SEC_FULL_SAMPLE = (
    "SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE,"
    " CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
    "1018GS2026, GS, 01-Jul-2026, 103.13, 100.55, 103.90, 100.55, 103.85, 103.85, 103.60,"
    " 69, 0.07, 8, 57, 82.61\n"
    "20MICRONS, EQ, 01-Jul-2026, 201.41, 203.94, 204.80, 198.01, 200.80, 199.35, 201.64,"
    " 141123, 284.56, 2987, 46976, 33.29\n"
)


def _fixture_text() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


def _fixture_zip() -> bytes:
    """The fixture CSV wrapped in a ZIP, as nsearchives serves it."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("BhavCopy_NSE_CM_0_0_0_20260702_F_0000.csv", _fixture_text())
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path):
    """Each test gets a cold on-disk cache and a cold HTTP session."""
    data_cache.reset_for_tests(tmp_path / "test_cache.db")
    nb.reset_for_tests()
    yield
    data_cache.reset_for_tests(None)
    nb.reset_for_tests()


# ---------------------------------------------------------------------------
# Parse — UDiFF fixture + the legacy fallback format.
# ---------------------------------------------------------------------------


def test_parse_udiff_keeps_equity_series_keyed_bare_symbol() -> None:
    rows = nb.parse_bhavcopy(_fixture_text())
    # EQ + BE + BZ kept (incl. the EQ-series ETF), keyed by bare symbol.
    assert set(rows) == {"RELIANCE", "TCS", "NIFTYBEES", "AAREYDRUGS", "ANKITMETAL"}
    rel = rows["RELIANCE"]
    assert rel.close == 1303.50
    assert rel.prev_close == 1308.00
    assert rel.volume == 17795024
    assert rel.high == 1313.20
    assert rel.low == 1299.00
    assert rel.series == "EQ"
    assert rows["AAREYDRUGS"].series == "BE"
    assert rows["ANKITMETAL"].series == "BZ"


def test_parse_udiff_excludes_non_equity_series() -> None:
    rows = nb.parse_bhavcopy(_fixture_text())
    # SME (SM), gilt (GS), debt (N1) and InvIT (IV) rows are dropped.
    for excluded in ("AGUL", "679GS2031", "888ECL28", "ANANTAM"):
        assert excluded not in rows


def test_parse_legacy_sec_full_format() -> None:
    rows = nb.parse_bhavcopy(_SEC_FULL_SAMPLE)
    assert set(rows) == {"20MICRONS"}  # the GS row is excluded
    row = rows["20MICRONS"]
    # CLOSE_PRICE (the official close, = UDiFF ClsPric — verified live against
    # both formats for 2026-07-01), NOT LAST_PRICE (200.80, the last trade).
    assert row.close == 199.35
    assert row.prev_close == 201.41
    assert row.volume == 141123
    assert row.high == 204.80
    assert row.low == 198.01
    assert row.series == "EQ"


def test_parse_garbage_yields_empty() -> None:
    assert nb.parse_bhavcopy("") == {}
    assert nb.parse_bhavcopy("<html>blocked</html>") == {}


# ---------------------------------------------------------------------------
# fetch_latest — walk-back, blocked degrade, cache hit.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_latest_walks_back_over_weekend_and_holiday(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Monday not yet published (404), weekend skipped requestless, Friday 404
    (holiday), Thursday 200 → Thursday's result with the correct trade_date."""
    monkeypatch.setattr(nb, "_ist_today", lambda: date(2026, 7, 6))  # a Monday
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if "20260706" in request.url.path:  # Monday — not yet published
            return httpx.Response(404)
        if "20260703" in request.url.path:  # Friday — holiday
            return httpx.Response(404)
        if "20260702" in request.url.path:  # Thursday — published
            return httpx.Response(200, content=_fixture_zip())
        raise AssertionError(f"unexpected request {request.url}")

    nb.reset_for_tests(httpx.MockTransport(handler))
    try:
        result = await nb.fetch_latest()
        assert result is not None
        assert result.trade_date == date(2026, 7, 2)
        assert result.rows["TCS"].close == 2068.10
        # Monday + Friday + Thursday — the weekend cost zero requests, and a
        # 404 never triggers the fallback host.
        assert len(requested) == 3
    finally:
        await nb.aclose()


@pytest.mark.asyncio
async def test_fetch_latest_blocked_returns_none_without_retry_storm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 403 on the primary AND the once-only fallback → ``None`` after exactly
    two requests — no walk-back continuation, no retry hammering."""
    monkeypatch.setattr(nb, "_ist_today", lambda: date(2026, 7, 2))  # a Thursday
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        return httpx.Response(403, text="Access Denied")

    nb.reset_for_tests(httpx.MockTransport(handler))
    try:
        assert await nb.fetch_latest() is None
        assert len(calls) == 2
        assert calls == ["nsearchives.nseindia.com", "archives.nseindia.com"]
    finally:
        await nb.aclose()


@pytest.mark.asyncio
async def test_fetch_latest_falls_back_to_legacy_host_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Primary blocked but the legacy host serves → the day still resolves."""
    monkeypatch.setattr(nb, "_ist_today", lambda: date(2026, 7, 2))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "nsearchives.nseindia.com":
            return httpx.Response(403, text="Access Denied")
        return httpx.Response(200, text=_SEC_FULL_SAMPLE)

    nb.reset_for_tests(httpx.MockTransport(handler))
    try:
        result = await nb.fetch_latest()
        assert result is not None
        assert result.trade_date == date(2026, 7, 2)
        assert result.rows["20MICRONS"].close == 199.35
    finally:
        await nb.aclose()


@pytest.mark.asyncio
async def test_fetch_latest_second_call_hits_cache_zero_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nb, "_ist_today", lambda: date(2026, 7, 2))
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=_fixture_zip())

    nb.reset_for_tests(httpx.MockTransport(handler))
    try:
        first = await nb.fetch_latest()
        assert first is not None and calls == 1
    finally:
        await nb.aclose()

    # A cold session whose transport would fail loudly if touched — the second
    # fetch must be served entirely from the parsed-rows cache.
    def explode(request: httpx.Request) -> httpx.Response:
        raise AssertionError("cache hit must not touch the network")

    nb.reset_for_tests(httpx.MockTransport(explode))
    try:
        second = await nb.fetch_latest()
        assert second is not None
        assert second.trade_date == date(2026, 7, 2)
        assert second.rows == first.rows
        assert calls == 1
    finally:
        await nb.aclose()


@pytest.mark.asyncio
async def test_holiday_404_cached_only_for_past_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A past-date 404 is a holiday → empty-marker cached; today's 404 means
    "not yet published" and must NOT be cached (the file lands ~16:30 IST)."""
    monkeypatch.setattr(nb, "_ist_today", lambda: date(2026, 7, 6))  # Monday

    def handler(request: httpx.Request) -> httpx.Response:
        if "20260702" in request.url.path:
            return httpx.Response(200, content=_fixture_zip())
        return httpx.Response(404)

    nb.reset_for_tests(httpx.MockTransport(handler))
    try:
        assert await nb.fetch_latest() is not None
        # Friday 2026-07-03 (past) 404 → marker cached; Monday (today) → not.
        assert await data_cache.get("nse_bhavcopy:20260703", 60.0) == {"empty": True}
        assert await data_cache.get("nse_bhavcopy:20260706", 60.0) is None
    finally:
        await nb.aclose()


# ---------------------------------------------------------------------------
# derive_market_cap
# ---------------------------------------------------------------------------


def test_derive_market_cap() -> None:
    assert nb.derive_market_cap(1303.50, 6_766_000_000) == pytest.approx(8.819481e12)
    assert nb.derive_market_cap(1303.50, None) is None
    assert nb.derive_market_cap(1303.50, 0.0) is None
    assert nb.derive_market_cap(1303.50, -5.0) is None
    assert nb.derive_market_cap(0.0, 1_000_000.0) is None
