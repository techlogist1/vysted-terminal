"""India BSE data provider — keyless EOD micro-cap coverage (FR-064, WS6).

The companion to :mod:`services.india_provider`: where the NSE provider serves
the large-/mid-cap EOD via jugaad, BSE is where the *micro-caps* live (the
B/X/XT/T/Z groups — thousands of names yfinance is documented-unreliable for and
NSE never listed). This provider gives instant full-universe EOD coverage by
pivoting around BSE's once-daily **BhavCopy** (the official end-of-day dump of
EVERY scrip) rather than per-symbol scraping:

  * ``get_history`` — EOD OHLCV assembled from the cached daily bhavcopies in the
    requested range, with each day's row located by the **numeric scrip code**
    (``FinInstrmId``) resolved from the bundled master (ticker → code), falling
    back to the ticker string only when the master carries no code. A cold cache
    downloads only the *recent* missing trading days (bounded — we never backfill
    years on a cold start; we serve what is cached + recent). Daily for ``1d``;
    weekly/monthly resampled from daily.
  * ``get_quote`` — the latest EOD close + the official prior close (→ change/%)
    from BSE's ``getScripHeaderData`` endpoint. INR, IST, ``provider="bse"``,
    EOD-labelled.
  * Intraday is **not** served keyless — it raises so the registry surfaces an
    honest "add a BYOK broker (Kite / Upstox / Dhan)" rather than a wrong/empty
    intraday chart.

Hardening mirrors :mod:`services.india_provider`: a realistic UA/Referer (BSE
serves an empty/blocked payload to an obvious bot), the on-disk cache-dir-race
retry, the IST trading-date recovery, and EOD labelling.

Licensing / provenance
~~~~~~~~~~~~~~~~~~~~~~~~

This is an **idea-level reimplementation** under the project's AGPL-3.0 — the
BhavCopy URL shape, the ``getScripHeaderData`` request, and the throttle are
*modelled on* the public BennyThadikaran/BseIndiaApi (GPL) but written here from
scratch. We do **not** import BseIndiaApi / bsedata / mthrottle or any GPL lib,
and we add **zero** new runtime dependency: the throttle is the ~10-line
:class:`_TokenBucket` below (replacing mthrottle), and the HTTP is the ``httpx``
already shipped. The full BSE scrip master (``bse_instruments.json``) is
regenerated the same way the NSE master is — see that file's header note.
"""

from __future__ import annotations

import calendar
import csv
import io
import json
import logging
import os
import threading
import time
import zipfile
from datetime import UTC, date, datetime, timedelta
from xml.etree import ElementTree as ET

import httpx
import pandas as pd

from models.market import OHLCVBar, OHLCVSeries, Quote
from services import locale, symbol_resolver
from services.errors import ProviderError

logger = logging.getLogger(__name__)

PROVIDER = "bse"

# EOD timeframes we serve from the daily bhavcopies (weekly/monthly resampled).
_EOD_TIMEFRAMES = {"1d", "1wk", "1mo"}
# Approximate lookback (calendar days) per public range token → bhavcopy window.
_RANGE_DAYS = {
    "5d": 12,
    "1mo": 38,
    "3mo": 100,
    "6mo": 190,
    "1y": 380,
    "2y": 760,
    "5y": 1850,
    "max": 3700,
}
_DEFAULT_RANGE_DAYS = 380

# A cold cache must not attempt to backfill years of bhavcopies on the first
# request (each missing day is a separate ~1 MB download). We download at most
# this many recent *trading* days of missing bhavcopies per call; the rest of a
# wide range is served from whatever is already cached. The cache warms over
# repeated use, so deep history fills in across sessions rather than in one
# blocking burst.
_MAX_COLD_DOWNLOADS = 8

# The BSE EOD BhavCopy (cash market, "F" full) — one CSV per trading day, every
# scrip. ``{ymd}`` is YYYYMMDD. Served as a ZIP wrapping the CSV.
_BHAVCOPY_URL = (
    "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{ymd}_F_0000.CSV"
)
# Per-scrip latest-EOD header (close + prior close) — keyed by BSE scrip code.
_SCRIP_HEADER_URL = "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w"

# BSE blocks an obvious bot; a real desktop UA + the bseindia.com Referer are
# required for both the bhavcopy download and the JSON header endpoint.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/csv, */*",
}
_CONNECT_TIMEOUT = 10.0
_READ_TIMEOUT = 20.0


# ---------------------------------------------------------------------------
# Throttle — a tiny thread-safe token bucket (replaces the GPL ``mthrottle``).
# ---------------------------------------------------------------------------


