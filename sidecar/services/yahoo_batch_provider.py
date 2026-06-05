"""Yahoo v7 batch quote provider — the screener's fast path (FR-126 / SC-034).

The per-symbol ``yfinance`` ``.info`` / ``.fast_info`` scrape is the screener
bottleneck: a full S&P 500 run fans out ~1000 individual HTTP round-trips
(fundamentals + quote per symbol), tripping Yahoo rate-limiting so a large
fraction of the universe silently drops and the cold run takes ~205 s.

This module replaces that fan-out for the curated equity universes with Yahoo's
``/v7/finance/quote`` BATCH endpoint: up to 50 symbols per request, so the 506
S&P 500 symbols collapse into ~11 calls. One shared :class:`httpx.AsyncClient`,
an ``asyncio.Semaphore(8)`` cap, ``asyncio.gather(return_exceptions=True)`` so a
single chunk failure never aborts the batch, a 15 s read timeout, and a
realistic User-Agent.

Cookie + crumb
~~~~~~~~~~~~~~

The v7 endpoint requires a session cookie and a matching CSRF "crumb". We
bootstrap both once (GET a Yahoo page to seed the cookie jar, then GET
``/v1/test/getcrumb`` with that cookie) and reuse them for the lifetime of the
process; a 401/403/"Invalid Crumb" response invalidates the cached crumb so the
chunk re-bootstraps and retries ONCE. The bootstrap is lock-guarded so a
concurrent fan-out mints a SINGLE crumb, not eight. Best-effort: if it fails we
still try the request without a crumb (Yahoo serves some regions cookieless),
and a total failure surfaces as a per-symbol skip reason, never a crash.

Field coverage
~~~~~~~~~~~~~~

v7 covers the COMMON screener criteria on the fast path — price, market cap,
P/E (trailing + forward), price/book, dividend yield, 52-week high/low, 52-week
change, EPS, book value, volume, currency, change%, name. It does NOT carry
sector, industry, PEG, beta, the profitability / health / growth / ownership
ratios, or price-to-sales / EV-EBITDA — those still need the per-symbol
``.info`` enrichment, but ONLY when a screen's criteria actually reference such
a field (see :func:`field_needs_enrichment`).

Pure ``httpx`` — no new dependency (the ``--onefile`` binary must still
build + boot; only the lead verifies that, so this stays on the existing
``httpx`` already shipped).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from models.fundamentals import Fundamentals
from models.market import Quote

logger = logging.getLogger(__name__)

PROVIDER = "yahoo-v7-batch"

#: Yahoo caps the v7 batch endpoint around 50 symbols per request before it
#: starts truncating / 400-ing; 50 keeps the 506-symbol S&P 500 at ~11 calls.
_CHUNK_SIZE = 50

#: Live concurrency cap on the batch chunk fan-out (spec §5.4). Eight in-flight
#: chunks saturate the wire without tripping Yahoo's per-IP throttle.
_BATCH_CONCURRENCY = 8

#: Read timeout per chunk request. A slow chunk fails fast and is itemized as a
#: skip rather than stalling the whole screen (the old 30 s per-symbol timeout
#: serialised into minutes).
_READ_TIMEOUT_SECONDS = 15.0
_CONNECT_TIMEOUT_SECONDS = 10.0

#: A real desktop UA — Yahoo serves an empty / non-ok payload to obvious bots.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
_CRUMB_URL = "https://query2.finance.yahoo.com/v1/test/getcrumb"
_COOKIE_BOOTSTRAP_URL = "https://fc.yahoo.com"
_COOKIE_BOOTSTRAP_FALLBACK = "https://finance.yahoo.com"


# ---------------------------------------------------------------------------
# Cookie + crumb session — bootstrapped once, reused, refreshed on rejection.
# ---------------------------------------------------------------------------


class _Session:
    """Process-lifetime cookie jar + crumb, guarded by an asyncio lock.

    A single shared :class:`httpx.AsyncClient` owns the cookie jar so the crumb
    stays paired with the cookie that minted it. ``crumb`` is ``None`` until the
    first successful bootstrap; :meth:`invalidate` drops it so a rejected request
    re-bootstraps on the next call. The lock serialises the bootstrap so a
    concurrent batch fans out a SINGLE crumb mint, not eight.
    """

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._client: httpx.AsyncClient | None = None
        self._transport = transport
        self.crumb: str | None = None
        self._lock = asyncio.Lock()

    async def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(
                    _READ_TIMEOUT_SECONDS,
                    connect=_CONNECT_TIMEOUT_SECONDS,
                ),
                headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
                transport=self._transport,
            )
        return self._client

    async def ensure_crumb(self) -> str | None:
        """Return a usable crumb, bootstrapping the cookie+crumb if needed.

        Best-effort: a bootstrap failure logs + returns ``None`` (the caller
        still attempts the request — some regions serve cookieless), never
        raises. Serialised behind the lock so a concurrent batch fans out a
        SINGLE bootstrap, not eight."""
        if self.crumb is not None:
            return self.crumb
        async with self._lock:
            if self.crumb is not None:  # someone bootstrapped while we waited
                return self.crumb
            client = await self.client()
            # 1) Seed the cookie jar. fc.yahoo.com reliably sets the consent
            #    cookie the crumb endpoint requires; finance.yahoo.com is the
            #    fallback when fc is unreachable.
            for url in (_COOKIE_BOOTSTRAP_URL, _COOKIE_BOOTSTRAP_FALLBACK):
                try:
                    await client.get(url)
                    if client.cookies:
                        break
                except httpx.HTTPError as exc:
                    logger.debug("yahoo batch: cookie bootstrap %s failed: %s", url, exc)
            # 2) Mint the crumb against the now-seeded cookie jar.
            try:
                resp = await client.get(_CRUMB_URL)
                if resp.status_code == 200:
                    crumb = resp.text.strip()
                    # A valid crumb is a short opaque token; an HTML/empty body
                    # means the cookie didn't take — leave crumb None.
                    if crumb and "<" not in crumb and len(crumb) < 64:
                        self.crumb = crumb
            except httpx.HTTPError as exc:
                logger.debug("yahoo batch: crumb fetch failed: %s", exc)
            return self.crumb

    def invalidate(self) -> None:
        """Drop the cached crumb so the next call re-bootstraps (post-401/403)."""
        self.crumb = None

    async def aclose(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception as exc:  # noqa: BLE001 — shutdown best-effort
                logger.debug("yahoo batch: client aclose raised: %s", exc)
            self._client = None
            self.crumb = None


_session = _Session()


async def aclose() -> None:
    """Close the shared client (lifespan shutdown — avoid a leaked socket)."""
    await _session.aclose()


def reset_for_tests(transport: httpx.BaseTransport | None = None) -> None:
    """Drop the cached session (crumb + client) so a test starts cold.

    An optional ``transport`` (e.g. ``httpx.MockTransport``) is installed on the
    fresh session so a test can mock the v7 endpoint deterministically without a
    real network round-trip."""
    global _session
    _session = _Session(transport=transport)


def _chunk(symbols: list[str], size: int = _CHUNK_SIZE) -> list[list[str]]:
    return [symbols[i : i + size] for i in range(0, len(symbols), size)]


async def _fetch_chunk(
    chunk: list[str],
    sem: asyncio.Semaphore,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Fetch one ≤50-symbol chunk; return (results_by_symbol, failures_by_symbol).

    A ``failures`` reason is one of the skip-ledger vocabulary
    (``timeout`` / ``rate_limited`` / ``no_data`` / ``not_found``). On a crumb
    rejection (401/403/Invalid Crumb) the crumb is invalidated and the chunk is
    retried once with a fresh crumb."""
    results: dict[str, dict[str, Any]] = {}
    failures: dict[str, str] = {}

    async with sem:
        client = await _session.client()
        attempted_refresh = False
        while True:
            crumb = await _session.ensure_crumb()
            params: dict[str, str] = {"symbols": ",".join(chunk)}
            if crumb:
                params["crumb"] = crumb
            try:
                resp = await client.get(_QUOTE_URL, params=params)
            except httpx.TimeoutException:
                for sym in chunk:
                    failures[sym] = "timeout"
                return results, failures
            except httpx.HTTPError as exc:
                logger.debug("yahoo batch: chunk request failed: %s", exc)
                for sym in chunk:
                    failures[sym] = "no_data"
                return results, failures

            if resp.status_code in (401, 403) and not attempted_refresh:
                _session.invalidate()
                attempted_refresh = True
                continue
            if resp.status_code == 429:
                for sym in chunk:
                    failures[sym] = "rate_limited"
                return results, failures
            if resp.status_code != 200:
                reason = "not_found" if resp.status_code == 404 else "no_data"
                for sym in chunk:
                    failures[sym] = reason
                return results, failures

            try:
                payload = resp.json()
            except ValueError:
                for sym in chunk:
                    failures[sym] = "no_data"
                return results, failures

            quote_response = payload.get("quoteResponse") or {}
            error = quote_response.get("error")
            if error and not attempted_refresh and "crumb" in str(error).lower():
                _session.invalidate()
                attempted_refresh = True
                continue
            rows = quote_response.get("result") or []
            for row in rows:
                sym = str(row.get("symbol", "")).upper()
                if sym:
                    results[sym] = row
            # Any requested symbol Yahoo did not return is itemized as not_found.
            returned = set(results)
            for sym in chunk:
                if sym.upper() not in returned:
                    failures.setdefault(sym, "not_found")
            return results, failures


