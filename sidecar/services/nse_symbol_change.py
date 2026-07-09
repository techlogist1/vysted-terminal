"""NSE symbol-change lane — an OLD ticker resolves to the CURRENT one (R12, D66).

The R12 battery finding: NSE renamed Gujarat Gas Ltd to **Gujarat Energy
Limited** and changed its NSE symbol **GUJGASLTD → GUJENERGY effective
2026-07-01** (same ISIN — a rename, not a new entity). The bundled resolver
masters were generated 2026-06-11 and predate the change, so the app kept
resolving "Gujarat Gas" / GUJGASLTD to the stale identity with full confidence.
This module is the missing lane: it downloads NSE's official symbol-change
master, parses it into ``old → new`` hops, and lets the resolver answer the
current symbol with an explicit rename annotation instead of the stale one.

Endpoint (verified live from this machine, 2026-07-10 IST)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The official symbol-change master, on the host the project's LESSONS.md calls
the reliable one (nsearchives)::

    https://nsearchives.nseindia.com/content/equities/symbolchange.csv

A ~68 KB **header-less** CSV (~1,050 rows), four positional columns::

    <NEW COMPANY NAME>, <OLD SYMBOL>, <NEW SYMBOL>, <DD-MON-YYYY>

e.g. the finding's row (verbatim)::

    GUJARAT ENERGY LIMITED,GUJGASLTD,GUJENERGY,01-JUL-2026

The date is an uppercase-month ``DD-MON-YYYY`` (``01-JUL-2026``). Some rows are
self-maps (old == new — a name-only change carried here) and are dropped; a new
symbol can itself later become an old symbol (chained renames — the resolver
follows the chain to the terminal current symbol). A sibling company-rename file
(``.../equities/namechange.csv``, keyed by the CURRENT symbol with prev/new
NAME) exists too; this module uses symbolchange.csv, whose new-name column is
enough for the resolver's rename annotation.

Caching + as-of
~~~~~~~~~~~~~~~

The file is a single cumulative master (not per-day), so the "as-of" is the day
we last fetched it. Parsed hops are stored via :mod:`services.data_cache` under
``nse_symbol_change:YYYYMMDD`` (IST fetch day) — the same daily-as-of discipline
as :mod:`services.nse_bhavcopy` — so at most one download per day. A rename is
DURABLE (unlike an EOD price), so the TTL is generous (30 days) and, when a
download fails, the most recent cached as-of within that window is used: a cold
boot that already fetched once keeps answering renames offline.

Resolver seam (offline-first)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The resolver is synchronous and offline-first, so it reads an in-process map
(:data:`_active_map`) that :func:`fetch_latest` populates. A cold app with no
network and no prior cache leaves the map EMPTY — :func:`lookup_current` returns
``None`` and the resolver is an honest no-op (it answers exactly as it did
before this lane existed, never a fabricated rename). :func:`schedule_refresh`
is a cheap, once-per-day, fire-and-forget trigger the resolve router calls so
the lane self-activates without a network touch on the hot path.

Honesty rule
~~~~~~~~~~~~

A rename is applied only when its effective date has PASSED (``<= as_of``). A
future-dated change is not yet applied. The lane never invents a symbol: every
answer traces to a row in the official master.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

from services import data_cache

logger = logging.getLogger(__name__)

PROVIDER = "nse-symbol-change"

_URL = "https://nsearchives.nseindia.com/content/equities/symbolchange.csv"

_CACHE_KEY = "nse_symbol_change:{ymd}"
#: A rename is durable — a generous TTL lets a network-down boot reuse a recent
#: as-of, and bounds how far :func:`fetch_latest` walks back for a cached file.
_CACHE_TTL_SECONDS = 30 * 24 * 3600.0
_MAX_STALE_DAYS = 30

#: Guard against a pathological rename cycle in the master (A→B→A).
_MAX_CHAIN_HOPS = 8

#: IST is a fixed +05:30 (no DST) — a plain offset avoids a tzdata dependency.
_IST = timezone(timedelta(hours=5, minutes=30), "IST")

# nsearchives serves an empty/blocked payload to an obvious bot; a real desktop
# UA + the nseindia.com referer mirror the nse_bhavcopy discipline.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Referer": "https://www.nseindia.com/",
    "Accept": "text/csv, */*",
}
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MIN_REQUEST_INTERVAL_SECONDS = 0.75

#: Uppercase 3-letter month tokens the master uses (``01-JUL-2026``). A manual
#: map keeps the parse locale-independent (``%b`` is locale-sensitive).
_MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


@dataclass(frozen=True)
class SymbolChange:
    """One ``old → new`` symbol-change row from the master."""

    old_symbol: str
    new_symbol: str
    effective_date: date | None
    new_name: str | None


@dataclass(frozen=True)
class AppliedRename:
    """The terminal current identity for a queried OLD symbol (chain followed)."""

    renamed_from: str  # the bare OLD symbol the caller asked about
    renamed_to: str  # the current symbol after every applicable hop
    effective_date: date  # when the caller's symbol was retired (first hop)
    new_name: str | None  # the terminal hop's company name, when the master has it


# ---------------------------------------------------------------------------
# Shared client + throttle (reset_for_tests installs a mock transport).
# ---------------------------------------------------------------------------

_client: httpx.AsyncClient | None = None
_transport: httpx.BaseTransport | None = None
_throttle_lock: asyncio.Lock = asyncio.Lock()
_last_request_at: float = 0.0

# In-process rename map the (synchronous, offline) resolver reads. Populated by
# fetch_latest; empty by default so a cold app is an honest no-op.
_active_map: dict[str, SymbolChange] = {}
_refreshed_on: date | None = None
_refresh_task: asyncio.Task[None] | None = None


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
            logger.debug("nse_symbol_change: client aclose raised: %s", exc)
        _client = None


def reset_for_tests(transport: httpx.BaseTransport | None = None) -> None:
    """Drop the shared client + in-process map so a test starts cold.

    Mirrors ``nse_bhavcopy.reset_for_tests``: an optional ``httpx.MockTransport``
    makes every request deterministic — no unit test touches the live network.
    """
    global _client, _transport, _last_request_at, _throttle_lock
    global _active_map, _refreshed_on, _refresh_task
    _client = None
    _transport = transport
    _last_request_at = 0.0
    # asyncio.Lock binds to the loop that first awaits it; each test runs its own
    # loop, so a cold start needs a fresh lock too.
    _throttle_lock = asyncio.Lock()
    _active_map = {}
    _refreshed_on = None
    _refresh_task = None


def set_active_map_for_tests(mapping: dict[str, SymbolChange]) -> None:
    """Inject a rename map directly (the resolver-integration test seam)."""
    global _active_map
    _active_map = {k.strip().upper(): v for k, v in mapping.items()}


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
# Parsing — header-less 4-column CSV → {OLD_SYMBOL: SymbolChange}.
# ---------------------------------------------------------------------------


def _parse_date(text: str) -> date | None:
    """Parse a ``DD-MON-YYYY`` cell (``01-JUL-2026``) to a date, or ``None``."""
    parts = str(text).strip().split("-")
    if len(parts) != 3:
        return None
    day_s, mon_s, year_s = parts
    month = _MONTHS.get(mon_s.strip().upper())
    if month is None:
        return None
    try:
        return date(int(year_s), month, int(day_s))
    except ValueError:
        return None


def parse_symbol_change(text: str) -> dict[str, SymbolChange]:
    """Parse the symbol-change CSV body into ``{OLD_SYMBOL: SymbolChange}``.

    Header-less, four positional columns (new name, old symbol, new symbol,
    effective date). Self-maps (old == new — a name-only change) and rows
    missing an old/new symbol are dropped. On a duplicate old symbol the last
    row wins. A garbage/blocked body yields ``{}``.
    """
    out: dict[str, SymbolChange] = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 4:
            continue
        new_name = row[0].strip()
        old_symbol = row[1].strip().upper()
        new_symbol = row[2].strip().upper()
        if not old_symbol or not new_symbol or old_symbol == new_symbol:
            continue
        out[old_symbol] = SymbolChange(
            old_symbol=old_symbol,
            new_symbol=new_symbol,
            effective_date=_parse_date(row[3]),
            new_name=new_name or None,
        )
    return out


# ---------------------------------------------------------------------------
# Cache shape — compact JSON-serialisable hops (mirrors nse_bhavcopy).
# ---------------------------------------------------------------------------


def _cache_key(day: date) -> str:
    return _CACHE_KEY.format(ymd=day.strftime("%Y%m%d"))


def _changes_to_cache(changes: dict[str, SymbolChange]) -> dict[str, object]:
    return {
        "changes": {
            old: [
                c.new_symbol,
                c.effective_date.isoformat() if c.effective_date else None,
                c.new_name,
            ]
            for old, c in changes.items()
        }
    }


def _changes_from_cache(payload: object) -> dict[str, SymbolChange] | None:
    """Rebuild the map from a cache payload; ``None`` for a malformed value."""
    if not isinstance(payload, dict) or "changes" not in payload:
        return None
    out: dict[str, SymbolChange] = {}
    try:
        for old, packed in payload["changes"].items():
            new_symbol, eff_iso, new_name = packed
            out[str(old)] = SymbolChange(
                old_symbol=str(old),
                new_symbol=str(new_symbol),
                effective_date=date.fromisoformat(eff_iso) if eff_iso else None,
                new_name=None if new_name is None else str(new_name),
            )
    except (TypeError, ValueError, AttributeError):
        logger.warning("nse_symbol_change: malformed cache payload — treating as miss")
        return None
    return out


# ---------------------------------------------------------------------------
# Synchronous lookup (the resolver's offline seam) — chain-following.
# ---------------------------------------------------------------------------


def _ist_today() -> date:
    """Today's IST calendar date (the test seam for deterministic gating)."""
    return datetime.now(tz=_IST).date()


