"""Provider registry — the single dispatch point routers call into.

Routers never import a concrete provider directly; they call the registry, which
picks the right provider per data class. Equity data resolves to yfinance,
crypto to ccxt. OpenBB, when present, is preferred for fundamentals/macro — in
Phase 1 it is absent and the registry falls back to yfinance. New providers
(including the Phase 2 OpenBB ODP wrap plugin) slot in here with no router
changes.
"""

from __future__ import annotations

from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
)
from models.market import OHLCVSeries, Quote
from services import ccxt_provider, openbb_provider, yfinance_provider

DEFAULT_CRYPTO_EXCHANGE = "binance"


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
    """Return valuation ratios and a company profile for ``symbol``."""
    return yfinance_provider.get_fundamentals(symbol)


def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``."""
    return yfinance_provider.get_income_statement(symbol)


def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    return yfinance_provider.get_balance_sheet(symbol)


def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    return yfinance_provider.get_cash_flow(symbol)


def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol``."""
    return yfinance_provider.get_analyst_rating(symbol)


def active_providers() -> dict[str, str]:
    """Report which provider currently backs each data class."""
    return {
        "equity": "yfinance",
        "crypto": f"ccxt ({', '.join(ccxt_provider.SUPPORTED_EXCHANGES)})",
        "fundamentals": "yfinance",
        "openbb": "available" if openbb_provider.is_available() else "deferred-to-phase-2",
    }
