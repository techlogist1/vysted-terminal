"""WS6 — the keyless BSE micro-cap provider (bhavcopy + getScripHeaderData).

The network seam (``bse_provider._http_get``) is monkeypatched so NO test hits
the live BSE; these assert the bhavcopy PARSE (from a fixture CSV captured from
the REAL 2026-06-09 ``BhavCopy_BSE_CM_…_F_0000.CSV`` shape), the history
assembly routed by SCRIP CODE from the regenerated master (ticker fallback when
the master has no code), the quote shape (header endpoint + bhavcopy fallback),
EOD-only timeframes, the non-BSE fast-fail, and the cache-dir-race retry.

ICONIKSPEV is the acceptance instrument: a real BSE-only group-X micro-cap
(scrip code 511260) present in the regenerated full master.
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from services import bse_provider, symbol_resolver
from services.errors import ProviderError

# The REAL modern bhavcopy header (observed live 2026-06-09) + the observed
# ICONIKSPEV row and a RELIANCE row. parse_bhavcopy must tolerate the full
# 34-column shape (option/expiry columns blank for cash-market rows).
_BHAV_HEADER = (
    "TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,"
    "FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,"
    "LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,"
    "TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4\n"
)
_ICONIK_ROW = (
    "2026-06-09,2026-06-09,CM,BSE,STK,511260,INE088P01015,ICONIKSPEV,X,,,,,"
    "ICONIK SPORTS AND EVENTS LIMIT,44.99,44.99,42.31,43.09,43.48,44.44,,43.09,,,"
    "5757,251369.00,88,F1,1,,,,,\n"
)
_RELIANCE_ROW = (
    "2026-06-09,2026-06-09,CM,BSE,STK,500325,INE002A01018,RELIANCE,A,,,,,"
    "Reliance Industries Ltd,2900.00,2950.00,2890.00,2940.00,2939.00,2910.00,,2940.00,,,"
    "500000,1467000000.00,25000,F1,1,,,,,\n"
)
_BHAVCOPY_CSV = _BHAV_HEADER + _ICONIK_ROW + _RELIANCE_ROW

# The same ICONIKSPEV scrip (FinInstrmId 511260) printed under a DRIFTED ticker
# spelling — the rename/SME-migration case scrip-code routing must survive.
_BHAVCOPY_CSV_RENAMED = _BHAV_HEADER + _ICONIK_ROW.replace(",ICONIKSPEV,", ",ICONIKOLD,")


def _csv_response(body: str) -> httpx.Response:
    return httpx.Response(200, content=body.encode("utf-8"))


@pytest.fixture(autouse=True)
def _reset_resolver() -> None:
    symbol_resolver.reset_caches_for_tests()


# --- bhavcopy PARSE (fixture CSV from the observed live shape — no network) --


def test_parse_bhavcopy_extracts_normalised_rows() -> None:
    frame = bse_provider.parse_bhavcopy(_BHAVCOPY_CSV)
    assert set(frame["ticker"]) == {"ICONIKSPEV", "RELIANCE"}
    row = frame[frame["ticker"] == "ICONIKSPEV"].iloc[0]
    assert row["code"] == "511260"
    assert row["series"] == "X"
    assert row["open"] == 44.99
    assert row["high"] == 44.99
    assert row["low"] == 42.31
    assert row["close"] == 43.09
    assert row["volume"] == 5757.0
    assert row["date"] == "2026-06-09"


def test_parse_bhavcopy_empty_body_is_empty_frame() -> None:
    assert bse_provider.parse_bhavcopy("").empty
    # A header-only body (no data rows) is also empty.
    assert bse_provider.parse_bhavcopy(_BHAV_HEADER).empty


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

    series = bse_provider.get_history("ICONIKSPEV", "1d", "1mo")
    assert series.provider == "bse"
    assert series.symbol == "ICONIKSPEV"
    assert series.bars
    # Every bar carries ICONIKSPEV's close from the fixture bhavcopy row.
    assert all(b.close == 43.09 for b in series.bars)
    # Bars are UTC-midnight dated and sorted ascending.
    ts = [b.timestamp for b in series.bars]
    assert ts == sorted(ts)
    assert all(b.timestamp.hour == 0 and b.timestamp.tzinfo is not None for b in series.bars)


def test_get_history_routes_by_scrip_code(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The bhavcopy prints the scrip under a DRIFTED ticker but the SAME numeric
    # FinInstrmId (511260). Scrip-code routing (master ticker → code) must still
    # find the row — a ticker-string match alone would return nothing.
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: _csv_response(_BHAVCOPY_CSV_RENAMED))
    series = bse_provider.get_history("ICONIKSPEV", "1d", "1mo")
    assert series.symbol == "ICONIKSPEV"  # the REQUESTED ticker, not the drifted print
    assert series.bars
    assert all(b.close == 43.09 for b in series.bars)


def test_get_history_ticker_fallback_without_code(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A master row without a scrip code (defensive: a future master gap) must
    # still serve via the ticker-string fallback.
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: _csv_response(_BHAVCOPY_CSV))
    monkeypatch.setattr(bse_provider, "_scrip_code", lambda symbol: None)
    series = bse_provider.get_history("ICONIKSPEV", "1d", "1mo")
    assert series.bars
    assert all(b.close == 43.09 for b in series.bars)


def test_get_history_resamples_weekly(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: _csv_response(_BHAVCOPY_CSV))
    series = bse_provider.get_history("ICONIKSPEV", "1wk", "1mo")
    assert series.timeframe == "1wk"
    assert series.bars
    assert all(b.close > 0 for b in series.bars)


def test_get_history_intraday_rejected() -> None:
    with pytest.raises(ProviderError, match="intraday"):
        bse_provider.get_history("ICONIKSPEV", "1h")


def test_get_history_no_data_raises(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The ticker is a known BSE scrip, but no bhavcopy carries it → ProviderError
    # (the registry then falls through; the router downgrades to a clean empty).
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: httpx.Response(404))
    with pytest.raises(ProviderError, match="no EOD data"):
        bse_provider.get_history("ICONIKSPEV", "1d")


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
        assert "scripcode=511260" in url  # ICONIKSPEV's code from the regenerated master
        return httpx.Response(
            200, json={"Header": [{"Scrip_Cd": "511260", "LTP": "43.09", "PrevClose": "44.44"}]}
        )

    monkeypatch.setattr(bse_provider, "_http_get", fake_get)
    q = bse_provider.get_quote("ICONIKSPEV")
    assert q.provider == "bse"
    # Quote.symbol is the requested bare ticker, NEVER the numeric scrip code.
    assert q.symbol == "ICONIKSPEV"
    assert q.symbol != "511260"
    assert q.currency == "INR"
    assert q.price == 43.09
    assert round(q.change, 2) == round(43.09 - 44.44, 2)
    assert round(q.change_percent, 4) == round((43.09 - 44.44) / 44.44 * 100.0, 4)


def test_quote_from_header_stamps_bare_not_scrip_code() -> None:
    # A realistic payload that lacks any ticker field (only the numeric scrip
    # code) must still produce Quote.symbol == the requested bare ticker so the
    # registry's _match_key symbol-match gate accepts it.
    payload = {"Header": [{"Scrip_Cd": "511260", "LTP": "43.09", "PrevClose": "44.44"}]}
    q = bse_provider._quote_from_header("ICONIKSPEV", payload)
    assert q is not None
    assert q.symbol == "ICONIKSPEV"
    assert q.provider == "bse"
    assert q.price == 43.09


def test_get_quote_falls_back_to_bhavcopy(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))

    def fake_get(url: str) -> httpx.Response:
        if "getScripHeaderData" in url:
            return httpx.Response(500)  # header endpoint down → bhavcopy fallback
        return _csv_response(_BHAVCOPY_CSV)

    monkeypatch.setattr(bse_provider, "_http_get", fake_get)
    q = bse_provider.get_quote("ICONIKSPEV")
    assert q.provider == "bse"
    assert q.symbol == "ICONIKSPEV"
    assert q.currency == "INR"
    assert q.price == 43.09


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
    assert "ICONIKSPEV" in set(frame["ticker"])


# --- token bucket (the mthrottle replacement) -------------------------------


def test_token_bucket_allows_burst_then_throttles() -> None:
    import time

    bucket = bse_provider._TokenBucket(rate=1000.0, capacity=2.0)
    # First two takes are instant (within the burst capacity).
    start = time.monotonic()
    bucket.take()
    bucket.take()
    assert time.monotonic() - start < 0.05
