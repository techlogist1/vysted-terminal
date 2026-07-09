import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BacktestResult, BacktestStrategySpec } from "../../../types/backtest";

// ---------------------------------------------------------------------------
// lightweight-charts mock — jsdom does not implement <canvas>. We record the
// addSeries / setData calls so we can assert the equity curve was painted.
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

// ---------------------------------------------------------------------------
// Mock the sidecar-client so we control catalogue + run-stream behaviour
// without an actual network call.
// ---------------------------------------------------------------------------

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

import { useBacktestStore } from "@/store/backtest";
import { useChatHistoryStore } from "@/store/chat-history";

import { BacktestPanel } from "./BacktestPanel";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const SAMPLE_STRATEGIES: BacktestStrategySpec[] = [
  {
    id: "mean_reversion",
    name: "Mean Reversion",
    description: "z-score entry/exit",
    paramsSchema: {
      type: "object",
      properties: {
        window: { type: "integer", default: 20 },
        entry_z: { type: "number", default: -2.0 },
      },
    },
  },
  {
    id: "trend_following",
    name: "Trend Following",
    description: "golden cross",
    paramsSchema: {
      type: "object",
      properties: {
        short_window: { type: "integer", default: 50 },
        long_window: { type: "integer", default: 200 },
      },
    },
  },
  {
    id: "custom",
    name: "Custom Strategy (DSL)",
    description: "your own entry/exit rules",
    paramsSchema: {
      type: "object",
      properties: {
        entry: { type: "string", default: "sma(20) > sma(50)" },
        exit: { type: "string", default: "rsi(14) > 70" },
        position_size: { type: "number", default: 100 },
      },
      required: ["entry", "exit"],
    },
  },
];

const SAMPLE_RESULT: BacktestResult = {
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
    totalReturn: 0.18,
    annualizedReturn: 0.15,
    sharpe: 1.4,
    sortino: 1.7,
    calmar: 1.0,
    maxDrawdownPct: -0.08,
    winRate: 0.62,
    tradeCount: 7,
    bestTradePnl: 3400,
    worstTradePnl: -1200,
  },
  trades: [
    {
      id: "tr1",
      symbol: "SPY",
      side: "buy",
      enteredAt: "2024-03-01",
      exitedAt: "2024-03-15",
      entryPrice: 510,
      exitPrice: 540,
      quantity: 100,
      pnl: 3000,
    },
  ],
  equityCurve: [
    { timestamp: "2024-01-02", equity: 100_000, drawdownPct: 0 },
    { timestamp: "2024-12-31", equity: 118_000, drawdownPct: -0.08 },
  ],
  startedAt: 1_710_000_000_000,
  durationMs: 320,
};