class _TokenBucket:
    """A minimal thread-safe token bucket so a bhavcopy backfill stays polite.

    ``rate`` tokens are refilled per second up to ``capacity``; :meth:`take`
    blocks just long enough for one token to be available. Replaces the GPL
    ``mthrottle`` with no new dependency — the provider calls are synchronous
    (the registry runs them on a thread), so a plain lock + monotonic clock is
    the right fit (no event loop required)."""

    def __init__(self, rate: float = 3.0, capacity: float = 3.0) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def take(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._tokens = min(self._capacity, self._tokens + (now - self._updated) * self._rate)
            self._updated = now
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self._rate
                time.sleep(wait)
                self._tokens = 0.0
                self._updated = time.monotonic()
            else:
                self._tokens -= 1.0


_bucket = _TokenBucket()


# ---------------------------------------------------------------------------
# Cache + HTTP seam (mockable in tests via the module-level _http_get).
# ---------------------------------------------------------------------------


def _cache_dir() -> str:
    """On-disk bhavcopy cache dir (mirrors jugaad's appdirs cache location)."""
    try:
        import appdirs

        base = appdirs.user_cache_dir("bse-bhavcopy")
    except Exception:  # noqa: BLE001 - appdirs missing → fall back to a temp dir
        base = os.path.join(os.path.expanduser("~"), ".cache", "bse-bhavcopy")
    return base


def _http_get(url: str) -> httpx.Response:
    """One throttled GET with the BSE-friendly headers (the network seam).

    Tests monkeypatch THIS function so no unit test touches the live network.
    """
    _bucket.take()
    with httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(_READ_TIMEOUT, connect=_CONNECT_TIMEOUT),
        headers=_HEADERS,
    ) as client:
        return client.get(url)


def is_available() -> bool:
    """True — the BSE backend is pure ``httpx`` (always shipped), no extra dep.

    Kept as a predicate so the registry declaration reads like the NSE one and a
    future hard gate (e.g. a region kill-switch) has a single seam.
    """
    return True


# ---------------------------------------------------------------------------
# IST trading-date helper (mirror india_provider).
# ---------------------------------------------------------------------------
#
# Unlike NSE (jugaad's ``DATE`` is an IST-midnight encoded in UTC, so the true
# IST trading date must be recovered with a +5.5h nudge), each BSE bhavcopy is
# keyed by its IST trading day already — we iterate IST trading days and download
# one bhavcopy per day, so the day IS the IST trading date with no decoding. The
# EOD-labelling convention is identical: a daily bar lives at UTC midnight of its
# IST trading date (the unambiguous by-date representation the chart renders).


def _bar_timestamp(trading_day: date) -> datetime:
    """Daily bar at UTC midnight of its IST trading date (mirrors india_provider)."""
    return datetime(trading_day.year, trading_day.month, trading_day.day, tzinfo=UTC)


# ---------------------------------------------------------------------------
# BhavCopy fetch + parse (idea-level reimpl; no GPL import).
# ---------------------------------------------------------------------------


def parse_bhavcopy(text: str) -> pd.DataFrame:
    """Parse a BSE BhavCopy CSV into a normalised per-scrip EOD frame.

    The modern BSE ``BhavCopy_BSE_CM_…_F_0000.CSV`` carries ISO-style headers
    (``TckrSymb``, ``FinInstrmId`` = scrip code, ``OpnPric``/``HghPric``/
    ``LwPric``/``ClsPric``/``TtlTradgVol``, ``TradDt``). Returns columns
    ``[code, ticker, open, high, low, close, volume, date]``; an unparseable /
    empty body yields an empty frame (the caller treats it as "no data that day").
    """
    rows: list[dict[str, object]] = []
    reader = csv.DictReader(io.StringIO(text))
    for raw in reader:
        # Tolerate stray whitespace in header names.
        row = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        ticker = row.get("TckrSymb") or row.get("SC_NAME") or ""
        code = row.get("FinInstrmId") or row.get("SC_CODE") or ""
        # Only the equity segment carries OHLC we chart; skip a blank row.
        close = _num(row.get("ClsPric") or row.get("CLOSE"))
        if close is None or not ticker:
            continue
        trad = row.get("TradDt") or row.get("TIMESTAMP") or ""
        rows.append(
            {
                "code": str(code).strip(),
                "ticker": str(ticker).strip().upper(),
                # Security series (e.g. "EQ"). A scrip can list under several series;
                # we chart the equity line, so the assembler prefers EQ when present.
                "series": (row.get("SctySrs") or row.get("SERIES") or "").strip().upper(),
                "open": _num(row.get("OpnPric") or row.get("OPEN")) or close,
                "high": _num(row.get("HghPric") or row.get("HIGH")) or close,
                "low": _num(row.get("LwPric") or row.get("LOW")) or close,
                "close": close,
                "volume": _num(row.get("TtlTradgVol") or row.get("NO_OF_SHRS")) or 0.0,
                "date": trad,
            }
        )
    return pd.DataFrame(rows)


