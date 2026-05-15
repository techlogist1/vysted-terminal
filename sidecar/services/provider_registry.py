"""Provider registry — the single dispatch point routers call into.

Routers never import a concrete provider directly; they call the registry, which
picks the right provider per data class. Equity quotes/history resolve to
yfinance; crypto to ccxt. Fundamentals + analyst ratings + macro prefer
openbb-mcp (the Phase-3 replacement for the retired Phase-2 OpenBB plugin) when
it is bundled, falling back to yfinance on MCP error.

openbb-mcp accessors are async (the underlying MCP client is async), so the
registry's openbb-backed methods are async too. The yfinance fallback stays
sync — the routers ``await`` the registry method either way; the registry
itself bridges the sync/async surfaces internally.
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
from services import ccxt_provider, openbb_mcp_provider, yfinance_provider
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


async def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol``.

    Prefers openbb-mcp when bundled; yfinance is the fallback for both the
    no-MCP build and any openbb-mcp upstream failure.
    """
    if openbb_mcp_provider.is_available():
        try:
            return await openbb_mcp_provider.get_fundamentals(symbol)
        except ProviderError as exc:
            _log.warning("openbb-mcp fundamentals failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_fundamentals(symbol)


async def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``."""
    if openbb_mcp_provider.is_available():
        try:
            return await openbb_mcp_provider.get_income_statement(symbol)
        except ProviderError as exc:
            _log.warning("openbb-mcp income statement failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_income_statement(symbol)


async def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    if openbb_mcp_provider.is_available():
        try:
            return await openbb_mcp_provider.get_balance_sheet(symbol)
        except ProviderError as exc:
            _log.warning("openbb-mcp balance sheet failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_balance_sheet(symbol)


async def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    if openbb_mcp_provider.is_available():
        try:
            return await openbb_mcp_provider.get_cash_flow(symbol)
        except ProviderError as exc:
            _log.warning("openbb-mcp cash flow failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_cash_flow(symbol)


async def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol``."""
    if openbb_mcp_provider.is_available():
        try:
            return await openbb_mcp_provider.get_analyst_rating(symbol)
        except ProviderError as exc:
            _log.warning("openbb-mcp analyst rating failed for %s, falling back: %s", symbol, exc)
    return yfinance_provider.get_analyst_rating(symbol)


async def get_macro_series(series_id: str, provider: str | None = None) -> MacroSeries:
    """Return a macro time-series by id (FRED-style).

    Macro data has no yfinance equivalent — when openbb-mcp is not bundled
    the caller gets a clean :class:`ProviderError` and the legacy ``/macro``
    router translates it into the existing 501 response.
    """
    if not openbb_mcp_provider.is_available():
        raise ProviderError(
            "Macro data requires the openbb-mcp plugin, which is not bundled in this build."
        )
    return await openbb_mcp_provider.get_macro_series(series_id, provider=provider)


def active_providers() -> dict[str, str]:
    """Report which provider currently backs each data class."""
    openbb_status = "available" if openbb_mcp_provider.is_available() else "unavailable"
    return {
        "equity": "yfinance",
        "crypto": f"ccxt ({', '.join(ccxt_provider.SUPPORTED_EXCHANGES)})",
        "fundamentals": "openbb-mcp (yfinance fallback)"
        if openbb_mcp_provider.is_available()
        else "yfinance",
        "macro": "openbb-mcp" if openbb_mcp_provider.is_available() else "unavailable",
        "openbb-mcp": openbb_status,
    }
