"""NSE UDiFF common bhavcopy — one-request EOD closes for the whole NSE (D54).

The R11 mandate: with ONE exchange-direct request, a fully-throttled-on-Yahoo
IP still gets TODAY'S closing prices for every NSE equity. This module
downloads and parses the official once-daily NSE equities bhavcopy — the
end-of-day dump of every listed instrument — walking back from today across
weekends/holidays until a published file is found.

Endpoints (both verified live from this machine, 2026-07-02 IST)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Primary — the UDiFF common bhavcopy NSE has served since ~July 2024, on the
host the project's LESSONS.md calls out as the reliable one (nsearchives)::

    https://nsearchives.nseindia.com/content/cm/
        BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip

A ~190 KB ZIP wrapping one CSV (~3,500 rows, all CM-segment instruments) with
ISO-style headers: ``TradDt, …, FinInstrmId, ISIN, TckrSymb, SctySrs, …,
OpnPric, HghPric, LwPric, ClsPric, LastPric, PrvsClsgPric, …, TtlTradgVol, …``.

Fallback — the older security-wise full bhavcopy (plain CSV, extra DELIV
columns), tried ONCE for the same date when the primary is blocked or errors
(different host, so an intermittent nsearchives block does not zero the day)::

    https://archives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv

Headers: ``SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE,
LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, …`` (note the
leading spaces in header names and cell values — stripped on parse).

Equity-series choice
~~~~~~~~~~~~~~~~~~~~

Only rows whose ``SctySrs``/``SERIES`` is **EQ, BE or BZ** are kept — the
main-board equity set: EQ (rolling settlement; also carries the listed ETFs),
BE (trade-for-trade) and BZ (surveillance trade-for-trade). This covers the
app's bundled NSE master (~2,675 symbols) with zero symbol collisions in the
live file (verified 2026-07-02: 2,703 unique EQ+BE+BZ rows). The SME board
(SM/ST — lot-traded, outside the master), debt/gilt series (GS/GB/N*/TB) and
REIT/InvIT unit series (RR/IV) are excluded. Were a symbol ever to appear in
two kept series on one day, the EQ row wins.

Caching
~~~~~~~

Parsed compact rows (never the raw ZIP) are stored via :mod:`services.data_cache`
under ``nse_bhavcopy:YYYYMMDD`` with a 7-day TTL, so repeated boots on the same
day parse from SQLite instead of re-downloading. A 404 on a date **before**
today (IST) is a holiday — cached as an empty marker so future walks skip it
without a request. A 404 on *today* is NOT cached (the file publishes ~16:30
IST; caching the miss would blind the rest of the day to the real file).

Session discipline
~~~~~~~~~~~~~~~~~~

One shared :class:`httpx.AsyncClient` with a realistic desktop UA + the
nseindia.com referer, a 30 s read timeout, and a light inter-request throttle.
On 401/403/429 or a transport error the fallback endpoint is tried once for
the same date; if that also fails, :func:`fetch_latest` returns ``None`` (the
caller degrades) — never a retry storm. Failures surface via the ``None``
return and a ``logger.warning``; this upstream is exchange archives, NOT the
Yahoo family, so it deliberately does not report into
``services.provider_health``.

Honesty rule
~~~~~~~~~~~~

This is EOD data. Every result is labeled by its ``trade_date`` and must be
presented as the close of that session — never as a live quote.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import time
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

from services import data_cache

logger = logging.getLogger(__name__)

PROVIDER = "nse-bhavcopy"

_UDIFF_URL = (
    "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip"
)
_SEC_FULL_URL = "https://archives.nseindia.com/products/content/sec_bhavdata_full_{dmy}.csv"

#: Main-board equity series (see the module docstring for the rationale).
EQUITY_SERIES = frozenset({"EQ", "BE", "BZ"})

_CACHE_KEY = "nse_bhavcopy:{ymd}"
_CACHE_TTL_SECONDS = 7 * 24 * 3600.0

#: IST is a fixed +05:30 (no DST) — a plain offset avoids a tzdata dependency.
_IST = timezone(timedelta(hours=5, minutes=30), "IST")

# NSE archives serve an empty/blocked payload to an obvious bot; a real desktop
# UA + the nseindia.com referer mirror the bse_provider discipline.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Referer": "https://www.nseindia.com/",
    "Accept": "text/csv, application/zip, */*",
}
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

#: Light throttle — minimum spacing between consecutive archive requests.
_MIN_REQUEST_INTERVAL_SECONDS = 0.75


@dataclass(frozen=True)
class BhavRow:
    """One instrument's EOD row from the bhavcopy (bare symbol is the dict key)."""

    close: float
    prev_close: float | None
    volume: float | None
    high: float | None
    low: float | None
    series: str


@dataclass(frozen=True)
class BhavcopyResult:
    """A parsed bhavcopy: the session it describes + rows keyed by BARE symbol."""

    trade_date: date
    rows: dict[str, BhavRow]


