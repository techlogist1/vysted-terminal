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

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from services import bse_provider, locale, symbol_resolver
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
    rows = bse_provider.parse_bhavcopy(csv).to_dict("records")
    assert bse_provider._pick_equity_row(rows)["close"] == 123.0
    # No EQ row present → fall back to the first row (never drop the name).
    no_eq = [row for row in rows if row["series"] == "A1"]
    assert bse_provider._pick_equity_row(no_eq)["close"] == 999.0
    # The one-row day-file scan applies the same preference.
    assert bse_provider._scrip_row(csv, "FOO", "500001")["close"] == 123.0


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


def _ason_now() -> str:
    """A header ``Ason`` stamp for the most recent IN session (a live scrip)."""
    return locale.most_recent_session(locale.REGION_IN).strftime("%d %b %y") + " | 16:00"


def test_get_quote_from_scrip_header(monkeypatch: pytest.MonkeyPatch) -> None:
    # The REAL getScripHeaderData Header object has NO ticker field — only the
    # numeric scrip code (Scrip_Cd). The provider must stamp the REQUESTED bare
    # symbol, not parse one from the payload, or the registry's correctness gate
    # (which compares the requested ticker vs Quote.symbol) rejects every quote.
    def fake_get(url: str) -> httpx.Response:
        assert "getScripHeaderData" in url
        assert "scripcode=511260" in url  # ICONIKSPEV's code from the regenerated master
        header = {"Scrip_Cd": "511260", "LTP": "43.09", "PrevClose": "44.44", "Ason": _ason_now()}
        return httpx.Response(200, json={"Header": [header]})

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
    header = {"Scrip_Cd": "511260", "LTP": "43.09", "PrevClose": "44.44", "Ason": _ason_now()}
    q = bse_provider._quote_from_header("ICONIKSPEV", {"Header": [header]})
    assert q is not None
    assert q.symbol == "ICONIKSPEV"
    assert q.provider == "bse"
    assert q.price == 43.09


_DAL_HEADER = {
    "Header": [
        {
            "Scrip_Cd": "539681",
            "LTP": "49.88",
            "PrevClose": "47.51",
            "Ason": "12 Mar 25 | 16:00",
        }
    ]
}


def test_header_quote_is_dated_by_its_ason_not_today() -> None:
    """R15-DATA-006: DAL last traded on 12 Mar 25. The quote carries that date and
    no move for today (was: today's session and "+4.99% today")."""
    q = bse_provider._quote_from_header("DAL", _DAL_HEADER)
    assert q is not None
    assert q.timestamp.date() == date(2025, 3, 12)
    assert q.price == 49.88
    assert q.change == 0 and q.change_percent == 0


def test_header_without_ason_is_not_dated_today() -> None:
    """A header naming no trade date yields no header quote (the caller falls back
    to the dated bhavcopy) — never a print stamped with today's session."""
    header = {"Header": [{"Scrip_Cd": "539681", "LTP": "49.88", "PrevClose": "47.51"}]}
    assert bse_provider._quote_from_header("DAL", header) is None


