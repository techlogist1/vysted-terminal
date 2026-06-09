"""NSE exchange-direct provider — the curl_cffi anti-bot lane (R7 Component 2).

The DIRECT companion to :mod:`services.india_provider` (the jugaad lane stays):
this module talks to ``www.nseindia.com``'s own JSON APIs through a
``curl_cffi`` Chrome-impersonated session with the NSE cookie dance, serving

  * ``get_history`` — EOD OHLCV from ``api/historicalOR/cm/equity`` (daily;
    weekly/monthly resampled). Intraday raises (the keyless live feed is
    session-locked) so the registry surfaces an honest "needs a BYOK broker".
  * ``get_quote`` — ``api/quote-equity`` when the edge serves it, falling back
    to an EOD quote derived from the last two ``historicalOR`` rows (close +
    the official ``CH_PREVIOUS_CLS_PRICE``).
  * ``get_corporate_announcements`` / ``get_results_calendar`` /
    ``get_shareholding_master`` — the raw corporate-disclosure lists Component 3
    (``services/corporate_disclosures.py``) models into typed shapes.

Every endpoint shape here was OBSERVED LIVE (scratch curl_cffi probe,
2026-06-10 IST, symbol RELIANCE) and the observed JSON is committed under
``tests/fixtures/nse/``:

  * ``GET /`` warm-up → 200, sets the Akamai cookies (``AKA_A2``/``_abck``/
    ``ak_bmsc``/``bm_sz``) the API paths require.
  * ``api/historicalOR/cm/equity?symbol=&series=["EQ"]&from=&to=`` → 200,
    ``{"data": [{CH_SYMBOL, CH_SERIES, CH_TIMESTAMP "YYYY-MM-DD" (the IST
    trading date directly — no UTC+5.5h decode needed, unlike jugaad),
    CH_OPENING_PRICE, CH_TRADE_HIGH_PRICE, CH_TRADE_LOW_PRICE,
    CH_CLOSING_PRICE, CH_PREVIOUS_CLS_PRICE, CH_TOT_TRADED_QTY, VWAP, …}, …
    newest-first], "meta": {...}}``. The legacy ``api/historical/cm/equity``
    path returned 503 — ``historicalOR`` is the live one.
  * ``api/corporate-announcements?index=equities&symbol=`` → 200, a bare list
    (FULL history, ~3,300 items / 2.8 MB for RELIANCE — trim client-side).
  * ``api/event-calendar?index=equities&symbol=`` → 200, bare list of
    ``{symbol, company, purpose, bm_desc, date "DD-Mon-YYYY"}``.
  * ``api/corporate-share-holdings-master?index=equities&symbol=`` → 200, bare
    list per quarter ``{date "31-MAR-2026", pr_and_prgrp, public_val,
    submissionDate, recordId, xbrl, …}``.
  * ``api/quote-equity?symbol=`` → **403 "Access Denied" (Akamai path ACL)**
    from the probe vantage on every variant (chrome/safari impersonation,
    page-level warm-ups, cookie hops via ``api/marketStatus`` 200) while the
    other API paths served fine on the SAME session. The quote parser is
    therefore defensive (the documented ``priceInfo`` contract, also relied on
    by the vendored jugaad ``NSELive.stock_quote``) and the OBSERVED behaviour
    — blocked → rotate → still blocked → breaker + EOD fallback — is the
    tested contract.

Anti-bot machinery (the brief's cookie-dance session):

  * cookie warm-up — a fresh session hits ``https://www.nseindia.com/`` before
    its first API call (the API 401/403s bare);
  * browser headers ride every API hit (``Accept``/``Accept-Language``/
    ``Referer``; TLS + UA + sec-ch-ua come from ``impersonate="chrome"``);
  * session rotation — a 401/403 discards the session, warms a fresh one, and
    retries ONCE; a second block raises (the registry falls through to jugaad/
    bse/yfinance);
  * throttle — ~1 req/s with jitter across ALL NSE traffic (module-global, the
    warm-up included);
  * circuit breaker — PER PATH (observed: the edge blocks ``quote-equity``
    while serving ``historicalOR`` on the same session, so one poisoned path
    must not take down the healthy ones): repeated post-rotation blocks open
    the path's circuit for a cooldown, during which calls fail fast without
    network.

The public accessors are synchronous, mirroring every other provider the
registry's sync resolver drives (callers run them in ``asyncio.to_thread``);
the shared session is guarded by a module lock so threaded callers serialize
(the 1 req/s throttle makes concurrency pointless anyway).
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

import pandas as pd

from models.market import OHLCVBar, OHLCVSeries, Quote
from services import locale, symbol_resolver
from services.errors import ProviderError

logger = logging.getLogger(__name__)

PROVIDER = "nse_direct"

_BASE = "https://www.nseindia.com"
_HISTORICAL_PATH = "/api/historicalOR/cm/equity"
_QUOTE_PATH = "/api/quote-equity"
_ANNOUNCEMENTS_PATH = "/api/corporate-announcements"
_EVENT_CALENDAR_PATH = "/api/event-calendar"
_SHAREHOLDING_PATH = "/api/corporate-share-holdings-master"

# Browser headers for the API hits. TLS fingerprint, User-Agent and the
# sec-ch-ua family come from curl_cffi's ``impersonate="chrome"``; these are the
# request-level headers the NSE front-end sends with its fetches.
_API_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}
_TIMEOUT = 20.0

# EOD timeframes served from historicalOR daily rows (weekly/monthly resampled).
_EOD_TIMEFRAMES = {"1d", "1wk", "1mo"}
# Approximate lookback (calendar days) per public range token.
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
# historicalOR is requested in bounded windows (the observed probe used 30
# days; NSE's own date-picker caps around a year — 90 days is safely inside).
_WINDOW_DAYS = 90
# The direct lane stays bounded: at most this many windows per request (~2y at
# ~1 req/s ≈ 10 s). A wider range raises so the registry falls through to
# jugaad (which has its own chunk pool) instead of stalling the chart for a
# minute — mirrors bse_provider's _MAX_COLD_DOWNLOADS bounding philosophy.
_MAX_WINDOWS = 9

# Default client-side trim for the announcements list (the endpoint returns the
# FULL history — ~3,300 items / 2.8 MB observed for RELIANCE).
_DEFAULT_ANNOUNCEMENT_LIMIT = 50

# Circuit breaker tuning: this many consecutive POST-ROTATION blocks on one
# path open its circuit for the cooldown.
_BREAKER_THRESHOLD = 3
_BREAKER_COOLDOWN_SECS = 300.0


def is_available() -> bool:
    """True if curl_cffi is importable (gates the registry declaration)."""
    try:
        import curl_cffi.requests  # noqa: F401

        return True
    except Exception:  # noqa: BLE001 - any import failure means "not available"
        return False


# ---------------------------------------------------------------------------
# Throttle — ~1 req/s with jitter across ALL NSE traffic (warm-ups included).
# ---------------------------------------------------------------------------


class _Throttle:
    """Thread-safe minimum-interval pacer with jitter.

    Each :meth:`wait` blocks until at least ``min_interval`` (+ a fresh random
    jitter in ``[0, jitter]``) has elapsed since the previous waited call —
    polite, non-bursty pacing that does not look metronomic to the edge.
    ``sleep``/``clock`` are injectable for tests (no real sleeping in pytest).
    """

    def __init__(
        self,
        min_interval: float = 1.0,
        jitter: float = 0.4,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._min_interval = min_interval
        self._jitter = jitter
        self._sleep = sleep
        self._clock = clock
        self._next_at = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            if now < self._next_at:
                self._sleep(self._next_at - now)
                now = self._next_at
            self._next_at = now + self._min_interval + random.uniform(0.0, self._jitter)


# ---------------------------------------------------------------------------
# Circuit breaker — per path, so a poisoned path can't take down healthy ones.
# ---------------------------------------------------------------------------


class _CircuitBreaker:
    """Open after ``threshold`` consecutive post-rotation blocks; fail fast
    until ``cooldown`` elapses, then allow a fresh attempt (half-open)."""

    def __init__(
        self,
        threshold: int = _BREAKER_THRESHOLD,
        cooldown: float = _BREAKER_COOLDOWN_SECS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._threshold = threshold
        self._cooldown = cooldown
        self._clock = clock
        self._blocks = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    def seconds_remaining(self) -> float:
        """Seconds of cooldown left while open; ``0.0`` when calls may proceed."""
        with self._lock:
            if self._opened_at is None:
                return 0.0
            elapsed = self._clock() - self._opened_at
            if elapsed >= self._cooldown:
                # Half-open: allow the next attempt; a block re-opens immediately.
                self._opened_at = None
                self._blocks = self._threshold - 1
                return 0.0
            return self._cooldown - elapsed

    def record_block(self) -> None:
        with self._lock:
            self._blocks += 1
            if self._blocks >= self._threshold:
                self._opened_at = self._clock()

    def record_ok(self) -> None:
        with self._lock:
            self._blocks = 0
            self._opened_at = None


# ---------------------------------------------------------------------------
# The cookie-dance session (warm-up, rotation) + the JSON seam.
# ---------------------------------------------------------------------------


def _new_session():  # noqa: ANN202 - curl_cffi session; seam monkeypatched in tests
    """Build a fresh Chrome-impersonated curl_cffi session (the test seam)."""
    from curl_cffi import requests as curl_requests

    return curl_requests.Session(impersonate="chrome")


class _SessionHolder:
    """Owns the live session; warms a fresh one lazily and rotates on demand."""

    def __init__(self) -> None:
        self._session = None

    def ensure(self):  # noqa: ANN202 - curl_cffi session
        if self._session is None:
            session = _new_session()
            _throttle.wait()
            try:
                resp = session.get(_BASE + "/", timeout=_TIMEOUT)
            except Exception as exc:
                raise ProviderError(f"nse_direct: cookie warm-up failed: {exc}") from exc
            if resp.status_code in (401, 403):
                raise ProviderError(f"nse_direct: cookie warm-up blocked (HTTP {resp.status_code})")
            self._session = session
        return self._session

    def rotate(self) -> None:
        if self._session is not None:
            try:
                self._session.close()
            except Exception:  # noqa: BLE001 - best-effort close
                pass
            self._session = None


_throttle = _Throttle()
_holder = _SessionHolder()
_breakers: dict[str, _CircuitBreaker] = {}
_lock = threading.Lock()


def _breaker_for(path: str) -> _CircuitBreaker:
    with _lock:
        breaker = _breakers.get(path)
        if breaker is None:
            breaker = _CircuitBreaker()
            _breakers[path] = breaker
        return breaker


def reset_for_tests() -> None:
    """Discard the session, breakers, and throttle pacing (test isolation)."""
    global _throttle
    _holder.rotate()
    _breakers.clear()
    _throttle = _Throttle()


def _get_json(path: str, params: dict[str, str], referer: str) -> object:
    """One throttled, cookie-danced GET returning parsed JSON.

    The full anti-bot ladder: circuit check → warm session → throttled GET →
    on 401/403 rotate the session and retry ONCE → a second block records into
    the path's breaker and raises. Any other non-200 / non-JSON body raises a
    plain :class:`ProviderError` (not a block — the breaker only counts
    bot-blocks). Serialized by the module lock (threaded registry callers).
    """
    breaker = _breaker_for(path)
    remaining = breaker.seconds_remaining()
    if remaining > 0:
        raise ProviderError(
            f"nse_direct: circuit open for {path} after repeated blocks "
            f"({remaining:.0f}s cooldown remaining)"
        )
    headers = dict(_API_HEADERS, Referer=referer)
    with _lock:
        last_status = 0
        for attempt in (0, 1):
            session = _holder.ensure()
            _throttle.wait()
            try:
                resp = session.get(_BASE + path, params=params, headers=headers, timeout=_TIMEOUT)
            except Exception as exc:
                raise ProviderError(f"nse_direct: transport failure on {path}: {exc}") from exc
            last_status = resp.status_code
            if resp.status_code in (401, 403):
                _holder.rotate()  # cookie set is burned — dance again
                if attempt == 0:
                    logger.debug(
                        "nse_direct: HTTP %s on %s — rotating session", resp.status_code, path
                    )
                    continue
                break
            if resp.status_code != 200:
                raise ProviderError(f"nse_direct: HTTP {resp.status_code} for {path}")
            try:
                payload = resp.json()
            except Exception as exc:
                raise ProviderError(f"nse_direct: non-JSON body from {path}: {exc}") from exc
            breaker.record_ok()
            return payload
        breaker.record_block()
        raise ProviderError(
            f"nse_direct: blocked (HTTP {last_status}) on {path} after session rotation"
        )


def _quote_referer(symbol: str) -> str:
    return f"{_BASE}/get-quotes/equity?symbol={symbol}"


# ---------------------------------------------------------------------------
# Symbol gating + EOD labelling (mirror india_provider).
# ---------------------------------------------------------------------------


def _require_nse(symbol: str) -> str:
    """Return the bare NSE symbol, or raise so the registry falls through fast
    (no network for a non-NSE ticker)."""
    bare = locale.strip_exchange_suffix(symbol)
    if not symbol_resolver.is_nse_symbol(bare):
        raise ProviderError(f"nse_direct: {symbol!r} is not a known NSE instrument")
    return bare


def _bar_timestamp(trading_day: date) -> datetime:
    """Daily bar at UTC midnight of its IST trading date (the project-wide
    by-date convention; ``CH_TIMESTAMP`` is already the IST trading date)."""
    return datetime(trading_day.year, trading_day.month, trading_day.day, tzinfo=UTC)


# ---------------------------------------------------------------------------
# History — api/historicalOR/cm/equity (observed shape).
# ---------------------------------------------------------------------------


def _fetch_historical_window(symbol: str, start: date, end: date) -> list[dict]:
    """One historicalOR window → the raw row dicts (may be empty)."""
    params = {
        "symbol": symbol,
        "series": '["EQ"]',
        "from": start.strftime("%d-%m-%Y"),
        "to": end.strftime("%d-%m-%Y"),
    }
    payload = _get_json(_HISTORICAL_PATH, params, _quote_referer(symbol))
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ProviderError(f"nse_direct: malformed historical payload for {symbol!r}")
    return [r for r in rows if isinstance(r, dict)]


def _rows_to_bars(rows: list[dict]) -> list[OHLCVBar]:
    """Observed row → bar. ``CH_TIMESTAMP`` is the IST trading date as
    ``YYYY-MM-DD``; rows arrive newest-first (the caller sorts + dedupes)."""
    bars: list[OHLCVBar] = []
    for row in rows:
        close = _num(row.get("CH_CLOSING_PRICE"))
        raw_day = row.get("CH_TIMESTAMP")
        if close is None or close <= 0 or not raw_day:
            continue
        try:
            trading_day = date.fromisoformat(str(raw_day))
        except ValueError:
            continue
        bars.append(
            OHLCVBar(
                timestamp=_bar_timestamp(trading_day),
                open=_num(row.get("CH_OPENING_PRICE")) or close,
                high=_num(row.get("CH_TRADE_HIGH_PRICE")) or close,
                low=_num(row.get("CH_TRADE_LOW_PRICE")) or close,
                close=close,
                volume=_num(row.get("CH_TOT_TRADED_QTY")) or 0.0,
            )
        )
    return bars


def _fetch_daily_bars(symbol: str, lookback_days: int) -> list[OHLCVBar]:
    """Daily bars over ``lookback_days``, assembled newest-window-first.

    Windows are bounded (:data:`_WINDOW_DAYS` × :data:`_MAX_WINDOWS`). The
    NEWEST window must succeed (its failure raises so the registry falls
    through); an OLDER window's failure truncates the series there instead —
    recent contiguous data beats an error, and never fabricates a gap.
    """
    today = datetime.now(tz=UTC).astimezone(locale.market_timezone(locale.REGION_IN)).date()
    start = today - timedelta(days=lookback_days)
    if lookback_days > _WINDOW_DAYS * _MAX_WINDOWS:
        raise ProviderError(
            f"nse_direct: range of {lookback_days}d exceeds the direct lane's "
            f"{_WINDOW_DAYS * _MAX_WINDOWS}d budget — serve wide ranges via jugaad"
        )
    bars: list[OHLCVBar] = []
    window_end = today
    first_window = True
    while window_end >= start:
        window_start = max(start, window_end - timedelta(days=_WINDOW_DAYS - 1))
        try:
            rows = _fetch_historical_window(symbol, window_start, window_end)
        except ProviderError:
            if first_window:
                raise
            logger.debug(
                "nse_direct: older window %s..%s failed for %s — truncating",
                window_start,
                window_end,
                symbol,
            )
            break
        bars.extend(_rows_to_bars(rows))
        first_window = False
        window_end = window_start - timedelta(days=1)
    # Ascending + dedupe by trading day (window edges can overlap a holiday).
    by_day: dict[datetime, OHLCVBar] = {b.timestamp: b for b in reversed(bars)}
    return [by_day[ts] for ts in sorted(by_day)]


def get_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
    """Return an EOD OHLCV series for an NSE instrument, exchange-direct.

    Daily for ``1d``; weekly/monthly resampled from daily. Intraday raises
    (keyless NSE is EOD-only — same honest contract as the jugaad lane).
    """
    if timeframe not in _EOD_TIMEFRAMES:
        raise ProviderError(
            f"nse_direct: intraday timeframe {timeframe!r} is not available keyless — "
            "add a BYOK broker (Angel One / Dhan) for NSE intraday"
        )
    bare = _require_nse(symbol)
    days = _RANGE_DAYS.get(range_ or "", _DEFAULT_RANGE_DAYS)
    daily = _fetch_daily_bars(bare, days)
    if not daily:
        raise ProviderError(f"nse_direct: no EOD data for {bare!r}")
    bars = _resample(daily, timeframe) if timeframe in {"1wk", "1mo"} else daily
    return OHLCVSeries(symbol=bare, timeframe=timeframe, bars=bars, provider=PROVIDER)


# ---------------------------------------------------------------------------
# Quote — api/quote-equity when served, historicalOR-derived EOD otherwise.
# ---------------------------------------------------------------------------


def get_quote(symbol: str) -> Quote:
    """Return the latest quote for an NSE instrument (INR).

    Primary: ``api/quote-equity`` (live-ish ``priceInfo``). The probe vantage
    observed this path Akamai-blocked while every other API path served — so a
    failure here is EXPECTED and falls back to an EOD quote derived from the
    last two ``historicalOR`` rows (close + official previous close), keeping
    the lane useful wherever the edge ACL bites.
    """
    bare = _require_nse(symbol)
    try:
        payload = _get_json(_QUOTE_PATH, {"symbol": bare}, _quote_referer(bare))
    except ProviderError as exc:
        logger.debug("nse_direct: quote-equity unavailable for %s (%s) — EOD fallback", bare, exc)
        payload = None
    if isinstance(payload, dict):
        quote = _quote_from_payload(bare, payload)
        if quote is not None:
            return quote
    return _quote_from_history(bare)


def _quote_from_payload(bare: str, payload: dict) -> Quote | None:
    """Defensive parse of the quote-equity ``priceInfo`` contract, or ``None``.

    The path was edge-blocked from the probe vantage so this shape could not be
    captured live; the parse trusts nothing — any missing/empty field returns
    ``None`` and the caller serves the OBSERVED historicalOR fallback instead.
    """
    price_info = payload.get("priceInfo")
    if not isinstance(price_info, dict):
        return None
    price = _num(price_info.get("lastPrice"))
    if price is None or price <= 0:
        return None
    prev = _num(price_info.get("previousClose"))
    change = _num(price_info.get("change"))
    if change is None:
        change = price - prev if prev else 0.0
    change_percent = _num(price_info.get("pChange"))
    if change_percent is None:
        change_percent = (change / prev * 100.0) if prev else 0.0
    trading_day = locale.most_recent_session(locale.REGION_IN)
    return Quote(
        symbol=bare,
        price=price,
        change=change,
        change_percent=change_percent,
        volume=None,
        currency="INR",
        market_state="REGULAR" if locale.is_market_open(locale.REGION_IN) else "CLOSED",
        timestamp=_bar_timestamp(trading_day),
        provider=PROVIDER,
    )


def _quote_from_history(bare: str) -> Quote:
    """EOD quote from the most recent historicalOR row (observed shape).

    Uses the row's official ``CH_PREVIOUS_CLS_PRICE`` for change/%, falling
    back to the prior row's close.
    """
    today = datetime.now(tz=UTC).astimezone(locale.market_timezone(locale.REGION_IN)).date()
    rows = _fetch_historical_window(bare, today - timedelta(days=14), today)
    rows = [r for r in rows if _num(r.get("CH_CLOSING_PRICE"))]
    if not rows:
        raise ProviderError(f"nse_direct: no EOD data for {bare!r}")
    rows.sort(key=lambda r: str(r.get("CH_TIMESTAMP") or ""))
    last = rows[-1]
    close = float(_num(last.get("CH_CLOSING_PRICE")) or 0.0)
    prev = _num(last.get("CH_PREVIOUS_CLS_PRICE"))
    if prev is None and len(rows) >= 2:
        prev = _num(rows[-2].get("CH_CLOSING_PRICE"))
    change = close - prev if prev else 0.0
    change_percent = (change / prev * 100.0) if prev else 0.0
    bars = _rows_to_bars([last])
    timestamp = bars[0].timestamp if bars else _bar_timestamp(today)
    return Quote(
        symbol=bare,
        price=close,
        change=change,
        change_percent=change_percent,
        volume=_num(last.get("CH_TOT_TRADED_QTY")),
        currency="INR",
        market_state="REGULAR" if locale.is_market_open(locale.REGION_IN) else "CLOSED",
        timestamp=timestamp,
        provider=PROVIDER,
    )


# ---------------------------------------------------------------------------
# Corporate disclosures — raw observed lists for Component 3 to model.
# ---------------------------------------------------------------------------


def _fetch_corporate_list(path: str, symbol: str) -> list[dict]:
    """Shared fetch for the three corporates endpoints (all bare JSON lists)."""
    bare = _require_nse(symbol)
    payload = _get_json(path, {"index": "equities", "symbol": bare}, _quote_referer(bare))
    if not isinstance(payload, list):
        raise ProviderError(f"nse_direct: malformed payload from {path} for {bare!r}")
    return [item for item in payload if isinstance(item, dict)]


def get_corporate_announcements(
    symbol: str, limit: int = _DEFAULT_ANNOUNCEMENT_LIMIT
) -> list[dict]:
    """Raw corporate announcements for ``symbol``, newest-first, trimmed.

    The endpoint returns the FULL history (observed: ~3,300 items / 2.8 MB for
    RELIANCE) already newest-first by ``sort_date``; we trim client-side.
    Observed item keys include ``an_dt``, ``attchmntFile``, ``attchmntText``,
    ``desc``, ``sm_isin``, ``sm_name``, ``sort_date``, ``symbol``.
    """
    return _fetch_corporate_list(_ANNOUNCEMENTS_PATH, symbol)[: max(limit, 0)]


def get_results_calendar(symbol: str) -> list[dict]:
    """Raw event-calendar rows for ``symbol`` (board meetings / results).

    Observed item shape: ``{symbol, company, purpose, bm_desc, date
    "DD-Mon-YYYY"}``.
    """
    return _fetch_corporate_list(_EVENT_CALENDAR_PATH, symbol)


def get_shareholding_master(symbol: str) -> list[dict]:
    """Raw quarterly shareholding-master rows for ``symbol``.

    Observed item shape carries the quarter (``date`` "31-MAR-2026"), the
    promoter+promoter-group percentage (``pr_and_prgrp``), the public
    percentage (``public_val``), ``submissionDate``, ``recordId`` and the
    ``xbrl`` archive URL. FII/DII splits live in the XBRL, not this master.
    """
    return _fetch_corporate_list(_SHAREHOLDING_PATH, symbol)


# ---------------------------------------------------------------------------
# Resample + numeric helpers (mirror india_provider).
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
    "get_corporate_announcements",
    "get_history",
    "get_quote",
    "get_results_calendar",
    "get_shareholding_master",
    "is_available",
    "reset_for_tests",
]