def lookup_current(symbol: str, as_of: date | None = None) -> AppliedRename | None:
    """Resolve an OLD ``symbol`` to its current identity, or ``None``.

    Reads the in-process :data:`_active_map` only (no network, no I/O) so the
    resolver stays synchronous and offline-first. Follows a chain of renames to
    the terminal current symbol, applying only hops whose effective date has
    PASSED (``<= as_of``, default IST today); a cycle or an unparsed date stops
    the walk. An empty map (cold app / no data) returns ``None`` — an honest
    no-op. Returns ``None`` when ``symbol`` is not a retired old symbol.
    """
    if as_of is None:
        as_of = _ist_today()
    current = symbol.strip().upper()
    if not current or not _active_map:
        return None
    visited = {current}
    first_effective: date | None = None
    terminal_symbol: str | None = None
    terminal_name: str | None = None
    for _ in range(_MAX_CHAIN_HOPS):
        change = _active_map.get(current)
        if change is None:
            break
        next_symbol = change.new_symbol.strip().upper()
        if next_symbol == current or next_symbol in visited:
            break  # self-map / cycle — terminal
        if change.effective_date is None or change.effective_date > as_of:
            break  # not yet effective (or undated) — do not apply
        if first_effective is None:
            first_effective = change.effective_date
        terminal_symbol = change.new_symbol
        terminal_name = change.new_name
        visited.add(next_symbol)
        current = next_symbol
    if terminal_symbol is None or first_effective is None:
        return None
    return AppliedRename(
        renamed_from=symbol.strip().upper(),
        renamed_to=terminal_symbol,
        effective_date=first_effective,
        new_name=terminal_name,
    )


