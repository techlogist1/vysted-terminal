/**
 * Vysted Terminal — backtest engine wire contract.
 *
 * Phase 4 ships a custom event-driven backtest engine in the Python sidecar
 * (`services/backtest_engine.py`). Strategies implement a `BacktestStrategy`
 * ABC; the engine fetches historical OHLCV through Phase 1's
 * `provider_registry` (yfinance + ccxt + openbb-mcp), walks bars in order,
 * captures trades into a trade log, computes equity curve + drawdown +
 * Sharpe + win rate at end. Walk-forward is supported via slice-and-aggregate.
 *
 * The AI Strategy Critic agent (`sidecar/agents/strategy_critic.json`) has
 * `backtest_summary` in its tool list since v0.4.0 — Phase 4 wires that tool
 * to a digest of `BacktestResult` so the critic can interrogate the result
 * end-to-end (Use Case 2 in BLUEPRINT §10).
 *
 * Why a custom engine instead of vectorbt/backtrader (both common):
 * - backtrader development stopped in 2018; security maintenance is unclear.
 * - vectorbt pulls heavy deps (numba) that risk pushing the main sidecar
 *   `--onefile` binary past the 120 MB threshold (CLAUDE.md Phase-3
 *   Gotcha — current main 67 MB).
 * - BLUEPRINT §7 Phase 4 wording "vectorbt+backtrader patterns" supports
 *   drawing on their design ideas without runtime dependency.
 */

// ---------------------------------------------------------------------------
// Strategy spec
// ---------------------------------------------------------------------------

/**
 * A backtestable strategy registered in the sidecar's strategy registry.
 * Strategies live server-side as Python `BacktestStrategy` subclasses
 * (`services/backtest_strategies.py`); the wire surface is this metadata
 * plus the JSON-Schema-validated `params` shape.
 */
export interface BacktestStrategySpec {
  /** Stable identifier, e.g. `"mean_reversion"`, `"trend_following"`. */
  id: string;
  /** Display name shown in the strategy picker. */
  name: string;
  /** One-line description shown beneath the name. */
  description: string;
  /**
   * JSON Schema (draft-07 subset) describing the `params` shape this
   * strategy accepts. The frontend renders a form from this schema.
   */
  paramsSchema: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Run request
// ---------------------------------------------------------------------------

/** Fee + slippage model applied to every simulated fill. */
export interface BacktestFeeModel {
  /** Per-side commission in basis points (5 = 0.05%). Default `5` for equities. */
  feeBps: number;
  /** Per-side slippage in basis points (5 = 0.05%). Default `5` for equities. */
  slippageBps: number;
}

/** `POST /backtest/run` request body. */
export interface BacktestRequest {
  /** Registered strategy id. */
  strategyId: string;
  /** Strategy-specific params; validated against `BacktestStrategySpec.paramsSchema`. */
  params: Record<string, unknown>;
  /** Tickers to trade. Many strategies trade only `symbols[0]`. */
  symbols: string[];
  /** Inclusive ISO-8601 date `YYYY-MM-DD`. */
  startDate: string;
  /** Inclusive ISO-8601 date `YYYY-MM-DD`. */
  endDate: string;
  /** Starting cash, in account currency. Default 100_000. */
  initialCapital: number;
  /** Fee model; default is equity defaults if omitted. */
  feeModel?: BacktestFeeModel;
  /** Walk-forward slice count (`1` = single in-sample run, default). */
  walkForwardSlices?: number;
}

// ---------------------------------------------------------------------------
// Result
// ---------------------------------------------------------------------------

/** A single trade in the trade log. */
export interface BacktestTrade {
  /** Stable id per trade. */
  id: string;
  symbol: string;
  side: "buy" | "sell";
  /** ISO timestamp of fill. */
  enteredAt: string;
  exitedAt?: string;
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  /** Realized P&L in account currency; undefined while the trade is open. */
  pnl?: number;
  /** Reason the trade closed (`"strategy"`, `"stop-loss"`, `"end-of-data"`). */
  closeReason?: string;
}

/** One point on the equity curve, sampled per bar. */
export interface EquityCurvePoint {
  /** ISO timestamp of the bar. */
  timestamp: string;
  /** Total account equity including open-position mark-to-market. */
  equity: number;
  /** Drawdown from running peak, expressed as a negative percent (-0.12 = -12%). */
  drawdownPct: number;
}

/** Walk-forward slice summary — one entry per slice when slices > 1. */
export interface WalkForwardSlice {
  index: number;
  startDate: string;
  endDate: string;
  totalReturn: number;
  sharpe: number;
  trades: number;
}

/** Aggregated metrics for a complete backtest. */
export interface BacktestMetrics {
  totalReturn: number;
  annualizedReturn: number;
  /** Annualised Sharpe (252-day, risk-free assumed 0 for simplicity in v0.5.0). */
  sharpe: number;
  sortino: number;
  calmar: number;
  /** Peak-to-trough drawdown as a negative fraction (-0.25 = -25%). */
  maxDrawdownPct: number;
  /** Win rate as fraction (0.55 = 55%). */
  winRate: number;
  /** Number of closed trades. */
  tradeCount: number;
  /** Best single-trade P&L. */
  bestTradePnl: number;
  /** Worst single-trade P&L. */
  worstTradePnl: number;
}

/** Full backtest result returned by `GET /backtest/runs/{id}`. */
export interface BacktestResult {
  runId: string;
  strategyId: string;
  request: BacktestRequest;
  metrics: BacktestMetrics;
  trades: BacktestTrade[];
  equityCurve: EquityCurvePoint[];
  walkForwardSlices?: WalkForwardSlice[];
  startedAt: number;
  durationMs: number;
}

// ---------------------------------------------------------------------------
// Run event stream
// ---------------------------------------------------------------------------

/** One event in a backtest run's SSE stream. */
export type BacktestRunEvent =
  | { kind: "run-start"; runId: string; totalBars: number; startedAt: number }
  | { kind: "progress"; runId: string; barsProcessed: number; equity: number }
  | { kind: "trade"; runId: string; trade: BacktestTrade }
  | { kind: "run-complete"; runId: string; result: BacktestResult }
  | { kind: "run-error"; runId: string; message: string };

// ---------------------------------------------------------------------------
// Strategy Critic backtest_summary tool digest
// ---------------------------------------------------------------------------

/**
 * The compact digest the Strategy Critic agent's `backtest_summary` tool
 * returns. The agent does NOT receive the raw equity curve (thousands of
 * points) or full trade log — only what's needed to apply the 9-section
 * critique framework. This shape stays stable across releases so the agent
 * prompt does not drift.
 */
export interface BacktestSummary {
  runId: string;
  strategyId: string;
  strategyParams: Record<string, unknown>;
  symbols: string[];
  startDate: string;
  endDate: string;
  metrics: BacktestMetrics;
  /** Up to 20 most-recent trades for sample-size reasoning. */
  recentTrades: BacktestTrade[];
  /** Top-3 and bottom-3 trades by P&L for outlier reasoning. */
  bestTrades: BacktestTrade[];
  worstTrades: BacktestTrade[];
  walkForwardSlices?: WalkForwardSlice[];
}