# ---------------------------------------------------------------------------
# Shared client + throttle (reset_for_tests installs a mock transport).
# ---------------------------------------------------------------------------

_client: httpx.AsyncClient | None = None
_transport: httpx.BaseTransport | None = None
_throttle_lock: asyncio.Lock = asyncio.Lock()
_last_request_at: float = 0.0


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=_TIMEOUT,
            headers=_HEADERS,
            transport=_transport,
        )
    return _client


async def aclose() -> None:
    """Close the shared client (lifespan shutdown — avoid a leaked socket)."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception as exc:  # noqa: BLE001 - shutdown best-effort
            logger.debug("nse_bhavcopy: client aclose raised: %s", exc)
        _client = None


def reset_for_tests(transport: httpx.BaseTransport | None = None) -> None:
    """Drop the shared client so a test starts cold on ``transport``.

    Mirrors ``yahoo_batch_provider.reset_for_tests``: an optional
    ``httpx.MockTransport`` makes every archive request deterministic — no unit
    test touches the live network. Tests should ``await aclose()`` first.
    """
    global _client, _transport, _last_request_at, _throttle_lock
    _client = None
    _transport = transport
    _last_request_at = 0.0
    # asyncio.Lock binds to the loop that first awaits it; each test runs its
    # own loop, so a cold start needs a fresh lock too.
    _throttle_lock = asyncio.Lock()


async def _throttled_get(url: str) -> httpx.Response:
    """One GET through the shared client, spaced by the light throttle."""
    global _last_request_at
    async with _throttle_lock:
        wait = _MIN_REQUEST_INTERVAL_SECONDS - (time.monotonic() - _last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at = time.monotonic()
    return await _get_client().get(url)


# ---------------------------------------------------------------------------
# Parsing — UDiFF primary + sec_bhavdata_full fallback, one compact shape.
# ---------------------------------------------------------------------------


def _num(value: object) -> float | None:
    """Coerce a possibly-blank CSV cell to ``float | None`` (never raises)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _keep(rows: dict[str, BhavRow], symbol: str, row: BhavRow) -> None:
    """Insert ``row`` under ``symbol``, preferring an existing EQ row on clash."""
    existing = rows.get(symbol)
    if existing is not None and existing.series == "EQ" and row.series != "EQ":
        return
    rows[symbol] = row


def parse_bhavcopy(text: str) -> dict[str, BhavRow]:
    """Parse a bhavcopy CSV body into equity rows keyed by BARE symbol.

    Detects the format from the header: the UDiFF common bhavcopy
    (``TckrSymb``/``SctySrs``/``ClsPric``) or the legacy security-wise full
    bhavcopy (``SYMBOL``/``SERIES``/``CLOSE_PRICE``). Non-equity series are
    dropped (see :data:`EQUITY_SERIES`); a row without a positive close is
    dropped (never fabricate a price). An unparseable body yields ``{}``.
    """
    rows: dict[str, BhavRow] = {}
    for raw in csv.DictReader(io.StringIO(text)):
        # Both formats (the legacy one pads header names AND cells) normalise
        # to stripped keys/values.
        row = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        udiff = "TckrSymb" in row
        symbol = (row.get("TckrSymb") if udiff else row.get("SYMBOL")) or ""
        series = ((row.get("SctySrs") if udiff else row.get("SERIES")) or "").upper()
        if not symbol or series not in EQUITY_SERIES:
            continue
        close = _num(row.get("ClsPric") if udiff else row.get("CLOSE_PRICE"))
        if close is None or close <= 0:
            continue
        _keep(
            rows,
            symbol.upper(),
            BhavRow(
                close=close,
                prev_close=_num(row.get("PrvsClsgPric") if udiff else row.get("PREV_CLOSE")),
                volume=_num(row.get("TtlTradgVol") if udiff else row.get("TTL_TRD_QNTY")),
                high=_num(row.get("HghPric") if udiff else row.get("HIGH_PRICE")),
                low=_num(row.get("LwPric") if udiff else row.get("LOW_PRICE")),
                series=series,
            ),
        )
    return rows


def _decode_body(content: bytes) -> str:
    """CSV text from a bhavcopy response body (handles the ZIP-wrapped CSV)."""
    if content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            name = next((n for n in zf.namelist() if n.upper().endswith(".CSV")), None)
            if name is None:
                logger.warning("nse_bhavcopy: ZIP carried no CSV member")
                return ""
            return zf.read(name).decode("utf-8", errors="replace")
    return content.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Cache shape — compact JSON-serialisable rows (never the raw ZIP).
# ---------------------------------------------------------------------------

_EMPTY_MARKER = {"empty": True}


def _cache_key(day: date) -> str:
    return _CACHE_KEY.format(ymd=day.strftime("%Y%m%d"))


def _rows_to_cache(rows: dict[str, BhavRow]) -> dict[str, object]:
    return {
        "rows": {
            sym: [r.close, r.prev_close, r.volume, r.high, r.low, r.series]
            for sym, r in rows.items()
        }
    }


