"""yfinance data provider — the no-API-key default for equity data.

Covers quotes, OHLCV history, valuation ratios, the three financial statements,
and analyst ratings. yfinance does synchronous network I/O; FastAPI runs the
sync router functions that call into here on a worker thread, so this module
stays plain synchronous code.

Every public function raises :class:`ProviderError` on failure. yfinance's
upstream API drifts over time, so each function is defensive and tests mock the
``yf`` module rather than hitting the network.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import yfinance as yf

import config
from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
    StatementLine,
)
from models.market import OHLCVBar, OHLCVSeries, Quote
from services import symbol_resolver
from services.errors import ProviderError

PROVIDER = "yfinance"

# Public timeframe -> (yfinance interval, default lookback period).
_TIMEFRAME_MAP: dict[str, tuple[str, str]] = {
    "1m": ("1m", "5d"),
    "5m": ("5m", "1mo"),
    "15m": ("15m", "1mo"),
    "30m": ("30m", "3mo"),
    "1h": ("1h", "6mo"),
    "1d": ("1d", "1y"),
    "1wk": ("1wk", "5y"),
    "1mo": ("1mo", "max"),
}


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _normalize_symbol(symbol: str) -> str:
    """Translate yfinance dot-ticker quirks (``BRK.B`` → ``BRK-B``).

    yfinance returns 502 / "no data" for symbols containing dots — its API
    expects the dash form (``BRK.B`` → ``BRK-B``, ``BF.B`` → ``BF-B``,
    ``RDS.A`` → ``RDS-A``). The mapping is yfinance-specific (other providers
    have their own conventions), so it lives in this provider rather than in
    the dispatch layer.
    """
    return symbol.replace(".", "-")


def _yahoo_symbol(symbol: str) -> str:
    """Resolve the symbol to the form Yahoo actually serves data for.

    Three cases, in order:
      * a ``.NS``/``.BO`` suffix is already a Yahoo India symbol — pass it through
        UNCHANGED (the old ``_normalize_symbol`` wrongly turned ``ROUTE.NS`` into
        ``ROUTE-NS`` via its dot→dash rule, which Yahoo 502s on — the root cause of
        the all-dashes Indian Equity Overview);
      * a bare ticker that is a known NSE instrument (and NOT also a US one) gets
        the ``.NS`` suffix so Yahoo returns NSE fundamentals instead of an empty
        US lookup;
      * everything else takes the US dot→dash quirk (``BRK.B`` → ``BRK-B``).
    """
    s = symbol.strip().upper()
    if s.endswith((".NS", ".BO")):
        return s
    # Region-aware NSE resolution. The symbol's intrinsic hint wins; else the
    # active session region. In an IN context a bare (dot-free) ticker takes the
    # NSE listing — this covers (a) in-master NSE names, (b) DUAL-listed names like
    # INFY where the IN user wants the INR NSE listing, not the US ADR, and (c)
    # names NOT in the bundled master (Yahoo 404s an unknown .NS, surfacing an
    # honest "unavailable" rather than silently serving a wrong/empty US row). A
    # dotted US quirk ticker (BRK.B) is left to the dash path below.
    region = symbol_resolver.region_hint(s) or config.get_region()
    if region == "IN" and "." not in s:
        return f"{s}.NS"
    if symbol_resolver.is_nse_symbol(s) and not symbol_resolver.is_us_symbol(s):
        return f"{s}.NS"
    return s.replace(".", "-")


def _num(value: Any) -> float | None:
    """Coerce a possibly-missing/NaN value to ``float | None``."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_quote(symbol: str) -> Quote:
    """Return the latest quote for ``symbol``.

    Routes through :func:`_yahoo_symbol` (NOT the US-only ``_normalize_symbol``) so
    a ``.NS``/``.BO`` Indian symbol passes through unchanged and a bare NSE ticker
    in an IN context resolves to the ``.NS`` listing — the same region-aware mapper
    fundamentals/statements already use (the dot→dash US quirk still applies). The
    old path turned ``RELIANCE.NS`` into ``RELIANCE-NS``, which Yahoo 502s on.
    """
    normalized = _yahoo_symbol(symbol)
    try:
        fast = yf.Ticker(normalized).fast_info
        price = float(fast.last_price)
        prev = float(fast.previous_close)
        volume = getattr(fast, "last_volume", None)
        currency = getattr(fast, "currency", None) or "USD"
    except Exception as exc:  # noqa: BLE001 - any yfinance failure is a provider error
        raise ProviderError(f"yfinance quote failed for {symbol!r}: {exc}") from exc

    change = price - prev
    change_percent = (change / prev * 100.0) if prev else 0.0
    return Quote(
        symbol=normalized.upper(),
        price=price,
        change=change,
        change_percent=change_percent,
        volume=_num(volume),
        currency=str(currency),
        timestamp=_utcnow(),
        provider=PROVIDER,
    )


