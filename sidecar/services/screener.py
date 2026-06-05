"""Screener / scanner filter engine — Phase 6 + R4 batch fast path (FR-126).

A fan-out service that resolves a universe of symbols, fetches each symbol's
``Fundamentals`` snapshot (plus latest ``Quote`` for price-derived fields),
applies an AND-combined list of :class:`ScreenerCriterion` filters, and returns
the matching rows sorted by ``market_cap`` desc.

Two fetch paths
~~~~~~~~~~~~~~~

  * **Batch fast path** (R4 / FR-126, equity universes) — the common screener
    fields (price, market cap, P/E, dividend yield, 52-week, volume, …) come
    from Yahoo's ``/v7/finance/quote`` BATCH endpoint via
    :mod:`services.yahoo_batch_provider`: ≤50 symbols/request, ~11 calls for the
    506-name S&P 500, cookie+crumb reused, ``Semaphore(8)`` + ``gather``. A full
    cold S&P 500 screen now returns in single-digit seconds (was ~205 s), and
    every dropped symbol is itemized in the skip ledger (SC-034 — zero silent
    drops). A criterion that needs a field v7 does not carry (sector/industry/
    peg/beta) triggers a throttled per-symbol ``.info`` ENRICHMENT of only the
    affected symbols.
  * **Per-symbol path** (the graceful fallback + non-equity + custom/test
    universes) — the original cache-first, semaphore-throttled
    :func:`provider_registry` fan-out. Used when the batch endpoint fails
    entirely (degrade, never crash) and for any symbol the batch did not cover.

Skip ledger
~~~~~~~~~~~

Every universe member that does not reach the evaluation set is itemized in
``ScreenerResult.skip_details`` with a reason (``timeout`` / ``not_found`` /
``no_data`` / ``rate_limited`` / ``correctness_gate`` / ``missing_field:<f>``)
— ``skipped_count == len(skip_details)``.

Warm precompute
~~~~~~~~~~~~~~~

:func:`start_warm_precompute` spawns a background task that re-warms the S&P 500
batch on an interval so warm runs are sub-second. It is started from the FastAPI
lifespan and cancelled on shutdown (no leaked task).
"""

from __future__ import annotations

import asyncio
import contextlib
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
    SkipDetail,
    StringEqCriterion,
)
from services import data_cache, provider_registry, yahoo_batch_provider
from services.errors import ProviderError

logger = logging.getLogger(__name__)

#: How long the resolved ``crypto-top50`` list stays in the cache before a
#: refresh is attempted. ccxt's top-by-volume ordering shifts slowly; one
#: day is the right balance between freshness and rate-limit politeness.
_CRYPTO_TOP50_TTL_SECONDS = 24 * 60 * 60

#: Per-symbol fan-out timeout (the fallback path). A single hung upstream does
#: not stall the screener — symbols that time out are itemized as ``timeout``.
_SYMBOL_TIMEOUT_SECONDS = 30.0

#: Hard upper bound on the request's ``limit`` field. v0.6.0 doesn't need
#: pagination so the result table caps at 1000 rows.
_MAX_LIMIT = 1000

# --- Concurrency + caching tiers (R4 / FR-126) ---------------------------------

#: Live concurrency cap on the per-symbol fallback / enrichment fan-out. The
#: batch path is the bulk fetch; this only throttles the residual symbols the
#: batch did not cover (and the enrichment of fields v7 omits), so it can be
#: modest without hurting the cold-run target.
_FETCH_CONCURRENCY = 12

#: QUOTE cache tier — short TTL (price moves intraday). 45 s sits inside the
#: spec's 15–60 s window: a re-run within the window is sub-second and avoids a
#: redundant batch call, but a price never goes stale enough to mislead.
_QUOTE_CACHE_TTL_SECONDS = 45.0