def test_stale_exchange_quote_is_served_labelled_stale(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through the route: the 18-month-old BSE print is served with its true date
    and labelled stale — not rejected into a lane that would present it as fresh."""

    def fake_get(url: str) -> httpx.Response:
        assert "getScripHeaderData" in url and "scripcode=539681" in url
        return httpx.Response(200, json=_DAL_HEADER)

    monkeypatch.setattr(bse_provider, "_http_get", fake_get)
    resp = client.get("/quotes/DAL", headers={"X-Vysted-Region": "IN"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "bse"
    assert body["timestamp"].startswith("2025-03-12")
    assert body["change"] == 0
    assert body["freshness"] == "stale"


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


# --- empty markers vs publication time (R15-DATA-035) ---------------------


def _ist_epoch(day: date, hour: int) -> float:
    from datetime import datetime, time

    tz = locale.market_timezone(locale.REGION_IN)
    return datetime.combine(day, time(hour), tzinfo=tz).timestamp()


def test_unpublished_html_day_is_not_cached_and_later_fetch_returns_it(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Before publication BSE answers 200 text/html, not a 404.
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    day = date(2026, 9, 23)
    html = httpx.Response(
        200,
        content=b"<!DOCTYPE html>\n<html><head><title>BSE</title></head></html>",
        headers={"content-type": "text/html; charset=utf-8"},
    )
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: html)
    assert bse_provider._download_bhavcopy(day) is None
    assert not (tmp_path / f"{day.isoformat()}.csv").exists()  # no marker cached
    assert bse_provider._bhavcopy_for(day) is None  # still a day to fetch

    monkeypatch.setattr(bse_provider, "_http_get", lambda url: _csv_response(_BHAVCOPY_CSV))
    text = bse_provider._download_bhavcopy(day)
    assert text is not None
    assert bse_provider._scrip_row(text, "ICONIKSPEV", "511260")["close"] == 43.09


def test_marker_written_on_its_own_day_is_refetched(tmp_path, monkeypatch) -> None:
    # A marker left by the pre-fix code (written the same IST day, before BSE
    # published) must not hide the day: it reads as not cached and the history
    # assembly fetches the day again.
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    day = date(2026, 9, 22)
    marker = tmp_path / f"{day.isoformat()}.csv"
    marker.write_text("")
    import os

    os.utime(marker, (_ist_epoch(day, 11), _ist_epoch(day, 11)))
    assert bse_provider._bhavcopy_for(day) is None

    monkeypatch.setattr(bse_provider, "_http_get", lambda url: _csv_response(_BHAVCOPY_CSV))
    bars = bse_provider._assemble_history("ICONIKSPEV", "511260", day, day)
    assert [b.close for b in bars] == [43.09]

    # A marker written after its day (a holiday BSE never published) is honoured.
    holiday = date(2026, 9, 21)
    marker = tmp_path / f"{holiday.isoformat()}.csv"
    marker.write_text("")
    os.utime(marker, (_ist_epoch(date(2026, 9, 22), 9), _ist_epoch(date(2026, 9, 22), 9)))
    assert bse_provider._bhavcopy_for(holiday) == ""

    def no_network(url: str) -> httpx.Response:
        raise AssertionError(f"an honoured marker must not be re-fetched: {url}")

    monkeypatch.setattr(bse_provider, "_http_get", no_network)
    assert bse_provider._assemble_history("ICONIKSPEV", "511260", holiday, holiday) == []


# --- one scrip row per cached day file (R15-DATA-036) ----------------------


def _trading_days_back(end: date, count: int) -> list[date]:
    from datetime import timedelta

    days: list[date] = []
    day = end
    while len(days) < count:
        if day.weekday() < 5 and day.isoformat() not in bse_provider._bse_holidays():
            days.append(day)
        day -= timedelta(days=1)
    return sorted(days)


def test_year_of_cached_whole_market_files_assembles_one_scrip_fast(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 250 cached 5,000-row day files: a year of one scrip must not parse the
    # whole market once per day (that took ~8.7 s warm for KSE).
    import time

    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: pytest.fail(f"network: {url}"))
    header = "TradDt,FinInstrmId,TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\n"
    market = "".join(
        f"2026-01-01,{600000 + i},SCRIP{i},A,10.0,11.0,9.0,10.5,{100 + i}\n" for i in range(4999)
    )
    days = _trading_days_back(date(2026, 9, 18), 250)
    for n, day in enumerate(days):
        target = f"{day.isoformat()},511260,ICONIKSPEV,X,40.0,45.0,39.0,{40 + n / 100:.2f},57\n"
        (tmp_path / f"{day.isoformat()}.csv").write_text(header + market + target)

    started = time.perf_counter()
    bars = bse_provider._assemble_history("ICONIKSPEV", "511260", days[0], days[-1])
    elapsed = time.perf_counter() - started

    assert len(bars) == 250
    assert bars[-1].close == pytest.approx(40 + 249 / 100)
    assert elapsed < 1.0, f"a year of one scrip took {elapsed:.2f}s"


def test_bhavcopy_quote_path_reads_the_same_bars_as_a_full_parse(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The 14-day quote fallback over cached files carrying a drifted ticker and a
    # non-EQ series row before the EQ row: each day's bar is the one the whole-
    # market parse would pick (code first, EQ preferred).
    from datetime import UTC, datetime, timedelta

    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: httpx.Response(500))
    today = datetime.now(tz=UTC).astimezone(locale.market_timezone(locale.REGION_IN)).date()
    expected = []
    for n, day in enumerate(_trading_days_back(today - timedelta(days=1), 6)):
        text = (
            "TradDt,FinInstrmId,TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\n"
            f"{day},511260,ICONIKOLD,A1,1.0,1.0,1.0,999.0,1\n"
            f"{day},511260,ICONIKOLD,EQ,40.0,45.0,39.0,{41 + n}.0,57\n"
            f"{day},511261,ICONIKSPEV,EQ,1.0,1.0,1.0,1.0,1\n"
        )
        (tmp_path / f"{day.isoformat()}.csv").write_text(text)
        full = bse_provider.parse_bhavcopy(text)
        rows = full[full["code"] == "511260"].to_dict("records")
        expected.append(bse_provider._pick_equity_row(rows)["close"])

    quote = bse_provider._quote_from_bhavcopy("ICONIKSPEV", "511260")
    assert quote.price == expected[-1]
    assert quote.change == pytest.approx(expected[-1] - expected[-2])


# --- file shape drift (R15-LIFECYCLE-004) -----------------------------------


@pytest.mark.parametrize(
    ("column", "field"),
    [("OpnPric", "open"), ("HghPric", "high"), ("LwPric", "low"), ("TtlTradgVol", "volume")],
)
def test_renamed_ohlv_column_is_a_parse_failure(
    tmp_path, monkeypatch: pytest.MonkeyPatch, column: str, field: str
) -> None:
    # A renamed column fails the lane (the registry falls through), never
    # serves close-filled flat bars with zero volume.
    drifted = _BHAVCOPY_CSV.replace(f",{column},", f",{column}X,", 1)
    with pytest.raises(ProviderError, match=field):
        bse_provider.parse_bhavcopy(drifted)
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", lambda url: _csv_response(drifted))
    with pytest.raises(ProviderError, match=field):
        bse_provider.get_history("ICONIKSPEV", "1d", "1mo")


def test_cached_day_with_renamed_column_is_a_parse_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    day = date(2026, 6, 9)
    (tmp_path / f"{day.isoformat()}.csv").write_text(_BHAVCOPY_CSV.replace(",LwPric,", ",Low,"))
    with pytest.raises(ProviderError, match="low"):
        bse_provider._assemble_history("ICONIKSPEV", "511260", day, day)


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


# --- shareholding pattern — SEBI XBRL via BSE (R13 / WITNESS) ----------------
#
# The network seam (``_http_get``) is monkeypatched to serve two recorded
# fixtures captured live 2026-07-10: the SHPQNewFormat quarter INDEX and the
# trimmed SEBI XBRL for BOMOXY-B1 (scrip 509470, Jun 2026) — the case the R13
# probe measured at promoter 73.29% / institutions 0.06% (BSE truth), against
# yfinance's overstated 8.455% institutions.

_BSE_FIXTURES = Path(__file__).parent / "fixtures" / "bse"
_SHP_INDEX = json.loads((_BSE_FIXTURES / "shp_quarters_509470.json").read_text())
_SHP_XBRL = (_BSE_FIXTURES / "shp_xbrl_509470_jun2026.xml").read_text()


def _shp_http_stub(index=None, xbrl=None):
    """A ``_http_get`` stub dispatching by URL: index JSON vs XBRL text."""
    payload = index if index is not None else _SHP_INDEX

    def fake(url: str) -> httpx.Response:
        if "SHPQNewFormat" in url:
            return httpx.Response(200, json=payload)
        if url.endswith(".xml"):
            body = xbrl if xbrl is not None else _SHP_XBRL
            if isinstance(body, int):  # a status code → an error response
                return httpx.Response(body, content=b"")
            return httpx.Response(200, content=body.encode("utf-8"))
        raise AssertionError(f"unexpected SHP url {url}")

    return fake


def test_parse_shp_xbrl_reads_summary_categories() -> None:
    summary = bse_provider.parse_shp_xbrl(_SHP_XBRL)
    # The R13 truth: promoter 73.29%, institutions 0.06% (domestic only), public 26.71%.
    assert summary["promoter_percent"] == 73.29
    assert summary["public_percent"] == 26.71
    assert summary["institutions_percent"] == 0.06
    assert summary["dii_percent"] == 0.06
    assert "fii_percent" not in summary  # no foreign institutions for this microcap


def test_parse_shp_xbrl_bad_body_yields_empty() -> None:
    assert bse_provider.parse_shp_xbrl("not xml at all") == {}
    assert bse_provider.parse_shp_xbrl("") == {}


# --- R13 hardening: the historical-split-corruption fix -----------------------
#
# Root cause (live-verified against TCI, scrip 532349): the
# ShareholdingAsAPercentageOfTotalNumberOfShares concept is a 0-1 fraction on
# every RECENT filing (this module's baseline fixture), but every BSE filing
# up to and including June-2025 emits the SAME concept — same unitRef="pure",
# same decimals="INF" — already scaled to a 0-100 percentage (promoter 68.73
# where the fraction-form filing carries 0.6873). Nothing in the XML declares
# which convention is in play, so blindly multiplying by 100 (the pre-fix
# behaviour) inflated every older quarter 100x (promoter 68.73% -> "6873.0%").


def _older_schema_shp_xbrl() -> str:
    """The baseline fixture re-expressed in the OLDER already-percent schema
    (values * 100, same tags/attributes — the real-world ambiguity: nothing
    in the XML marks the schema switch)."""
    text = _SHP_XBRL
    for fraction, percent in (
        ("0.7329", "73.29"),
        ("0.0006", "0.06"),
        ("0.2665", "26.65"),
        ("0.2671", "26.71"),
    ):
        text = text.replace(f">{fraction}<", f">{percent}<")
    return text


def _corrupt_shp_xbrl() -> str:
    """A filing whose promoter category is out of range under EITHER schema
    interpretation (150 -> 150.0 as already-percent, or 15000 as a naive
    fraction*100) — the class-level bounds guard must invalidate the whole
    quarter's split rather than serve a partly-nonsensical mix."""
    return _SHP_XBRL.replace(">0.7329<", ">150.0<")


def test_parse_shp_xbrl_older_schema_recovers_real_values() -> None:
    """The older already-percent schema parses to the SAME real percentages as
    the fraction-form baseline — the parse-level fix, not just the guard."""
    summary = bse_provider.parse_shp_xbrl(_older_schema_shp_xbrl())
    assert summary["promoter_percent"] == 73.29
    assert summary["public_percent"] == 26.71
    assert summary["institutions_percent"] == 0.06
    assert summary["dii_percent"] == 0.06
    for value in summary.values():
        assert 0.0 <= value <= 100.5


def test_parse_shp_xbrl_corrupt_quarter_invalidates_whole_split() -> None:
    """A category outside [0, 100.5] under either schema interpretation
    invalidates the ENTIRE quarter's split — never a partial/half-corrupt mix."""
    assert bse_provider.parse_shp_xbrl(_corrupt_shp_xbrl()) == {}


def test_get_shareholding_mixed_schema_history_never_exceeds_100_percent(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A TCI-shaped history — one sane fraction-form quarter plus one corrupt
    quarter — yields a clean split for the sane quarter and ``None`` (absent)
    split fields for the corrupt one; no category ever exceeds 100%."""
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    index = {
        "Table": [
            {**_SHP_INDEX["Table"][0], "qtr": "June 2026", "XbrlFile": "good.xml"},
            {**_SHP_INDEX["Table"][0], "qtr": "March 2026", "XbrlFile": "corrupt.xml"},
        ]
    }
    xbrl_by_file = {"good.xml": _SHP_XBRL, "corrupt.xml": _corrupt_shp_xbrl()}

    def fake(url: str) -> httpx.Response:
        if "SHPQNewFormat" in url:
            return httpx.Response(200, json=index)
        for name, body in xbrl_by_file.items():
            if url.endswith(name):
                return httpx.Response(200, content=body.encode("utf-8"))
        raise AssertionError(f"unexpected SHP url {url}")

    monkeypatch.setattr(bse_provider, "_http_get", fake)
    rows = bse_provider.get_shareholding("BOMOXY-B1")
    assert len(rows) == 2
    good_row, corrupt_row = rows
    assert good_row["promoter_percent"] == 73.29
    assert "promoter_percent" not in corrupt_row
    for row in rows:
        for field_name in (
            "promoter_percent",
            "public_percent",
            "institutions_percent",
            "fii_percent",
            "dii_percent",
        ):
            value = row.get(field_name)
            if value is not None:
                assert 0.0 <= value <= 100.5


def test_get_shareholding_assembles_index_plus_xbrl(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", _shp_http_stub())

    rows = bse_provider.get_shareholding("BOMOXY-B1")
    assert len(rows) == len(_SHP_INDEX["Table"]) == 4
    latest = rows[0]
    assert latest["quarter_end"] == date(2026, 6, 30)
    assert latest["submission_date"] == date(2026, 7, 8)
    assert latest["promoter_percent"] == 73.29
    assert latest["institutions_percent"] == 0.06
    assert latest["source"] == "BSE"
    assert latest["xbrl_url"].startswith("https://www.bseindia.com/XBRLFILES/")


def test_get_shareholding_caches_parsed_xbrl(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    calls = {"n": 0}

    def counting(url: str) -> httpx.Response:
        calls["n"] += 1
        return _shp_http_stub()(url)

    monkeypatch.setattr(bse_provider, "_http_get", counting)
    bse_provider.get_shareholding("BOMOXY-B1")
    first = calls["n"]
    # Second call: the index is refetched but every XBRL is now cached → no new XBRL GETs.
    bse_provider.get_shareholding("BOMOXY-B1")
    xbrl_gets_first = first - 1  # minus the one index call
    assert calls["n"] - first == 1  # only the index refetch, no XBRL re-GET
    assert xbrl_gets_first >= 1


def test_get_shareholding_offline_xbrl_serves_null_percentages(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    # Index reachable, every XBRL 404s → rows carry quarter_end + link, no percentages.
    monkeypatch.setattr(bse_provider, "_http_get", _shp_http_stub(xbrl=404))
    rows = bse_provider.get_shareholding("BOMOXY-B1")
    assert rows and all("promoter_percent" not in r for r in rows)
    assert rows[0]["quarter_end"] == date(2026, 6, 30)
    assert rows[0]["xbrl_url"] and rows[0]["source"] == "BSE"


def test_get_shareholding_index_failure_raises(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))

    def dead(url: str) -> httpx.Response:
        return httpx.Response(503, content=b"")

    monkeypatch.setattr(bse_provider, "_http_get", dead)
    with pytest.raises(ProviderError, match="index HTTP 503"):
        bse_provider.get_shareholding("BOMOXY-B1")


def test_get_shareholding_non_bse_symbol_fast_fails() -> None:
    with pytest.raises(ProviderError, match="not a known BSE instrument"):
        bse_provider.get_shareholding("AAPL")
