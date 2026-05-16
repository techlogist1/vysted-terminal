"""Backtest engine Pydantic models — mirror of ``types/backtest.ts``.

Phase 4 ships a custom event-driven backtest engine
(``services/backtest_engine.py``). Strategies subclass ``BacktestStrategy``
ABC; the engine fetches historical OHLCV via Phase 1's ``provider_registry``,
walks bars, captures trades, computes metrics + equity curve + drawdown.

The ``BacktestSummary`` shape is the Strategy Critic agent's
``backtest_summary`` tool's return shape — kept compact so the agent prompt
does not drift across releases.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BacktestStrategySpec(BaseModel):
    """A registered backtest strategy's metadata."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    name: str
    description: str
    params_schema: dict[str, Any] = Field(alias="paramsSchema")


class BacktestFeeModel(BaseModel):
    """Fee + slippage model applied to every simulated fill."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    fee_bps: float = Field(alias="feeBps", default=5.0)
    slippage_bps: float = Field(alias="slippageBps", default=5.0)


class BacktestRequest(BaseModel):
    """``POST /backtest/run`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")
    params: dict[str, Any] = Field(default_factory=dict)
    symbols: list[str]
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    initial_capital: float = Field(alias="initialCapital", default=100_000.0)
    fee_model: BacktestFeeModel | None = Field(default=None, alias="feeModel")
    walk_forward_slices: int = Field(alias="walkForwardSlices", default=1, ge=1, le=10)


class BacktestTrade(BaseModel):
    """A single trade in the trade log."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    symbol: str
    side: Literal["buy", "sell"]
    entered_at: str = Field(alias="enteredAt")
    exited_at: str | None = Field(default=None, alias="exitedAt")
    entry_price: float = Field(alias="entryPrice")
    exit_price: float | None = Field(default=None, alias="exitPrice")
    quantity: float
    pnl: float | None = None
    close_reason: str | None = Field(default=None, alias="closeReason")


class EquityCurvePoint(BaseModel):
    """One point on the equity curve, sampled per bar."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    timestamp: str
    equity: float
    drawdown_pct: float = Field(alias="drawdownPct")


class WalkForwardSlice(BaseModel):
    """Walk-forward slice summary."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    index: int
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    total_return: float = Field(alias="totalReturn")
    sharpe: float
    trades: int


class BacktestMetrics(BaseModel):
    """Aggregated metrics for a complete backtest."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    total_return: float = Field(alias="totalReturn")
    annualized_return: float = Field(alias="annualizedReturn")
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown_pct: float = Field(alias="maxDrawdownPct")
    win_rate: float = Field(alias="winRate")
    trade_count: int = Field(alias="tradeCount")
    best_trade_pnl: float = Field(alias="bestTradePnl")
    worst_trade_pnl: float = Field(alias="worstTradePnl")


class BacktestResult(BaseModel):
    """Full backtest result returned by ``GET /backtest/runs/{id}``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    run_id: str = Field(alias="runId")
    strategy_id: str = Field(alias="strategyId")
    request: BacktestRequest
    metrics: BacktestMetrics
    trades: list[BacktestTrade]
    equity_curve: list[EquityCurvePoint] = Field(alias="equityCurve")
    walk_forward_slices: list[WalkForwardSlice] | None = Field(
        default=None, alias="walkForwardSlices"
    )
    started_at: int = Field(alias="startedAt")
    duration_ms: float = Field(alias="durationMs")


class BacktestRunEvent(BaseModel):
    """One SSE event in a backtest run."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    kind: Literal["run-start", "progress", "trade", "run-complete", "run-error"]
    run_id: str = Field(alias="runId")
    total_bars: int | None = Field(default=None, alias="totalBars")
    started_at: int | None = Field(default=None, alias="startedAt")
    bars_processed: int | None = Field(default=None, alias="barsProcessed")
    equity: float | None = None
    trade: BacktestTrade | None = None
    result: BacktestResult | None = None
    message: str | None = None


class BacktestSummary(BaseModel):
    """Strategy Critic ``backtest_summary`` tool's return shape.

    Compact digest — the agent does NOT receive the raw equity curve or
    full trade log, only what's needed to apply the 9-section critique
    framework from ``sidecar/agents/strategy_critic.json``.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    run_id: str = Field(alias="runId")
    strategy_id: str = Field(alias="strategyId")
    strategy_params: dict[str, Any] = Field(alias="strategyParams")
    symbols: list[str]
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    metrics: BacktestMetrics
    recent_trades: list[BacktestTrade] = Field(alias="recentTrades")
    best_trades: list[BacktestTrade] = Field(alias="bestTrades")
    worst_trades: list[BacktestTrade] = Field(alias="worstTrades")
    walk_forward_slices: list[WalkForwardSlice] | None = Field(
        default=None, alias="walkForwardSlices"
    )
