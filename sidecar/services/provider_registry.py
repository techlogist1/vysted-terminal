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

from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
)
from models.market import MacroSeries, OHLCVSeries, Quote
from services import ccxt_provider, openbb_mcp_provider, yfinance_provider
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
    (empty = any).
    """

    id: str
    serves: dict[str, Callable[..., Any]]
    rank: int = 100
    requires: Callable[[], bool] | None = None
    asset_classes: frozenset[str] = field(default_factory=frozenset)

    def available(self) -> bool:
        return self.requires is None or bool(self.requires())

    def serves_asset_class(self, asset_class: str | None) -> bool:
        return not self.asset_classes or asset_class is None or asset_class in self.asset_classes


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
    # yfinance — the broad equity default + fallback for fundamentals/statements/
    # analyst when openbb-mcp is absent or errors. No macro equivalent.
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


def _candidates(model_key: ModelKey, asset_class: str | None) -> list[ProviderDeclaration]:
    """Installed providers serving ``model_key`` for the ``asset_class`` hint,
    in preference order (lower rank first)."""
    matched = [
        p
        for p in _PROVIDERS
        if model_key in p.serves and p.available() and p.serves_asset_class(asset_class)
    ]
    return sorted(matched, key=lambda p: p.rank)


def _no_provider_error(model_key: ModelKey, asset_class: str | None) -> ProviderError:
    return ProviderError(
        f"no provider available for {model_key!r}"
        + (f" (asset_class={asset_class!r})" if asset_class else "")
    )


def _resolve_sync(model_key: ModelKey, asset_class: str | None, /, *args: Any) -> Any:
    """Walk SYNC providers for ``model_key`` in preference order, returning the
    first success. A :class:`ProviderError` from one provider falls through to
    the next; the last error (or a no-provider error) propagates.

    Provenance is left untouched — the serving provider's ``provider`` field is
    whatever it wrote."""
    candidates = _candidates(model_key, asset_class)
    if not candidates:
        raise _no_provider_error(model_key, asset_class)
    last_exc: ProviderError | None = None
    for provider in candidates:
        try:
            return provider.serves[model_key](*args)
        except ProviderError as exc:
            last_exc = exc
            _log.warning(
                "provider %s failed for %s, falling through: %s", provider.id, model_key, exc
            )
    assert last_exc is not None
    raise last_exc


async def _resolve_async(model_key: ModelKey, asset_class: str | None, /, *args: Any) -> Any:
    """Walk providers for ``model_key`` in preference order, awaiting async
    accessors and calling sync ones inline (these resolvers back fundamentals/
    statements/analyst/macro — openbb-mcp async first, yfinance sync fallback).

    Provenance is left untouched (see :func:`_resolve_sync`)."""
    candidates = _candidates(model_key, asset_class)
    if not candidates:
        raise _no_provider_error(model_key, asset_class)
    last_exc: ProviderError | None = None
    for provider in candidates:
        try:
            fn = provider.serves[model_key]
            result = fn(*args)
            return await result if inspect.isawaitable(result) else result
        except ProviderError as exc:
            last_exc = exc
            _log.warning(
                "provider %s failed for %s, falling through: %s", provider.id, model_key, exc
            )
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Public accessors — UNCHANGED signatures so every router stays untouched.
# ---------------------------------------------------------------------------


def get_quote(symbol: str, asset_class: str = "equity") -> Quote:
    """Return the latest quote; resolved by the ``quote`` model-key. Synchronous
    (callers run it on a thread) — its providers (ccxt, yfinance) are sync."""
    return _resolve_sync("quote", asset_class, symbol)


def get_history(
    symbol: str,
    timeframe: str,
    range_: str | None = None,
    asset_class: str = "equity",
) -> OHLCVSeries:
    """Return an OHLCV series; resolved by the ``ohlcv`` model-key. Synchronous."""
    return _resolve_sync("ohlcv", asset_class, symbol, timeframe, range_)


async def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios + company profile; prefers openbb-mcp, falls
    through to yfinance on a ProviderError."""
    return await _resolve_async("fundamentals", "equity", symbol)


async def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``."""
    return await _resolve_async("income_statement", "equity", symbol)


async def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    return await _resolve_async("balance_sheet", "equity", symbol)


async def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    return await _resolve_async("cash_flow", "equity", symbol)


async def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol``."""
    return await _resolve_async("analyst_rating", "equity", symbol)


async def get_macro_series(series_id: str, provider: str | None = None) -> MacroSeries:
    """Return a macro time-series by id (FRED-style).

    Macro has no yfinance equivalent — when openbb-mcp is not bundled the
    resolver finds no provider and raises a clean :class:`ProviderError`, which
    the ``/macro`` router translates into its existing 501 response."""
    return await _resolve_async("macro_series", None, series_id, provider)


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