def get_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` at ``timeframe``.

    Routes through :func:`_yahoo_symbol` so ``RELIANCE.NS`` / ``532837.BO`` pass
    through unchanged instead of being mangled to the all-dashes form Yahoo 502s on.
    """
    normalized = _yahoo_symbol(symbol)
    interval, default_period = _TIMEFRAME_MAP.get(timeframe, ("1d", "1y"))
    period = range_ or default_period
    try:
        frame = yf.Ticker(normalized).history(period=period, interval=interval)
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance history failed for {symbol!r}: {exc}") from exc

    bars: list[OHLCVBar] = []
    for index, row in frame.iterrows():
        timestamp = index.to_pydatetime() if hasattr(index, "to_pydatetime") else index
        bars.append(
            OHLCVBar(
                timestamp=timestamp,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            )
        )
    return OHLCVSeries(symbol=normalized.upper(), timeframe=timeframe, bars=bars, provider=PROVIDER)


def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios, profitability, health, and a company profile.

    Uses :func:`_yahoo_symbol` so a bare NSE ticker (``ROUTE``) or a ``.NS`` form
    (``ROUTE.NS``) actually hits Yahoo's India data instead of an empty US lookup
    — the fix for the all-dashes Indian Equity Overview.
    """
    yahoo = _yahoo_symbol(symbol)
    try:
        info = yf.Ticker(yahoo).info
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance fundamentals failed for {symbol!r}: {exc}") from exc

    # yfinance 1.3.0 returns ``dividendYield`` as a percentage number (e.g.
    # ``0.36`` for AAPL, ``6.01`` for VZ) — not a fraction. The contract is a
    # fraction (the panel ×100s it). Guard against negative / absurd (>200%)
    # values reaching the UI as a glitchy readout (the "-88.58" class of bug).
    raw_yield = _num(info.get("dividendYield"))
    div_yield: float | None = None
    if raw_yield is not None:
        frac = raw_yield / 100.0
        div_yield = frac if 0.0 <= frac <= 2.0 else None

    # yfinance reports debtToEquity in percent form (150.0 = 1.5x); normalise to a
    # ratio so the screener/overview read the conventional D/E.
    raw_de = _num(info.get("debtToEquity"))
    debt_to_equity = (raw_de / 100.0) if raw_de is not None else None

    return Fundamentals(
        symbol=yahoo,
        name=info.get("longName") or info.get("shortName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        currency=info.get("currency") or info.get("financialCurrency"),
        # Valuation
        market_cap=_num(info.get("marketCap")),
        pe_ratio=_num(info.get("trailingPE")),
        forward_pe=_num(info.get("forwardPE")),
        peg_ratio=_num(info.get("trailingPegRatio") or info.get("pegRatio")),
        price_to_book=_num(info.get("priceToBook")),
        price_to_sales=_num(info.get("priceToSalesTrailing12Months")),
        ev_to_ebitda=_num(info.get("enterpriseToEbitda")),
        book_value=_num(info.get("bookValue")),
        dividend_yield=div_yield,
        dividend_per_share=_num(info.get("dividendRate")),
        eps=_num(info.get("trailingEps")),
        beta=_num(info.get("beta")),
        fifty_two_week_high=_num(info.get("fiftyTwoWeekHigh")),
        fifty_two_week_low=_num(info.get("fiftyTwoWeekLow")),
        fifty_two_week_change=_num(info.get("52WeekChange")),
        # Profitability (fractions)
        roe=_num(info.get("returnOnEquity")),
        roa=_num(info.get("returnOnAssets")),
        gross_margin=_num(info.get("grossMargins")),
        operating_margin=_num(info.get("operatingMargins")),
        profit_margin=_num(info.get("profitMargins")),
        # Financial health
        debt_to_equity=debt_to_equity,
        current_ratio=_num(info.get("currentRatio")),
        quick_ratio=_num(info.get("quickRatio")),
        # Size & growth
        revenue_ttm=_num(info.get("totalRevenue")),
        net_income_ttm=_num(info.get("netIncomeToCommon")),
        free_cash_flow=_num(info.get("freeCashflow")),
        shares_outstanding=_num(info.get("sharesOutstanding")),
        revenue_growth=_num(info.get("revenueGrowth")),
        earnings_growth=_num(info.get("earningsGrowth")),
        # Ownership (fractions)
        held_percent_insiders=_num(info.get("heldPercentInsiders")),
        held_percent_institutions=_num(info.get("heldPercentInstitutions")),
        provider=PROVIDER,
    )


def _statement_lines(frame: pd.DataFrame) -> tuple[list[str], list[StatementLine]]:
    """Convert a yfinance statement DataFrame to (periods, lines)."""
    periods = [str(getattr(col, "year", col)) for col in frame.columns]
    lines: list[StatementLine] = []
    for label, row in frame.iterrows():
        values = {period: _num(row.iloc[idx]) for idx, period in enumerate(periods)}
        lines.append(StatementLine(label=str(label), values=values))
    return periods, lines


def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``."""
    normalized = _yahoo_symbol(symbol)
    try:
        frame = yf.Ticker(normalized).income_stmt
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance income statement failed for {symbol!r}: {exc}") from exc
    periods, lines = _statement_lines(frame)
    return IncomeStatement(
        symbol=normalized.upper(), periods=periods, lines=lines, provider=PROVIDER
    )


def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    normalized = _yahoo_symbol(symbol)
    try:
        frame = yf.Ticker(normalized).balance_sheet
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance balance sheet failed for {symbol!r}: {exc}") from exc
    periods, lines = _statement_lines(frame)
    return BalanceSheet(symbol=normalized.upper(), periods=periods, lines=lines, provider=PROVIDER)


def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    normalized = _yahoo_symbol(symbol)
    try:
        frame = yf.Ticker(normalized).cashflow
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance cash flow failed for {symbol!r}: {exc}") from exc
    periods, lines = _statement_lines(frame)
    return CashFlowStatement(
        symbol=normalized.upper(), periods=periods, lines=lines, provider=PROVIDER
    )


def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings and price targets for ``symbol``."""
    normalized = _yahoo_symbol(symbol)
    try:
        ticker = yf.Ticker(normalized)
        recommendations = ticker.recommendations
        targets = ticker.analyst_price_targets
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance analyst rating failed for {symbol!r}: {exc}") from exc

    counts = {"strongBuy": 0, "buy": 0, "hold": 0, "sell": 0, "strongSell": 0}
    if recommendations is not None and not recommendations.empty:
        latest = recommendations.iloc[0]
        for key in counts:
            value = _num(latest.get(key))
            counts[key] = int(value) if value is not None else 0

    targets = targets or {}
    return AnalystRating(
        symbol=normalized.upper(),
        consensus=_consensus(counts),
        target_mean=_num(targets.get("mean")),
        target_high=_num(targets.get("high")),
        target_low=_num(targets.get("low")),
        strong_buy=counts["strongBuy"],
        buy=counts["buy"],
        hold=counts["hold"],
        sell=counts["sell"],
        strong_sell=counts["strongSell"],
        provider=PROVIDER,
    )


def _consensus(counts: dict[str, int]) -> str | None:
    """Derive a coarse consensus label from the rating counts."""
    total = sum(counts.values())
    if total == 0:
        return None
    bullish = counts["strongBuy"] + counts["buy"]
    bearish = counts["sell"] + counts["strongSell"]
    if bullish > bearish and bullish >= counts["hold"]:
        return "buy"
    if bearish > bullish and bearish >= counts["hold"]:
        return "sell"
    return "hold"