def _pick_equity_row(match: pd.DataFrame) -> pd.Series:
    """From the rows matching a ticker, prefer the equity (``EQ``) security series
    when present — a scrip can list under several series and we chart the equity
    line — else fall back to the first row (no name is dropped if BSE happens to
    label its equity series differently than ``EQ``)."""
    if "series" in match.columns:
        eq = match[match["series"] == "EQ"]
        if not eq.empty:
            return eq.iloc[0]
    return match.iloc[0]


def _decode_bhavcopy_body(resp: httpx.Response) -> str:
    """Return the CSV text from a bhavcopy response (handles a ZIP-wrapped CSV)."""
    content = resp.content
    if content[:2] == b"PK":  # a ZIP archive — extract the single CSV member
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            name = next((n for n in zf.namelist() if n.upper().endswith(".CSV")), None)
            if name is None:
                raise ProviderError("bse: bhavcopy ZIP carried no CSV member")
            return zf.read(name).decode("utf-8", errors="replace")
    return content.decode("utf-8", errors="replace")


def _bhavcopy_for(day: date) -> pd.DataFrame | None:
    """Return the cached/downloaded bhavcopy frame for ``day``, or ``None``.

    ``None`` means "no trading data for that day" (a weekend/holiday, or a
    download miss) — the caller simply skips it. A cached empty marker prevents
    re-downloading a known-empty day every call. Resilient to the cache-dir race
    (``FileExistsError`` → ensure the dir + retry once), mirroring india_provider.
    """
    cache = _cache_dir()
    path = os.path.join(cache, f"{day.isoformat()}.csv")
    for _attempt in range(2):
        try:
            os.makedirs(cache, exist_ok=True)
            if os.path.exists(path):
                text = _read_cached(path)
                return parse_bhavcopy(text) if text else None
            return None  # not cached — caller decides whether to download
        except FileExistsError:
            continue  # cache-dir race — ensure dir + retry once
    return None


def _read_cached(path: str) -> str:
    with open(path, encoding="utf-8") as fp:
        return fp.read()


def _download_bhavcopy(day: date) -> pd.DataFrame | None:
    """Download + cache the bhavcopy for ``day``; return its frame or ``None``.

    A 404 (no file for a weekend/holiday/not-yet-published day) is cached as an
    empty marker so it is not re-fetched. Any other transport failure returns
    ``None`` (best-effort — the range assembly skips a missing day, never crashes).
    """
    ymd = day.strftime("%Y%m%d")
    url = _BHAVCOPY_URL.format(ymd=ymd)
    cache = _cache_dir()
    path = os.path.join(cache, f"{day.isoformat()}.csv")
    try:
        resp = _http_get(url)
    except Exception as exc:  # noqa: BLE001 - any transport failure is non-fatal
        logger.debug("bse: bhavcopy download failed for %s: %s", day, exc)
        return None
    if resp.status_code == 404:
        _write_cache(cache, path, "")  # cache the empty marker
        return None
    if resp.status_code != 200:
        logger.debug("bse: bhavcopy %s returned HTTP %s", day, resp.status_code)
        return None
    try:
        text = _decode_bhavcopy_body(resp)
    except ProviderError as exc:
        logger.debug("bse: bhavcopy decode failed for %s: %s", day, exc)
        return None
    frame = parse_bhavcopy(text)
    if frame.empty:
        _write_cache(cache, path, "")
        return None
    _write_cache(cache, path, text)
    return frame