# ---------------------------------------------------------------------------
# Fetch — one download per day, cached; hydrates the in-process map.
# ---------------------------------------------------------------------------


def _set_active_map(changes: dict[str, SymbolChange]) -> None:
    global _active_map
    _active_map = changes


async def _download_and_parse() -> dict[str, SymbolChange] | None:
    """Download + parse the master once; ``None`` on any failure/blocked body."""
    try:
        resp = await _throttled_get(_URL)
    except httpx.HTTPError as exc:
        logger.warning("nse_symbol_change: request failed (%s)", exc)
        return None
    if resp.status_code != 200:
        logger.warning("nse_symbol_change: HTTP %s from %s", resp.status_code, resp.url)
        return None
    changes = parse_symbol_change(resp.text)
    if not changes:
        logger.warning("nse_symbol_change: master parsed to zero rows — treating as a miss")
        return None
    return changes


async def fetch_latest(max_stale_days: int = _MAX_STALE_DAYS) -> dict[str, SymbolChange] | None:
    """Return the parsed symbol-change map and hydrate the resolver's map.

    Order: today's cache (no network) → download today (cache under today's key)
    → the most recent cached as-of within ``max_stale_days`` (network-down
    fallback — a rename is durable). Returns ``None`` and leaves the in-process
    map untouched when nothing is available (a cold app with no network stays an
    honest no-op). Never raises for a network/parse failure — it degrades.
    """
    today = _ist_today()

    cached = await data_cache.get(_cache_key(today), _CACHE_TTL_SECONDS)
    changes = _changes_from_cache(cached)
    if changes is not None:
        _set_active_map(changes)
        return changes

    changes = await _download_and_parse()
    if changes is not None:
        await data_cache.set(_cache_key(today), _changes_to_cache(changes))
        _set_active_map(changes)
        return changes

    for offset in range(1, max_stale_days + 1):
        day = today - timedelta(days=offset)
        cached = await data_cache.get(_cache_key(day), _CACHE_TTL_SECONDS)
        changes = _changes_from_cache(cached)
        if changes is not None:
            logger.info("nse_symbol_change: network down — serving cached as-of %s", day)
            _set_active_map(changes)
            return changes

    logger.warning("nse_symbol_change: no file and no recent cache — rename lane is a no-op")
    return None


async def _refresh_guarded() -> None:
    global _refreshed_on
    try:
        await fetch_latest()
    except Exception as exc:  # noqa: BLE001 - a refresh failure must never surface
        logger.debug("nse_symbol_change: background refresh failed: %s", exc)
    finally:
        _refreshed_on = _ist_today()


async def schedule_refresh() -> None:
    """Fire a once-per-day, non-blocking background refresh of the rename map.

    Cheap and safe to call on every resolve: it returns immediately (no network
    on the hot path). It spawns at most one refresh per IST day, and never while
    a prior refresh is still in flight. For immediate + periodic freshness across
    the agent/search resolve paths too, the app lifespan should also drive
    :func:`fetch_latest` (see the module docstring).
    """
    global _refresh_task
    if _refreshed_on == _ist_today():
        return
    if _refresh_task is not None and not _refresh_task.done():
        return
    _refresh_task = asyncio.create_task(_refresh_guarded())


__all__ = [
    "PROVIDER",
    "AppliedRename",
    "SymbolChange",
    "aclose",
    "fetch_latest",
    "lookup_current",
    "parse_symbol_change",
    "reset_for_tests",
    "schedule_refresh",
    "set_active_map_for_tests",
]
