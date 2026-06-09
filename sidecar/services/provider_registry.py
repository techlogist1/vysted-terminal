"""Provider registry — the single dispatch point routers call into.

Routers never import a concrete provider directly; they call the registry, which
resolves the right provider for each request. FR-035/FR-053: dispatch is no
longer a hardcoded ``if asset_class`` switch — it is a resolver keyed by a
STANDARD MODEL KEY (``quote``, ``ohlcv``, ``fundamentals``, ``income_statement``,
…) that walks installed providers in a PREFERENCE ORDER, trying each until one
succeeds. ``asset_class`` becomes a resolution *hint*, not the switch.

This mirrors :mod:`services.agent_tools.catalog`'s "declare once, project to
many": a small in-module table of :class:`ProviderDeclaration` rows (id, the
model-keys it serves, a preference rank, a credential/availability gate, the
asset-class hints it answers) is the single source of truth. :func:`active_providers`
(surfaced at ``/health``) is DERIVED from that table — never a hand-maintained dict.

Provenance lives on every result model (the ``provider`` field each provider
sets). The resolver never overwrites it: whichever provider actually served the
request (after any fallback) is the one named in the field.

The public accessor signatures are UNCHANGED so every router stays untouched:
``get_quote``/``get_history`` stay synchronous (their providers — ccxt, yfinance
— are sync, and callers wrap them in ``asyncio.to_thread``); the openbb-backed
methods stay ``async``. Two resolvers — one sync, one async — share the same
declaration table and the same preference-order fallthrough.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import config
from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
)
from models.market import MacroSeries, OHLCVSeries, Quote
from services import (
    bse_provider,
    ccxt_provider,
    correctness_gate,
    india_provider,
    nse_provider,
    openbb_mcp_provider,
    symbol_resolver,
    yfinance_provider,
)
from services.errors import ProviderError

DEFAULT_CRYPTO_EXCHANGE = "binance"

_log = logging.getLogger(__name__)

# Standard model keys — the resolver's routing vocabulary (FR-035). Every public
# accessor maps to exactly one. Asset class is a *hint* layered on top, not a key.
ModelKey = Literal[
    "quote",
    "ohlcv",
    "fundamentals",
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "analyst_rating",
    "macro_series",
]


# ---------------------------------------------------------------------------
# Provider declarations — declared once, projected to the resolver + /health.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderDeclaration:
    """One installed data provider — the single declaration the resolver reads.

    ``serves`` maps each model-key it can answer to the bound accessor (sync or
    async). ``rank`` is the preference order *within* a model-key (lower wins).
    ``requires`` is a no-arg predicate gating availability (e.g. an MCP plugin
    being bundled); when it returns ``False`` the provider is skipped entirely.
    ``asset_classes`` narrows which asset-class hints the provider answers
    (empty = any). ``region`` narrows which locales the provider serves (empty =
    any region) — the seam that routes an NSE request to the India provider and
    keeps it out of a US request (FR-060/064).
    """

    id: str
    serves: dict[str, Callable[..., Any]]
    rank: int = 100
    requires: Callable[[], bool] | None = None
    asset_classes: frozenset[str] = field(default_factory=frozenset)
    region: frozenset[str] = field(default_factory=frozenset)

    def available(self) -> bool:
        return self.requires is None or bool(self.requires())

    def serves_asset_class(self, asset_class: str | None) -> bool:
        return not self.asset_classes or asset_class is None or asset_class in self.asset_classes

    def serves_region(self, region: str | None) -> bool:
        return not self.region or region is None or region in self.region


# The ``serves`` callables and ``requires`` predicates dispatch through the
# provider MODULE at invocation time (``lambda *a: module.fn(*a)``) rather than
# binding the function object at declaration time — so the live attribute is
# always used (and tests that monkeypatch a provider module reach the resolver).
_PROVIDERS: tuple[ProviderDeclaration, ...] = (
    # crypto market data — preferred for the crypto asset-class hint only.
    ProviderDeclaration(
        id="ccxt",
        rank=10,
        asset_classes=frozenset({"crypto"}),
        serves={
            "quote": lambda symbol: ccxt_provider.get_ticker(DEFAULT_CRYPTO_EXCHANGE, symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: ccxt_provider.get_ohlcv(
                DEFAULT_CRYPTO_EXCHANGE, symbol, timeframe
            ),
        },
    ),
    # openbb-mcp — preferred for fundamentals/statements/analyst/macro when bundled.
    ProviderDeclaration(
        id="openbb-mcp",
        rank=10,
        requires=lambda: openbb_mcp_provider.is_available(),
        serves={
            "fundamentals": lambda symbol: openbb_mcp_provider.get_fundamentals(symbol),
            "income_statement": lambda symbol: openbb_mcp_provider.get_income_statement(symbol),
            "balance_sheet": lambda symbol: openbb_mcp_provider.get_balance_sheet(symbol),
            "cash_flow": lambda symbol: openbb_mcp_provider.get_cash_flow(symbol),
            "analyst_rating": lambda symbol: openbb_mcp_provider.get_analyst_rating(symbol),
            "macro_series": lambda series_id, provider=None: openbb_mcp_provider.get_macro_series(
                series_id, provider=provider
            ),
        },
    ),
    # nse_direct — the exchange-direct anti-bot lane (curl_cffi cookie dance,
    # R7 Component 2), region-scoped to IN and ranked ABOVE the jugaad lane
    # (nse, 20): when www.nseindia.com serves us directly we prefer the
    # first-party EOD rows; any block/throttle/circuit-open falls through to
    # jugaad → bse → gated yfinance. Serves quote + ohlcv only.
    ProviderDeclaration(
        id="nse_direct",
        rank=15,
        requires=lambda: nse_provider.is_available(),
        asset_classes=frozenset({"equity"}),
        region=frozenset({"IN"}),
        serves={
            "quote": lambda symbol: nse_provider.get_quote(symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: nse_provider.get_history(
                symbol, timeframe, range_
            ),
        },
    ),
    # nse (jugaad-data) — the keyless India equity/ETF default, region-scoped to
    # IN and ranked ABOVE yfinance so a `.NS`/`.BO` request is served by the
    # locale-correct EOD source, not documented-unreliable yfinance (#2612/#2055).
    # Serves quote + ohlcv only; IN fundamentals fall through to yfinance.
    ProviderDeclaration(
        id="nse",
        rank=20,
        requires=lambda: india_provider.is_available(),
        asset_classes=frozenset({"equity"}),
        region=frozenset({"IN"}),
        serves={
            "quote": lambda symbol: india_provider.get_quote(symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: india_provider.get_history(
                symbol, timeframe, range_
            ),
        },
    ),
    # bse — the keyless India MICRO-CAP EOD default (the B/X/XT/T/Z groups NSE
    # never listed), region-scoped to IN and ranked BETWEEN nse (20) and yfinance
    # (50): a bare BSE-only ticker (or a `.BO` request) resolves to IN and is
    # served EOD from the daily BhavCopy cache, not documented-unreliable yfinance
    # (#2612/#2055). Serves quote + ohlcv only (mirrors nse); IN fundamentals fall
    # through to yfinance. nse still wins for a dual-listed name (lower rank).
    ProviderDeclaration(
        id="bse",
        rank=25,
        requires=lambda: bse_provider.is_available(),
        asset_classes=frozenset({"equity"}),
        region=frozenset({"IN"}),
        serves={
            "quote": lambda symbol: bse_provider.get_quote(symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: bse_provider.get_history(
                symbol, timeframe, range_
            ),
        },
    ),
    # yfinance — the broad equity default + fallback for fundamentals/statements/
    # analyst when openbb-mcp is absent or errors. No macro equivalent. Serves any
    # region (the US default *and* the gated last-resort for IN behind `nse`).
    ProviderDeclaration(
        id="yfinance",
        rank=50,
        asset_classes=frozenset({"equity"}),
        serves={
            "quote": lambda symbol: yfinance_provider.get_quote(symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: yfinance_provider.get_history(
                symbol, timeframe, range_
            ),
            "fundamentals": lambda symbol: yfinance_provider.get_fundamentals(symbol),
            "income_statement": lambda symbol: yfinance_provider.get_income_statement(symbol),
            "balance_sheet": lambda symbol: yfinance_provider.get_balance_sheet(symbol),
            "cash_flow": lambda symbol: yfinance_provider.get_cash_flow(symbol),
            "analyst_rating": lambda symbol: yfinance_provider.get_analyst_rating(symbol),
        },
    ),
)


# A validator applied to a provider's result before it is accepted (the
# correctness gate, FR-063). It returns the value on success or raises a
# CorrectnessError (a ProviderError) to advance to the next provider.
Validator = Callable[[Any], Any]

# An acceptor decides whether a VALID result is also COMPLETE enough to return,
# or whether the registry should try the next (richer) provider. Distinct from a
# Validator: a validator rejects a WRONG result (raises → fall through); an
# acceptor declines an INCOMPLETE-but-correct result (returns False → try next,
# but keep it as the fallback if no richer provider exists). Used for the
# openbb→yfinance fundamentals enrichment below.
Acceptor = Callable[[Any], bool]

# The profitability / financial-health / growth fields the screener's numeric
# criteria + the curated presets rely on. openbb-mcp serves valuation (pe,
# market-cap, dividend) but does not populate these, so a fundamentals result
# with NONE of them is treated as "incomplete" — the registry falls through to
# the richer yfinance path that does populate them (fixing the empty screener /
# equity overview + the 5 empty presets). Kept as a tuple so the acceptor below
# and any future caller share one definition.
_SCREENER_GRADE_FIELDS: tuple[str, ...] = (
    "roe",
    "roa",
    "profit_margin",
    "operating_margin",
    "gross_margin",
    "debt_to_equity",
    "current_ratio",
    "quick_ratio",
    "revenue_growth",
    "earnings_growth",
)


def _fundamentals_screener_complete(result: Any) -> bool:
    """True when a fundamentals result carries at least one screener-grade field.

    A result missing ALL of :data:`_SCREENER_GRADE_FIELDS` (the openbb-mcp case
    for nearly every symbol) is incomplete → the registry tries the next provider
    (yfinance), which populates them. If every provider is sparse, the highest-
    ranked partial is still returned (never a hard failure)."""
    return any(getattr(result, field, None) is not None for field in _SCREENER_GRADE_FIELDS)


def _effective_region(symbol: str | None, region: str | None) -> str:
    """Resolve the region a request should route to.

    Precedence: an explicit ``region`` arg → the symbol's intrinsic region (a
    ``.NS`` suffix or an unambiguous master membership) → the active request
    region (``config.get_region()``). So ``GOLDBEES`` routes to IN even in a US
    session, while an ambiguous bare ticker defers to the user's locale.
    """
    if region:
        return config.normalize_region(region)
    if symbol:
        hint = symbol_resolver.region_hint(symbol)
        if hint:
            return hint
    return config.get_region()


def _candidates(
    model_key: ModelKey, asset_class: str | None, region: str | None
) -> list[ProviderDeclaration]:
    """Installed providers serving ``model_key`` for the ``asset_class`` +
    ``region`` hints, in preference order (lower rank first)."""
    matched = [
        p
        for p in _PROVIDERS
        if model_key in p.serves
        and p.available()
        and p.serves_asset_class(asset_class)
        and p.serves_region(region)
    ]
    return sorted(matched, key=lambda p: p.rank)


def _no_provider_error(
    model_key: ModelKey, asset_class: str | None, region: str | None
) -> ProviderError:
    detail = ", ".join(
        part
        for part in (
            f"asset_class={asset_class!r}" if asset_class else "",
            f"region={region!r}" if region else "",
        )
        if part
    )
    return ProviderError(
        f"no provider available for {model_key!r}" + (f" ({detail})" if detail else "")
    )


def _resolve_sync(
    model_key: ModelKey,
    asset_class: str | None,
    region: str | None,
    validate: Validator | None,
    /,
    *args: Any,
) -> Any:
    """Walk SYNC providers for ``model_key`` in preference order, returning the
    first result that passes the correctness gate. A :class:`ProviderError` (or a
    gate :class:`CorrectnessError`) from one provider falls through to the next;
    the last error (or a no-provider error) propagates.

    Provenance is left untouched — the serving provider's ``provider`` field is
    whatever it wrote."""
    candidates = _candidates(model_key, asset_class, region)
    if not candidates:
        raise _no_provider_error(model_key, asset_class, region)
    last_exc: ProviderError | None = None
    for provider in candidates:
        try:
            result = provider.serves[model_key](*args)
            return validate(result) if validate is not None else result
        except ProviderError as exc:
            last_exc = exc
            _log.warning(
                "provider %s failed for %s, falling through: %s", provider.id, model_key, exc
            )
    assert last_exc is not None
    raise last_exc


async def _resolve_async(
    model_key: ModelKey,
    asset_class: str | None,
    region: str | None,
    validate: Validator | None,
    /,
    *args: Any,
    accept: Acceptor | None = None,
) -> Any:
    """Walk providers for ``model_key`` in preference order, awaiting async
    accessors and calling sync ones inline (these resolvers back fundamentals/
    statements/analyst/macro — openbb-mcp async first, yfinance sync fallback).
    The correctness gate is applied to each result before acceptance.

    ``accept`` (optional) gates COMPLETENESS, not correctness: when a result is
    valid but ``accept`` returns False (e.g. openbb fundamentals missing every
    screener-grade field), the registry keeps it as a fallback and tries the next
    (richer) provider; the first such partial is returned only if no later
    provider yields an accepted result. ``accept=None`` preserves the original
    "first valid wins" behaviour for every other model-key.

    Provenance is left untouched (see :func:`_resolve_sync`)."""
    candidates = _candidates(model_key, asset_class, region)
    if not candidates:
        raise _no_provider_error(model_key, asset_class, region)
    last_exc: ProviderError | None = None
    best_incomplete: Any = None
    have_incomplete = False
    for provider in candidates:
        try:
            fn = provider.serves[model_key]
            result = fn(*args)
            resolved = await result if inspect.isawaitable(result) else result
            validated = validate(resolved) if validate is not None else resolved
        except ProviderError as exc:
            last_exc = exc
            _log.warning(
                "provider %s failed for %s, falling through: %s", provider.id, model_key, exc
            )
            continue
        if accept is None or accept(validated):
            return validated
        # Valid but INCOMPLETE for this model-key — remember the highest-ranked
        # partial and try the next provider for richer data.
        if not have_incomplete:
            best_incomplete = validated
            have_incomplete = True
            _log.info(
                "provider %s returned an incomplete %s; trying next for richer data",
                provider.id,
                model_key,
            )
    if have_incomplete:
        return best_incomplete
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Public accessors — UNCHANGED signatures so every router stays untouched.
# ---------------------------------------------------------------------------


def get_quote(symbol: str, asset_class: str = "equity", region: str | None = None) -> Quote:
    """Return the latest quote; resolved by the ``quote`` model-key. Synchronous
    (callers run it on a thread) — its providers (ccxt, yfinance, nse) are sync.

    ``region`` (default: inferred from the symbol then the active request region)
    routes between the US (yfinance) and IN (nse) equity providers; the
    correctness gate validates equity results before acceptance (FR-062/063)."""
    eff = _effective_region(symbol, region)
    validate = None if asset_class == "crypto" else _quote_validator(symbol, eff)
    return _resolve_sync("quote", asset_class, eff, validate, symbol)


def get_history(
    symbol: str,
    timeframe: str,
    range_: str | None = None,
    asset_class: str = "equity",
    region: str | None = None,
) -> OHLCVSeries:
    """Return an OHLCV series; resolved by the ``ohlcv`` model-key. Synchronous."""
    eff = _effective_region(symbol, region)
    validate = None if asset_class == "crypto" else _series_validator(symbol, eff)
    return _resolve_sync("ohlcv", asset_class, eff, validate, symbol, timeframe, range_)


async def get_fundamentals(symbol: str, region: str | None = None) -> Fundamentals:
    """Return valuation ratios + company profile. Prefers openbb-mcp, but falls
    through to yfinance both on a ProviderError AND when openbb returns a result
    with no screener-grade fields (roe/margins/debt/growth) — see
    :func:`_fundamentals_screener_complete`. This is what fills the screener,
    the equity overview, and the curated presets with real ratios."""
    eff = _effective_region(symbol, region)
    return await _resolve_async(
        "fundamentals",
        "equity",
        eff,
        _fundamentals_validator(symbol, eff),
        symbol,
        accept=_fundamentals_screener_complete,
    )


async def get_income_statement(symbol: str, region: str | None = None) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``."""
    return await _resolve_async(
        "income_statement", "equity", _effective_region(symbol, region), None, symbol
    )