def _rows_from_cache(payload: object) -> dict[str, BhavRow] | None:
    """Rebuild rows from a cache payload; ``None`` for a marker/malformed value."""
    if not isinstance(payload, dict) or "rows" not in payload:
        return None
    out: dict[str, BhavRow] = {}
    try:
        for sym, packed in payload["rows"].items():
            close, prev_close, volume, high, low, series = packed
            out[sym] = BhavRow(
                close=float(close),
                prev_close=None if prev_close is None else float(prev_close),
                volume=None if volume is None else float(volume),
                high=None if high is None else float(high),
                low=None if low is None else float(low),
                series=str(series),
            )
    except (TypeError, ValueError, AttributeError):
        logger.warning("nse_bhavcopy: malformed cache payload — treating as miss")
        return None
    return out


# ---------------------------------------------------------------------------
# Fetch — walk back from IST-today until a published bhavcopy is found.
# ---------------------------------------------------------------------------


def _ist_today() -> date:
    """Today's IST calendar date (the test seam for deterministic walk-backs)."""
    return datetime.now(tz=_IST).date()


async def _fetch_day(day: date) -> tuple[str, dict[str, BhavRow] | None]:
    """Fetch + parse one date. Returns ``(status, rows)``.

    ``status`` is ``"ok"`` (rows present), ``"missing"`` (404 — holiday or not
    yet published) or ``"failed"`` (blocked / transport error on the primary
    AND the once-only fallback — the walk must stop and degrade).
    """
    primary = _UDIFF_URL.format(ymd=day.strftime("%Y%m%d"))
    fallback = _SEC_FULL_URL.format(dmy=day.strftime("%d%m%Y"))
    for attempt, url in enumerate((primary, fallback)):
        try:
            resp = await _throttled_get(url)
        except httpx.HTTPError as exc:
            logger.warning("nse_bhavcopy: request failed for %s (%s)", day, exc)
            continue
        if resp.status_code == 404:
            # No file for this date — a holiday, or today's not yet published.
            # The fallback host would 404 identically; don't double-request.
            return "missing", None
        if resp.status_code != 200:
            logger.warning(
                "nse_bhavcopy: HTTP %s for %s on %s host — %s",
                resp.status_code,
                day,
                "primary" if attempt == 0 else "fallback",
                "trying fallback once" if attempt == 0 else "degrading",
            )
            continue
        rows = parse_bhavcopy(_decode_body(resp.content))
        if rows:
            return "ok", rows
        logger.warning("nse_bhavcopy: %s parsed to zero equity rows on %s", day, resp.url)
    return "failed", None


async def fetch_latest(max_lookback_days: int = 7) -> BhavcopyResult | None:
    """Return the most recent available NSE equities bhavcopy, or ``None``.

    Walks back from today (IST) up to ``max_lookback_days`` calendar days:
    weekends are skipped without a request, a 404 (holiday / not yet published)
    walks back one day, and a blocked/failed date — after the once-only
    fallback-host attempt — returns ``None`` so the caller degrades (never a
    retry storm). Results are EOD, labeled by ``trade_date`` — never live.
    """
    today = _ist_today()
    for offset in range(max_lookback_days + 1):
        day = today - timedelta(days=offset)
        if day.weekday() >= 5:  # weekend — NSE never publishes; skip requestless
            continue
        cached = await data_cache.get(_cache_key(day), _CACHE_TTL_SECONDS)
        if cached is not None:
            rows = _rows_from_cache(cached)
            if rows:
                return BhavcopyResult(trade_date=day, rows=rows)
            continue  # cached empty marker — a known holiday; walk back
        status, rows = await _fetch_day(day)
        if status == "ok" and rows:
            await data_cache.set(_cache_key(day), _rows_to_cache(rows))
            return BhavcopyResult(trade_date=day, rows=rows)
        if status == "missing":
            if day < today:
                # A past-date 404 is a holiday — permanent; mark it so future
                # walks skip the request. Today's 404 just means "not yet
                # published" (the file lands ~16:30 IST) — never cached.
                await data_cache.set(_cache_key(day), _EMPTY_MARKER)
            continue
        logger.warning("nse_bhavcopy: giving up for %s — caller degrades", day)
        return None
    logger.warning("nse_bhavcopy: no bhavcopy found within %d days of %s", max_lookback_days, today)
    return None


def derive_market_cap(close: float, shares_outstanding: float | None) -> float | None:
    """EOD market cap = close x shares outstanding; ``None`` when unknowable."""
    if shares_outstanding is None or shares_outstanding <= 0 or close <= 0:
        return None
    return close * shares_outstanding


__all__ = [
    "PROVIDER",
    "EQUITY_SERIES",
    "BhavRow",
    "BhavcopyResult",
    "aclose",
    "derive_market_cap",
    "fetch_latest",
    "parse_bhavcopy",
    "reset_for_tests",
]
