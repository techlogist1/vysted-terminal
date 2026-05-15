"""Provider registry — the single dispatch point routers call into.

Routers never import a concrete provider directly; they call the registry, which
picks the right provider per data class. Equity quotes/history resolve to
yfinance; crypto to ccxt. Fundamentals (and the new macro hook) prefer OpenBB
when it is bundled in this build, falling back to yfinance on import miss or any
upstream error. New providers slot in here with no router changes.
"""

from __future__ import annotations

import logging

from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
)
from models.market import MacroSeries, OHLCVSeries, Quote
from services import ccxt_provider, openbb_provider, yfinance_provider
from services.errors import ProviderError

DEFAULT_CRYPTO_EXCHANGE = "binance"

_log = logging.getLogger(__name__)


def get_quote(symbol: str, asset_class: str = "equity") -> Quote:
    """Return the latest quote, dispatching by asset class."""
    if asset_class == "crypto":
        return ccxt_provider.get_ticker(DEFAULT_CRYPTO_EXCHANGE, symbol)
    return yfinance_provider.get_quote(symbol)


def get_history(
    symbol: str,
    timeframe: str,
    range_: str | None = None,
    asset_class: str = "equity",
) -> OHLCVSeries:
    """Return an OHLCV series, dispatching by asset class."""
    if asset_class == "crypto":
        return ccxt_provider.get_ohlcv(DEFAULT_CRYPTO_EXCHANGE, symbol, timeframe)
    return yfinance_provider.get_history(symbol, timeframe, range_)


def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol``.

    Prefers OpenBB when bundled; yfinance is the fallback for both the
    no-OpenBB build and any OpenBB upstream failure.
    """
    if openbb_provider.is_available():
        try:
            return openbb_provider.get_fundamentals(symbol)
        except ProviderError as exc:
            _log.warning("OpenBB fundamentals failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_fundamentals(symbol)


def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``."""
    if openbb_provider.is_available():
        try:
            return openbb_provider.get_income_statement(symbol)
        except ProviderError as exc:
            _log.warning("OpenBB income statement failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_income_statement(symbol)


def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    if openbb_provider.is_available():
        try:
            return openbb_provider.get_balance_sheet(symbol)
        except ProviderError as exc:
            _log.warning("OpenBB balance sheet failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_balance_sheet(symbol)


def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    if openbb_provider.is_available():
        try:
            return openbb_provider.get_cash_flow(symbol)
        except ProviderError as exc:
            _log.warning("OpenBB cash flow failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_cash_flow(symbol)


def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol``."""
    if openbb_provider.is_available():
        try:
            return openbb_provider.get_analyst_rating(symbol)
        except ProviderError as exc:
            _log.warning("OpenBB analyst rating failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_analyst_rating(symbol)


def get_macro_series(series_id: str, provider: str | None = None) -> MacroSeries:
    """Return a macro time-series by id (FRED-style).

    Macro data has no yfinance equivalent — when OpenBB is not bundled the
    caller gets a clean :class:`ProviderError` and the legacy ``/macro``
    router translates it into the existing 501 response.
    """
    if not openbb_provider.is_available():
        raise ProviderError(
            "Macro data requires the OpenBB plugin, which is not bundled in this build."
        )
    return openbb_provider.get_macro_series(series_id, provider=provider)


def active_providers() -> dict[str, str]:
    """Report which provider currently backs each data class."""
    openbb_status = "available" if openbb_provider.is_available() else "unavailable"
    return {
        "equity": "yfinance",
        "crypto": f"ccxt ({', '.join(ccxt_provider.SUPPORTED_EXCHANGES)})",
        "fundamentals": "openbb (yfinance fallback)"
        if openbb_provider.is_available()
        else "yfinance",
        "macro": "openbb" if openbb_provider.is_available() else "unavailable",
        "openbb": openbb_status,
    }