def _write_cache(cache: str, path: str, text: str) -> None:
    for _attempt in range(2):
        try:
            os.makedirs(cache, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fp:
                fp.write(text)
            return
        except FileExistsError:
            continue  # cache-dir race — ensure dir + retry once
        except OSError as exc:  # pragma: no cover - disk failure is non-fatal
            logger.debug("bse: bhavcopy cache write failed for %s: %s", path, exc)
            return


# ---------------------------------------------------------------------------
# Symbol gating + scrip-code resolution.
# ---------------------------------------------------------------------------


def _require_bse(symbol: str) -> str:
    """Return the bare BSE symbol, or raise so the registry falls through fast.

    A non-BSE ticker is rejected without a network call — the registry then
    resolves it via the next provider.
    """
    bare = locale.strip_exchange_suffix(symbol)
    if not symbol_resolver.is_bse_symbol(bare):
        raise ProviderError(f"bse: {symbol!r} is not a known BSE instrument")
    return bare


def _scrip_code(symbol: str) -> str | None:
    """Resolve a bare BSE ticker → its numeric scrip code (header endpoint key)."""
    return symbol_resolver.bse_scrip_code(symbol)


# ---------------------------------------------------------------------------
# Public accessors — synchronous (the registry runs them on a thread).
# ---------------------------------------------------------------------------


def get_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
    """Return an EOD OHLCV series for a BSE instrument.

    Routed by SCRIP CODE: the bare ticker is looked up in the bundled master
    (ticker → numeric code) and each bhavcopy day's row is located by
    ``FinInstrmId`` — deterministic even when a scrip's printed ticker drifts
    from the master spelling (renames, SME migrations); the ticker string is
    only the fallback when the master carries no code. Assembled from the daily
    bhavcopies in the requested range: every cached day is read, and up to
    :data:`_MAX_COLD_DOWNLOADS` recent missing trading days are downloaded (so a
    cold cache serves recent EOD immediately and deep history fills in across
    sessions). Daily for ``1d``; weekly/monthly resampled. Intraday timeframes
    raise (keyless BSE is EOD-only).
    """
    if timeframe not in _EOD_TIMEFRAMES:
        raise ProviderError(
            f"bse: intraday timeframe {timeframe!r} is not available keyless — "
            "add a BYOK broker (Kite / Upstox / Dhan) for BSE intraday"
        )
    bare = _require_bse(symbol)
    code = _scrip_code(bare)
    days = _RANGE_DAYS.get(range_ or "", _DEFAULT_RANGE_DAYS)
    today = datetime.now(tz=UTC).astimezone(locale.market_timezone(locale.REGION_IN)).date()
    start = today - timedelta(days=days)

    daily = _assemble_history(bare, code, start, today)
    if not daily:
        raise ProviderError(f"bse: no EOD data for {bare!r}")
    bars = _resample(daily, timeframe) if timeframe in {"1wk", "1mo"} else daily
    return OHLCVSeries(symbol=bare, timeframe=timeframe, bars=bars, provider=PROVIDER)


def _match_scrip(frame: pd.DataFrame, ticker: str, code: str | None) -> pd.DataFrame:
    """Rows for this instrument in one bhavcopy frame — scrip code first.

    The numeric ``FinInstrmId`` from the master is the deterministic key (ticker
    spellings drift across renames; codes never do). The ticker match is the
    fallback for a master row without a code — and for a code that misses the
    day's file (e.g. a bhavcopy older than a re-coding).
    """
    if code:
        match = frame[frame["code"] == code]
        if not match.empty:
            return match
    return frame[frame["ticker"] == ticker]


def _assemble_history(ticker: str, code: str | None, start: date, end: date) -> list[OHLCVBar]:
    """Walk trading days in ``[start, end]``, collecting this scrip's daily bar.

    Cached bhavcopies are read for the whole range; missing *recent* trading days
    are downloaded up to the cold-download budget (newest-first) so a cold cache
    still serves recent EOD without a multi-year backfill burst. Rows are located
    by scrip code (ticker fallback) via :func:`_match_scrip`.
    """
    trading_days = [
        d
        for d in _iter_days(start, end)
        if d.weekday() < 5 and d.isoformat() not in _bse_holidays()
    ]
    downloads_left = _MAX_COLD_DOWNLOADS
    bars: list[OHLCVBar] = []
    # Newest-first so the cold-download budget spends on the most recent days.
    for day in reversed(trading_days):
        frame = _bhavcopy_for(day)
        if frame is None and downloads_left > 0:
            frame = _download_bhavcopy(day)
            downloads_left -= 1
        if frame is None or frame.empty:
            continue
        match = _match_scrip(frame, ticker, code)
        if match.empty:
            continue
        row = _pick_equity_row(match)
        bars.append(
            OHLCVBar(
                timestamp=_bar_timestamp(day),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"] or 0.0),
            )
        )
    bars.sort(key=lambda b: b.timestamp)
    return bars


def get_quote(symbol: str) -> Quote:
    """Return the latest EOD quote for a BSE instrument (INR, T+1 EOD).

    Routed by SCRIP CODE from the master (ticker → code). Primary path: BSE's
    ``getScripHeaderData`` keyed by the code (latest close + official prior
    close → change/%). If the header endpoint is unavailable, falls back to the
    two most-recent bhavcopy closes — also code-routed — so a quote is still
    served keyless.
    """
    bare = _require_bse(symbol)
    code = _scrip_code(bare)
    header = _fetch_scrip_header(bare, code) if code else None
    if header is not None:
        return header
    return _quote_from_bhavcopy(bare, code)


def _fetch_scrip_header(bare: str, code: str) -> Quote | None:
    """Derive a quote from ``getScripHeaderData`` for ``code``, or ``None``.

    ``bare`` is the requested ticker, threaded through so the resulting
    ``Quote.symbol`` is the bare symbol the caller asked for (the live header
    payload has no ticker field — only the numeric scrip code — so deriving the
    symbol from the payload would yield the scrip code and trip the registry's
    correctness gate, mirroring india_provider which always sets ``symbol=bare``).
    Best-effort — any transport/parse failure returns ``None`` so the caller can
    fall back to the bhavcopy-derived quote.
    """
    url = f"{_SCRIP_HEADER_URL}?Debtflag=&scripcode={code}&seriesid="
    try:
        resp = _http_get(url)
        if resp.status_code != 200:
            return None
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001 - any header failure → bhavcopy fallback
        logger.debug("bse: scrip header fetch failed for %s: %s", code, exc)
        return None
    return _quote_from_header(bare, payload)


def _quote_from_header(bare: str, payload: dict) -> Quote | None:
    """Build a Quote for ``bare`` from a ``getScripHeaderData`` payload, or ``None``.

    The endpoint returns ``{"Header": [{"Scrip_Cd"/"ScripCode","LTP"/"CurrVal",
    "PrevClose"/"Prev_Cls","Volume",...}]}`` — keyed by the numeric scrip code,
    with NO ticker field. We read the latest close and the official prior close
    defensively (BSE has renamed these fields over time) and stamp the requested
    ``bare`` symbol (NOT the scrip code) so the registry's symbol-match
    correctness gate accepts the quote, mirroring india_provider. The bar is
    labelled at the most-recent IST session.
    """
    header_list = payload.get("Header") if isinstance(payload, dict) else None
    if not header_list:
        return None
    h = header_list[0] if isinstance(header_list, list) else header_list
    close = _num(h.get("LTP") or h.get("CurrVal") or h.get("Close"))
    if close is None or close <= 0:
        return None
    prev = _num(h.get("PrevClose") or h.get("Prev_Cls") or h.get("PreviousClose"))
    change = close - prev if prev else 0.0
    change_percent = (change / prev * 100.0) if prev else 0.0
    trading_day = locale.most_recent_session(locale.REGION_IN)
    return Quote(
        symbol=bare,
        price=close,
        change=change,
        change_percent=change_percent,
        volume=_num(h.get("Volume") or h.get("TotalTradedQty")),
        currency="INR",
        market_state="REGULAR" if locale.is_market_open(locale.REGION_IN) else "CLOSED",
        timestamp=_bar_timestamp(trading_day),
        provider=PROVIDER,
    )


def _quote_from_bhavcopy(bare: str, code: str | None) -> Quote:
    """Fallback quote — the two most-recent bhavcopy closes for ``bare``."""
    today = datetime.now(tz=UTC).astimezone(locale.market_timezone(locale.REGION_IN)).date()
    bars = _assemble_history(bare, code, today - timedelta(days=14), today)
    if not bars:
        raise ProviderError(f"bse: no EOD data for {bare!r}")
    last = bars[-1]
    prev_close = bars[-2].close if len(bars) >= 2 else None
    change = last.close - prev_close if prev_close else 0.0
    change_percent = (change / prev_close * 100.0) if prev_close else 0.0
    return Quote(
        symbol=bare,
        price=last.close,
        change=change,
        change_percent=change_percent,
        volume=last.volume,
        currency="INR",
        market_state="REGULAR" if locale.is_market_open(locale.REGION_IN) else "CLOSED",
        timestamp=last.timestamp,
        provider=PROVIDER,
    )


# ---------------------------------------------------------------------------
# Shareholding pattern — the SEBI XBRL via BSE (R13 / WITNESS).
# ---------------------------------------------------------------------------
#
# BSE exposes no non-interactive JSON with the PARSED category percentages (its
# CorporatesSHPSecuritybeta lane returns ``{}`` to a non-browser caller), but it
# DOES expose two stable, keyless surfaces the site's own Angular app drives:
#
#   * ``SHPQNewFormat`` — the per-scrip quarter INDEX, one cheap JSON call:
#     ``{"Table": [{qtrid, qtr "June 2026", XbrlFile, filing_date_time,
#     xbrlurl "/XBRLFILES/.../<...>_SP.html"}, ...]}`` newest-first.
#   * the SEBI shareholding-pattern **XBRL** for each quarter, at
#     ``/XBRLFILES/SHPXBRLDataXML/<XbrlFile>`` — the AUTHORITATIVE, regulator-
#     mandated filing. The summary category percentages are the
#     ``in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares`` facts, one
#     per single-category context (promoter / public / institutions / …). This
#     is the SAME primary source screener.in / trendlyne aggregate — read direct.
#
# The XBRL is parsed for up to :data:`_MAX_SHP_XBRL_PARSES` recent quarters per
# call and each parse is cached on disk keyed by the immutable filing name, so a
# warm cache is free and deep history fills in across sessions (mirroring the
# bhavcopy cold-download discipline). Offline — or a parse miss — degrades to
# null percentages with the quarter-end + XBRL link still served; never guessed.

_SHP_INDEX_URL = "https://api.bseindia.com/BseIndiaAPI/api/SHPQNewFormat/w"
_SHP_XBRL_BASE = "https://www.bseindia.com/XBRLFILES/SHPXBRLDataXML/"
_SHP_SITE_BASE = "https://www.bseindia.com"
#: Live XBRL parses ATTEMPTED per call; cached quarters cost nothing (so a warm
#: cache serves full history, and offline caps the network to this many misses).
_MAX_SHP_XBRL_PARSES = 8
#: The SEBI SHP concept carrying a category's holding as a fraction (0-1).
_SHP_PCT_CONCEPT = "ShareholdingAsAPercentageOfTotalNumberOfShares"
#: XBRL category-member localname → our summary field.
_SHP_CATEGORY = {
    "ShareholdingOfPromoterAndPromoterGroupMember": "promoter",
    "PublicShareholdingMember": "public",
    "InstitutionsMember": "institutions",
    "InstitutionsDomesticMember": "institutions_domestic",
    "InstitutionsForeignMember": "institutions_foreign",
    "NonInstitutionsMember": "non_institutions",
}
_MONTHS = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}


