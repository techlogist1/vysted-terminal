"""Columnar SQLite fundamentals cache — the screener's data spine (R10, D40).

One row per symbol (quote form, e.g. ``RELIANCE.NS``) carrying identity,
sector/industry (+ ``sector_source``: ``"seed"`` build-time map / ``"bse"`` /
``"yfinance"``), the full screener numeric vocabulary, the live-quote columns,
and PER-TIER freshness stamps:

  - ``quote_updated_at`` — the v7 quote tier. TTL 600 s on the full-market
    universes (a 5k-symbol sweep cannot re-run per keystroke) / 45 s on the
    curated ones (the old screener quote tier).
  - ``v7_updated_at``    — the v7 valuation tier (market cap, P/E, …). TTL 6 h.
  - ``info_updated_at``  — the deep per-symbol ``.info`` tier (sector, ROE,
    margins, growth, …). TTL 7 d.

The DB lives at ``config.get_data_dir()/fundamentals_cache.db`` (precedent
``portfolio_db.py``); access is synchronous ``sqlite3`` serialized under a
module ``asyncio.Lock`` — every public function is async and lock-guarded, so
the event loop never sees a concurrent writer and a test points the store at a
``tmp_path`` via :func:`reset_for_tests`.

``prefilter`` is the prune phase's SQL translation. Its contract is SOUNDNESS:
pruning may only WIDEN, never narrow, the true match set — a symbol is removed
ONLY when a FRESH, NON-NULL stored value definitively fails an AND-ed cheap
criterion. NULL or stale values keep the symbol (the sweep may fill them).
"""

from __future__ import annotations

import asyncio
import contextlib
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config import get_data_dir
from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import (
    NumericBetweenCriterion,
    NumericThresholdCriterion,
    ScreenerCriterion,
    SetInCriterion,
    StringEqCriterion,
)

DB_FILENAME = "fundamentals_cache.db"

# --- Per-tier TTLs (D40) --------------------------------------------------------
#: Quote tier on the full-market universes (nse-all / bse-all / india-all).
TTL_QUOTE_FULL_SECONDS = 600.0
#: Quote tier on the curated universes — matches the old screener quote cache.
TTL_QUOTE_CURATED_SECONDS = 45.0
#: v7 valuation tier (market cap, P/E, 52-week, …).
TTL_V7_SECONDS = 6 * 60 * 60.0
#: Deep ``.info`` tier (sector, ROE, margins, growth, ownership, …).
TTL_INFO_SECONDS = 7 * 24 * 60 * 60.0

#: Numeric ``Fundamentals`` fields stored 1:1 as columns (the screener's full
#: numeric vocabulary minus the quote-derived trio, which rides ``quote_*``).
_NUMERIC_FIELDS: tuple[str, ...] = (
    "market_cap",
    "pe_ratio",
    "forward_pe",
    "peg_ratio",
    "price_to_book",
    "price_to_sales",
    "ev_to_ebitda",
    "book_value",
    "dividend_yield",
    "eps",
    "beta",
    "roe",
    "roa",
    "gross_margin",
    "operating_margin",
    "profit_margin",
    "debt_to_equity",
    "current_ratio",
    "quick_ratio",
    "revenue_growth",
    "earnings_growth",
    "fifty_two_week_high",
    "fifty_two_week_low",
    "fifty_two_week_change",
    "held_percent_insiders",
    "held_percent_institutions",
    "shares_outstanding",
)

