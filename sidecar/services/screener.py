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

from config import get_region
from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import (
    CriterionGroup,
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

#: Locale-sensible default screener universe per region (Pass B / Pillar A —
#: FR-060). The :class:`ScreenerRequest` always carries an explicit ``universe``
#: today (the frontend universe-picker supplies it; the field is required with no
#: default), so this is consulted only when a caller has to *choose* a default
#: rather than overriding an explicit one — e.g. a region-aware UI/agent default
#: or a future "no universe given" entrypoint. US/GLOBAL → ``sp500``; IN →
#: ``nifty50`` (which already ships as ``nifty50.json``).
_DEFAULT_UNIVERSE_BY_REGION: dict[str, ScreenerUniverseId] = {
    "US": "sp500",
    "IN": "nifty50",
    "GLOBAL": "sp500",
}


def default_universe_for_region(region: str | None = None) -> ScreenerUniverseId:
    """Return the locale-sensible default screener universe for ``region``.

    ``region`` defaults to the active per-request region (:func:`config.get_region`).
    US/GLOBAL → ``"sp500"``; IN → ``"nifty50"``. Used where a default universe must
    be chosen; an explicit ``ScreenerRequest.universe`` is never overridden.
    """
    resolved = region if region is not None else get_region()
    return _DEFAULT_UNIVERSE_BY_REGION.get(resolved, "sp500")


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

#: Batching layer (003 — the prerequisite for the full-500 universe). The screener
#: fans out a per-symbol fundamentals+quote fetch; doing all ~500 at once would get
#: yfinance to rate-limit/drop. A semaphore throttles concurrency, and a per-symbol
#: cache makes re-runs (and overlapping universes) near-instant. 12 concurrent keeps
#: the first cold run brisk without tripping rate limits.
_FETCH_CONCURRENCY = 12
#: Per-symbol pair cache TTL — fundamentals move daily, quotes intraday; an hour is
#: a sound research-screener freshness window and makes iterating criteria instant.
_PAIR_CACHE_TTL_SECONDS = 3600.0


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

    A non-empty ``custom_symbols`` list takes precedence over the named
    universe — the caller explicitly listed the symbols they want to screen.
    Previously ``custom_symbols`` was honoured ONLY when ``universe_id ==
    "custom"`` and was silently ignored when sent alongside e.g. ``"sp500"``
    (Phase 9.5 nit: screener ignored custom_symbols). Otherwise the shipped JSON
    snapshots seed the universe; the crypto path additionally checks the data
    cache for a refreshed list.
    """
    cleaned = [s.strip().upper() for s in (custom_symbols or []) if s and s.strip()]
    if cleaned:
        return ScreenerUniverse(
            id="custom",
            label="Custom",
            symbols=cleaned,
            asset_class="equity",
        )
    if universe_id == "custom":
        # Explicit custom universe but no usable symbols → a 4xx-grade error.
        raise ProviderError("custom universe requires a non-empty symbol list")

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
            "screener:universe:crypto-top50",
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
                "screener:universe:crypto-top50",
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


def _string_field_value(fundamentals: Fundamentals, quote: Quote | None, field: str) -> str | None:
    """Resolve a string field's value. ``currency`` lives on the quote (equity
    quotes default to ``USD``), so special-case it like the numeric price/volume
    trio rather than reading a non-existent ``Fundamentals.currency`` attribute
    — which made every ``currency`` criterion silently fail and return zero rows
    for an all-USD universe. A crypto-only flow without a quote resolves
    ``currency`` to ``None`` (the criterion fails, honestly)."""
    if field == "currency":
        return quote.currency if quote is not None else None
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
        value = _string_field_value(fundamentals, quote, criterion.field)
        if value is None:
            return False
        return value.casefold() == criterion.value.casefold()

    if isinstance(criterion, SetInCriterion):
        if criterion.field == "symbol":
            haystack = {s.upper() for s in criterion.value}
            return fundamentals.symbol.upper() in haystack
        value = _string_field_value(fundamentals, quote, criterion.field)
        if value is None:
            return False
        return value.casefold() in {v.casefold() for v in criterion.value}

    return False


def _evaluate_group(
    group: CriterionGroup,
    fundamentals: Fundamentals,
    quote: Quote | None,
) -> bool:
    """Recursively evaluate an AND/OR group. An empty group matches everything."""
    if not group.criteria:
        return True
    results = [
        _evaluate_group(node, fundamentals, quote)
        if isinstance(node, CriterionGroup)
        else _evaluate_criterion(node, fundamentals, quote)
        for node in group.criteria
    ]
    return any(results) if group.combinator == "or" else all(results)


def apply_criteria(
    rows: list[tuple[Fundamentals, Quote | None]],
    criteria: list[ScreenerCriterion],
    group: CriterionGroup | None = None,
) -> list[ScreenerResultRow]:
    """Filter fundamentals+quote pairs by the criteria, ordered by market_cap desc.

    When ``group`` is given it supersedes the flat ``criteria`` and is evaluated as
    a boolean AND/OR tree; otherwise the flat ``criteria`` are AND-combined (the
    back-compat path). Symbols whose ``market_cap`` is unknown sort to the end.
    """
    matched: list[ScreenerResultRow] = []
    for fundamentals, quote in rows:
        passed_indices: list[int] = []
        if group is not None:
            # Boolean-tree path (OR / nested). matched_criteria isn't a flat-index
            # concept here, so it stays empty.
            if not _evaluate_group(group, fundamentals, quote):
                continue
        else:
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
                forward_pe=fundamentals.forward_pe,
                peg_ratio=fundamentals.peg_ratio,
                price_to_book=fundamentals.price_to_book,
                dividend_yield=fundamentals.dividend_yield,
                roe=fundamentals.roe,
                debt_to_equity=fundamentals.debt_to_equity,
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
    except (ProviderError, TimeoutError) as exc:
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
    except (ProviderError, TimeoutError) as exc:
        logger.debug("screener: quote failed for %s: %s", symbol, exc)
        # A missing quote drops the price-derived criteria but is not
        # itself a hard failure — return the fundamentals-only pair.
        quote = None
    except Exception as exc:  # noqa: BLE001
        logger.warning("screener: unexpected quote error for %s: %s", symbol, exc)
        quote = None

    return fundamentals, quote


async def _cached_pair(
    symbol: str, asset_class: str, sem: asyncio.Semaphore
) -> tuple[Fundamentals, Quote | None] | None:
    """Cache-first, concurrency-throttled wrapper over :func:`_fetch_pair`.

    A cache hit (within ``_PAIR_CACHE_TTL_SECONDS``) returns instantly with no
    network call; a miss fetches UNDER the semaphore — throttling the cold fan-out
    so a ~500-symbol universe doesn't trip yfinance rate limits — then caches the
    serialised pair. This is the batching layer that makes the full S&P 500
    universe viable (and re-runs / overlapping universes near-instant).
    """
    cache_key = f"screener:pair:{asset_class}:{symbol.upper()}"
    cached = await data_cache.get(cache_key, _PAIR_CACHE_TTL_SECONDS)
    if isinstance(cached, dict) and "fundamentals" in cached:
        try:
            fundamentals = Fundamentals(**cached["fundamentals"])
            quote = Quote(**cached["quote"]) if cached.get("quote") else None
            return fundamentals, quote
        except Exception as exc:  # noqa: BLE001 - a stale/garbled cache row is just a miss
            logger.debug("screener: bad cache row for %s: %s", symbol, exc)

    async with sem:
        pair = await _fetch_pair(symbol, asset_class)
    if pair is None:
        return None
    fundamentals, quote = pair
    try:
        await data_cache.set(
            cache_key,
            {
                "fundamentals": fundamentals.model_dump(mode="json"),
                "quote": quote.model_dump(mode="json") if quote is not None else None,
            },
        )
    except Exception as exc:  # noqa: BLE001 - caching is best-effort, never fatal
        logger.debug("screener: cache write failed for %s: %s", symbol, exc)
    return pair


async def run_screener(req: ScreenerRequest) -> ScreenerResult:
    """Resolve the universe, fan out (throttled + cached), filter, and return.

    Filters by the request's ``group`` (AND/OR boolean tree) when present, else by
    the flat AND-combined ``criteria``. Returns up to ``req.limit`` rows sorted by
    market cap desc.
    """
    started_at = time.monotonic()

    # ``req.universe`` is always explicit (required on ScreenerRequest, no default)
    # — region-default selection happens upstream where a default is chosen, via
    # ``default_universe_for_region``; here we honour exactly what the caller sent.
    universe = await resolve_universe(req.universe, req.custom_symbols)

    # Throttled + cached fan-out (the batching layer). The semaphore caps live
    # concurrency so a full-500 cold run doesn't trip rate limits; cache hits skip
    # the network entirely. ``_cached_pair`` swallows per-symbol failures (returns
    # None), so a raised exception here is a true bug.
    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
    pairs_raw = await asyncio.gather(
        *(_cached_pair(sym, universe.asset_class, sem) for sym in universe.symbols)
    )
    pairs: list[tuple[Fundamentals, Quote | None]] = [
        pair for pair in pairs_raw if pair is not None
    ]

    matched = apply_criteria(pairs, list(req.criteria), group=req.group)

    # Apply limit. Clamp to ``_MAX_LIMIT`` so a malformed request body
    # cannot pull a 10k-row response.
    limit = max(1, min(int(req.limit), _MAX_LIMIT))
    rows = matched[:limit]

    duration_ms = (time.monotonic() - started_at) * 1000.0
    return ScreenerResult(
        universe=req.universe,
        evaluated_count=len(pairs),
        skipped_count=len(universe.symbols) - len(pairs),
        result_count=len(rows),
        rows=rows,
        duration_ms=duration_ms,
    )


__all__ = [
    "apply_criteria",
    "default_universe_for_region",
    "resolve_universe",
    "run_screener",
]