#: FUNDAMENTALS / profile cache tier — long TTL (valuation ratios, sector, peg,
#: beta move daily at most). Six hours keeps a research session iterating
#: criteria instantly without re-scraping ``.info``.
_FUNDAMENTALS_CACHE_TTL_SECONDS = 6 * 60 * 60.0

# --- Warm-universe precompute (R4 / FR-126) ------------------------------------

#: Re-warm interval for the S&P 500 batch so warm runs stay sub-second. Slightly
#: under the quote TTL so the cache rarely goes cold between warms.
_WARM_INTERVAL_SECONDS = 40.0
#: Universes the background worker pre-warms. Equity-only (the batch path).
_WARM_UNIVERSES: tuple[ScreenerUniverseId, ...] = ("sp500",)


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
# Criteria field introspection — what does THIS screen actually need?
# ---------------------------------------------------------------------------


def _criteria_fields(criteria: list[ScreenerCriterion]) -> set[str]:
    """Every field referenced by the screen's criteria (flat list)."""
    fields: set[str] = set()
    for criterion in criteria:
        field = getattr(criterion, "field", None)
        if field:
            fields.add(field)
    return fields


def _enrichment_fields_needed(criteria: list[ScreenerCriterion]) -> set[str]:
    """The screened fields the v7 batch row cannot supply (need ``.info``)."""
    return {f for f in _criteria_fields(criteria) if yahoo_batch_provider.field_needs_enrichment(f)}


# ---------------------------------------------------------------------------
# Caching helpers — separate quote (short TTL) + fundamentals (long TTL) tiers.
# ---------------------------------------------------------------------------


def _quote_cache_key(symbol: str) -> str:
    return f"screener:quote:{symbol.upper()}"


def _fundamentals_cache_key(symbol: str) -> str:
    return f"screener:fundamentals:{symbol.upper()}"


async def _read_cached_quote(symbol: str) -> Quote | None:
    cached = await data_cache.get(_quote_cache_key(symbol), _QUOTE_CACHE_TTL_SECONDS)
    if isinstance(cached, dict):
        with contextlib.suppress(Exception):
            return Quote(**cached)
    return None


async def _read_cached_fundamentals(symbol: str) -> Fundamentals | None:
    cached = await data_cache.get(_fundamentals_cache_key(symbol), _FUNDAMENTALS_CACHE_TTL_SECONDS)
    if isinstance(cached, dict):
        with contextlib.suppress(Exception):
            return Fundamentals(**cached)
    return None


async def _write_cached_quote(quote: Quote) -> None:
    with contextlib.suppress(Exception):
        await data_cache.set(_quote_cache_key(quote.symbol), quote.model_dump(mode="json"))


async def _write_cached_fundamentals(fundamentals: Fundamentals) -> None:
    with contextlib.suppress(Exception):
        await data_cache.set(
            _fundamentals_cache_key(fundamentals.symbol),
            fundamentals.model_dump(mode="json"),
        )


# ---------------------------------------------------------------------------
# Per-symbol fallback fetch (the graceful-degrade + enrichment path)
# ---------------------------------------------------------------------------


