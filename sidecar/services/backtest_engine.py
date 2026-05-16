"""Custom event-driven backtest engine — Phase 4 foundation.

The engine walks historical OHLCV bars in order, calls each strategy's
``on_bar`` hook for every bar, applies the order intents the strategy
returns against a simulated :class:`SimPortfolio`, and at the end
computes the aggregated :class:`BacktestResult` — total return, Sharpe,
Sortino, Calmar, max drawdown, win rate, trade log, equity curve.

The engine is intentionally strategy-agnostic; concrete strategies are
Teammate K's deliverable, registered via :func:`register_strategy` into
the module-level registry.

Walk-forward: the engine slices the requested date range into N equal
sections, runs the strategy independently on each, and aggregates the
per-slice metrics into ``BacktestResult.walk_forward_slices``. The total
metrics come from the full unsliced run so a 1-slice walk-forward equals
the original backtest.

Why custom, not vectorbt / backtrader:
- backtrader development tapered in 2018; security maintenance unclear.
- vectorbt pulls heavy deps (numba) that risk the 120 MB main-sidecar
  threshold (CLAUDE.md Phase-3 Gotcha; current main 67 MB).
- BLUEPRINT §7 Phase 4's "vectorbt+backtrader patterns" wording supports
  drawing on their design ideas without runtime dependency.
"""

from __future__ import annotations

import logging
import math
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from models.backtest import (
    BacktestFeeModel,
    BacktestMetrics,
    BacktestRequest,
    BacktestResult,
    BacktestRunEvent,
    BacktestTrade,
    EquityCurvePoint,
    WalkForwardSlice,
)

logger = logging.getLogger(__name__)

EventCallback = Callable[[BacktestRunEvent], Awaitable[None]]


class BacktestEngineError(RuntimeError):
    """Raised when a backtest cannot run (bad request, unknown strategy)."""


# ---------------------------------------------------------------------------
# Public ABC for strategies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Bar:
    """One OHLCV bar fed to the strategy. The engine's normalised shape."""

    timestamp: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class BacktestOrderIntent:
    """A strategy's intent to take a position at the current bar's close.

    The engine fills at the bar's close adjusted by the fee + slippage
    model. Positive ``quantity`` = long; negative = short / sell-to-close.
    """

    symbol: str
    quantity: float
    reason: str = ""


@dataclass
class _OpenPosition:
    """Internal sim-portfolio open position."""

    trade_id: str
    symbol: str
    quantity: float
    entry_price: float
    entered_at: str


@dataclass
class SimPortfolio:
    """In-memory portfolio fed to strategies on each bar.

    Strategies READ this (cash, equity, positions) and RETURN intents;
    the engine applies them, NOT the strategy directly.
    """

    cash: float
    positions: dict[str, _OpenPosition] = field(default_factory=dict)

    def equity(self, current_prices: dict[str, float]) -> float:
        """Mark-to-market portfolio equity at the given closing prices."""
        position_value = sum(
            pos.quantity * current_prices.get(pos.symbol, pos.entry_price)
            for pos in self.positions.values()
        )
        return self.cash + position_value

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions


class BacktestStrategy(ABC):
    """Subclass + register to add a strategy to the engine."""

    NAME: ClassVar[str]

    def __init__(self, params: dict[str, Any]) -> None:
        self.params = params

    @abstractmethod
    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        """Called once per bar. Return any orders to take at this bar's close."""


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

_STRATEGIES: dict[str, type[BacktestStrategy]] = {}


def register_strategy(strategy_id: str, cls: type[BacktestStrategy]) -> None:
    """Register a strategy class under a stable id."""
    _STRATEGIES[strategy_id] = cls
    logger.debug("backtest_engine: registered strategy %r -> %s", strategy_id, cls.__name__)


def registered_strategies() -> list[str]:
    return sorted(_STRATEGIES)


def get_strategy_class(strategy_id: str) -> type[BacktestStrategy] | None:
    return _STRATEGIES.get(strategy_id)


def reset_registry_for_tests() -> None:
    _STRATEGIES.clear()


# ---------------------------------------------------------------------------
# Historical-bar source (foundation supplies an injectable callable)
# ---------------------------------------------------------------------------

BarLoader = Callable[[list[str], str, str], Awaitable[list[Bar]]]


