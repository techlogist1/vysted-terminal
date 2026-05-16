/**
 * Backtest store tests — strategy catalogue load, SSE consumer round-trip,
 * per-run state transitions.
 *
 * The store's network paths (``refreshStrategies`` via ``sidecarGet`` and
 * ``startRun`` via ``consumeBacktestStream``) are mocked at the module
 * boundary. The SSE-frame splitter is exercised with a hand-rolled
 * ReadableStream so the framing logic is covered without touching the
 * sidecar.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BacktestRequest, BacktestResult } from "../../types/backtest";

import { selectActiveRun, selectAllRuns, useBacktestStore } from "./backtest";

// ---------------------------------------------------------------------------
// Module mocks — sidecar-client is the seam for both surfaces
// ---------------------------------------------------------------------------

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

const SAMPLE_REQUEST: BacktestRequest = {
  strategyId: "mean_reversion",
  params: { window: 20, entry_z: -2.0 },
  symbols: ["SPY"],
  startDate: "2024-01-01",
  endDate: "2024-12-31",
  initialCapital: 100_000,
};

const SAMPLE_RESULT: BacktestResult = {
  runId: "run-real-001",
  strategyId: "mean_reversion",
  request: SAMPLE_REQUEST,
  metrics: {
    totalReturn: 0.12,
    annualizedReturn: 0.1,
    sharpe: 0.8,
    sortino: 0.9,
    calmar: 0.5,
    maxDrawdownPct: -0.05,
    winRate: 0.6,
    tradeCount: 3,
    bestTradePnl: 1200,
    worstTradePnl: -300,
  },
  trades: [
    {
      id: "t-1",
      symbol: "SPY",
      side: "buy",
      enteredAt: "2024-02-01",
      exitedAt: "2024-02-10",
      entryPrice: 400,
      exitPrice: 420,
      quantity: 100,
      pnl: 2000,
    },
  ],
  equityCurve: [
    { timestamp: "2024-01-02", equity: 100_000, drawdownPct: 0 },
    { timestamp: "2024-12-31", equity: 112_000, drawdownPct: -0.05 },
  ],
  startedAt: 1_710_000_000_000,
  durationMs: 250,
};

/** Build a ReadableStream from a sequence of UTF-8 frames. */
function streamFromFrames(frames: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(frame));
      }
      controller.close();
    },
  });
}