#: The v7 batch tier's numeric coverage — exactly the fields
#: ``yahoo_batch_provider.fundamentals_from_v7`` populates. ``upsert_v7``
#: writes these; everything else is the ``.info`` tier.
_V7_NUMERIC_FIELDS: tuple[str, ...] = (
    "market_cap",
    "pe_ratio",
    "forward_pe",
    "price_to_book",
    "book_value",
    "dividend_yield",
    "eps",
    "fifty_two_week_high",
    "fifty_two_week_low",
    "fifty_two_week_change",
    "shares_outstanding",
)

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS fundamentals (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    exchange TEXT,
    isin TEXT,
    scrip_code TEXT,
    bse_group TEXT,
    sector TEXT,
    industry TEXT,
    sector_source TEXT,
    currency TEXT,
    {", ".join(f"{f} REAL" for f in _NUMERIC_FIELDS)},
    quote_price REAL,
    quote_change REAL,
    quote_change_percent REAL,
    quote_volume REAL,
    quote_currency TEXT,
    quote_market_state TEXT,
    quote_timestamp TEXT,
    quote_updated_at REAL,
    v7_updated_at REAL,
    info_updated_at REAL,
    provider TEXT
);
CREATE INDEX IF NOT EXISTS idx_fundamentals_sector ON fundamentals(sector);
CREATE INDEX IF NOT EXISTS idx_fundamentals_mcap ON fundamentals(market_cap DESC);
CREATE INDEX IF NOT EXISTS idx_fundamentals_info_at ON fundamentals(info_updated_at);
"""

_lock = asyncio.Lock()
_db_path_override: Path | None = None


def _db_path() -> str:
    if _db_path_override is not None:
        return str(_db_path_override)
    return str(get_data_dir() / DB_FILENAME)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def reset_for_tests(path: Path | str | None = None) -> None:
    """Point the store at ``path`` (a test ``tmp_path`` file) or back at the
    default data-dir location (``None``). Also re-arms the lock so an event
    loop torn down mid-test cannot leave it held."""
    global _db_path_override, _lock
    _db_path_override = Path(path) if path is not None else None
    _lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


async def seed_universe(rows: list[dict[str, Any]]) -> int:
    """Seed identity rows (symbol, name, exchange, isin, scrip_code, group,
    sector, industry_raw→industry, sector_source, shares_outstanding).

    INSERTs unknown symbols; for existing rows fills ONLY the identity /
    seed columns that are currently NULL — a seed never clobbers a fetched
    value (the build-time map is the floor, not the truth). Returns the number
    of rows touched."""
    if not rows:
        return 0

    def _work() -> int:
        with contextlib.closing(_connect()) as conn:
            touched = 0
            for row in rows:
                symbol = str(row.get("symbol") or "").strip().upper()
                if not symbol:
                    continue
                cur = conn.execute(
                    """
                    INSERT INTO fundamentals (
                        symbol, name, exchange, isin, scrip_code, bse_group,
                        sector, industry, sector_source, shares_outstanding
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        name = COALESCE(fundamentals.name, excluded.name),
                        exchange = COALESCE(fundamentals.exchange, excluded.exchange),
                        isin = COALESCE(fundamentals.isin, excluded.isin),
                        scrip_code = COALESCE(fundamentals.scrip_code, excluded.scrip_code),
                        bse_group = COALESCE(fundamentals.bse_group, excluded.bse_group),
                        sector = COALESCE(fundamentals.sector, excluded.sector),
                        industry = COALESCE(fundamentals.industry, excluded.industry),
                        sector_source = COALESCE(
                            fundamentals.sector_source, excluded.sector_source
                        ),
                        shares_outstanding = COALESCE(
                            fundamentals.shares_outstanding, excluded.shares_outstanding
                        )
                    """,
                    (
                        symbol,
                        row.get("name"),
                        row.get("exchange"),
                        row.get("isin"),
                        row.get("scrip_code"),
                        row.get("group"),
                        row.get("sector"),
                        row.get("industry"),
                        row.get("sector_source"),
                        row.get("shares_outstanding"),
                    ),
                )
                touched += cur.rowcount
            conn.commit()
            return touched

    async with _lock:
        return await asyncio.to_thread(_work)


def _quote_columns(quote: Quote | None) -> dict[str, Any]:
    if quote is None:
        return {}
    return {
        "quote_price": quote.price,
        "quote_change": quote.change,
        "quote_change_percent": quote.change_percent,
        "quote_volume": quote.volume,
        "quote_currency": quote.currency,
        "quote_market_state": quote.market_state,
        "quote_timestamp": quote.timestamp.isoformat() if quote.timestamp else None,
        "quote_updated_at": time.time(),
    }


async def upsert_v7(symbol: str, fundamentals: Fundamentals, quote: Quote | None) -> None:
    """Write one v7 batch row: the v7-tier numerics + the quote columns,
    stamping ``v7_updated_at`` (and ``quote_updated_at`` when a quote rode
    along). v7 carries no sector — sector columns are untouched."""
    cols: dict[str, Any] = {
        "name": fundamentals.name,
        "currency": fundamentals.currency,
        "provider": fundamentals.provider,
        "v7_updated_at": time.time(),
    }
    for field in _V7_NUMERIC_FIELDS:
        value = getattr(fundamentals, field, None)
        if value is not None:
            cols[field] = value
    cols.update(_quote_columns(quote))
    await _upsert(symbol, cols)


async def upsert_info(symbol: str, fundamentals: Fundamentals) -> None:
    """Write one deep ``.info`` enrichment row: the FULL numeric vocabulary +
    sector/industry (``sector_source`` becomes the provider — a live fetch
    outranks the build-time seed), stamping ``info_updated_at``. The registry
    ``.info`` fundamentals are a superset of the v7 tier, so ``v7_updated_at``
    is stamped too (the sweep can skip a freshly-info'd symbol)."""
    now = time.time()
    cols: dict[str, Any] = {
        "name": fundamentals.name,
        "currency": fundamentals.currency,
        "provider": fundamentals.provider,
        "info_updated_at": now,
        "v7_updated_at": now,
    }
    if fundamentals.sector is not None:
        cols["sector"] = fundamentals.sector
        cols["sector_source"] = fundamentals.provider or "yfinance"
    if fundamentals.industry is not None:
        cols["industry"] = fundamentals.industry
    for field in _NUMERIC_FIELDS:
        value = getattr(fundamentals, field, None)
        if value is not None:
            cols[field] = value
    await _upsert(symbol, cols)


async def _upsert(symbol: str, cols: dict[str, Any]) -> None:
    key = symbol.strip().upper()
    if not key or not cols:
        return
    names = list(cols)
    assignments = ", ".join(f"{c} = excluded.{c}" for c in names)
    sql = (
        f"INSERT INTO fundamentals (symbol, {', '.join(names)}) "
        f"VALUES (?, {', '.join('?' for _ in names)}) "
        f"ON CONFLICT(symbol) DO UPDATE SET {assignments}"
    )
    values = [key, *[cols[c] for c in names]]

    def _work() -> None:
        with contextlib.closing(_connect()) as conn:
            conn.execute(sql, values)
            conn.commit()

    async with _lock:
        await asyncio.to_thread(_work)


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def _chunked(items: list[str], size: int = 500) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def fetch_rows(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Raw store rows for ``symbols`` (upper-keyed; missing symbols absent)."""
    keys = [s.strip().upper() for s in symbols if s and s.strip()]
    if not keys:
        return {}

    def _work() -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        with contextlib.closing(_connect()) as conn:
            for chunk in _chunked(keys):
                marks = ", ".join("?" for _ in chunk)
                for row in conn.execute(
                    f"SELECT * FROM fundamentals WHERE symbol IN ({marks})", chunk
                ):
                    out[row["symbol"]] = dict(row)
        return out

    async with _lock:
        return await asyncio.to_thread(_work)


def row_to_pair(row: dict[str, Any]) -> tuple[Fundamentals, Quote | None]:
    """Materialize one store row as the engine's ``(Fundamentals, Quote|None)``."""
    fundamentals = Fundamentals(
        symbol=row["symbol"],
        name=row.get("name"),
        sector=row.get("sector"),
        industry=row.get("industry"),
        currency=row.get("currency"),
        provider=row.get("provider") or "fundamentals-store",
        **{f: row.get(f) for f in _NUMERIC_FIELDS},
    )
    quote: Quote | None = None
    if row.get("quote_price") is not None:
        ts_raw = row.get("quote_timestamp")
        try:
            timestamp = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(tz=UTC)
        except ValueError:
            timestamp = datetime.now(tz=UTC)
        quote = Quote(
            symbol=row["symbol"],
            price=row["quote_price"],
            change=row.get("quote_change") or 0.0,
            change_percent=row.get("quote_change_percent") or 0.0,
            volume=row.get("quote_volume"),
            currency=row.get("quote_currency") or "USD",
            market_state=row.get("quote_market_state"),
            timestamp=timestamp,
            provider=row.get("provider") or "fundamentals-store",
        )
    return fundamentals, quote


async def query(
    symbols: list[str],
    require_fields: set[str] | None = None,
    *,
    quote_ttl: float = TTL_QUOTE_FULL_SECONDS,
    v7_ttl: float = TTL_V7_SECONDS,
    info_ttl: float = TTL_INFO_SECONDS,
) -> dict[str, dict[str, Any]]:
    """Rows for ``symbols`` whose data is FRESH enough to serve.

    A row qualifies when its v7 tier is fresh (``v7_updated_at`` within
    ``v7_ttl``) AND its quote tier is fresh (within ``quote_ttl``) AND every
    field in ``require_fields`` is non-NULL with its OWN tier fresh (an
    ``.info``-tier field needs ``info_updated_at`` within ``info_ttl``; sector
    seeded from the build-time map counts — the map is static truth)."""
    rows = await fetch_rows(symbols)
    now = time.time()
    v7_set = set(_V7_NUMERIC_FIELDS)
    out: dict[str, dict[str, Any]] = {}
    for key, row in rows.items():
        v7_at = row.get("v7_updated_at")
        quote_at = row.get("quote_updated_at")
        if v7_at is None or now - v7_at > v7_ttl:
            continue
        if quote_at is None or now - quote_at > quote_ttl:
            continue
        ok = True
        for field in require_fields or set():
            if row.get(_field_column(field)) is None:
                ok = False
                break
            if field in ("sector", "industry"):
                # Seeded sector/industry is static truth; a live (.info)
                # value re-stamps info_updated_at anyway.
                continue
            if field not in v7_set and field not in ("price", "change_percent_1d", "volume"):
                info_at = row.get("info_updated_at")
                if info_at is None or now - info_at > info_ttl:
                    ok = False
                    break
        if ok:
            out[key] = row
    return out


async def stale_symbols(
    symbols: list[str],
    *,
    quote_ttl: float = TTL_QUOTE_FULL_SECONDS,
    v7_ttl: float = TTL_V7_SECONDS,
) -> list[str]:
    """The subset of ``symbols`` whose v7/quote tiers are missing or stale —
    exactly what the budgeted sweep must fetch. Preserves input order."""
    rows = await fetch_rows(symbols)
    now = time.time()
    out: list[str] = []
    for sym in symbols:
        key = sym.strip().upper()
        row = rows.get(key)
        if row is None:
            out.append(sym)
            continue
        v7_at = row.get("v7_updated_at")
        quote_at = row.get("quote_updated_at")
        if v7_at is None or now - v7_at > v7_ttl or quote_at is None or now - quote_at > quote_ttl:
            out.append(sym)
    return out


# ---------------------------------------------------------------------------
# Prefilter — cheap-criteria SQL translation (prune phase).
# ---------------------------------------------------------------------------

#: Criterion field → store column for the quote-derived trio.
_QUOTE_FIELD_COLUMNS = {
    "price": "quote_price",
    "change_percent_1d": "quote_change_percent",
    "volume": "quote_volume",
}


def _field_column(field: str) -> str:
    return _QUOTE_FIELD_COLUMNS.get(field, field)


def _criterion_fails_sql(criterion: ScreenerCriterion) -> tuple[str, list[Any]] | None:
    """SQL predicate that is TRUE when a FRESH NON-NULL value DEFINITIVELY
    fails ``criterion`` — the only condition under which pruning is sound.

    Numeric criteria additionally require the value's tier stamp to be fresh
    (``:now`` minus the stamp within the tier TTL) — a stale number may have
    moved, so it cannot prune. Sector/industry/symbol values are static
    (seed/master truth), so non-NULL alone suffices. Returns ``None`` for a
    criterion this translation cannot soundly prune on."""
    if isinstance(criterion, NumericThresholdCriterion):
        col = _field_column(criterion.field)
        op = {"gt": "<=", "lt": ">=", "gte": "<", "lte": ">"}[criterion.operator]
        return f"({col} IS NOT NULL AND {_fresh_sql(criterion.field)} AND {col} {op} ?)", [
            criterion.value
        ]
    if isinstance(criterion, NumericBetweenCriterion):
        col = _field_column(criterion.field)
        return (
            f"({col} IS NOT NULL AND {_fresh_sql(criterion.field)} AND ({col} < ? OR {col} > ?))",
            [criterion.value.min, criterion.value.max],
        )
    if isinstance(criterion, StringEqCriterion):
        if criterion.field == "currency":
            return None  # rides the quote, locale-shaped — evaluate in phase F
        col = criterion.field
        return f"({col} IS NOT NULL AND {col} COLLATE NOCASE != ?)", [criterion.value]
    if isinstance(criterion, SetInCriterion):
        if not criterion.value:
            return None  # empty set cannot translate; phase F fails it honestly
        marks = ", ".join("?" for _ in criterion.value)
        if criterion.field == "symbol":
            return (
                f"(symbol COLLATE NOCASE NOT IN ({marks}))",
                [v.upper() for v in criterion.value],
            )
        col = criterion.field
        return (
            f"({col} IS NOT NULL AND {col} COLLATE NOCASE NOT IN ({marks}))",
            list(criterion.value),
        )
    return None


def _fresh_sql(field: str) -> str:
    """Freshness predicate for a numeric field's serving tier (see module doc)."""
    if field in _QUOTE_FIELD_COLUMNS:
        return (
            f"(quote_updated_at IS NOT NULL AND ? - quote_updated_at <= {TTL_QUOTE_FULL_SECONDS})"
        )
    if field in _V7_NUMERIC_FIELDS:
        return f"(v7_updated_at IS NOT NULL AND ? - v7_updated_at <= {TTL_V7_SECONDS})"
    return f"(info_updated_at IS NOT NULL AND ? - info_updated_at <= {TTL_INFO_SECONDS})"


async def prefilter(symbols: list[str], cheap_criteria: list[ScreenerCriterion]) -> list[str]:
    """Prune ``symbols`` by the AND-ed ``cheap_criteria`` — soundly.

    Removes a symbol ONLY when a stored, fresh, non-NULL value definitively
    fails one of the criteria (each criterion is AND-ed, so failing one is
    fatal). NULL / stale / missing rows are KEPT — pruning may only widen,
    never narrow, the candidate set. Preserves input order."""
    if not symbols or not cheap_criteria:
        return list(symbols)
    predicates: list[str] = []
    params: list[Any] = []
    now = time.time()
    for criterion in cheap_criteria:
        translated = _criterion_fails_sql(criterion)
        if translated is None:
            continue
        sql, crit_params = translated
        # ``_fresh_sql`` injects one ``?`` (the now timestamp) BEFORE the
        # criterion's own params in numeric predicates.
        if isinstance(criterion, (NumericThresholdCriterion, NumericBetweenCriterion)):
            params.extend([now, *crit_params])
        else:
            params.extend(crit_params)
        predicates.append(sql)
    if not predicates:
        return list(symbols)

    fails = " OR ".join(predicates)

    def _work() -> set[str]:
        keys = [s.strip().upper() for s in symbols]
        failed: set[str] = set()
        with contextlib.closing(_connect()) as conn:
            for chunk in _chunked(keys):
                marks = ", ".join("?" for _ in chunk)
                sql = f"SELECT symbol FROM fundamentals WHERE symbol IN ({marks}) AND ({fails})"
                for row in conn.execute(sql, [*chunk, *params]):
                    failed.add(row["symbol"])
        return failed

    async with _lock:
        failed = await asyncio.to_thread(_work)
    return [s for s in symbols if s.strip().upper() not in failed]


async def info_priority(symbols: list[str], limit: int) -> list[str]:
    """The next ``limit`` symbols the deep crawler should ``.info``-fetch:
    never-fetched first, market cap descending, then stalest first."""
    keys = [s.strip().upper() for s in symbols if s and s.strip()]
    if not keys or limit <= 0:
        return []

    def _work() -> list[str]:
        out: list[tuple[int, float, float, str]] = []
        with contextlib.closing(_connect()) as conn:
            for chunk in _chunked(keys):
                marks = ", ".join("?" for _ in chunk)
                for row in conn.execute(
                    f"SELECT symbol, market_cap, info_updated_at FROM fundamentals "
                    f"WHERE symbol IN ({marks})",
                    chunk,
                ):
                    never = 0 if row["info_updated_at"] is None else 1
                    out.append(
                        (
                            never,
                            -(row["market_cap"] or 0.0),
                            row["info_updated_at"] or 0.0,
                            row["symbol"],
                        )
                    )
        out.sort()
        return [sym for _n, _m, _a, sym in out[:limit]]

    async with _lock:
        return await asyncio.to_thread(_work)


async def freshness(symbols: list[str]) -> dict[str, float]:
    """The honest-coverage ``freshness`` block over the rows serving a result:
    the OLDEST stamp per tier (epoch seconds), keys omitted when no row
    carries the tier."""
    rows = await fetch_rows(symbols)
    out: dict[str, float] = {}
    for tier, key in (
        ("quote_updated_at", "quotes_as_of"),
        ("v7_updated_at", "valuation_as_of"),
        ("info_updated_at", "deep_as_of"),
    ):
        stamps = [row[tier] for row in rows.values() if row.get(tier) is not None]
        if stamps:
            out[key] = min(stamps)
    return out


__all__ = [
    "DB_FILENAME",
    "TTL_INFO_SECONDS",
    "TTL_QUOTE_CURATED_SECONDS",
    "TTL_QUOTE_FULL_SECONDS",
    "TTL_V7_SECONDS",
    "fetch_rows",
    "freshness",
    "info_priority",
    "prefilter",
    "query",
    "reset_for_tests",
    "row_to_pair",
    "seed_universe",
    "stale_symbols",
    "upsert_info",
    "upsert_v7",
]