def _shp_cache_dir() -> str:
    """On-disk cache dir for parsed SHP summaries (under the bhavcopy base)."""
    return os.path.join(_cache_dir(), "shp")


def get_shareholding(symbol: str) -> list[dict]:
    """Quarterly shareholding-pattern rows for a BSE instrument, newest-first.

    Each row: ``{quarter_end (date), submission_date (date|None), xbrl_url,
    source "BSE"}`` plus — for the recent parsed quarters — ``promoter_percent``,
    ``public_percent``, ``institutions_percent`` and the ``dii``/``fii`` split
    (0-100 floats) read from the SEBI XBRL. Older quarters beyond the per-call
    parse budget carry the quarter-end + XBRL link with the percentages absent —
    honest, never fabricated; the warm cache fills them in over sessions.

    Raises :class:`ProviderError` only when the quarter index itself is
    unreachable (so the caller records the lane failure); a non-BSE ticker
    fast-fails without a network call.
    """
    bare = _require_bse(symbol)
    code = _scrip_code(bare)
    if not code:
        raise ProviderError(f"bse shareholding: no scrip code for {bare!r} in the master")
    quarters = _fetch_shp_index(code)
    rows: list[dict] = []
    budget = _MAX_SHP_XBRL_PARSES
    for quarter in quarters:
        if not isinstance(quarter, dict):
            continue
        xbrl_file = _clean_str(quarter.get("XbrlFile"))
        summary = _shp_cached_summary(xbrl_file) if xbrl_file else None
        if summary is None and xbrl_file and budget > 0:
            budget -= 1  # one network attempt spent (success or miss)
            summary = _fetch_and_parse_shp_xbrl(xbrl_file)
        row: dict = {
            "quarter_end": _shp_quarter_end(quarter.get("qtr")),
            "submission_date": _shp_filing_date(quarter.get("filing_date_time")),
            "xbrl_url": _shp_site_url(quarter.get("xbrlurl")),
            "source": PROVIDER.upper(),
        }
        if summary:
            row.update(summary)
        rows.append(row)
    return rows