async def get_balance_sheet(symbol: str, region: str | None = None) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    return await _resolve_async(
        "balance_sheet", "equity", _effective_region(symbol, region), None, symbol
    )


async def get_cash_flow(symbol: str, region: str | None = None) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    return await _resolve_async(
        "cash_flow", "equity", _effective_region(symbol, region), None, symbol
    )


async def get_analyst_rating(symbol: str, region: str | None = None) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol``."""
    return await _resolve_async(
        "analyst_rating", "equity", _effective_region(symbol, region), None, symbol
    )


async def get_macro_series(series_id: str, provider: str | None = None) -> MacroSeries:
    """Return a macro time-series by id (FRED-style).

    Macro has no yfinance equivalent — when openbb-mcp is not bundled the
    resolver finds no provider and raises a clean :class:`ProviderError`, which
    the ``/macro`` router translates into its existing 501 response."""
    return await _resolve_async("macro_series", None, None, None, series_id, provider)


# --- Correctness-gate validators (closures binding the requested symbol+region) ---


def _quote_validator(symbol: str, region: str) -> Validator:
    return lambda result: correctness_gate.validate_quote(result, symbol, region)


def _series_validator(symbol: str, region: str) -> Validator:
    return lambda result: correctness_gate.validate_series(result, symbol, region)


def _fundamentals_validator(symbol: str, region: str) -> Validator:
    return lambda result: correctness_gate.validate_fundamentals(result, symbol, region)


# ---------------------------------------------------------------------------
# /health — DERIVED from the declarations (FR-053), never a hand-kept dict.
# ---------------------------------------------------------------------------


def active_providers() -> dict[str, str]:
    """Report which provider currently backs each model-key, derived from the
    declaration table + each provider's current availability. The first
    (preferred + available) provider per model-key is named; a lower-ranked
    available fallback is noted; an unavailable-only key reports 'unavailable'."""
    report: dict[str, str] = {}
    model_keys = sorted({k for p in _PROVIDERS for k in p.serves})
    for model_key in model_keys:
        ranked = sorted((p for p in _PROVIDERS if model_key in p.serves), key=lambda p: p.rank)
        available = [p for p in ranked if p.available()]
        if not available:
            report[model_key] = "unavailable"
            continue
        primary = available[0].id
        fallbacks = [p.id for p in available[1:]]
        report[model_key] = f"{primary} ({', '.join(fallbacks)} fallback)" if fallbacks else primary
    # Keep the openbb-mcp availability line the existing /health consumers read.
    report["openbb-mcp"] = "available" if openbb_mcp_provider.is_available() else "unavailable"
    return report


__all__ = [
    "DEFAULT_CRYPTO_EXCHANGE",
    "ModelKey",
    "ProviderDeclaration",
    "active_providers",
    "get_analyst_rating",
    "get_balance_sheet",
    "get_cash_flow",
    "get_fundamentals",
    "get_history",
    "get_income_statement",
    "get_macro_series",
    "get_quote",
]
