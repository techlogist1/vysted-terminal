"""Screener / scanner filter engine — R10 phased rewrite (E4 dead; D40).

A fan-out service that resolves a universe of symbols, gathers each symbol's
``Fundamentals`` + latest ``Quote``, applies an AND-combined list (or an AND/OR
``group`` tree) of :class:`ScreenerCriterion` filters plus an optional custom
``formula``, and returns the matching rows sorted by ``market_cap`` desc.

Phased engine (the batch universes: sp500 / nifty50 / nse-all / bse-all /
india-all)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every run executes under a WALL BUDGET (default 120 s — the unbounded
``screener.py:687`` batch call that hung the UI for 5 minutes is dead):

  U  universe   — resolve the symbol list (5 s cap; bundled JSON, instant).
  P  prefilter  — the top-level AND-ed CHEAP criteria (sector / industry /
     v7-tier numerics) prune candidates via the SQLite fundamentals store
     (:mod:`services.fundamentals_store`). Pruning is SOUND: a symbol is
     dropped only when a fresh, non-NULL stored value definitively fails an
     AND-ed criterion — NULL / stale / missing rows are kept, and OR subtrees
     never prune. Pruning may only WIDEN, never narrow, the true match set.
  B  sweep      — the stale-or-missing candidates are batch-fetched from the
     Yahoo v7 quote endpoint, the WHOLE sweep inside
     ``asyncio.wait_for(min(60, remaining))``, chunked ≤50 under a semaphore;
     each chunk upserts into the store INCREMENTALLY so a timeout keeps the
     completed work. The cheap criteria re-apply afterwards (now they bite).
     Batch misses retry once on the per-symbol fallback within the budget.
  E  enrich     — SURVIVORS ONLY whose criteria/formula reference a field the
     v7 row cannot supply get a per-symbol ``.info`` fetch (15 s each,
     ``Semaphore(12)``), the whole phase inside ``remaining − 10 s``.
  F  evaluate   — criteria + group + formula + sort + limit, the existing
     semantics, served from the store rows.

On wall expiry or cancellation the run FINALIZES A PARTIAL: unevaluated
symbols are itemized in the skip ledger (reason ``budget_exhausted``),
``partial=True``, ``coverage`` carries the one human line, and ``freshness``
stamps the serving tiers. ``on_progress(phase, done, total, detail)`` fires per
chunk/phase; inside an agent tool dispatch the same frames bridge to
``config.get_step_sink()`` so chat renders a live "sweeping quotes 850/2,100".

Currency note: ``market_cap`` (and every currency-denominated field) is in the
LISTING currency — INR for ``.NS`` / ``.BO`` symbols. A ``market_cap > 1e10``
criterion against india-all means ₹1,000 crore, not $10 B.

The ``custom`` / ``crypto-top50`` universes stay on the per-symbol registry
path (no v7 batch equivalent), cache-first against the same store, under the
same wall budget.

Warm precompute
~~~~~~~~~~~~~~~

:func:`start_warm_precompute` re-warms the S&P 500 batch into the store on an
interval with exponential 429 backoff (state observable in
``_warm_consecutive_throttles``); :mod:`services.fundamentals_warm` runs the
region-aware India warming on the same backoff discipline.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import resources
from typing import Any

import config
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
    SkipDetail,
    StringEqCriterion,
)
from services import (
    data_cache,
    fundamentals_store,
    provider_health,
    provider_registry,
    screener_formula,
    screener_universe_india,
    yahoo_batch_provider,
)
from services.errors import ProviderError
from services.research.models import ResearchStep

logger = logging.getLogger(__name__)

#: Locale-sensible default screener universe per region (Pass B / Pillar A —
#: FR-060). Consulted only when a caller must *choose* a default; an explicit
#: ``ScreenerRequest.universe`` is never overridden.
_DEFAULT_UNIVERSE_BY_REGION: dict[str, ScreenerUniverseId] = {
    "US": "sp500",
    "IN": "nifty50",
    "GLOBAL": "sp500",
}


def default_universe_for_region(region: str | None = None) -> ScreenerUniverseId:
    """Return the locale-sensible default screener universe for ``region``."""
    resolved = region if region is not None else get_region()
    return _DEFAULT_UNIVERSE_BY_REGION.get(resolved, "sp500")


#: How long the resolved ``crypto-top50`` list stays cached before refresh.
_CRYPTO_TOP50_TTL_SECONDS = 24 * 60 * 60

#: Default wall budget for one screener run (R10 / D40). The route and the
#: agent tool both ride this; the SSE stream surfaces progress inside it.
DEFAULT_WALL_BUDGET_SECONDS = 120.0
#: Phase U cap — universe resolution is bundled-JSON instant; 5 s is paranoia.
_UNIVERSE_PHASE_TIMEOUT_SECONDS = 5.0
#: Phase B cap — the whole v7 sweep runs inside min(this, remaining).
_SWEEP_PHASE_CAP_SECONDS = 60.0
#: Reserved tail for evaluate+finalize — phase E gets ``remaining − this``.
_FINALIZE_RESERVE_SECONDS = 10.0
#: Per-symbol ``.info`` enrichment timeout (phase E).
_INFO_TIMEOUT_SECONDS = 15.0
#: Per-symbol fan-out timeout on the fallback path (custom / crypto / retries).
_SYMBOL_TIMEOUT_SECONDS = 30.0
#: Hard upper bound on the request's ``limit`` field.
_MAX_LIMIT = 1000
#: Concurrency cap on per-symbol fetches (fallback + enrichment).
_FETCH_CONCURRENCY = 12
#: Sweep chunk size (mirrors the v7 endpoint's ~50-symbol cap).
_SWEEP_CHUNK_SIZE = 50
#: Concurrent in-flight sweep chunks.
_SWEEP_CONCURRENCY = 8

# --- Warm-universe precompute (R4 / FR-126) ------------------------------------

_WARM_INTERVAL_SECONDS = 40.0
_WARM_UNIVERSES: tuple[ScreenerUniverseId, ...] = ("sp500",)

# --- Warm-loop exponential backoff (self-throttle fix) -------------------------
#
# A warm cycle that comes back rate-limited grows the next sleep geometrically
# (``min(cap, base × factor**n)`` over ``n`` consecutive throttled cycles) with
# ±jitter; the first clean cycle resets to base. Shared discipline: the India
# warm worker (services.fundamentals_warm) imports these same constants +
# ``_warm_sleep_seconds`` rather than duplicating them.
_WARM_BACKOFF_FACTOR = 1.8
_WARM_BACKOFF_CAP_SECONDS = 600.0
_WARM_BACKOFF_JITTER_FRACTION = 0.2
_WARM_THROTTLE_RATIO = 0.5

#: Observable backoff state: consecutive throttled warm cycles.
_warm_consecutive_throttles = 0

#: Universes that take the v7 BATCH fast path. ``custom`` / ``crypto-top50``
#: stay per-symbol (no v7 batch equivalent / arbitrary symbols).
_BATCH_UNIVERSES: frozenset[ScreenerUniverseId] = frozenset(
    {"sp500", "nifty50", "nse-all", "bse-all", "india-all"}
)

#: Progress callback shape: ``(phase, done, total, detail)``.
ProgressFn = Callable[[str, int, int, str], None]


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
        raise ProviderError(f"missing universe snapshot {filename!r}") from exc


async def resolve_universe(
    universe_id: ScreenerUniverseId,
    custom_symbols: list[str] | None = None,
) -> ScreenerUniverse:
    """Return the :class:`ScreenerUniverse` for ``universe_id``.

    A non-empty ``custom_symbols`` list takes precedence over the named
    universe. The India full-market ids resolve from the bundled resolver
    masters (:mod:`services.screener_universe_india`); the curated ids from
    the shipped JSON snapshots; crypto additionally checks the data cache for
    a refreshed list.
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
        raise ProviderError("custom universe requires a non-empty symbol list")

    if screener_universe_india.is_india_universe(universe_id):
        return screener_universe_india.load_india_universe(universe_id)

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
    """Resolve a numeric field's value from a fundamentals+quote pair."""
    if field == "price":
        return quote.price if quote is not None else None
    if field == "change_percent_1d":
        return quote.change_percent if quote is not None else None
    if field == "volume":
        return quote.volume if quote is not None else None
    return getattr(fundamentals, field, None)