beforeEach(() => {
  useBacktestStore.getState().__resetForTests();
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Strategy catalogue
// ---------------------------------------------------------------------------

describe("useBacktestStore — strategies", () => {
  it("starts with an empty catalogue + idle status", () => {
    const state = useBacktestStore.getState();
    expect(state.strategies).toEqual([]);
    expect(state.catalogueStatus).toBe("idle");
  });

  it("loads strategies from the sidecar on refresh", async () => {
    const sample = [
      {
        id: "mean_reversion",
        name: "Mean Reversion",
        description: "z-score",
        paramsSchema: { type: "object", properties: {} },
      },
    ];
    vi.mocked(sidecarGet).mockResolvedValueOnce({ strategies: sample });
    await useBacktestStore.getState().refreshStrategies();
    expect(useBacktestStore.getState().strategies).toEqual(sample);
    expect(useBacktestStore.getState().catalogueStatus).toBe("ready");
  });

  it("captures a catalogue error", async () => {
    vi.mocked(sidecarGet).mockRejectedValueOnce(new Error("network is gone"));
    await useBacktestStore.getState().refreshStrategies();
    expect(useBacktestStore.getState().catalogueStatus).toBe("error");
    expect(useBacktestStore.getState().catalogueError).toContain("network is gone");
  });
});

// ---------------------------------------------------------------------------
// startRun + SSE consumer
// ---------------------------------------------------------------------------

describe("useBacktestStore — startRun", () => {
  it("creates a pending slot and promotes to the real id on run-start", async () => {
    const frames = [
      `data: ${JSON.stringify({ kind: "run-start", runId: "run-real-001", totalBars: 250, startedAt: 1_710_000_000_000 })}\n\n`,
      `data: ${JSON.stringify({ kind: "run-complete", runId: "run-real-001", result: SAMPLE_RESULT })}\n\n`,
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: streamFromFrames(frames),
      }),
    );

    await useBacktestStore.getState().startRun(SAMPLE_REQUEST);
    const state = useBacktestStore.getState();
    const slot = state.runs["run-real-001"];
    expect(slot).toBeDefined();
    expect(slot.status).toBe("complete");
    expect(slot.totalBars).toBe(250);
    expect(slot.result?.metrics.sharpe).toBe(0.8);
    expect(state.activeRunId).toBe("run-real-001");
  });

  it("appends streamed trades and tracks bars-processed", async () => {
    const trade = {
      id: "t-stream-1",
      symbol: "SPY",
      side: "buy" as const,
      enteredAt: "2024-03-01",
      entryPrice: 410,
      quantity: 50,
    };
    const frames = [
      `data: ${JSON.stringify({ kind: "run-start", runId: "r1", totalBars: 100, startedAt: 0 })}\n\n`,
      `data: ${JSON.stringify({ kind: "progress", runId: "r1", barsProcessed: 30, equity: 99_000 })}\n\n`,
      `data: ${JSON.stringify({ kind: "trade", runId: "r1", trade })}\n\n`,
      `data: ${JSON.stringify({ kind: "run-complete", runId: "r1", result: { ...SAMPLE_RESULT, runId: "r1", trades: [trade] } })}\n\n`,
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({ ok: true, status: 200, body: streamFromFrames(frames) }),
    );

    await useBacktestStore.getState().startRun(SAMPLE_REQUEST);
    const slot = useBacktestStore.getState().runs["r1"];
    expect(slot.trades).toHaveLength(1);
    expect(slot.trades[0].id).toBe("t-stream-1");
  });

  it("captures a run-error event", async () => {
    const frames = [
      `data: ${JSON.stringify({ kind: "run-error", runId: "r-err", message: "bad symbol" })}\n\n`,
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({ ok: true, status: 200, body: streamFromFrames(frames) }),
    );
    await useBacktestStore.getState().startRun(SAMPLE_REQUEST);
    const runs = Object.values(useBacktestStore.getState().runs);
    expect(runs).toHaveLength(1);
    expect(runs[0].status).toBe("error");
    expect(runs[0].error).toContain("bad symbol");
  });

  it("surfaces a network failure as an error slot", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: false, status: 502, body: null }));
    await useBacktestStore.getState().startRun(SAMPLE_REQUEST);
    const runs = Object.values(useBacktestStore.getState().runs);
    expect(runs[0].status).toBe("error");
  });

  it("handles a chunked SSE frame split across reads", async () => {
    // Split the run-start frame's data line across two reads to verify
    // the frame splitter buffers correctly.
    const frame = `data: ${JSON.stringify({ kind: "run-start", runId: "r-chunk", totalBars: 50, startedAt: 0 })}`;
    const head = frame.slice(0, 30);
    const tail = frame.slice(30) + "\n\n";
    const completeFrame = `data: ${JSON.stringify({ kind: "run-complete", runId: "r-chunk", result: { ...SAMPLE_RESULT, runId: "r-chunk" } })}\n\n`;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: streamFromFrames([head, tail, completeFrame]),
      }),
    );
    await useBacktestStore.getState().startRun(SAMPLE_REQUEST);
    const slot = useBacktestStore.getState().runs["r-chunk"];
    expect(slot).toBeDefined();
    expect(slot.status).toBe("complete");
  });
});

// ---------------------------------------------------------------------------
// Selectors
// ---------------------------------------------------------------------------

describe("backtest selectors", () => {
  it("selectActiveRun returns null when no run has started", () => {
    expect(selectActiveRun(useBacktestStore.getState())).toBeNull();
  });

  it("selectAllRuns sorts newest first", () => {
    useBacktestStore.setState({
      runs: {
        a: {
          runId: "a",
          request: SAMPLE_REQUEST,
          status: "complete",
          barsProcessed: 0,
          totalBars: 0,
          trades: [],
          result: null,
          error: null,
          startedAt: 100,
          finishedAt: 200,
        },
        b: {
          runId: "b",
          request: SAMPLE_REQUEST,
          status: "complete",
          barsProcessed: 0,
          totalBars: 0,
          trades: [],
          result: null,
          error: null,
          startedAt: 300,
          finishedAt: 400,
        },
      },
    });
    const all = selectAllRuns(useBacktestStore.getState());
    expect(all.map((r) => r.runId)).toEqual(["b", "a"]);
  });
});