async def _default_bar_loader(symbols: list[str], start: str, end: str) -> list[Bar]:
    """Default bar loader — pulls from yfinance via the provider registry.

    Teammate K may swap this for a more powerful loader (per-symbol
    different sources, intraday bars, etc.); the engine accepts any
    callable matching :data:`BarLoader`.
    """
    # Foundation kept minimal — Teammate K wires the real OHLCV plumbing
    # into the strategy backtests. For unit-test parity an in-memory
    # fixture loader is injected via run_backtest's `bar_loader` kwarg.
    raise NotImplementedError(
        "Foundation backtest_engine does not bundle a default bar loader; "
        "pass bar_loader= to run_backtest(). Teammate K wires production."
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


async def _emit(callback: EventCallback | None, event: BacktestRunEvent) -> None:
    if callback is None:
        return
    try:
        await callback(event)
    except Exception as exc:  # noqa: BLE001
        logger.warning("backtest_engine: on_event callback raised %s", exc)


def _apply_fees(price: float, side: str, fees: BacktestFeeModel) -> float:
    """Adjust the bar's close price by fee + slippage in BPS."""
    bps = (fees.fee_bps + fees.slippage_bps) / 10_000.0
    return price * (1.0 + bps) if side == "buy" else price * (1.0 - bps)


def _slice_dates(start_date: str, end_date: str, slices: int) -> list[tuple[str, str]]:
    """Split a [start, end] date range into N equal slices.

    Operates on ISO-8601 YYYY-MM-DD strings. Used by walk-forward; for
    slices==1 returns a single full-range tuple.
    """
    from datetime import date, timedelta

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if slices <= 1:
        return [(start_date, end_date)]
    total_days = (end - start).days
    if total_days < slices:
        # Not enough days for the requested slice count; fall back to single.
        return [(start_date, end_date)]
    step = total_days / slices
    boundaries = [start + timedelta(days=int(round(step * i))) for i in range(slices + 1)]
    return [(boundaries[i].isoformat(), boundaries[i + 1].isoformat()) for i in range(slices)]


def _compute_metrics(
    equity_curve: list[EquityCurvePoint],
    trades: list[BacktestTrade],
    initial_capital: float,
) -> BacktestMetrics:
    """Derive the BacktestMetrics from the equity curve + trade log."""
    if not equity_curve:
        return BacktestMetrics(
            totalReturn=0.0,
            annualizedReturn=0.0,
            sharpe=0.0,
            sortino=0.0,
            calmar=0.0,
            maxDrawdownPct=0.0,
            winRate=0.0,
            tradeCount=0,
            bestTradePnl=0.0,
            worstTradePnl=0.0,
        )

    final_equity = equity_curve[-1].equity
    total_return = (final_equity - initial_capital) / initial_capital

    # Daily returns from the equity curve.
    returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1].equity
        curr = equity_curve[i].equity
        if prev > 0:
            returns.append((curr - prev) / prev)

    mean_return = statistics.fmean(returns) if returns else 0.0
    stdev = statistics.pstdev(returns) if len(returns) > 1 else 0.0
    downside = [r for r in returns if r < 0]
    downside_stdev = statistics.pstdev(downside) if len(downside) > 1 else 0.0

    # Annualised — 252 trading days. Sharpe and Sortino without a
    # risk-free rate (v0.5.0 simplification documented in
    # types/backtest.ts).
    annualised_return = (1 + mean_return) ** 252 - 1 if mean_return else 0.0
    sharpe = (mean_return / stdev) * math.sqrt(252) if stdev > 0 else 0.0
    sortino = (mean_return / downside_stdev) * math.sqrt(252) if downside_stdev > 0 else 0.0

    max_drawdown_pct = min((p.drawdown_pct for p in equity_curve), default=0.0)
    calmar = (annualised_return / abs(max_drawdown_pct)) if max_drawdown_pct < 0 else 0.0

    closed_trades = [t for t in trades if t.pnl is not None]
    pnls = [t.pnl for t in closed_trades if t.pnl is not None]
    winners = [p for p in pnls if p > 0]
    win_rate = (len(winners) / len(pnls)) if pnls else 0.0

    return BacktestMetrics(
        totalReturn=total_return,
        annualizedReturn=annualised_return,
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        maxDrawdownPct=max_drawdown_pct,
        winRate=win_rate,
        tradeCount=len(closed_trades),
        bestTradePnl=max(pnls) if pnls else 0.0,
        worstTradePnl=min(pnls) if pnls else 0.0,
    )


