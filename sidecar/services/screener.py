"""Screener / scanner filter engine — Phase 6 (Teammate Sc).

A small fan-out service that resolves a universe of symbols, fetches each
symbol's ``Fundamentals`` snapshot (plus latest ``Quote`` for price-derived
fields) in parallel via :func:`asyncio.gather`, applies an AND-combined
list of :class:`ScreenerCriterion` filters, and returns the matching
rows sorted by ``market_cap`` desc.

Public surface
~~~~~~~~~~~~~~

  - :func:`run_screener(req)` — top-level entry the router awaits.
  - :func:`resolve_universe(id, custom_symbols)` — returns the
    :class:`ScreenerUniverse` for the requested id. ``"sp500"``,
    ``"nifty50"``, and ``"crypto-top50"`` are seeded from the shipped
    JSON snapshots under :mod:`services.screener_universes`. The
    ``"crypto-top50"`` path caches a refreshed list via
    :mod:`services.data_cache` (24h TTL) — the seed is the offline
    fallback when the cache is cold and ccxt is unreachable.
  - :func:`apply_criteria(rows, criteria)` — pure filter; returns the
    rows that match every criterion. Exposed so tests can exercise the
    discriminated-union operator dispatch without an HTTP round-trip.

Design notes
~~~~~~~~~~~~

The criteria union is discriminated by ``operator``; each operator
maps to a small comparator function. Missing field values (``None``
on Fundamentals — market_cap is unknown for many crypto pairs, P/E is
unknown for unprofitable names) **fail** any numeric criterion — a
"market cap > 100B" criterion drops names whose market cap is unknown
rather than masking them as matches.

Performance: with the v0.6.0 seeded universes (≤100 names), the
asyncio.gather fan-out completes in O(longest provider latency) — the
yfinance fallback path is sync-on-thread per symbol but the registry's
openbb-mcp preference batches well. The :func:`run_screener` entry
sets a per-symbol ``asyncio.timeout`` (30s) so a single hung upstream
does not stall the screener.

Each result row records ``matched_criteria`` — the indices of the
input criteria the row satisfied (which is always every index, since
we filter on AND; the field is retained for parity with the
``ScreenerResultRow`` TypeScript mirror and for future OR-grouping).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from importlib import resources
from typing import Any

from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import (
    NumericBetweenCriterion,
    NumericThresholdCriterion,
    ScreenerCriterion,
    ScreenerRequest,
    ScreenerResult,
    ScreenerResultRow,
    ScreenerUniverse,
    ScreenerUniverseId,
    SetInCriterion,
    StringEqCriterion,
)
from services import data_cache, provider_registry
from services.errors import ProviderError

logger = logging.getLogger(__name__)

#: How long the resolved ``crypto-top50`` list stays in the cache before a
#: refresh is attempted. ccxt's top-by-volume ordering shifts slowly; one
#: day is the right balance between freshness and rate-limit politeness.
_CRYPTO_TOP50_TTL_SECONDS = 24 * 60 * 60

#: Per-symbol fan-out timeout. A single hung upstream does not stall the
#: screener — symbols that time out get dropped from the result set.
_SYMBOL_TIMEOUT_SECONDS = 30.0

#: Hard upper bound on the request's ``limit`` field. v0.6.0 doesn't need
#: pagination so the result table caps at 1000 rows.
_MAX_LIMIT = 1000


# ---------------------------------------------------------------------------
# Universe resolution
# ---------------------------------------------------------------------------


def _load_universe_snapshot(filename: str) -> dict[str, Any]:
    """Load one of the shipped universe JSON snapshots."""
    try:
        with (
            resources.files("services.screener_universes")
            .joinpath(filename)
            .open("r", encoding="utf-8")
        ) as fp:
            return json.load(fp)
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        # ``ModuleNotFoundError`` is raised by ``importlib.resources`` on a
        # missing package — treat both as "no snapshot shipped".
        raise ProviderError(f"missing universe snapshot {filename!r}") from exc


async def resolve_universe(
    universe_id: ScreenerUniverseId,
    custom_symbols: list[str] | None = None,
) -> ScreenerUniverse:
    """Return the :class:`ScreenerUniverse` for ``universe_id``.

    ``"custom"`` consumes the request's ``custom_symbols``. Otherwise
    the shipped JSON snapshots seed the universe; the crypto path
    additionally checks the data cache for a refreshed list.
    """
    if universe_id == "custom":
        symbols = [s.strip().upper() for s in (custom_symbols or []) if s and s.strip()]
        if not symbols:
            raise ProviderError("custom universe requires a non-empty symbol list")
        return ScreenerUniverse(
            id="custom",
            label="Custom",
            symbols=symbols,
            asset_class="equity",
        )

    if universe_id == "sp500":
        snapshot = _load_universe_snapshot("sp500.json")
        return ScreenerUniverse(
            id="sp500",
            label=snapshot.get("label", "S&P 500"),
            symbols=list(snapshot["symbols"]),
            asset_class="equity",
        )

    if universe_id == "nifty50":
        snapshot = _load_universe_snapshot("nifty50.json")
        return ScreenerUniverse(
            id="nifty50",
            label=snapshot.get("label", "NIFTY 50"),
            symbols=list(snapshot["symbols"]),
            asset_class="equity",
        )

    if universe_id == "crypto-top50":
        # Prefer the cached top-50 list if it's still fresh; fall back
        # to the shipped seed otherwise. The cache hit avoids re-loading
        # the JSON on every screener run; a future v0.7+ refresh worker
        # populates the cache from ccxt.
        cached = await data_cache.get(
            f"screener:universe:crypto-top50",
            ttl_seconds=_CRYPTO_TOP50_TTL_SECONDS,
        )
        if cached and isinstance(cached, dict) and cached.get("symbols"):
            symbols = list(cached["symbols"])
            label = cached.get("label", "Crypto Top 50")
        else:
            snapshot = _load_universe_snapshot("crypto_top50.json")
            symbols = list(snapshot["symbols"])
            label = snapshot.get("label", "Crypto Top 50")
            await data_cache.set(
                f"screener:universe:crypto-top50",
                {"symbols": symbols, "label": label, "seeded_from_snapshot": True},
            )
        return ScreenerUniverse(
            id="crypto-top50",
            label=label,
            symbols=symbols,
            asset_class="crypto",
        )

    raise ProviderError(f"unknown universe id {universe_id!r}")


# ---------------------------------------------------------------------------
# Criterion evaluation — discriminated-union dispatch
# ---------------------------------------------------------------------------


def _numeric_field_value(
    fundamentals: Fundamentals, quote: Quote | None, field: str
) -> float | None:
    """Resolve a numeric field's value from a fundamentals+quote pair.

    Most numeric fields live on :class:`Fundamentals`; the price /
    change% / volume trio is derived from the latest :class:`Quote`.
    Returns ``None`` if the underlying provider did not populate the
    field — the caller treats a ``None`` as a "criterion fails".
    """
    if field == "price":
        return quote.price if quote is not None else None
    if field == "change_percent_1d":
        return quote.change_percent if quote is not None else None
    if field == "volume":
        return quote.volume if quote is not None else None
    # Everything else maps directly to a ``Fundamentals`` attribute.
    return getattr(fundamentals, field, None)


def _string_field_value(fundamentals: Fundamentals, field: str) -> str | None:
    """Resolve a string field's value. ``currency`` is on the quote — but
    the screener doesn't currently fetch quotes for crypto-only flows, so
    only fundamentals-side string fields are first-class today."""
    return getattr(fundamentals, field, None)


def _evaluate_criterion(
    criterion: ScreenerCriterion,
    fundamentals: Fundamentals,
    quote: Quote | None,
) -> bool:
    """Return ``True`` if the row satisfies the criterion."""
    if isinstance(criterion, NumericThresholdCriterion):
        value = _numeric_field_value(fundamentals, quote, criterion.field)
        if value is None:
            return False
        threshold = criterion.value
        if criterion.operator == "gt":
            return value > threshold
        if criterion.operator == "lt":
            return value < threshold
        if criterion.operator == "gte":
            return value >= threshold
        if criterion.operator == "lte":
            return value <= threshold
        return False

    if isinstance(criterion, NumericBetweenCriterion):
        value = _numeric_field_value(fundamentals, quote, criterion.field)
        if value is None:
            return False
        return criterion.value.min <= value <= criterion.value.max

    if isinstance(criterion, StringEqCriterion):
        value = _string_field_value(fundamentals, criterion.field)
        if value is None:
            return False
        return value.casefold() == criterion.value.casefold()

    if isinstance(criterion, SetInCriterion):
        if criterion.field == "symbol":
            haystack = {s.upper() for s in criterion.value}
            return fundamentals.symbol.upper() in haystack
        value = _string_field_value(fundamentals, criterion.field)
        if value is None:
            return False
        return value.casefold() in {v.casefold() for v in criterion.value}

    return False


def apply_criteria(
    rows: list[tuple[Fundamentals, Quote | None]],
    criteria: list[ScreenerCriterion],
) -> list[ScreenerResultRow]:
    """Apply AND-combined criteria to a list of fundamentals+quote pairs.

    Returns a list of :class:`ScreenerResultRow`, ordered by
    ``market_cap`` descending. Symbols whose ``market_cap`` is unknown
    sort to the end.
    """
    matched: list[ScreenerResultRow] = []
    for fundamentals, quote in rows:
        passed_indices: list[int] = []
        all_passed = True
        for idx, criterion in enumerate(criteria):
            if _evaluate_criterion(criterion, fundamentals, quote):
                passed_indices.append(idx)
            else:
                all_passed = False
                break
        if not all_passed:
            continue
        matched.append(
            ScreenerResultRow(
                symbol=fundamentals.symbol,
                name=fundamentals.name,
                sector=fundamentals.sector,
                industry=fundamentals.industry,
                market_cap=fundamentals.market_cap,
                pe_ratio=fundamentals.pe_ratio,
                price=quote.price if quote is not None else None,
                change_percent_1d=quote.change_percent if quote is not None else None,
                volume=quote.volume if quote is not None else None,
                matched_criteria=passed_indices,
            )
        )
    matched.sort(
        key=lambda row: (row.market_cap is None, -(row.market_cap or 0.0)),
    )
    return matched


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------


async def _fetch_pair(symbol: str, asset_class: str) -> tuple[Fundamentals, Quote | None] | None:
    """Fetch ``(Fundamentals, Quote | None)`` for one symbol.

    Wraps both calls in their own try/except so a single symbol's
    failure does not poison the whole screener. Returns ``None`` for
    skipped symbols; the caller filters those out.
    """
    try:
        fundamentals = await asyncio.wait_for(
            provider_registry.get_fundamentals(symbol),
            timeout=_SYMBOL_TIMEOUT_SECONDS,
        )
    except (ProviderError, asyncio.TimeoutError, TimeoutError) as exc:
        logger.debug("screener: fundamentals failed for %s: %s", symbol, exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("screener: unexpected fundamentals error for %s: %s", symbol, exc)
        return None

    quote: Quote | None = None
    try:
        # provider_registry.get_quote is synchronous — run on a thread
        # so the gather() fan-out does not block the event loop.
        quote = await asyncio.wait_for(
            asyncio.to_thread(provider_registry.get_quote, symbol, asset_class),
            timeout=_SYMBOL_TIMEOUT_SECONDS,
        )
    except (ProviderError, asyncio.TimeoutError, TimeoutError) as exc:
        logger.debug("screener: quote failed for %s: %s", symbol, exc)
        # A missing quote drops the price-derived criteria but is not
        # itself a hard failure — return the fundamentals-only pair.
        quote = None
    except Exception as exc:  # noqa: BLE001
        logger.warning("screener: unexpected quote error for %s: %s", symbol, exc)
        quote = None

    return fundamentals, quote


async def run_screener(req: ScreenerRequest) -> ScreenerResult:
    """Resolve the universe, fan out, filter, and return the result.

    AND-combines every criterion. Returns up to ``req.limit`` rows
    sorted by market cap desc.
    """
    started_at = time.monotonic()

    universe = await resolve_universe(req.universe, req.custom_symbols)

    # Fan out fundamentals+quote fetches in parallel. ``return_exceptions``
    # is False here because ``_fetch_pair`` already swallows per-symbol
    # failures — a raised exception inside _fetch_pair is a true bug.
    pairs_raw = await asyncio.gather(
        *(_fetch_pair(sym, universe.asset_class) for sym in universe.symbols)
    )
    pairs: list[tuple[Fundamentals, Quote | None]] = [
        pair for pair in pairs_raw if pair is not None
    ]

    matched = apply_criteria(pairs, list(req.criteria))

    # Apply limit. Clamp to ``_MAX_LIMIT`` so a malformed request body
    # cannot pull a 10k-row response.
    limit = max(1, min(int(req.limit), _MAX_LIMIT))
    rows = matched[:limit]

    duration_ms = (time.monotonic() - started_at) * 1000.0
    return ScreenerResult(
        universe=req.universe,
        evaluated_count=len(pairs),
        result_count=len(rows),
        rows=rows,
        duration_ms=duration_ms,
    )


__all__ = [
    "apply_criteria",
    "resolve_universe",
    "run_screener",
]
