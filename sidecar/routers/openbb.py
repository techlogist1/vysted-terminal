"""OpenBB router — endpoints the OpenBB plugin proxies through.

The plugin's TS entry-point hits these routes via the standard sidecar HTTP
client; the router unwraps the request and delegates to
:mod:`services.openbb_provider`. Every route degrades gracefully: if OpenBB is
not bundled (`is_available()` returns ``False``) the router replies with a
clean 503 and the caller falls back to its yfinance equivalent.

Note: these endpoints intentionally mirror the shapes returned by the existing
``/quotes``, ``/history``, and ``/fundamentals`` routers. The plugin proxies
these routes one-for-one rather than re-shaping data on the frontend.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
)
from models.market import MacroSeries, OHLCVSeries, Quote
from services import openbb_provider

router = APIRouter(prefix="/openbb", tags=["openbb"])


def _ensure_available() -> None:
    """Reject every request with a 503 when OpenBB is not bundled."""
    if not openbb_provider.is_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "OpenBB is not bundled in this build — the plugin is registered "
                "but inactive. The provider registry will fall back to yfinance."
            ),
        )


@router.get("/status")
def get_status() -> dict[str, object]:
    """Report whether OpenBB is bundled and routable in this build."""
    return {
        "available": openbb_provider.is_available(),
        "provider": openbb_provider.PROVIDER,
    }


@router.get("/quotes/{symbol}")
def get_quote(symbol: str) -> Quote:
    """Return the latest quote for ``symbol`` via OpenBB."""
    _ensure_available()
    return openbb_provider.get_quote(symbol)


@router.get("/history/{symbol}")
def get_history(
    symbol: str,
    timeframe: str = "1d",
    range_: str | None = Query(default=None, alias="range"),
) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` at ``timeframe`` via OpenBB."""
    _ensure_available()
    return openbb_provider.get_history(symbol, timeframe, range_)


@router.get("/fundamentals/{symbol}")
def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol`` via OpenBB."""
    _ensure_available()
    return openbb_provider.get_fundamentals(symbol)


@router.get("/fundamentals/{symbol}/income")
def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol`` via OpenBB."""
    _ensure_available()
    return openbb_provider.get_income_statement(symbol)


@router.get("/fundamentals/{symbol}/balance")
def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol`` via OpenBB."""
    _ensure_available()
    return openbb_provider.get_balance_sheet(symbol)


@router.get("/fundamentals/{symbol}/cashflow")
def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash flow statement excerpt for ``symbol`` via OpenBB."""
    _ensure_available()
    return openbb_provider.get_cash_flow(symbol)


@router.get("/fundamentals/{symbol}/ratings")
def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol`` via OpenBB."""
    _ensure_available()
    return openbb_provider.get_analyst_rating(symbol)


@router.get("/macro/{series_id}")
def get_macro_series(
    series_id: str,
    provider: str | None = Query(default=None, description="Upstream OpenBB provider id"),
) -> MacroSeries:
    """Return a macro series by id (FRED-style) via OpenBB."""
    _ensure_available()
    return openbb_provider.get_macro_series(series_id, provider=provider)
