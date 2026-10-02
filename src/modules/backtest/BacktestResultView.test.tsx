import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { BacktestResult } from "../../../types/backtest";
import type { BacktestRunState } from "@/store/backtest";

// ---------------------------------------------------------------------------
// lightweight-charts mock — jsdom does not implement <canvas>.
// ---------------------------------------------------------------------------

const lineSeries = { setData: vi.fn(), priceScaleId: vi.fn() };
const areaSeries = { setData: vi.fn(), priceScaleId: vi.fn() };
const timeScale = { fitContent: vi.fn() };
const chartApi = {
  addSeries: vi.fn((type: unknown) => (type === "Area" ? areaSeries : lineSeries)),
  removeSeries: vi.fn(),
  timeScale: vi.fn(() => timeScale),
  remove: vi.fn(),
};
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => chartApi),
  LineSeries: "Line",
  AreaSeries: "Area",
}));

import { BacktestResultView } from "./BacktestResultView";

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Fixtures — one open trade, no closed trades (R15-UI-061).
// ---------------------------------------------------------------------------

const BASE_RESULT: BacktestResult = {
  runId: "run-1",
  strategyId: "mean_reversion",
  request: {
    strategyId: "mean_reversion",
    params: { window: 20 },
    symbols: ["SPY"],
    startDate: "2024-01-01",
    endDate: "2025-12-31",
    initialCapital: 100_000,
  },
  metrics: {
    totalReturn: 0,
    annualizedReturn: 0,
    sharpe: 0,
    sortino: 0,
    calmar: 0,
    maxDrawdownPct: 0,
    winRate: 0,
    tradeCount: 0,
    bestTradePnl: 0,
    worstTradePnl: 0,
  },
  trades: [
    {
      id: "tr1",
      symbol: "SPY",
      side: "buy",
      enteredAt: "2024-03-01",
      entryPrice: 510,
      quantity: 100,
    },
  ],
  equityCurve: [{ timestamp: "2024-01-02", equity: 100_000, drawdownPct: 0 }],
  startedAt: 1_710_000_000_000,
  durationMs: 320,
};

const BASE_RUN: BacktestRunState = {
  runId: "run-1",
  request: BASE_RESULT.request,
  status: "complete",
  barsProcessed: 1,
  totalBars: 1,
  trades: BASE_RESULT.trades,
  result: BASE_RESULT,
  error: null,
  startedAt: BASE_RESULT.startedAt,
  finishedAt: BASE_RESULT.startedAt + 320,
};

describe("BacktestResultView", () => {
  it("splits the trade-log header into closed vs open counts (R15-UI-061)", () => {
    const { container } = render(<BacktestResultView run={BASE_RUN} onRetry={vi.fn()} />);
    expect(container.textContent).toContain("Trades: 0");
    expect(container.textContent).toContain("Trades (0 closed, 1 open)");
  });
});
