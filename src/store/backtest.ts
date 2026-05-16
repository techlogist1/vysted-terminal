/**
 * Backtest store — registered strategy catalogue + per-run state +
 * SSE-consumer for ``POST /backtest/run``.
 *
 * Teammate K v0.5.0 wire — the store holds three things:
 *
 * - ``strategies`` — the metadata catalogue fetched from
 *   ``GET /backtest/strategies``. The picker renders a dropdown from
 *   ``id``+``name`` and a params form from ``paramsSchema``.
 * - ``runs[runId]`` — every backtest the user has kicked off this
 *   session. Indexed by run id so the result view subscribes to one
 *   slot directly. Each run carries its request, latest progress, the
 *   final :type:`BacktestResult` once complete, plus error/streaming
 *   flags so the result view can show a spinner / error chip.
 * - ``activeRunId`` — the result the BacktestPanel is currently
 *   showing; bumped by ``startRun`` so the panel jumps to the new run
 *   the instant it begins.
 *
 * The SSE consumer mirrors the chat sidebar's framing pattern (``fetch``
 * + native streaming reader + a ``data:``-line splitter). On
 * ``run-complete`` we drop the full :type:`BacktestResult` into the
 * slot; on ``run-error`` we capture the message. Tests inject a fake
 * fetch + readable stream so the store can be exercised without a
 * sidecar.
 */

import { create } from "zustand";

import { getSidecarBaseUrl, sidecarGet } from "@/lib/sidecar-client";

import type {
  BacktestRequest,
  BacktestResult,
  BacktestRunEvent,
  BacktestStrategySpec,
  BacktestTrade,
} from "../../types/backtest";

// ---------------------------------------------------------------------------
// State types
// ---------------------------------------------------------------------------

/** Catalogue load status — separate from per-run state. */
export type BacktestCatalogueStatus = "idle" | "loading" | "ready" | "error";

/** Per-run lifecycle status — drives the result view's progress chrome. */
export type BacktestRunStatus = "pending" | "streaming" | "complete" | "error";

/** One backtest run's slice. The result view reads this. */
export interface BacktestRunState {
  /** Stable id — the run id the sidecar assigned. */
  runId: string;
  /** The request payload the user submitted. */
  request: BacktestRequest;
  status: BacktestRunStatus;
  /** Most recent progress event. */
  barsProcessed: number;
  totalBars: number;
  /** Live trade log — appended on each ``trade`` event. */
  trades: BacktestTrade[];
  /** Final result, populated on ``run-complete``. */
  result: BacktestResult | null;
  /** Human-readable error message on ``run-error``. */
  error: string | null;
  /** Timestamps for progress chrome. */
  startedAt: number;
  finishedAt: number | null;
}

interface BacktestStoreState {
  strategies: BacktestStrategySpec[];
  catalogueStatus: BacktestCatalogueStatus;
  catalogueError: string | null;

  runs: Record<string, BacktestRunState>;
  activeRunId: string | null;

  /** Fetch the registered strategies + their paramsSchema. */
  refreshStrategies: () => Promise<void>;

  /**
   * Kick off a new backtest run. Returns the temporary run id used to
   * key the slot before the sidecar's first event lands; the sidecar's
   * real run id replaces this on the first ``run-start`` event.
   */
  startRun: (request: BacktestRequest, options?: { signal?: AbortSignal }) => Promise<string>;

  /** Switch the active run shown in the panel. */
  setActiveRunId: (runId: string | null) => void;

  /** Test-only: hard reset (consumers do this between specs). */
  __resetForTests: () => void;
}

const PENDING_TOTAL_BARS = 0;