def _fetch_shp_index(code: str) -> list[dict]:
    """The SHPQNewFormat quarter index for ``code`` — the raw row dicts."""
    url = f"{_SHP_INDEX_URL}?scripcode={code}"
    try:
        resp = _http_get(url)
    except Exception as exc:  # noqa: BLE001 - surfaced as a lane error
        raise ProviderError(f"bse shareholding: transport failure: {exc}") from exc
    if resp.status_code != 200:
        raise ProviderError(f"bse shareholding: index HTTP {resp.status_code}")
    try:
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001 - a non-JSON body is a lane error
        raise ProviderError(f"bse shareholding: non-JSON index: {exc}") from exc
    table = payload.get("Table") if isinstance(payload, dict) else None
    if not isinstance(table, list):
        raise ProviderError(f"bse shareholding: malformed index for scrip {code}")
    return [row for row in table if isinstance(row, dict)]


def _fetch_and_parse_shp_xbrl(xbrl_file: str) -> dict | None:
    """Download + parse ONE quarter's SEBI XBRL; cache + return its summary.

    ``None`` on any transport/parse failure (offline no-op) — the caller then
    serves that quarter's row without percentages.
    """
    url = _SHP_XBRL_BASE + xbrl_file
    try:
        resp = _http_get(url)
    except Exception as exc:  # noqa: BLE001 - a fetch miss is non-fatal
        logger.debug("bse: SHP XBRL fetch failed for %s: %s", xbrl_file, exc)
        return None
    if resp.status_code != 200:
        logger.debug("bse: SHP XBRL %s returned HTTP %s", xbrl_file, resp.status_code)
        return None
    summary = parse_shp_xbrl(resp.text)
    if summary:
        _shp_write_cache(xbrl_file, summary)
        return summary
    return None