beforeEach(() => {
  useBacktestStore.getState().__resetForTests();
  useChatHistoryStore.getState().clear();
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("BacktestPanel", () => {
  it("loads strategies on mount and selects the first", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
    render(<BacktestPanel />);
    await waitFor(() => {
      expect(screen.getByText("Mean Reversion")).toBeInTheDocument();
    });
    expect(screen.getByText("Trend Following")).toBeInTheDocument();
    // The first strategy is auto-selected — params form fills with defaults.
    await waitFor(() => {
      expect(screen.getByLabelText("window")).toHaveValue(20);
    });
  });

  it("renders the params form from the selected strategy's schema", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
    render(<BacktestPanel />);
    await waitFor(() => screen.getByText("Trend Following"));
    fireEvent.click(screen.getByText("Trend Following"));
    await waitFor(() => {
      expect(screen.getByLabelText("short_window")).toHaveValue(50);
      expect(screen.getByLabelText("long_window")).toHaveValue(200);
    });
  });

  it("shows the empty state when no run has started", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
    render(<BacktestPanel />);
    await waitFor(() => screen.getByText("Mean Reversion"));
    expect(screen.getByText(/Run your first backtest/i)).toBeInTheDocument();
  });

  it("renders the result view once a run completes", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
    render(<BacktestPanel />);
    await waitFor(() => screen.getByText("Mean Reversion"));

    // Stuff the store with a completed run directly — the store is the
    // single source of truth and we exercise startRun separately.
    useBacktestStore.setState({
      runs: {
        "run-1": {
          runId: "run-1",
          request: SAMPLE_RESULT.request,
          status: "complete",
          barsProcessed: 250,
          totalBars: 250,
          trades: SAMPLE_RESULT.trades,
          result: SAMPLE_RESULT,
          error: null,
          startedAt: SAMPLE_RESULT.startedAt,
          finishedAt: SAMPLE_RESULT.startedAt + 320,
        },
      },
      activeRunId: "run-1",
    });

    await waitFor(() => {
      expect(screen.getByText(/Sharpe:/)).toBeInTheDocument();
      // The metrics row carries the headline P&L.
      expect(screen.getByText("+18.00%")).toBeInTheDocument();
      expect(screen.getByText("1.40")).toBeInTheDocument();
    });
    // Trade table renders the one closed trade.
    expect(screen.getByText("$3,000")).toBeInTheDocument();
  });

  it("pre-loads a Strategy Critic prompt when Open in Critic is clicked", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
    render(<BacktestPanel />);
    await waitFor(() => screen.getByText("Mean Reversion"));
    useBacktestStore.setState({
      runs: {
        "run-1": {
          runId: "run-1",
          request: SAMPLE_RESULT.request,
          status: "complete",
          barsProcessed: 0,
          totalBars: 0,
          trades: SAMPLE_RESULT.trades,
          result: SAMPLE_RESULT,
          error: null,
          startedAt: 0,
          finishedAt: 0,
        },
      },
      activeRunId: "run-1",
    });

    const button = await waitFor(() => screen.getByTestId("open-in-critic"));
    fireEvent.click(button);
    const messages = useChatHistoryStore.getState().messages;
    expect(messages.length).toBeGreaterThanOrEqual(1);
    const promptText = messages[messages.length - 1].content;
    expect(promptText).toContain("/agent strategy_critic");
    expect(promptText).toContain("run-1");
  });

  it("disables the Run button while a backtest is streaming", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
    render(<BacktestPanel />);
    await waitFor(() => screen.getByText("Mean Reversion"));
    useBacktestStore.setState({
      runs: {
        "run-X": {
          runId: "run-X",
          request: SAMPLE_RESULT.request,
          status: "streaming",
          barsProcessed: 50,
          totalBars: 250,
          trades: [],
          result: null,
          error: null,
          startedAt: 0,
          finishedAt: null,
        },
      },
      activeRunId: "run-X",
    });
    await waitFor(() => {
      const button = screen.getByTestId("run-backtest");
      expect(button).toBeDisabled();
    });
    expect(screen.getByTestId("streaming-progress")).toBeInTheDocument();
  });

  it("swaps the params form for the DSL editor on the custom strategy and gates Run on validity", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          ok: false,
          errors: [{ rule: "entry", message: "unknown identifier 'smaa'", position: 8 }],
          indicators: [],
          requiredBars: 0,
        }),
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);
    try {
      vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
      render(<BacktestPanel />);
      await waitFor(() => screen.getByText("Custom Strategy (DSL)"));
      fireEvent.click(screen.getByText("Custom Strategy (DSL)"));

      // The definition editor replaces the generic params form.
      await waitFor(() => {
        expect(screen.getByTestId("custom-strategy-editor")).toBeInTheDocument();
      });
      expect(screen.queryByTestId("params-form")).not.toBeInTheDocument();
      // Defaults from the spec's paramsSchema flow into the rule editors.
      expect(screen.getByTestId("custom-rule-entry")).toHaveValue("sma(20) > sma(50)");

      // Inline validation fails → the error renders and Run is gated off.
      await waitFor(() => {
        expect(screen.getByTestId("rule-error-entry")).toHaveTextContent("unknown identifier");
      });
      await waitFor(() => {
        expect(screen.getByTestId("run-backtest")).toBeDisabled();
      });

      // A fixed definition re-validates clean → Run is live again.
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({ ok: true, errors: [], indicators: ["sma(20)"], requiredBars: 20 }),
      } as unknown as Response);
      fireEvent.change(screen.getByTestId("custom-rule-entry"), {
        target: { value: "close > sma(20)" },
      });
      await waitFor(() => {
        expect(screen.getByTestId("run-backtest")).toBeEnabled();
      });
      expect(screen.getByTestId("custom-valid-summary")).toHaveTextContent("needs 20 bars");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("renders composed empty states for the no-run panel and an empty trade log", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
    render(<BacktestPanel />);
    await waitFor(() => screen.getByText("Mean Reversion"));
    // No run yet → the composed EmptyState, not a bare paragraph.
    const emptyState = screen.getByTestId("empty-state");
    expect(emptyState).toHaveTextContent("Run your first backtest");
    expect(screen.getByTestId("empty-state-icon")).toBeInTheDocument();

    // A completed run with zero trades → the dense trade-log EmptyState.
    const tradelessResult = { ...SAMPLE_RESULT, trades: [] };
    useBacktestStore.setState({
      runs: {
        "run-2": {
          runId: "run-2",
          request: SAMPLE_RESULT.request,
          status: "complete",
          barsProcessed: 250,
          totalBars: 250,
          trades: [],
          result: tradelessResult,
          error: null,
          startedAt: SAMPLE_RESULT.startedAt,
          finishedAt: SAMPLE_RESULT.startedAt + 320,
        },
      },
      activeRunId: "run-2",
    });
    await waitFor(() => {
      expect(screen.getByText("No trades yet")).toBeInTheDocument();
    });
    expect(screen.getByTestId("empty-state")).toHaveAttribute("data-dense", "true");
  });

  it("keeps real column widths in the trade table (no fixed colgroup truncation)", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
    render(<BacktestPanel />);
    await waitFor(() => screen.getByText("Mean Reversion"));
    const wideTrade = {
      id: "tr-wide",
      symbol: "BRK.A",
      side: "buy" as const,
      enteredAt: "2024-03-01",
      exitedAt: "2024-03-15",
      entryPrice: 612345.67,
      exitPrice: 645678.99,
      quantity: 1234567,
      pnl: 41172530.88,
    };
    useBacktestStore.setState({
      runs: {
        "run-3": {
          runId: "run-3",
          request: SAMPLE_RESULT.request,
          status: "complete",
          barsProcessed: 250,
          totalBars: 250,
          trades: [wideTrade],
          result: { ...SAMPLE_RESULT, trades: [wideTrade] },
          error: null,
          startedAt: SAMPLE_RESULT.startedAt,
          finishedAt: SAMPLE_RESULT.startedAt + 320,
        },
      },
      activeRunId: "run-3",
    });
    await waitFor(() => {
      expect(screen.getByText("612345.67")).toBeInTheDocument();
    });
    const table = screen.getByText("612345.67").closest("table");
    expect(table).not.toBeNull();
    // Auto layout — no table-fixed, no <colgroup> clipping numbers mid-digit.
    expect(table?.className).not.toContain("table-fixed");
    expect(table?.querySelector("colgroup")).toBeNull();
    // Numeric cells stay right-aligned tabular.
    const entryCell = screen.getByText("612345.67").closest("td");
    expect(entryCell?.className).toContain("text-right");
    expect(entryCell?.className).toContain("tabular-nums");
    expect(screen.getByText("1,234,567")).toBeInTheDocument();
  });
});

// D65 (R12): a run whose entries were skipped for insufficient cash must
// surface the engine's warnings strip — never a silent all-zero result.
describe("BacktestPanel warnings (D65)", () => {
  it("renders result.warnings as a warning strip", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: SAMPLE_STRATEGIES });
    render(<BacktestPanel />);
    await waitFor(() => screen.getByText("Mean Reversion"));

    const warnedResult = {
      ...SAMPLE_RESULT,
      trades: [],
      warnings: [
        "37 buy signal(s) skipped — the position size cost more than available cash (largest shortfall 52,340). Reduce position_size or raise initial_capital.",
      ],
    };
    useBacktestStore.setState({
      runs: {
        "run-w": {
          runId: "run-w",
          request: SAMPLE_RESULT.request,
          status: "complete",
          barsProcessed: 250,
          totalBars: 250,
          trades: [],
          result: warnedResult,
          error: null,
          startedAt: SAMPLE_RESULT.startedAt,
          finishedAt: SAMPLE_RESULT.startedAt + 320,
        },
      },
      activeRunId: "run-w",
    });

    await waitFor(() => {
      const strip = screen.getByTestId("run-warning");
      expect(strip).toHaveTextContent("37 buy signal(s) skipped");
    });
  });
});