def _string_field_value(fundamentals: Fundamentals, quote: Quote | None, field: str) -> str | None:
    """Resolve a string field's value. ``currency`` lives on the quote."""
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

    When ``group`` is given it supersedes the flat ``criteria``; otherwise the
    flat ``criteria`` are AND-combined. Symbols whose ``market_cap`` is unknown
    sort to the end.
    """
    matched: list[ScreenerResultRow] = []
    for fundamentals, quote in rows:
        passed_indices: list[int] = []
        if group is not None:
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
# Criteria field introspection
# ---------------------------------------------------------------------------


def _group_fields(group: CriterionGroup) -> set[str]:
    """Every field referenced anywhere in an AND/OR group tree (recursive)."""
    fields: set[str] = set()
    for node in group.criteria:
        if isinstance(node, CriterionGroup):
            fields |= _group_fields(node)
        else:
            field_name = getattr(node, "field", None)
            if field_name:
                fields.add(field_name)
    return fields


def _criteria_fields(criteria: list[ScreenerCriterion], group: CriterionGroup | None) -> set[str]:
    """Every field referenced by the screen — flat criteria AND the group tree."""
    fields: set[str] = set()
    for criterion in criteria:
        field_name = getattr(criterion, "field", None)
        if field_name:
            fields.add(field_name)
    if group is not None:
        fields |= _group_fields(group)
    return fields


def _enrichment_fields_needed(
    criteria: list[ScreenerCriterion],
    group: CriterionGroup | None,
    formula_fields: frozenset[str] = frozenset(),
) -> set[str]:
    """The screened fields the v7 batch row cannot supply (need ``.info``)."""
    return {
        f
        for f in (_criteria_fields(criteria, group) | set(formula_fields))
        if yahoo_batch_provider.field_needs_enrichment(f)
    }


# ---------------------------------------------------------------------------
# Cheap-criteria extraction (phase P)
# ---------------------------------------------------------------------------

#: String/set fields the store can prune on (seeded sector map / masters).
_CHEAP_STRING_FIELDS = frozenset({"sector", "industry", "symbol"})


def _is_cheap(criterion: ScreenerCriterion) -> bool:
    """True when the store's prefilter can soundly prune on this criterion.

    Numeric criteria are cheap when the field rides the v7/quote tier (no
    ``.info`` needed); string/set criteria when the field is sector / industry
    / symbol (seed-or-master truth). ``currency`` is quote-shaped — phase F.
    """
    if isinstance(criterion, (NumericThresholdCriterion, NumericBetweenCriterion)):
        return not yahoo_batch_provider.field_needs_enrichment(criterion.field)
    if isinstance(criterion, (StringEqCriterion, SetInCriterion)):
        return criterion.field in _CHEAP_STRING_FIELDS
    return False


def _and_leaves(group: CriterionGroup) -> list[ScreenerCriterion]:
    """Leaf criteria that are unconditionally AND-ed by ``group``.

    Recurses through nested AND groups; an OR subtree contributes NOTHING —
    pruning on any of its branches could narrow the match set (a row failing
    one OR branch may pass another, possibly on a not-yet-fetched tier), so
    OR trees never prune. Strictly sound: skipping prune work only widens.
    """
    if group.combinator != "and":
        return []
    leaves: list[ScreenerCriterion] = []
    for node in group.criteria:
        if isinstance(node, CriterionGroup):
            leaves.extend(_and_leaves(node))
        else:
            leaves.append(node)
    return leaves


def _cheap_prune_criteria(
    criteria: list[ScreenerCriterion], group: CriterionGroup | None
) -> list[ScreenerCriterion]:
    """The top-level AND-ed cheap criteria the prefilter may prune on.

    When ``group`` is present it supersedes the flat list at evaluation time,
    so ONLY its AND-ed leaves prune (pruning on the inactive flat list could
    narrow incorrectly). The custom ``formula`` never prunes (expression
    grammar — evaluated in phase F)."""
    source = _and_leaves(group) if group is not None else list(criteria)
    return [c for c in source if _is_cheap(c)]


# ---------------------------------------------------------------------------
# Per-symbol fetch (fallback path + phase E enrichment)
# ---------------------------------------------------------------------------


async def _fetch_pair(
    symbol: str, asset_class: str
) -> tuple[tuple[Fundamentals, Quote | None] | None, str | None]:
    """Fetch ``(Fundamentals, Quote | None)`` for one symbol via the registry.

    Returns ``(pair, skip_reason)``. ``pair is None`` ⇒ the symbol is skipped
    and ``skip_reason`` is a ledger reason. A fundamentals failure is fatal for
    the symbol; a quote failure only drops the price-derived fields.
    """
    if provider_health.is_open(provider_health.YAHOO):
        # D53: the Yahoo family is inside an open cooldown — spend nothing.
        return None, "rate_limited"
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
        if exc.kind == "rate_limited":
            return None, "rate_limited"
        return None, "not_found" if exc.kind == "not_found" else "correctness_gate"
    except Exception as exc:  # noqa: BLE001
        logger.warning("screener: unexpected fundamentals error for %s: %s", symbol, exc)
        return None, "no_data"

    quote: Quote | None = None
    try:
        # provider_registry.get_quote is synchronous — run on a thread.
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


async def _store_pair(symbol: str, pair: tuple[Fundamentals, Quote | None]) -> None:
    """Persist a registry-resolved pair: the rich fundamentals are info-tier
    (a superset of v7), the quote rides the quote tier."""
    fundamentals, quote = pair
    await fundamentals_store.upsert_info(symbol, fundamentals)
    await fundamentals_store.upsert_v7(symbol, fundamentals, quote)


# ---------------------------------------------------------------------------
# Run state + finalization (honest partials)
# ---------------------------------------------------------------------------


@dataclass
class _RunState:
    """Mutable accounting for one screener run, finalizable at ANY phase."""

    universe: ScreenerUniverse
    #: Current candidate set (upper-cased), in universe order.
    candidates: list[str]
    #: Symbols pruned by a FRESH failing cheap criterion — evaluated-as-failed.
    pruned_failed: set[str] = field(default_factory=set)
    #: Skip reasons keyed by upper symbol (provisional until finalize).
    skip_reasons: dict[str, str] = field(default_factory=dict)
    #: True once any phase was cut short (budget / cancellation).
    partial: bool = False
    #: True once any phase observed upstream throttling (R11 / D53).
    throttled_seen: bool = False


def _progress_emitter(on_progress: ProgressFn | None) -> ProgressFn:
    """Compose the caller's ``on_progress`` with the agent step sink (when the
    run executes inside an agent tool dispatch) — both best-effort."""
    sink = config.get_step_sink()

    def emit(phase: str, done: int, total: int, detail: str) -> None:
        if on_progress is not None:
            with contextlib.suppress(Exception):
                on_progress(phase, done, total, detail)
        if sink is not None:
            with contextlib.suppress(Exception):
                sink(ResearchStep(kind="tool", detail=f"screener: {detail}"))

    return emit


#: Quote-tier fields (the trio the store keys off ``quote_*`` columns).
_QUOTE_TRIO = frozenset({"price", "change_percent_1d", "volume"})
#: Fields that are static master/seed truth — always servable, never aged.
_STATIC_FIELDS = frozenset({"sector", "industry", "symbol", "currency"})
#: The v7 valuation tier's field set (mirrors the store's write vocabulary).
_V7_FIELD_SET = frozenset(fundamentals_store._V7_NUMERIC_FIELDS)


def _field_serving(
    row: dict[str, Any],
    field_name: str,
    now: float,
    quote_ttl: float,
) -> tuple[bool, float | None, bool]:
    """How a NON-NULL ``field_name`` value on ``row`` is being served (D52).

    Returns ``(is_live, age_stamp, used_seed)``:
      - ``is_live`` — the value's own tier stamp is within its serving TTL
        (an exchange-direct EOD stamp counts as live for the quote trio and
        ``market_cap`` — it is today's close, honestly timestamped).
      - ``age_stamp`` — the epoch stamp that dates the value (``None`` for
        static fields or a value with no recorded stamp).
      - ``used_seed`` — the value's only provenance is the bundled snapshot.
    """
    if field_name in _STATIC_FIELDS:
        return True, None, False
    v7_at = row.get("v7_updated_at")
    info_at = row.get("info_updated_at")
    seed_at = row.get("seed_updated_at")
    eod_at = row.get("eod_updated_at")
    quote_at = row.get("quote_updated_at")

    if field_name in _QUOTE_TRIO:
        if quote_at is not None and now - quote_at <= quote_ttl:
            return True, quote_at, False
        if eod_at is not None and now - eod_at <= fundamentals_store.TTL_EOD_SECONDS:
            return True, eod_at, False
        stamp = quote_at or eod_at or seed_at
        return False, stamp, quote_at is None and eod_at is None and seed_at is not None
    if field_name in _V7_FIELD_SET:
        if v7_at is not None and now - v7_at <= fundamentals_store.TTL_V7_SECONDS:
            return True, v7_at, False
        if (
            field_name == "market_cap"
            and eod_at is not None
            and now - eod_at <= fundamentals_store.TTL_EOD_SECONDS
        ):
            # The bhavcopy lane refreshes market_cap (close × shares) daily.
            return True, eod_at, False
        stamp = v7_at or seed_at
        return False, stamp, v7_at is None and seed_at is not None
    # Deep .info tier.
    if info_at is not None and now - info_at <= fundamentals_store.TTL_INFO_SECONDS:
        return True, info_at, False
    stamp = info_at or seed_at
    return False, stamp, info_at is None and seed_at is not None


def _row_has_any_data(row: dict[str, Any]) -> bool:
    """True when the row carries at least one data tier (live, EOD, or seed)
    — an identity-only row (name/sector but zero numerics provenance) is not
    servable and stays itemized exactly as before D52."""
    return any(
        row.get(stamp) is not None
        for stamp in (
            "v7_updated_at",
            "info_updated_at",
            "quote_updated_at",
            "eod_updated_at",
            "seed_updated_at",
        )
    )


async def _finalize(
    req: ScreenerRequest,
    state: _RunState,
    compiled_formula: Any,
    needed_fields: set[str],
    started_at: float,
) -> ScreenerResult:
    """Materialize the result from the store — works mid-run for partials.

    R11 (D52) serve-with-label ladder: a row whose live tiers are stale (or
    never fetched) is no longer dropped when its values are still present from
    an earlier fetch or the bundled seed pack — it is EVALUATED and served
    with an honest ``data_basis``/``data_as_of`` label. Only rows with zero
    data provenance, or NULL values for a field the screen references, are
    itemized as skips."""
    rows_by_symbol = await fundamentals_store.fetch_rows(state.candidates)
    now = time.time()
    quote_ttl = (
        fundamentals_store.TTL_QUOTE_FULL_SECONDS
        if screener_universe_india.is_india_universe(req.universe)
        else fundamentals_store.TTL_QUOTE_CURATED_SECONDS
    )
    formula_fields = compiled_formula.fields if compiled_formula is not None else frozenset()
    # Basis is judged over the fields the screen USED plus the two every row
    # displays regardless (the sort key and the price column) — a row whose
    # only price is a stale one must not read as "live".
    basis_fields = (
        _criteria_fields(list(req.criteria), req.group)
        | set(formula_fields)
        | {"market_cap", "price"}
    )

    pairs_by_symbol: dict[str, tuple[Fundamentals, Quote | None]] = {}
    #: Per-symbol honesty labels for rows that reach evaluation.
    row_basis: dict[str, str] = {}
    row_as_of: dict[str, float | None] = {}
    seed_stamps_used: list[float] = []
    for sym in state.candidates:
        key = sym.upper()
        row = rows_by_symbol.get(key)
        if row is None or not _row_has_any_data(row):
            # Never fetched and not in the seed pack — itemized, never served.
            # A reason recorded during the sweep / fallback sticks; otherwise
            # a partial run owns the miss (budget_exhausted), a complete one
            # is no_data.
            state.skip_reasons.setdefault(key, "budget_exhausted" if state.partial else "no_data")
            continue
        absent = next(
            (f for f in sorted(needed_fields) if row.get(f) is None),
            None,
        )
        if absent is not None:
            state.skip_reasons[key] = f"missing_field:{absent}"
            continue
        live_count = 0
        aged = 0
        stale_stamps: list[float] = []
        for field_name in basis_fields:
            if field_name in _STATIC_FIELDS:
                continue
            column = fundamentals_store._field_column(field_name)
            if row.get(column) is None:
                continue
            is_live, age_stamp, used_seed = _field_serving(row, field_name, now, quote_ttl)
            aged += 1
            if is_live:
                live_count += 1
            elif age_stamp is not None:
                stale_stamps.append(age_stamp)
                if used_seed:
                    seed_stamps_used.append(age_stamp)
        if aged == 0 or live_count == aged:
            row_basis[key] = "live"
            row_as_of[key] = None
        else:
            row_basis[key] = "mixed" if live_count > 0 else "snapshot"
            row_as_of[key] = min(stale_stamps) if stale_stamps else None
        pairs_by_symbol[key] = fundamentals_store.row_to_pair(row)
        state.skip_reasons.pop(key, None)

    # Custom formula — AND semantics; a row missing a referenced field is
    # itemized, a rejected row stays in the evaluated count.
    formula_rejected: set[str] = set()
    if compiled_formula is not None:
        for key, (fundamentals, quote) in list(pairs_by_symbol.items()):
            matched_row, missing = screener_formula.evaluate_formula(
                compiled_formula, fundamentals, quote
            )
            if missing is not None:
                pairs_by_symbol.pop(key)
                state.skip_reasons[key] = f"missing_field:{missing}"
            elif not matched_row:
                formula_rejected.add(key)

    matched = apply_criteria(
        [pair for key, pair in pairs_by_symbol.items() if key not in formula_rejected],
        list(req.criteria),
        group=req.group,
    )
    limit = max(1, min(int(req.limit), _MAX_LIMIT))
    rows = matched[:limit]

    # R11 (D52/D57): stamp every served row with its honesty labels — the
    # listing currency and the serving basis computed above.
    basis_counts: dict[str, int] = {}
    for result_row in rows:
        key = result_row.symbol.upper()
        store_row = rows_by_symbol.get(key) or {}
        result_row.currency = store_row.get("currency") or store_row.get("quote_currency")
        result_row.data_basis = row_basis.get(key)
        result_row.data_as_of = row_as_of.get(key)
        if result_row.data_basis:
            basis_counts[result_row.data_basis] = basis_counts.get(result_row.data_basis, 0) + 1

    # Itemized skip ledger (SC-034 — zero silent drops). A symbol is skipped
    # iff it neither produced an evaluable pair nor failed a fresh prune.
    evaluated = set(pairs_by_symbol) | state.pruned_failed
    skip_details: list[SkipDetail] = []
    for sym in state.universe.symbols:
        key = sym.upper()
        if key not in evaluated:
            default = "budget_exhausted" if state.partial else "no_data"
            skip_details.append(SkipDetail(symbol=key, reason=state.skip_reasons.get(key, default)))

    evaluated_count = len(pairs_by_symbol) + len(state.pruned_failed)
    total = len(state.universe.symbols)
    coverage = f"screened {evaluated_count:,} of {total:,} — {len(skip_details):,} unavailable"
    not_live = basis_counts.get("snapshot", 0) + basis_counts.get("mixed", 0)
    stale_as_of = [stamp for stamp in row_as_of.values() if stamp is not None]
    if not_live and stale_as_of:
        oldest = datetime.fromtimestamp(min(stale_as_of), tz=UTC).date().isoformat()
        coverage += f" · {not_live:,} rows on stale/snapshot basis (oldest {oldest})"
    freshness = await fundamentals_store.freshness(list(pairs_by_symbol)) or None
    if seed_stamps_used:
        freshness = dict(freshness or {})
        freshness["seed_as_of"] = min(seed_stamps_used)

    # ``partial`` now means "rows remain UNEVALUATED": a budget-cut run whose
    # every row still served (live or labeled stale/snapshot) evaluated the
    # whole universe — the honesty rides ``data_basis``/``throttled``, not a
    # contradictory partial flag (D52).
    partial = state.partial and bool(skip_details)
    throttled = state.throttled_seen or provider_health.is_open(provider_health.YAHOO)

    duration_ms = (time.monotonic() - started_at) * 1000.0
    return ScreenerResult(
        universe=req.universe,
        evaluated_count=evaluated_count,
        skipped_count=len(skip_details),
        skip_details=skip_details,
        result_count=len(rows),
        rows=rows,
        duration_ms=duration_ms,
        partial=partial,
        coverage=coverage,
        freshness=freshness,
        basis_counts=basis_counts or None,
        throttled=throttled,
    )


# ---------------------------------------------------------------------------
# Phase B — budgeted v7 batch sweep
# ---------------------------------------------------------------------------


async def _sweep_v7(
    stale: list[str],
    budget_s: float,
    state: _RunState,
    emit: ProgressFn,
) -> None:
    """Sweep the stale candidates through the v7 batch endpoint into the store.

    The WHOLE sweep runs inside ``asyncio.wait_for(budget_s)`` — chunks of
    ≤50 under a semaphore, each chunk upserting incrementally so a timeout
    keeps every completed chunk. Batch misses land in ``state.skip_reasons``
    PROVISIONALLY (the fallback retries them)."""
    if not stale or budget_s <= 0:
        if stale:
            state.partial = True
        return
    chunks = [stale[i : i + _SWEEP_CHUNK_SIZE] for i in range(0, len(stale), _SWEEP_CHUNK_SIZE)]
    sem = asyncio.Semaphore(_SWEEP_CONCURRENCY)
    done = 0
    total = len(stale)

    async def _one(chunk: list[str]) -> None:
        nonlocal done
        async with sem:
            rows, failures = await yahoo_batch_provider.fetch_quotes_batch(chunk)
        if any(reason == "rate_limited" for reason in failures.values()):
            state.throttled_seen = True
        items: list[tuple[str, Fundamentals, Quote | None]] = []
        for sym in chunk:
            key = sym.upper()
            row = rows.get(key)
            if row is None:
                state.skip_reasons[key] = failures.get(sym, "not_found")
                continue
            quote = yahoo_batch_provider.quote_from_v7(row)
            if quote is None:
                state.skip_reasons[key] = "no_data"
                continue
            items.append((key, yahoo_batch_provider.fundamentals_from_v7(row), quote))
            state.skip_reasons.pop(key, None)
        # One store transaction per chunk — per-symbol connect+commit cost
        # ~1.4 ms each (~7 s serialized over a cold 5k-symbol india sweep).
        await fundamentals_store.upsert_v7_batch(items)
        done += len(chunk)
        emit("sweep", done, total, f"sweeping quotes {done:,}/{total:,}")

    try:
        await asyncio.wait_for(asyncio.gather(*(_one(c) for c in chunks)), timeout=budget_s)
    except TimeoutError:
        state.partial = True
        logger.warning(
            "screener: v7 sweep hit its %.0fs budget at %d/%d symbols — partial",
            budget_s,
            done,
            total,
        )


async def _fallback_retry(
    symbols: list[str],
    asset_class: str,
    budget_s: float,
    state: _RunState,
    emit: ProgressFn,
) -> None:
    """Per-symbol registry retry for batch misses, inside ``budget_s``.

    A recovered symbol lands in the store (info+quote tiers) and clears its
    provisional skip; a failed retry's reason supersedes the provisional one."""
    if not symbols or budget_s <= 0:
        if symbols:
            state.partial = True
        return
    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
    done = 0
    total = len(symbols)

    async def _one(sym: str) -> None:
        nonlocal done
        async with sem:
            pair, reason = await _fetch_pair(sym, asset_class)
        key = sym.upper()
        if pair is not None:
            await _store_pair(key, pair)
            state.skip_reasons.pop(key, None)
        elif reason is not None:
            state.skip_reasons[key] = reason
            if reason == "rate_limited":
                state.throttled_seen = True
        done += 1
        if done % 25 == 0 or done == total:
            emit("sweep", done, total, f"retrying misses {done:,}/{total:,}")

    try:
        await asyncio.wait_for(asyncio.gather(*(_one(s) for s in symbols)), timeout=budget_s)
    except TimeoutError:
        state.partial = True
        logger.warning("screener: fallback retry hit its budget at %d/%d", done, total)


# ---------------------------------------------------------------------------
# Phase E — targeted .info enrichment of survivors
# ---------------------------------------------------------------------------


async def _enrich_survivors(
    needed: set[str],
    budget_s: float,
    state: _RunState,
    emit: ProgressFn,
) -> None:
    """Per-symbol ``.info`` enrichment of SURVIVORS whose store row lacks a
    needed field — 15 s per symbol, ``Semaphore(12)``, whole phase inside
    ``budget_s``. A symbol still missing a needed field after enrichment is
    itemized ``missing_field:<f>`` at finalize (phase F checks the row)."""
    if not needed:
        return
    rows = await fundamentals_store.fetch_rows(state.candidates)
    to_enrich = [
        sym
        for sym in state.candidates
        if sym.upper() not in state.skip_reasons
        and any((rows.get(sym.upper()) or {}).get(f) is None for f in needed)
    ]
    if not to_enrich:
        return
    if budget_s <= 0:
        state.partial = True
        return
    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
    done = 0
    total = len(to_enrich)

    async def _one(sym: str) -> None:
        nonlocal done
        key = sym.upper()
        if provider_health.is_open(provider_health.YAHOO):
            # D53: open circuit — the field stays missing and the serve-with-
            # label ladder covers the row from stale/seed basis instead.
            state.throttled_seen = True
            done += 1
            return
        async with sem:
            try:
                rich = await asyncio.wait_for(
                    provider_registry.get_fundamentals(key),
                    timeout=_INFO_TIMEOUT_SECONDS,
                )
            except (TimeoutError, Exception) as exc:  # noqa: BLE001 — field stays missing
                if isinstance(exc, ProviderError) and exc.kind == "rate_limited":
                    state.throttled_seen = True
                logger.debug("screener: enrichment failed for %s: %s", key, exc)
                done += 1
                return
        await fundamentals_store.upsert_info(key, rich)
        done += 1
        if done % 10 == 0 or done == total:
            emit("enrich", done, total, f"enriching fundamentals {done:,}/{total:,}")

    try:
        await asyncio.wait_for(asyncio.gather(*(_one(s) for s in to_enrich)), timeout=budget_s)
    except TimeoutError:
        state.partial = True
        logger.warning("screener: enrichment hit its budget at %d/%d", done, total)


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------


async def run_screener(
    req: ScreenerRequest,
    *,
    wall_budget_s: float = DEFAULT_WALL_BUDGET_SECONDS,
    on_progress: ProgressFn | None = None,
) -> ScreenerResult:
    """Run the phased screener under a wall budget (see module docstring).

    Returns up to ``req.limit`` rows sorted by market cap desc. Every dropped
    symbol is itemized in ``skip_details``; ``skipped_count ==
    len(skip_details)`` always. On wall expiry or task cancellation the run
    finalizes an honest PARTIAL (``partial=True`` + ``coverage`` +
    ``budget_exhausted`` skips) instead of hanging or vanishing.
    """
    started_at = time.monotonic()
    deadline = started_at + max(1.0, wall_budget_s)

    def remaining() -> float:
        return max(0.0, deadline - time.monotonic())

    emit = _progress_emitter(on_progress)

    universe = await asyncio.wait_for(
        resolve_universe(req.universe, req.custom_symbols),
        timeout=min(_UNIVERSE_PHASE_TIMEOUT_SECONDS, max(0.1, remaining())),
    )
    emit("universe", 1, 1, f"{universe.label}: {len(universe.symbols):,} symbols")

    criteria = list(req.criteria)
    group = req.group
    compiled_formula = (
        screener_formula.compile_formula(req.formula)
        if req.formula and req.formula.strip()
        else None
    )
    formula_fields = compiled_formula.fields if compiled_formula is not None else frozenset()
    needed_fields = _enrichment_fields_needed(criteria, group, formula_fields)

    state = _RunState(
        universe=universe,
        candidates=[s.upper() for s in universe.symbols],
    )

    # The background .info crawler pauses while a foreground screen runs.
    from services import fundamentals_warm

    fundamentals_warm.screen_started()
    try:
        try:
            if universe.id in _BATCH_UNIVERSES and universe.asset_class == "equity":
                await _run_batch_phases(req, universe, state, needed_fields, remaining, emit)
            else:
                await _run_per_symbol(universe, state, remaining, emit)
        except asyncio.CancelledError:
            # Client disconnect / task cancel — finalize the partial honestly.
            # The store keeps every chunk that completed; uncancel() clears the
            # pending cancellation so the result can be delivered.
            state.partial = True
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                task.uncancel()
            logger.info("screener: run cancelled — finalizing partial")
    finally:
        fundamentals_warm.screen_finished()

    emit("evaluate", 1, 1, f"evaluating {len(state.candidates):,} candidates")
    return await _finalize(req, state, compiled_formula, needed_fields, started_at)


async def _run_batch_phases(
    req: ScreenerRequest,
    universe: ScreenerUniverse,
    state: _RunState,
    needed_fields: set[str],
    remaining: Callable[[], float],
    emit: ProgressFn,
) -> None:
    """Phases P → B → E for the batch universes (curated + India full-market)."""
    is_full = screener_universe_india.is_india_universe(universe.id)
    quote_ttl = (
        fundamentals_store.TTL_QUOTE_FULL_SECONDS
        if is_full
        else fundamentals_store.TTL_QUOTE_CURATED_SECONDS
    )

    # Phase P — sound SQL prune on the top-level AND-ed cheap criteria. The
    # universe's serving quote TTL rides along so a curated screen never
    # prunes on a quote older than its own 45 s tier.
    cheap = _cheap_prune_criteria(list(req.criteria), req.group)
    if cheap:
        before = len(state.candidates)
        kept = await fundamentals_store.prefilter(state.candidates, cheap, quote_ttl=quote_ttl)
        state.pruned_failed |= set(state.candidates) - set(kept)
        state.candidates = kept
        emit("prefilter", len(kept), before, f"prefilter kept {len(kept):,} of {before:,}")

    # Phase B — budgeted sweep of the stale-or-missing candidates.
    stale = await fundamentals_store.stale_symbols(state.candidates, quote_ttl=quote_ttl)
    if stale:
        await _sweep_v7(stale, min(_SWEEP_PHASE_CAP_SECONDS, remaining()), state, emit)

    # Re-apply the cheap criteria — fresh post-sweep values prune properly now.
    if cheap:
        before = len(state.candidates)
        kept = await fundamentals_store.prefilter(state.candidates, cheap, quote_ttl=quote_ttl)
        if len(kept) != before:
            newly_pruned = set(state.candidates) - set(kept)
            # A symbol whose sweep failed is a SKIP, not an evaluated-fail.
            state.pruned_failed |= {s for s in newly_pruned if s not in state.skip_reasons}
            state.candidates = kept
            emit("prefilter", len(kept), before, f"post-sweep prune kept {len(kept):,}")

    # Batch misses retry once on the per-symbol fallback (graceful degrade;
    # it may resolve a symbol the endpoint truncated or a missing field).
    misses = [s for s in state.candidates if s in state.skip_reasons]
    if misses:
        await _fallback_retry(
            misses,
            universe.asset_class,
            max(0.0, remaining() - _FINALIZE_RESERVE_SECONDS),
            state,
            emit,
        )

    # Phase E — targeted enrichment of survivors only.
    await _enrich_survivors(
        needed_fields,
        max(0.0, remaining() - _FINALIZE_RESERVE_SECONDS),
        state,
        emit,
    )


async def _run_per_symbol(
    universe: ScreenerUniverse,
    state: _RunState,
    remaining: Callable[[], float],
    emit: ProgressFn,
) -> None:
    """The per-symbol registry path (custom / crypto) — cache-first against
    the store, the whole fan-out inside the wall budget."""
    rows = await fundamentals_store.fetch_rows(state.candidates)
    now = time.time()
    to_fetch: list[str] = []
    for sym in state.candidates:
        row = rows.get(sym.upper())
        info_at = (row or {}).get("info_updated_at")
        quote_at = (row or {}).get("quote_updated_at")
        if (
            row is None
            or info_at is None
            or now - info_at > fundamentals_store.TTL_INFO_SECONDS
            or quote_at is None
            or now - quote_at > fundamentals_store.TTL_QUOTE_CURATED_SECONDS
        ):
            to_fetch.append(sym)
    if not to_fetch:
        return
    budget = max(0.0, remaining() - _FINALIZE_RESERVE_SECONDS)
    if budget <= 0:
        state.partial = True
        return
    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
    done = 0
    total = len(to_fetch)

    async def _one(sym: str) -> None:
        nonlocal done
        async with sem:
            pair, reason = await _fetch_pair(sym, universe.asset_class)
        key = sym.upper()
        if pair is not None:
            await _store_pair(key, pair)
        elif reason is not None:
            state.skip_reasons[key] = reason
        done += 1
        if done % 10 == 0 or done == total:
            emit("sweep", done, total, f"fetching {done:,}/{total:,}")

    try:
        await asyncio.wait_for(asyncio.gather(*(_one(s) for s in to_fetch)), timeout=budget)
    except TimeoutError:
        state.partial = True
        logger.warning("screener: per-symbol fan-out hit the wall at %d/%d", done, total)


# ---------------------------------------------------------------------------
# Warm-universe precompute worker (R4 / FR-126)
# ---------------------------------------------------------------------------

_warm_task: asyncio.Task[None] | None = None


async def _warm_once() -> bool:
    """Pre-warm one batch cycle over the warm universes into the store.

    Returns ``True`` when the cycle was RATE-LIMITED (≥ ``_WARM_THROTTLE_RATIO``
    of warmed symbols came back ``rate_limited``) — the loop's backoff signal."""
    requested = 0
    rate_limited = 0
    for universe_id in _WARM_UNIVERSES:
        try:
            universe = await resolve_universe(universe_id)
        except ProviderError as exc:
            logger.debug("screener warm: cannot resolve %s: %s", universe_id, exc)
            continue
        symbols = list(universe.symbols)
        requested += len(symbols)
        rows, failures = await yahoo_batch_provider.fetch_quotes_batch(symbols)
        rate_limited += sum(1 for reason in failures.values() if reason == "rate_limited")
        items = []
        for _sym, row in rows.items():
            quote = yahoo_batch_provider.quote_from_v7(row)
            if quote is not None:
                items.append((quote.symbol, yahoo_batch_provider.fundamentals_from_v7(row), quote))
        await fundamentals_store.upsert_v7_batch(items)
    return requested > 0 and rate_limited >= requested * _WARM_THROTTLE_RATIO


def _warm_sleep_seconds(base: float, consecutive_throttles: int) -> float:
    """Jittered next-cycle sleep for a warm loop given the throttle streak.

    ``consecutive_throttles == 0`` → ``base`` (+jitter). Each additional
    consecutive throttled cycle multiplies the sleep by ``_WARM_BACKOFF_FACTOR``
    (capped at ``_WARM_BACKOFF_CAP_SECONDS``); ±jitter de-synchronises a fleet.
    Shared by the India warm worker (:mod:`services.fundamentals_warm`)."""
    target = min(
        _WARM_BACKOFF_CAP_SECONDS,
        base * (_WARM_BACKOFF_FACTOR**consecutive_throttles),
    )
    jitter = target * _WARM_BACKOFF_JITTER_FRACTION
    return max(0.0, target + random.uniform(-jitter, jitter))


async def _warm_loop(interval: float) -> None:
    """Background loop: warm immediately, then re-warm with adaptive backoff.

    R11 (D53): a cycle is skipped outright while a foreground screen is
    running (the user's run owns the upstream — warming beside it was
    self-inflicted throttle pressure) or while the Yahoo circuit is open."""
    from services import fundamentals_warm

    global _warm_consecutive_throttles
    _warm_consecutive_throttles = 0
    try:
        while True:
            if fundamentals_warm.foreground_screen_running() or provider_health.is_open(
                provider_health.YAHOO
            ):
                await asyncio.sleep(_warm_sleep_seconds(interval, 0))
                continue
            try:
                throttled = await _warm_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — a warm cycle is best-effort
                logger.debug("screener warm cycle failed: %s", exc)
                throttled = False

            if throttled:
                _warm_consecutive_throttles += 1
                sleep_s = _warm_sleep_seconds(interval, _warm_consecutive_throttles)
                logger.warning(
                    "screener warm: rate-limited (consecutive throttled cycles=%d); "
                    "backing off %.0fs before the next warm (base=%.0fs, cap=%.0fs)",
                    _warm_consecutive_throttles,
                    sleep_s,
                    interval,
                    _WARM_BACKOFF_CAP_SECONDS,
                )
            else:
                if _warm_consecutive_throttles > 0:
                    logger.info(
                        "screener warm: clean cycle after %d throttled; "
                        "backoff reset to base (%.0fs)",
                        _warm_consecutive_throttles,
                        interval,
                    )
                _warm_consecutive_throttles = 0
                sleep_s = _warm_sleep_seconds(interval, 0)

            await asyncio.sleep(sleep_s)
    except asyncio.CancelledError:
        logger.debug("screener warm loop cancelled")
        raise


def start_warm_precompute(interval: float = _WARM_INTERVAL_SECONDS) -> None:
    """Start the warm-precompute background task (idempotent)."""
    global _warm_task
    if _warm_task is not None and not _warm_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("screener warm: no running loop; precompute not started")
        return
    _warm_task = loop.create_task(_warm_loop(interval))


async def stop_warm_precompute() -> None:
    """Cancel + await the warm-precompute task, then close the batch client."""
    global _warm_task
    task = _warm_task
    _warm_task = None
    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
    await yahoo_batch_provider.aclose()


__all__ = [
    "DEFAULT_WALL_BUDGET_SECONDS",
    "apply_criteria",
    "default_universe_for_region",
    "resolve_universe",
    "run_screener",
    "start_warm_precompute",
    "stop_warm_precompute",
]
