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

import csv
import io
import logging
import os
import threading
import time
import zipfile
from datetime import UTC, date, datetime, timedelta

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


__all__ = ["PROVIDER", "get_history", "get_quote", "is_available", "parse_bhavcopy"]
