/**
 * Agent-runs store — the agents rail (FR-027, US9).
 *
 * Tracks agent runs so the rail shows live status, cost-so-far, and the budget,
 * and offers cancel / bring-to-foreground. Foreground runs (Ask/Edit/Build) are
 * local + ephemeral; a Delegate run is a DURABLE, budget-guarded background run
 * tracked by the sidecar (`/runs`) — it carries a `sidecarRunId`, and a poller
 * (`lib/delegate-runs`) syncs its cost/status into this store so the rail
 * reflects it even after the launching connection closes. A run that breaches
 * its BudgetGuard ends as `error` with the breach reason (SC-008).
 */

import { create } from "zustand";

import type { AgentMode } from "../../types/agent-modes";

export type AgentRunStatus = "running" | "done" | "error" | "cancelled" | "paused";

/** Hard ceilings for a Delegate run — the first breach aborts it (FR-026). */
export interface AgentRunBudget {
  maxTokens?: number;
  maxSpendUsd?: number;
  maxWallSeconds?: number;
  maxSteps?: number;
}

/** Cost-so-far for a run (tokens + estimated USD + steps). */
export interface AgentRunCost {
  tokens: number;
  spendUsd: number;
  steps: number;
}

export interface AgentRun {
  id: string;
  agentId: string | null;
  agentName: string;
  mode: AgentMode;
  status: AgentRunStatus;
  startedAt: number;
  endedAt?: number;
  /** Short status detail (e.g. an error/breach message, a pause question). */
  detail?: string;
  /** Cost-so-far (tokens + USD + steps), updated as the run reports usage. */
  cost?: AgentRunCost;
  /** The run's hard budget (Delegate runs); undefined for unbounded foreground. */
  budget?: AgentRunBudget;
  /** Sidecar run id for a DURABLE (Delegate) run — links to `/runs/{id}`. */
  sidecarRunId?: string;
  /** A human-in-the-loop question the run is paused on (FR-028). */
  question?: string;
  /** Abort the run (foreground: aborts the stream; durable: cancels via the rail). */
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
  /** Find a run by its sidecar run id (used by the durable-run poller). */
  bySidecarId: (sidecarRunId: string) => AgentRun | undefined;
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
        r.id === id && (r.status === "running" || r.status === "paused")
          ? { ...r, status: "cancelled", endedAt: Date.now() }
          : r,
      ),
    }));
  },

  removeRun: (id) => set((state) => ({ runs: state.runs.filter((r) => r.id !== id) })),

  clearFinished: () => set((state) => ({ runs: state.runs.filter((r) => r.status === "running") })),

  activeRuns: () => get().runs.filter((r) => r.status === "running" || r.status === "paused"),

  bySidecarId: (sidecarRunId) => get().runs.find((r) => r.sidecarRunId === sidecarRunId),
}));

/** Test helper: reset the agent-runs store. */
export function resetAgentRunsStoreForTests(): void {
  useAgentRunsStore.setState({ runs: [] });
  _seq = 0;
}