async def _fetch_pair(
    symbol: str, asset_class: str
) -> tuple[tuple[Fundamentals, Quote | None] | None, str | None]:
    """Fetch ``(Fundamentals, Quote | None)`` for one symbol via the registry.

    Returns ``(pair, skip_reason)``. ``pair is None`` ⇒ the symbol is skipped
    and ``skip_reason`` is a ledger reason. A fundamentals failure is fatal for
    the symbol; a quote failure only drops the price-derived fields.
    """
    try:
        fundamentals = await asyncio.wait_for(
            provider_registry.get_fundamentals(symbol),
            timeout=_SYMBOL_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.debug("screener: fundamentals timed out for %s", symbol)
        return None, "timeout"
    except ProviderError as exc:
        logger.debug("screener: fundamentals failed for %s: %s", symbol, exc)
        return None, "correctness_gate"
    except Exception as exc:  # noqa: BLE001
        logger.warning("screener: unexpected fundamentals error for %s: %s", symbol, exc)
        return None, "no_data"

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
        quote = None
    except Exception as exc:  # noqa: BLE001
        logger.warning("screener: unexpected quote error for %s: %s", symbol, exc)
        quote = None

    return (fundamentals, quote), None


async def _cached_fallback_pair(
    symbol: str, asset_class: str, sem: asyncio.Semaphore
) -> tuple[str, tuple[Fundamentals, Quote | None] | None, str | None]:
    """Cache-first per-symbol fetch under the semaphore. Returns
    ``(symbol, pair, skip_reason)``."""
    cached_fund = await _read_cached_fundamentals(symbol)
    cached_quote = await _read_cached_quote(symbol)
    if cached_fund is not None:
        return symbol, (cached_fund, cached_quote), None
    async with sem:
        pair, reason = await _fetch_pair(symbol, asset_class)
    if pair is not None:
        await _write_cached_fundamentals(pair[0])
        if pair[1] is not None:
            await _write_cached_quote(pair[1])
    return symbol, pair, reason


# ---------------------------------------------------------------------------
# Batch fast path (Yahoo v7) + per-symbol enrichment
# ---------------------------------------------------------------------------


async def _enrich_one(
    symbol: str,
    base: Fundamentals,
    needed: set[str],
    sem: asyncio.Semaphore,
) -> tuple[str, Fundamentals, str | None]:
    """Per-symbol ``.info`` enrichment of the fields v7 omits.

    Pulls the richer registry ``Fundamentals`` and copies ONLY the
    ``needed`` (enrichment) fields onto the batch ``base`` so the criterion can
    evaluate. Returns ``(symbol, merged, skip_reason)`` — ``skip_reason`` is
    ``missing_field:<f>`` when the enrichment still cannot supply a needed
    field, else ``None``."""
    # Cache hit (long TTL) — reuse a prior enrichment.
    cached = await _read_cached_fundamentals(symbol)
    if cached is not None and all(getattr(cached, f, None) is not None for f in needed):
        merged = _merge_enrichment(base, cached, needed)
        return symbol, merged, None
    async with sem:
        try:
            rich = await asyncio.wait_for(
                provider_registry.get_fundamentals(symbol),
                timeout=_SYMBOL_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            return symbol, base, "missing_field:" + sorted(needed)[0]
        except Exception as exc:  # noqa: BLE001 — any failure ⇒ field stays missing
            logger.debug("screener: enrichment failed for %s: %s", symbol, exc)
            return symbol, base, "missing_field:" + sorted(needed)[0]
    await _write_cached_fundamentals(rich)
    merged = _merge_enrichment(base, rich, needed)
    # If a needed field is STILL None after enrichment, itemize it.
    for field in sorted(needed):
        if getattr(merged, field, None) is None:
            return symbol, merged, f"missing_field:{field}"
    return symbol, merged, None


def _merge_enrichment(base: Fundamentals, rich: Fundamentals, fields: set[str]) -> Fundamentals:
    """Return a copy of ``base`` with the ``fields`` taken from ``rich``."""
    overrides = {f: getattr(rich, f, None) for f in fields}
    return base.model_copy(update=overrides)


async def _batch_collect(
    universe: ScreenerUniverse,
    criteria: list[ScreenerCriterion],
) -> tuple[
    dict[str, tuple[Fundamentals, Quote | None]],
    dict[str, str],
]:
    """Run the batch fast path over an equity universe.

    Returns ``(pairs_by_symbol, provisional_skip_reasons)``. ``pairs`` are the
    symbols the batch (or its cache) resolved; ``provisional_skip_reasons`` maps
    each UNRESOLVED symbol to the batch's reason (``not_found`` / ``timeout`` /
    ``rate_limited`` / ``no_data`` / ``missing_field:<f>``). The caller retries
    every unresolved symbol on the per-symbol fallback — these reasons only
    stick if the fallback ALSO fails. On a TOTAL batch wipeout (endpoint down)
    ``pairs`` is empty → full graceful degrade to the fallback path.
    """
    symbols = list(universe.symbols)
    pairs: dict[str, tuple[Fundamentals, Quote | None]] = {}
    skips: dict[str, str] = {}

    # 1) Warm-cache pass: a fresh quote (short TTL) + fundamentals (long TTL)
    #    avoids a network call entirely (sub-second warm runs).
    miss: list[str] = []
    for sym in symbols:
        c_quote = await _read_cached_quote(sym)
        c_fund = await _read_cached_fundamentals(sym)
        if c_quote is not None and c_fund is not None:
            pairs[sym.upper()] = (c_fund, c_quote)
        else:
            miss.append(sym)

    # 2) Batch-fetch the cache misses.
    if miss:
        rows, failures = await yahoo_batch_provider.fetch_quotes_batch(miss)
        for sym in miss:
            row = rows.get(sym.upper())
            if row is None:
                # Itemize the batch failure reason (default not_found).
                skips[sym.upper()] = failures.get(sym, "not_found")
                continue
            quote = yahoo_batch_provider.quote_from_v7(row)
            if quote is None:
                skips[sym.upper()] = "no_data"
                continue
            fundamentals = yahoo_batch_provider.fundamentals_from_v7(row)
            pairs[sym.upper()] = (fundamentals, quote)
            await _write_cached_quote(quote)
            await _write_cached_fundamentals(fundamentals)

    # 3) Enrichment — only when a criterion needs a field v7 omits.
    needed = _enrichment_fields_needed(criteria)
    if needed and pairs:
        sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
        to_enrich = [
            (sym, fund)
            for sym, (fund, _q) in pairs.items()
            if any(getattr(fund, f, None) is None for f in needed)
        ]
        results = await asyncio.gather(
            *(_enrich_one(sym, fund, needed, sem) for sym, fund in to_enrich)
        )
        for sym, merged, reason in results:
            quote = pairs[sym][1]
            pairs[sym] = (merged, quote)
            if reason is not None:
                # A needed field is still missing → drop the symbol, itemized.
                pairs.pop(sym, None)
                skips[sym] = reason

    return pairs, skips


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------


async def run_screener(req: ScreenerRequest) -> ScreenerResult:
    """Resolve the universe, fan out (batch fast path + fallback), filter, return.

    AND-combines every criterion. Returns up to ``req.limit`` rows sorted by
    market cap desc. Every dropped symbol is itemized in ``skip_details``
    (SC-034); ``skipped_count == len(skip_details)``.
    """
    started_at = time.monotonic()

    universe = await resolve_universe(req.universe, req.custom_symbols)
    criteria = list(req.criteria)

    pairs_by_symbol: dict[str, tuple[Fundamentals, Quote | None]] = {}
    skip_reasons: dict[str, str] = {}
    fallback_symbols: list[str] = list(universe.symbols)

    # --- Batch fast path (equity only). Crypto / anything else stays on the
    #     per-symbol path (ccxt has no v7 batch equivalent). ---
    if universe.asset_class == "equity":
        try:
            batch_pairs, batch_skips = await _batch_collect(universe, criteria)
        except Exception as exc:  # noqa: BLE001 — batch must never crash the screen
            logger.warning("screener: batch path failed, degrading to per-symbol: %s", exc)
            batch_pairs, batch_skips = {}, {}
        pairs_by_symbol.update(batch_pairs)
        # The batch's skip reasons are PROVISIONAL — every unresolved symbol is
        # retried on the per-symbol fallback (it may fill a missing field or a
        # symbol the batch endpoint truncated). The reason only sticks if the
        # fallback ALSO cannot resolve it.
        skip_reasons.update(batch_skips)
        fallback_symbols = [s for s in universe.symbols if s.upper() not in pairs_by_symbol]

    # --- Per-symbol fallback (residual symbols + non-equity). ---
    if fallback_symbols:
        sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
        fallback_results = await asyncio.gather(
            *(_cached_fallback_pair(sym, universe.asset_class, sem) for sym in fallback_symbols)
        )
        for sym, pair, reason in fallback_results:
            key = sym.upper()
            if pair is not None:
                pairs_by_symbol[key] = pair
                skip_reasons.pop(key, None)
            elif reason is not None:
                # Fallback's reason supersedes the batch's provisional one.
                skip_reasons[key] = reason

    pairs = list(pairs_by_symbol.values())
    matched = apply_criteria(pairs, criteria)

    # Apply limit. Clamp to ``_MAX_LIMIT`` so a malformed request body
    # cannot pull a 10k-row response.
    limit = max(1, min(int(req.limit), _MAX_LIMIT))
    rows = matched[:limit]

    # Build the itemized skip ledger (SC-034 — zero silent drops). A symbol is
    # skipped iff it produced no evaluable pair; reason defaults to no_data.
    evaluated = set(pairs_by_symbol)
    skip_details: list[SkipDetail] = []
    for sym in universe.symbols:
        key = sym.upper()
        if key not in evaluated:
            skip_details.append(SkipDetail(symbol=key, reason=skip_reasons.get(key, "no_data")))

    duration_ms = (time.monotonic() - started_at) * 1000.0
    return ScreenerResult(
        universe=req.universe,
        evaluated_count=len(pairs),
        skipped_count=len(skip_details),
        skip_details=skip_details,
        result_count=len(rows),
        rows=rows,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Warm-universe precompute worker (R4 / FR-126)
# ---------------------------------------------------------------------------

_warm_task: asyncio.Task[None] | None = None


async def _warm_once() -> None:
    """Pre-warm one batch cycle over the warm universes (best-effort)."""
    for universe_id in _WARM_UNIVERSES:
        try:
            universe = await resolve_universe(universe_id)
        except ProviderError as exc:
            logger.debug("screener warm: cannot resolve %s: %s", universe_id, exc)
            continue
        rows, _failures = await yahoo_batch_provider.fetch_quotes_batch(list(universe.symbols))
        for _sym, row in rows.items():
            quote = yahoo_batch_provider.quote_from_v7(row)
            if quote is not None:
                await _write_cached_quote(quote)
                await _write_cached_fundamentals(yahoo_batch_provider.fundamentals_from_v7(row))


async def _warm_loop(interval: float) -> None:
    """Background loop: warm immediately, then re-warm every ``interval`` s.

    Swallows every per-cycle error (a transient Yahoo blip must not kill the
    worker) and exits cleanly on cancellation."""
    try:
        while True:
            try:
                await _warm_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — a warm cycle is best-effort
                logger.debug("screener warm cycle failed: %s", exc)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.debug("screener warm loop cancelled")
        raise


def start_warm_precompute(interval: float = _WARM_INTERVAL_SECONDS) -> None:
    """Start the warm-precompute background task (idempotent).

    Spawned from the FastAPI lifespan AFTER startup so it never blocks the
    sidecar boot the Tauri core waits on. The task is detached; the loop's
    first iteration runs the initial warm. Re-calling while a task is live is a
    no-op."""
    global _warm_task
    if _warm_task is not None and not _warm_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop (e.g. called outside an async context) — skip; the
        # lifespan is the real caller and always has a loop.
        logger.debug("screener warm: no running loop; precompute not started")
        return
    _warm_task = loop.create_task(_warm_loop(interval))


async def stop_warm_precompute() -> None:
    """Cancel + await the warm-precompute task so it does not leak on shutdown."""
    global _warm_task
    task = _warm_task
    _warm_task = None
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await task
    await yahoo_batch_provider.aclose()


__all__ = [
    "apply_criteria",
    "resolve_universe",
    "run_screener",
    "start_warm_precompute",
    "stop_warm_precompute",
]