def parse_shp_xbrl(xml_text: str) -> dict:
    """Parse a SEBI SHP XBRL into summary category percentages (0-100 floats).

    Returns any of ``promoter_percent`` / ``public_percent`` /
    ``institutions_percent`` / ``dii_percent`` / ``fii_percent`` the filing
    carried; a missing category is simply absent (never fabricated). A
    non-XBRL / unparseable body yields ``{}``. Pure + synchronous so tests pin
    it against a recorded fixture.

    Schema note (R13 hardening — the historical-split-corruption fix): the
    ``ShareholdingAsAPercentageOfTotalNumberOfShares`` concept is documented
    as a 0-1 fraction (``unitRef="pure"``) and every RECENT BSE filing (~Sep
    2025 onward) follows that convention — but older filings emit the SAME
    concept, with the SAME ``unitRef``/``decimals`` attributes, already
    scaled to a 0-100 percentage (observed live: TCI's June-2025-and-older
    quarters carry ``68.73`` where the March-2026 quarter carries ``0.6873``
    for the identical promoter category). Nothing in the XML declares which
    convention is in play, so the scale is inferred per-filing: a single
    category can never legitimately exceed ``1.0`` as a true fraction (that
    would be >100% of one member), so any raw value > 1.0 anywhere in the
    filing is conclusive proof it uses the already-percent convention.
    :func:`_validate_shp_summary` is the backstop for anything this inference
    still gets wrong.
    """
    text = (xml_text or "").lstrip("﻿")
    if not text.strip():
        return {}
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except ET.ParseError:
        return {}
    contexts: dict[str, list[str]] = {}
    for ctx in root.iter():
        if _xml_local(ctx.tag) != "context":
            continue
        cid = ctx.get("id")
        if not cid:
            continue
        contexts[cid] = [
            (member.text or "").strip().rsplit(":", 1)[-1]
            for member in ctx.iter()
            if _xml_local(member.tag) == "explicitMember"
        ]
    raw: dict[str, float] = {}
    for element in root.iter():
        if _xml_local(element.tag) != _SHP_PCT_CONCEPT or not (
            element.text and element.text.strip()
        ):
            continue
        members = contexts.get(element.get("contextRef", ""), [])
        if len(members) != 1:  # a summary category has exactly one member
            continue
        field = _SHP_CATEGORY.get(members[0])
        if field is None or field in raw:
            continue
        try:
            raw[field] = float(element.text.strip())
        except ValueError:
            continue
    if not raw:
        return {}
    # A genuine fraction never exceeds 1.0 for a single category — any raw
    # value above that is decisive proof of the older already-percent schema.
    scale = 1.0 if any(abs(value) > 1.0 for value in raw.values()) else 100.0
    found = {field: round(value * scale, 4) for field, value in raw.items()}
    return _validate_shp_summary(_shp_summary_from_categories(found))


def _shp_summary_from_categories(found: dict[str, float]) -> dict:
    """Category percentages → the summary row, deriving the institutions total.

    Institutions total prefers the explicit ``InstitutionsMember``; else the
    domestic+foreign sum; else public − non-institutions. FII/DII map from the
    foreign/domestic institution members (the split the NSE master lacks)."""
    out: dict = {}
    if "promoter" in found:
        out["promoter_percent"] = found["promoter"]
    if "public" in found:
        out["public_percent"] = found["public"]
    if "non_institutions" in found:
        # The SEBI "Non-Institutions" member — the true non-institutional public
        # float the FII/DII split carves out of the (institution-inclusive)
        # "Public" category. Surfaced so a consumer can distinguish the two.
        out["public_non_institutional_percent"] = found["non_institutions"]
    domestic = found.get("institutions_domestic")
    foreign = found.get("institutions_foreign")
    if domestic is not None:
        out["dii_percent"] = domestic
    if foreign is not None:
        out["fii_percent"] = foreign
    institutions = found.get("institutions")
    if institutions is None and (domestic is not None or foreign is not None):
        institutions = round((domestic or 0.0) + (foreign or 0.0), 4)
    elif institutions is None and "public" in found and "non_institutions" in found:
        institutions = round(found["public"] - found["non_institutions"], 4)
    if institutions is not None:
        out["institutions_percent"] = institutions
    return out


#: The summary fields that are genuine percentages of total shares — every one
#: of them must land in [0, 100.5] (a small tolerance over 100 for rounding)
#: or the filing's split is unreliable end to end.
_SHP_PCT_FIELDS = (
    "promoter_percent",
    "public_percent",
    "institutions_percent",
    "dii_percent",
    "fii_percent",
    "public_non_institutional_percent",
)