/** Generate a temporary id used until the sidecar assigns the real one. */
function tempRunId(): string {
  return `pending-${Math.random().toString(36).slice(2, 10)}`;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useBacktestStore = create<BacktestStoreState>((set) => ({
  strategies: [],
  catalogueStatus: "idle",
  catalogueError: null,
  runs: {},
  activeRunId: null,

  refreshStrategies: async () => {
    set({ catalogueStatus: "loading", catalogueError: null });
    try {
      const payload = await sidecarGet<{ strategies: BacktestStrategySpec[] }>(
        "/backtest/strategies",
      );
      set({
        strategies: payload.strategies ?? [],
        catalogueStatus: "ready",
        catalogueError: null,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load strategies";
      set({ catalogueStatus: "error", catalogueError: message });
    }
  },

  startRun: async (request, options) => {
    const tempId = tempRunId();
    set((state) => ({
      runs: {
        ...state.runs,
        [tempId]: {
          runId: tempId,
          request,
          status: "pending",
          barsProcessed: 0,
          totalBars: PENDING_TOTAL_BARS,
          trades: [],
          result: null,
          error: null,
          startedAt: Date.now(),
          finishedAt: null,
        },
      },
      activeRunId: tempId,
    }));

    let resolvedRunId = tempId;

    const handleEvent = (event: BacktestRunEvent): void => {
      if (event.kind === "run-start") {
        // The sidecar assigns the real id on its first event; promote
        // the slot from the temp id to the real one so subsequent
        // lookups by run id resolve.
        const realId = event.runId;
        set((state) => {
          const slot = state.runs[resolvedRunId];
          if (!slot) {
            return state;
          }
          const { [resolvedRunId]: _removed, ...others } = state.runs;
          void _removed;
          return {
            runs: {
              ...others,
              [realId]: {
                ...slot,
                runId: realId,
                status: "streaming",
                totalBars: event.totalBars,
                startedAt: event.startedAt,
              },
            },
            activeRunId: realId,
          };
        });
        resolvedRunId = realId;
        return;
      }
      if (event.kind === "progress") {
        set((state) => {
          const slot = state.runs[event.runId] ?? state.runs[resolvedRunId];
          if (!slot) {
            return state;
          }
          const id = slot.runId;
          return {
            runs: {
              ...state.runs,
              [id]: {
                ...slot,
                barsProcessed: event.barsProcessed,
              },
            },
          };
        });
        return;
      }
      if (event.kind === "trade") {
        set((state) => {
          const slot = state.runs[event.runId] ?? state.runs[resolvedRunId];
          if (!slot) {
            return state;
          }
          const id = slot.runId;
          return {
            runs: {
              ...state.runs,
              [id]: {
                ...slot,
                trades: [...slot.trades, event.trade],
              },
            },
          };
        });
        return;
      }
      if (event.kind === "run-complete") {
        set((state) => {
          const slot = state.runs[event.runId] ?? state.runs[resolvedRunId];
          if (!slot) {
            return state;
          }
          const id = slot.runId;
          return {
            runs: {
              ...state.runs,
              [id]: {
                ...slot,
                status: "complete",
                result: event.result,
                // Folded trade list from the result is authoritative.
                trades: event.result.trades,
                finishedAt: Date.now(),
              },
            },
            activeRunId: id,
          };
        });
        return;
      }
      if (event.kind === "run-error") {
        set((state) => {
          const slot = state.runs[event.runId] ?? state.runs[resolvedRunId];
          if (!slot) {
            return state;
          }
          const id = slot.runId;
          return {
            runs: {
              ...state.runs,
              [id]: {
                ...slot,
                status: "error",
                error: event.message,
                finishedAt: Date.now(),
              },
            },
          };
        });
        return;
      }
    };

    try {
      await consumeBacktestStream(request, handleEvent, options?.signal);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Backtest stream failed";
      set((state) => {
        const slot = state.runs[resolvedRunId];
        if (!slot) {
          return state;
        }
        return {
          runs: {
            ...state.runs,
            [resolvedRunId]: {
              ...slot,
              status: "error",
              error: message,
              finishedAt: Date.now(),
            },
          },
        };
      });
    }

    return resolvedRunId;
  },

  setActiveRunId: (runId) => set({ activeRunId: runId }),

  __resetForTests: () =>
    set({
      strategies: [],
      catalogueStatus: "idle",
      catalogueError: null,
      runs: {},
      activeRunId: null,
    }),
}));

// ---------------------------------------------------------------------------
// SSE consumer
// ---------------------------------------------------------------------------

/**
 * Stream ``POST /backtest/run`` and invoke ``onEvent`` for every frame.
 * Internally a fetch + native ReadableStream + a ``data:``-line
 * splitter — same pattern as the chat sidebar's
 * ``modules/chat/streaming.ts``.
 *
 * Exposed for tests to swap in a fake transport.
 */
export async function consumeBacktestStream(
  request: BacktestRequest,
  onEvent: (event: BacktestRunEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const base = await getSidecarBaseUrl();
  const url = new URL("/backtest/run", base);
  const body = JSON.stringify(serialiseRequest(request));
  const response = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body,
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Backtest stream failed (${response.status})`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      let separator = buffer.indexOf("\n\n");
      while (separator !== -1) {
        const frame = buffer.slice(0, separator);
        buffer = buffer.slice(separator + 2);
        const event = parseFrame(frame);
        if (event) {
          onEvent(event);
        }
        separator = buffer.indexOf("\n\n");
      }
    }
    if (buffer.trim()) {
      const event = parseFrame(buffer);
      if (event) {
        onEvent(event);
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/** Convert the camelCase frontend request to the Pydantic-aliased wire shape. */
function serialiseRequest(request: BacktestRequest): Record<string, unknown> {
  return {
    strategyId: request.strategyId,
    params: request.params,
    symbols: request.symbols,
    startDate: request.startDate,
    endDate: request.endDate,
    initialCapital: request.initialCapital,
    feeModel: request.feeModel,
    walkForwardSlices: request.walkForwardSlices,
  };
}

/** Parse one SSE frame; returns null for non-data frames. */
function parseFrame(frame: string): BacktestRunEvent | null {
  const dataLines = frame
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());
  if (dataLines.length === 0) {
    return null;
  }
  const payload = dataLines.join("\n");
  try {
    return JSON.parse(payload) as BacktestRunEvent;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Selectors
// ---------------------------------------------------------------------------

/** Pick the active run (or ``null`` when no run has started). */
export function selectActiveRun(state: BacktestStoreState): BacktestRunState | null {
  if (!state.activeRunId) {
    return null;
  }
  return state.runs[state.activeRunId] ?? null;
}

/** List all run slots, newest-first. */
export function selectAllRuns(state: BacktestStoreState): BacktestRunState[] {
  return Object.values(state.runs).sort((a, b) => b.startedAt - a.startedAt);
}