async def fetch_quotes_batch(
    symbols: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Batch-fetch raw v7 quote rows for ``symbols`` (chunked, concurrent).

    Returns ``(rows_by_upper_symbol, failures_by_input_symbol)``. ``failures``
    maps each unreturned input symbol to a skip-ledger reason. Never raises:
    every per-chunk error is captured as a failure reason so the screener can
    itemize it (SC-034 — zero silent drops). A total wipeout (every chunk fails)
    leaves ``rows`` empty so the caller can degrade to the per-symbol path."""
    cleaned = [s.strip() for s in symbols if s and s.strip()]
    if not cleaned:
        return {}, {}
    chunks = _chunk(cleaned)
    sem = asyncio.Semaphore(_BATCH_CONCURRENCY)
    chunk_results = await asyncio.gather(
        *(_fetch_chunk(chunk, sem) for chunk in chunks),
        return_exceptions=True,
    )
    rows: dict[str, dict[str, Any]] = {}
    failures: dict[str, str] = {}
    for idx, item in enumerate(chunk_results):
        if isinstance(item, BaseException):
            # An unexpected exception escaping a chunk — itemize its symbols.
            logger.warning("yahoo batch: chunk %d raised: %s", idx, item)
            for sym in chunks[idx]:
                failures.setdefault(sym, "no_data")
            continue
        chunk_rows, chunk_failures = item
        rows.update(chunk_rows)
        for sym, reason in chunk_failures.items():
            failures.setdefault(sym, reason)
    # A symbol that appears in BOTH (returned in one form, requested in another)
    # is a success — drop it from failures.
    for sym in list(failures):
        if sym.upper() in rows:
            failures.pop(sym, None)
    return rows, failures


# ---------------------------------------------------------------------------
# Field mapping — v7 row → (Quote, Fundamentals).
# ---------------------------------------------------------------------------


def _num(value: Any) -> float | None:
    """Coerce a v7 numeric (may be missing / a dict on some fields) to float."""
    if value is None or isinstance(value, (dict, list, str, bool)):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    # Guard against NaN / inf leaking into the criteria comparators.
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _normalize_dividend_yield(row: dict[str, Any]) -> float | None:
    """Resolve a fractional dividend yield (0.012 = 1.2%) from a v7 row.

    v7 exposes ``trailingAnnualDividendYield`` already as a FRACTION (0.0044 for
    AAPL) — preferred. ``dividendYield`` on v7 is a PERCENT number (0.44), so it
    is divided by 100 as a fallback. Mirrors the guard in
    ``yfinance_provider.get_fundamentals`` (reject absurd > 200%)."""
    frac = _num(row.get("trailingAnnualDividendYield"))
    if frac is None:
        pct = _num(row.get("dividendYield"))
        frac = (pct / 100.0) if pct is not None else None
    if frac is None:
        return None
    return frac if 0.0 <= frac <= 2.0 else None


def _normalize_fifty_two_week_change(row: dict[str, Any]) -> float | None:
    """Resolve the fractional 52-week change (0.21 = 21%) from a v7 row.

    v7's ``fiftyTwoWeekChangePercent`` is a PERCENT number (e.g. 21.4 for +21.4%);
    the ``Fundamentals.fifty_two_week_change`` contract is a FRACTION (the panel
    ×100s it), matching ``yfinance``'s ``52WeekChange`` which is already a
    fraction. Divide by 100 to land on the fraction."""
    pct = _num(row.get("fiftyTwoWeekChangePercent"))
    if pct is None:
        return None
    return pct / 100.0


def quote_from_v7(row: dict[str, Any]) -> Quote | None:
    """Build a :class:`Quote` from a v7 quote row, or ``None`` if priceless.

    A row without a usable ``regularMarketPrice`` is dropped (the correctness
    invariant: never present a fabricated price); the caller itemizes it as
    ``no_data``."""
    symbol = str(row.get("symbol", "")).upper()
    price = _num(row.get("regularMarketPrice"))
    if not symbol or price is None or price <= 0:
        return None
    change = _num(row.get("regularMarketChange")) or 0.0
    change_percent = _num(row.get("regularMarketChangePercent")) or 0.0
    volume = _num(row.get("regularMarketVolume"))
    currency = str(row.get("currency") or "USD")
    ts_epoch = row.get("regularMarketTime")
    try:
        timestamp = (
            datetime.fromtimestamp(int(ts_epoch), tz=UTC) if ts_epoch else datetime.now(tz=UTC)
        )
    except (TypeError, ValueError, OSError):
        timestamp = datetime.now(tz=UTC)
    return Quote(
        symbol=symbol,
        price=price,
        change=change,
        change_percent=change_percent,
        volume=volume,
        currency=currency,
        market_state=row.get("marketState"),
        timestamp=timestamp,
        provider=PROVIDER,
    )


def fundamentals_from_v7(row: dict[str, Any]) -> Fundamentals:
    """Build a :class:`Fundamentals` from a v7 quote row (the fields v7 carries).

    Populates ONLY the fields the v7 quote row actually carries — valuation
    ratios (market cap, trailing/forward P/E, price/book, book value), EPS, the
    52-week range + change, dividend yield, currency, name. Everything v7 omits
    (``sector``/``industry``/``peg_ratio``/``beta``/``price_to_sales``/
    ``ev_to_ebitda``/profitability/health/growth/ownership) is left ``None`` —
    a screen that filters on one of those triggers per-symbol ``.info``
    enrichment (or itemizes the symbol ``missing_field:<field>``)."""
    symbol = str(row.get("symbol", "")).upper()
    return Fundamentals(
        symbol=symbol,
        name=row.get("longName") or row.get("shortName"),
        currency=str(row["currency"]) if row.get("currency") else None,
        # Valuation (v7-covered)
        market_cap=_num(row.get("marketCap")),
        pe_ratio=_num(row.get("trailingPE")),
        forward_pe=_num(row.get("forwardPE")),
        price_to_book=_num(row.get("priceToBook")),
        book_value=_num(row.get("bookValue")),
        dividend_yield=_normalize_dividend_yield(row),
        eps=_num(row.get("epsTrailingTwelveMonths")),
        fifty_two_week_high=_num(row.get("fiftyTwoWeekHigh")),
        fifty_two_week_low=_num(row.get("fiftyTwoWeekLow")),
        fifty_two_week_change=_normalize_fifty_two_week_change(row),
        provider=PROVIDER,
    )


#: Screener criteria fields the v7 batch row CANNOT supply — a screen filtering
#: on any of these needs the per-symbol ``.info`` enrichment for the field to be
#: present (else the symbol is itemized ``missing_field:<field>``). Everything
#: NOT in this set (price, market_cap, pe_ratio, forward_pe, price_to_book,
#: book_value, dividend_yield, eps, fifty_two_week_high/low/change, volume,
#: change_percent_1d, price, currency) is on the batch fast path.
_ENRICHMENT_FIELDS: frozenset[str] = frozenset(
    {
        # string profile — the v7 quote row carries neither
        "sector",
        "industry",
        # valuation v7 omits
        "peg_ratio",
        "price_to_sales",
        "ev_to_ebitda",
        "beta",
        # profitability (fractions) — none on the v7 quote row
        "roe",
        "roa",
        "gross_margin",
        "operating_margin",
        "profit_margin",
        # financial health
        "debt_to_equity",
        "current_ratio",
        "quick_ratio",
        # growth (fractions)
        "revenue_growth",
        "earnings_growth",
        # ownership (fractions)
        "held_percent_insiders",
        "held_percent_institutions",
    }
)


def field_needs_enrichment(field: str) -> bool:
    """True when ``field`` is NOT served by the v7 batch row.

    The screener consults this for each criterion field: a field outside the
    batch coverage forces per-symbol ``.info`` enrichment (or, if that fails,
    the symbol is itemized ``missing_field:<field>``)."""
    return field in _ENRICHMENT_FIELDS


def chunk_count(n: int) -> int:
    """Number of v7 batch calls a universe of ``n`` symbols costs (~11 for 506)."""
    if n <= 0:
        return 0
    return (n + _CHUNK_SIZE - 1) // _CHUNK_SIZE


__all__ = [
    "PROVIDER",
    "aclose",
    "chunk_count",
    "fetch_quotes_batch",
    "field_needs_enrichment",
    "fundamentals_from_v7",
    "quote_from_v7",
    "reset_for_tests",
]