def _validate_shp_summary(summary: dict) -> dict:
    """Class-level guard against a corrupt/unknown-schema quarter (R13 hardening).

    Any parsed category percentage outside ``[0, 100.5]`` invalidates the
    WHOLE quarter's split — a partially-nonsensical mix (some fields sane,
    one at 1500%) is worse than none, since a consumer has no way to tell
    which half to trust. Returns ``{}`` on any violation so the caller's
    quarter row keeps its ``quarter_end``/``xbrl_url`` but every split field
    stays ``None`` — honest, never fabricated, never half-corrupt."""
    for field_name in _SHP_PCT_FIELDS:
        value = summary.get(field_name)
        if value is not None and not (0.0 <= value <= 100.5):
            return {}
    return summary


def _shp_cached_summary(xbrl_file: str) -> dict | None:
    """The cached parsed summary for a filing, or ``None``.

    Re-validated on every read (not just at write time): a disk cache
    written by a pre-fix build carries the 100x-scaled corruption forever
    otherwise — :func:`_validate_shp_summary` self-heals a stale corrupt
    entry back to ``{}`` (treated as a cache miss below), so the next call
    re-parses the filing under the corrected scale inference instead of
    replaying the old bug from disk indefinitely.
    """
    path = os.path.join(_shp_cache_dir(), f"{xbrl_file}.json")
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fp:
                data = json.load(fp)
            if not isinstance(data, dict):
                return None
            validated = _validate_shp_summary(data)
            return validated or None
    except (OSError, ValueError) as exc:
        logger.debug("bse: SHP cache read failed for %s: %s", xbrl_file, exc)
    return None


def _shp_write_cache(xbrl_file: str, summary: dict) -> None:
    """Cache a parsed summary keyed by the immutable filing name."""
    cache = _shp_cache_dir()
    path = os.path.join(cache, f"{xbrl_file}.json")
    for _attempt in range(2):
        try:
            os.makedirs(cache, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(summary, fp)
            return
        except FileExistsError:
            continue  # cache-dir race — ensure dir + retry once
        except OSError as exc:  # pragma: no cover - disk failure is non-fatal
            logger.debug("bse: SHP cache write failed for %s: %s", path, exc)
            return


def _shp_quarter_end(qtr: object) -> date | None:
    """``"June 2026"`` → the last calendar day of that month (2026-06-30)."""
    raw = _clean_str(qtr)
    if not raw:
        return None
    parts = raw.split()
    if len(parts) != 2:
        return None
    month = _MONTHS.get(parts[0].lower())
    if not month:
        return None
    try:
        year = int(parts[1])
    except ValueError:
        return None
    return date(year, month, calendar.monthrange(year, month)[1])


def _shp_filing_date(raw: object) -> date | None:
    """``"2026-07-08T15:21:20.487"`` → the calendar day; ``None`` if unparseable."""
    text = _clean_str(raw)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _shp_site_url(path: object) -> str | None:
    """A site-relative ``xbrlurl`` → an absolute bseindia.com URL."""
    text = _clean_str(path)
    if not text:
        return None
    return text if text.startswith("http") else _SHP_SITE_BASE + text


def _clean_str(value: object) -> str | None:
    """A stripped non-empty string (coercing numbers), else ``None``."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _xml_local(tag: str) -> str:
    """The local (namespace-stripped) name of an XML tag."""
    return tag.rsplit("}", 1)[-1]


# ---------------------------------------------------------------------------
# Resample + small numeric helpers (mirror india_provider).
# ---------------------------------------------------------------------------


def _resample(bars: list[OHLCVBar], timeframe: str) -> list[OHLCVBar]:
    """Resample daily bars to weekly/monthly OHLCV (right-labelled)."""
    if not bars:
        return bars
    rule = "W" if timeframe == "1wk" else "ME"
    frame = pd.DataFrame(
        {
            "timestamp": [b.timestamp for b in bars],
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
        }
    ).set_index("timestamp")
    agg = frame.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    agg = agg.dropna(subset=["open", "close"])
    out: list[OHLCVBar] = []
    for ts, row in agg.iterrows():
        out.append(
            OHLCVBar(
                timestamp=ts.to_pydatetime(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
    return out


def _iter_days(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def _bse_holidays() -> frozenset[str]:
    """BSE shares the NSE trading calendar — reuse the bundled NSE holiday set."""
    return locale._HOLIDAYS_BY_REGION.get(locale.REGION_IN, frozenset())


def _num(value: object) -> float | None:
    """Coerce a possibly-missing/NaN cell to ``float | None``."""
    if value is None or value == "":
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "PROVIDER",
    "get_history",
    "get_quote",
    "get_shareholding",
    "is_available",
    "parse_bhavcopy",
    "parse_shp_xbrl",
]
