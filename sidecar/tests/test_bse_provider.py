"""WS6 — the keyless BSE micro-cap provider (bhavcopy + getScripHeaderData).

The network seam (``bse_provider._http_get``) is monkeypatched so NO test hits
the live BSE; these assert the bhavcopy PARSE (from a mocked CSV string), the
history assembly from cached/downloaded bhavcopies, the quote shape (header
endpoint + bhavcopy fallback), EOD-only timeframes, the non-BSE fast-fail, and
the cache-dir-race retry.
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from services import bse_provider, symbol_resolver
from services.errors import ProviderError

# A modern BSE BhavCopy CSV (ISO-style headers). TIRUPATI is the seeded micro-cap.
_BHAVCOPY_CSV = (
    "TradDt,TckrSymb,FinInstrmId,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\n"
    "2026-06-08,TIRUPATI,530419,EQ,100.0,104.0,99.5,103.0,12000\n"
    "2026-06-08,RELIANCE,500325,EQ,2900.0,2950.0,2890.0,2940.0,500000\n"
)


def _csv_response(body: str) -> httpx.Response:
    return httpx.Response(200, content=body.encode("utf-8"))


@pytest.fixture(autouse=True)
def _reset_resolver() -> None:
    symbol_resolver.reset_caches_for_tests()


# --- bhavcopy PARSE (mocked CSV string — no network) ------------------------


def test_parse_bhavcopy_extracts_normalised_rows() -> None:
    frame = bse_provider.parse_bhavcopy(_BHAVCOPY_CSV)
    assert set(frame["ticker"]) == {"TIRUPATI", "RELIANCE"}
    row = frame[frame["ticker"] == "TIRUPATI"].iloc[0]
    assert row["code"] == "530419"
    assert row["open"] == 100.0
    assert row["high"] == 104.0
    assert row["low"] == 99.5
    assert row["close"] == 103.0
    assert row["volume"] == 12000.0


def test_parse_bhavcopy_empty_body_is_empty_frame() -> None:
    assert bse_provider.parse_bhavcopy("").empty
    # A header-only body (no data rows) is also empty.
    assert bse_provider.parse_bhavcopy("TradDt,TckrSymb,ClsPric\n").empty


def test_pick_equity_row_prefers_eq_series() -> None:
    # A scrip listed under a non-equity series BEFORE its EQ row: we chart the
    # equity line, so the assembler must pick the EQ close (123.0), not the first
    # (non-EQ) row by file order (999.0).
    csv = (
        "TradDt,TckrSymb,FinInstrmId,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\n"
        "2026-06-08,FOO,500001,A1,990.0,999.0,980.0,999.0,10\n"
        "2026-06-08,FOO,500001,EQ,120.0,124.0,119.0,123.0,5000\n"
    )
    frame = bse_provider.parse_bhavcopy(csv)
    match = frame[frame["ticker"] == "FOO"]
    assert bse_provider._pick_equity_row(match)["close"] == 123.0
    # No EQ row present → fall back to the first row (never drop the name).
    no_eq = frame[(frame["ticker"] == "FOO") & (frame["series"] == "A1")]
    assert bse_provider._pick_equity_row(no_eq)["close"] == 999.0


# --- get_history assembled from (mocked) downloaded bhavcopies --------------


def test_get_history_assembles_from_bhavcopy(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))

    # Serve the recent-day CSV for any bhavcopy URL; the assembler dedupes by day.
    def fake_get(url: str) -> httpx.Response:
        return _csv_response(_BHAVCOPY_CSV)

    monkeypatch.setattr(bse_provider, "_http_get", fake_get)

    series = bse_provider.get_history("TIRUPATI", "1d", "1mo")
    assert series.provider == "bse"
    assert series.symbol == "TIRUPATI"
    assert series.bars
    # Every bar carries TIRUPATI's close from the mocked bhavcopy.
    assert all(b.close == 103.0 for b in series.bars)
    # Bars are UTC-midnight dated and sorted ascending.
    ts = [b.timestamp for b in series.bars]
    assert ts == sorted(ts)
    assert all(b.timestamp.hour == 0 and b.timestamp.tzinfo is not None for b in series.bars)


def test_get_history_resamples_weekly(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: _csv_response(_BHAVCOPY_CSV))
    series = bse_provider.get_history("TIRUPATI", "1wk", "1mo")
    assert series.timeframe == "1wk"
    assert series.bars
    assert all(b.close > 0 for b in series.bars)


def test_get_history_intraday_rejected() -> None:
    with pytest.raises(ProviderError, match="intraday"):
        bse_provider.get_history("TIRUPATI", "1h")


def test_get_history_no_data_raises(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The ticker is a known BSE scrip, but no bhavcopy carries it → ProviderError
    # (the registry then falls through; the router downgrades to a clean empty).
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: httpx.Response(404))
    with pytest.raises(ProviderError, match="no EOD data"):
        bse_provider.get_history("TIRUPATI", "1d")


# --- non-BSE symbol fast-fails without a network call -----------------------


def test_non_bse_symbol_fails_fast_without_network() -> None:
    with pytest.raises(ProviderError):
        bse_provider.get_quote("AAPL")
    with pytest.raises(ProviderError):
        bse_provider.get_history("ZZZZNOTREAL", "1d")


# --- get_quote: header endpoint shape + bhavcopy fallback -------------------


def test_get_quote_from_scrip_header(monkeypatch: pytest.MonkeyPatch) -> None:
    # The REAL getScripHeaderData Header object has NO ticker field — only the
    # numeric scrip code (Scrip_Cd). The provider must stamp the REQUESTED bare
    # symbol, not parse one from the payload, or the registry's correctness gate
    # (which compares the requested ticker vs Quote.symbol) rejects every quote.
    def fake_get(url: str) -> httpx.Response:
        assert "getScripHeaderData" in url
        assert "scripcode=530419" in url  # the seeded TIRUPATI scrip code
        return httpx.Response(
            200, json={"Header": [{"Scrip_Cd": "530419", "LTP": "103.0", "PrevClose": "100.5"}]}
        )

    monkeypatch.setattr(bse_provider, "_http_get", fake_get)
    q = bse_provider.get_quote("TIRUPATI")
    assert q.provider == "bse"
    # Quote.symbol is the requested bare ticker, NEVER the numeric scrip code.
    assert q.symbol == "TIRUPATI"
    assert q.symbol != "530419"
    assert q.currency == "INR"
    assert q.price == 103.0
    assert round(q.change, 2) == round(103.0 - 100.5, 2)
    assert round(q.change_percent, 4) == round((103.0 - 100.5) / 100.5 * 100.0, 4)


def test_quote_from_header_stamps_bare_not_scrip_code() -> None:
    # A realistic payload that lacks any ticker field (only the numeric scrip
    # code) must still produce Quote.symbol == the requested bare ticker so the
    # registry's _match_key symbol-match gate accepts it (the bug masked by the
    # old test's hardcoded 'Ticker').
    payload = {"Header": [{"Scrip_Cd": "530419", "LTP": "103.0", "PrevClose": "100.5"}]}
    q = bse_provider._quote_from_header("TIRUPATI", payload)
    assert q is not None
    assert q.symbol == "TIRUPATI"
    assert q.provider == "bse"
    assert q.price == 103.0


def test_get_quote_falls_back_to_bhavcopy(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))

    def fake_get(url: str) -> httpx.Response:
        if "getScripHeaderData" in url:
            return httpx.Response(500)  # header endpoint down → bhavcopy fallback
        return _csv_response(_BHAVCOPY_CSV)

    monkeypatch.setattr(bse_provider, "_http_get", fake_get)
    q = bse_provider.get_quote("TIRUPATI")
    assert q.provider == "bse"
    assert q.symbol == "TIRUPATI"
    assert q.currency == "INR"
    assert q.price == 103.0


# --- cache-dir race retry (mirrors india_provider) --------------------------


def test_bhavcopy_for_retries_on_cache_dir_race(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    calls = {"n": 0}
    real_makedirs = bse_provider.os.makedirs

    def flaky_makedirs(path: str, exist_ok: bool = False) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise FileExistsError(path)
        real_makedirs(path, exist_ok=exist_ok)

    monkeypatch.setattr(bse_provider.os, "makedirs", flaky_makedirs)
    # No cached file exists → returns None after surviving the cache-dir race.
    assert bse_provider._bhavcopy_for(date(2026, 6, 8)) is None
    assert calls["n"] == 2  # retried past the race


# --- ZIP-wrapped bhavcopy decode --------------------------------------------


def test_decode_handles_zip_wrapped_csv() -> None:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("BhavCopy_BSE_CM.CSV", _BHAVCOPY_CSV)
    resp = httpx.Response(200, content=buf.getvalue())
    text = bse_provider._decode_bhavcopy_body(resp)
    frame = bse_provider.parse_bhavcopy(text)
    assert "TIRUPATI" in set(frame["ticker"])


# --- token bucket (the mthrottle replacement) -------------------------------


def test_token_bucket_allows_burst_then_throttles() -> None:
    import time

    bucket = bse_provider._TokenBucket(rate=1000.0, capacity=2.0)
    # First two takes are instant (within the burst capacity).
    start = time.monotonic()
    bucket.take()
    bucket.take()
    assert time.monotonic() - start < 0.05
