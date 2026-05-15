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

from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
    StatementLine,
)
from models.market import OHLCVBar, OHLCVSeries, Quote
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
    """Return the latest quote for ``symbol``."""
    try:
        fast = yf.Ticker(symbol).fast_info
        price = float(fast.last_price)
        prev = float(fast.previous_close)
        volume = getattr(fast, "last_volume", None)
        currency = getattr(fast, "currency", None) or "USD"
    except Exception as exc:  # noqa: BLE001 - any yfinance failure is a provider error
        raise ProviderError(f"yfinance quote failed for {symbol!r}: {exc}") from exc

    change = price - prev
    change_percent = (change / prev * 100.0) if prev else 0.0
    return Quote(
        symbol=symbol.upper(),
        price=price,
        change=change,
        change_percent=change_percent,
        volume=_num(volume),
        currency=str(currency),
        timestamp=_utcnow(),
        provider=PROVIDER,
    )


def get_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` at ``timeframe``."""
    interval, default_period = _TIMEFRAME_MAP.get(timeframe, ("1d", "1y"))
    period = range_ or default_period
    try:
        frame = yf.Ticker(symbol).history(period=period, interval=interval)
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
    return OHLCVSeries(symbol=symbol.upper(), timeframe=timeframe, bars=bars, provider=PROVIDER)


def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol``."""
    try:
        info = yf.Ticker(symbol).info
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance fundamentals failed for {symbol!r}: {exc}") from exc

    # yfinance 1.3.0 returns ``dividendYield`` as a percentage number
    # (e.g. ``0.36`` for AAPL, ``6.01`` for VZ) — not a fraction. The
    # ``Fundamentals.dividend_yield`` contract is a fraction (the panel
    # multiplies by 100 to display a percentage), so normalise here.
    raw_yield = _num(info.get("dividendYield"))
    return Fundamentals(
        symbol=symbol.upper(),
        name=info.get("longName") or info.get("shortName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        market_cap=_num(info.get("marketCap")),
        pe_ratio=_num(info.get("trailingPE")),
        forward_pe=_num(info.get("forwardPE")),
        peg_ratio=_num(info.get("trailingPegRatio") or info.get("pegRatio")),
        price_to_book=_num(info.get("priceToBook")),
        dividend_yield=(raw_yield / 100.0) if raw_yield is not None else None,
        eps=_num(info.get("trailingEps")),
        beta=_num(info.get("beta")),
        fifty_two_week_high=_num(info.get("fiftyTwoWeekHigh")),
        fifty_two_week_low=_num(info.get("fiftyTwoWeekLow")),
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
    try:
        frame = yf.Ticker(symbol).income_stmt
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance income statement failed for {symbol!r}: {exc}") from exc
    periods, lines = _statement_lines(frame)
    return IncomeStatement(symbol=symbol.upper(), periods=periods, lines=lines, provider=PROVIDER)


def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    try:
        frame = yf.Ticker(symbol).balance_sheet
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance balance sheet failed for {symbol!r}: {exc}") from exc
    periods, lines = _statement_lines(frame)
    return BalanceSheet(symbol=symbol.upper(), periods=periods, lines=lines, provider=PROVIDER)


def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    try:
        frame = yf.Ticker(symbol).cashflow
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance cash flow failed for {symbol!r}: {exc}") from exc
    periods, lines = _statement_lines(frame)
    return CashFlowStatement(symbol=symbol.upper(), periods=periods, lines=lines, provider=PROVIDER)


def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings and price targets for ``symbol``."""
    try:
        ticker = yf.Ticker(symbol)
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
        symbol=symbol.upper(),
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
