/**
 * Agent-runs store — the agents rail (FR-027, US3 AS3).
 *
 * Tracks agent runs the user has launched so the agents rail can show live
 * status and offer cancel / bring-to-foreground. In P1 a run is a foreground
 * invocation (bounded by the sidecar's tool-round cap); Delegate runs surface
 * here too. P3 deepens this into durable, budget-guarded background runs
 * (cost-so-far, checkpoint/resume, HITL) — the shape carries those fields now so
 * the rail UI does not change when durability lands.
 */

import { create } from "zustand";

import type { AgentMode } from "../../types/agent-modes";

export type AgentRunStatus = "running" | "done" | "error" | "cancelled" | "paused";

export interface AgentRun {
  id: string;
  agentId: string | null;
  agentName: string;
  mode: AgentMode;
  status: AgentRunStatus;
  startedAt: number;
  endedAt?: number;
  /** Short status detail (e.g. an error message, a pause question). */
  detail?: string;
  /** Cost-so-far (tokens) — populated as the run reports usage. P3 adds $/budget. */
  tokens?: number;
  /** Abort the run (P1: aborts the foreground stream). */
  abort?: () => void;
}

let _seq = 0;
function nextRunId(): string {
  _seq += 1;
  return `run-${_seq}`;
}

interface AgentRunsState {
  runs: AgentRun[];
  startRun: (run: Omit<AgentRun, "id" | "status" | "startedAt">) => string;
  updateRun: (id: string, patch: Partial<AgentRun>) => void;
  endRun: (id: string, status: Exclude<AgentRunStatus, "running">, detail?: string) => void;
  cancelRun: (id: string) => void;
  removeRun: (id: string) => void;
  clearFinished: () => void;
  activeRuns: () => AgentRun[];
}

export const useAgentRunsStore = create<AgentRunsState>((set, get) => ({
  runs: [],

  startRun: (run) => {
    const id = nextRunId();
    const entry: AgentRun = { ...run, id, status: "running", startedAt: Date.now() };
    set((state) => ({ runs: [entry, ...state.runs] }));
    return id;
  },

  updateRun: (id, patch) =>
    set((state) => ({
      runs: state.runs.map((r) => (r.id === id ? { ...r, ...patch } : r)),
    })),

  endRun: (id, status, detail) =>
    set((state) => ({
      // Only an active run can transition to a terminal status — so a cancel
      // (cancelRun) and the abort-driven onError->endRun don't double-write;
      // the first terminal write wins.
      runs: state.runs.map((r) =>
        r.id === id && (r.status === "running" || r.status === "paused")
          ? { ...r, status, detail: detail ?? r.detail, endedAt: Date.now() }
          : r,
      ),
    })),

  cancelRun: (id) => {
    const run = get().runs.find((r) => r.id === id);
    run?.abort?.();
    set((state) => ({
      runs: state.runs.map((r) =>
        r.id === id && r.status === "running"
          ? { ...r, status: "cancelled", endedAt: Date.now() }
          : r,
      ),
    }));
  },

  removeRun: (id) => set((state) => ({ runs: state.runs.filter((r) => r.id !== id) })),

  clearFinished: () => set((state) => ({ runs: state.runs.filter((r) => r.status === "running") })),

  activeRuns: () => get().runs.filter((r) => r.status === "running" || r.status === "paused"),
}));

/** Test helper: reset the agent-runs store. */
export function resetAgentRunsStoreForTests(): void {
  useAgentRunsStore.setState({ runs: [] });
  _seq = 0;
}