async def _run_single_slice(
    strategy: BacktestStrategy,
    bars: list[Bar],
    initial_capital: float,
    fees: BacktestFeeModel,
) -> tuple[list[BacktestTrade], list[EquityCurvePoint]]:
    """Run one (non-walk-forward) backtest slice; return trades + curve."""
    portfolio = SimPortfolio(cash=initial_capital)
    trades: list[BacktestTrade] = []
    closed_lookup: dict[str, BacktestTrade] = {}
    equity_curve: list[EquityCurvePoint] = []

    last_close_per_symbol: dict[str, float] = {}
    peak_equity = initial_capital

    for bar in bars:
        last_close_per_symbol[bar.symbol] = bar.close
        intents = await strategy.on_bar(bar, portfolio)

        for intent in intents:
            if intent.quantity == 0:
                continue
            side = "buy" if intent.quantity > 0 else "sell"
            fill_price = _apply_fees(bar.close, side, fees)
            cost = abs(intent.quantity) * fill_price

            if side == "buy":
                # New long position OR add to existing.
                if portfolio.cash < cost:
                    continue  # silently skip insufficient cash
                portfolio.cash -= cost
                trade_id = str(uuid.uuid4())
                portfolio.positions[intent.symbol] = _OpenPosition(
                    trade_id=trade_id,
                    symbol=intent.symbol,
                    quantity=intent.quantity,
                    entry_price=fill_price,
                    entered_at=bar.timestamp,
                )
                trades.append(
                    BacktestTrade(
                        id=trade_id,
                        symbol=intent.symbol,
                        side="buy",
                        enteredAt=bar.timestamp,
                        entryPrice=fill_price,
                        quantity=intent.quantity,
                    )
                )
            else:
                # Sell — close an existing long, if any.
                position = portfolio.positions.get(intent.symbol)
                if position is None:
                    continue
                portfolio.cash += abs(intent.quantity) * fill_price
                pnl = (fill_price - position.entry_price) * position.quantity
                # Update the entering trade record with exit details.
                for t in trades:
                    if t.id == position.trade_id:
                        closed = t.model_copy(
                            update={
                                "exited_at": bar.timestamp,
                                "exit_price": fill_price,
                                "pnl": pnl,
                                "close_reason": intent.reason or "strategy",
                            }
                        )
                        closed_lookup[t.id] = closed
                        break
                portfolio.positions.pop(intent.symbol, None)

        # Mark-to-market equity at this bar's close.
        equity_now = portfolio.equity(last_close_per_symbol)
        peak_equity = max(peak_equity, equity_now)
        drawdown_pct = (equity_now - peak_equity) / peak_equity if peak_equity > 0 else 0.0
        equity_curve.append(
            EquityCurvePoint(
                timestamp=bar.timestamp,
                equity=equity_now,
                drawdownPct=drawdown_pct,
            )
        )

    # Replace closed-trade records with their updated versions.
    trades = [closed_lookup.get(t.id, t) for t in trades]
    return trades, equity_curve


async def run_backtest(
    request: BacktestRequest,
    *,
    bar_loader: BarLoader | None = None,
    on_event: EventCallback | None = None,
) -> BacktestResult:
    """Run a backtest end-to-end."""
    strategy_cls = _STRATEGIES.get(request.strategy_id)
    if strategy_cls is None:
        raise BacktestEngineError(
            f"unknown strategy {request.strategy_id!r}; registered: {registered_strategies()}"
        )

    loader = bar_loader or _default_bar_loader
    fees = request.fee_model or BacktestFeeModel()
    run_id = str(uuid.uuid4())
    started_at = int(time.time() * 1000)
    started_ns = time.perf_counter_ns()

    bars = await loader(request.symbols, request.start_date, request.end_date)
    bars_sorted = sorted(bars, key=lambda b: (b.timestamp, b.symbol))
    await _emit(
        on_event,
        BacktestRunEvent(
            kind="run-start",
            runId=run_id,
            totalBars=len(bars_sorted),
            startedAt=started_at,
        ),
    )

    # Full unsliced run for the headline metrics + equity curve + trade log.
    strategy = strategy_cls(request.params)
    trades, equity_curve = await _run_single_slice(
        strategy, bars_sorted, request.initial_capital, fees
    )
    metrics = _compute_metrics(equity_curve, trades, request.initial_capital)

    # Walk-forward slices, if requested.
    walk_forward_slices: list[WalkForwardSlice] | None = None
    if request.walk_forward_slices > 1:
        walk_forward_slices = []
        for idx, (slice_start, slice_end) in enumerate(
            _slice_dates(request.start_date, request.end_date, request.walk_forward_slices)
        ):
            slice_bars = [b for b in bars_sorted if slice_start <= b.timestamp <= slice_end]
            if not slice_bars:
                continue
            slice_strategy = strategy_cls(request.params)
            slice_trades, slice_curve = await _run_single_slice(
                slice_strategy, slice_bars, request.initial_capital, fees
            )
            slice_metrics = _compute_metrics(slice_curve, slice_trades, request.initial_capital)
            walk_forward_slices.append(
                WalkForwardSlice(
                    index=idx,
                    startDate=slice_start,
                    endDate=slice_end,
                    totalReturn=slice_metrics.total_return,
                    sharpe=slice_metrics.sharpe,
                    trades=slice_metrics.trade_count,
                )
            )

    duration_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
    result = BacktestResult(
        runId=run_id,
        strategyId=request.strategy_id,
        request=request,
        metrics=metrics,
        trades=trades,
        equityCurve=equity_curve,
        walkForwardSlices=walk_forward_slices,
        startedAt=started_at,
        durationMs=duration_ms,
    )

    await _emit(on_event, BacktestRunEvent(kind="run-complete", runId=run_id, result=result))
    return result
