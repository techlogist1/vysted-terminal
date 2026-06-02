/**
 * Durable Delegate runs — the frontend half (FR-026/027/028, US9).
 *
 * A Delegate run is launched on the sidecar (`POST /agents/{id}/runs`) where it
 * runs detached under a BudgetGuard. This module mirrors each run into the
 * agent-runs store and POLLS `GET /runs` so the agents rail shows live
 * cost-so-far + status even after the launching connection closes (durability).
 * Cancel, resume, and human-in-the-loop answers route to the run routes. A run
 * that breaches its budget comes back as `error` with the breach reason (SC-008).
 */

import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { type AgentRunBudget, type AgentRunStatus, useAgentRunsStore } from "@/store/agent-runs";

import type { AgentContextSnapshot, LLMProviderId } from "../../types/ai";

export interface DelegateLaunch {
  agentId: string;
  agentName: string;
  prompt: string;
  contextSnapshot?: AgentContextSnapshot;
  provider?: LLMProviderId;
  model?: string;
  apiKey?: string;
  budget: AgentRunBudget;
  options?: Record<string, unknown>;
}

/** Wire shape of a run from `GET /runs` (snake_case from the sidecar). */
interface RunWire {
  id: string;
  agent_id: string | null;
  agent_name?: string;
  status: AgentRunStatus;
  cost?: { tokens?: number; spend_usd?: number; steps?: number };
  detail?: string;
  question?: string;
}

const POLL_MS = 2000;
let pollTimer: ReturnType<typeof setInterval> | null = null;

/** Consecutive `/runs` poll failures. After {@link POLL_FAIL_THRESHOLD} the live
 *  rail badges its active runs as stale instead of freezing on a frozen readout
 *  forever (A6 — a delegate run must never silently lose contact). */
let pollFailures = 0;
const POLL_FAIL_THRESHOLD = 5;

/** Badge every active run as having lost contact with the sidecar. */
function markRunsStale(): void {
  const store = useAgentRunsStore.getState();
  for (const run of store.runs) {
    if (run.sidecarRunId && (run.status === "running" || run.status === "paused")) {
      store.updateRun(run.id, {
        detail: "Lost contact with the run — the sidecar may be down. Status may be stale.",
      });
    }
  }
}

function ensurePolling(): void {
  if (pollTimer !== null || typeof window === "undefined") {
    return;
  }
  pollTimer = setInterval(() => void pollDelegateRuns(), POLL_MS);
}

/** Launch a durable Delegate run + mirror it into the rail. */
export async function launchDelegateRun(launch: DelegateLaunch): Promise<void> {
  const store = useAgentRunsStore.getState();
  const localId = store.startRun({
    agentId: launch.agentId,
    agentName: launch.agentName,
    mode: "delegate",
    budget: launch.budget,
    cost: { tokens: 0, spendUsd: 0, steps: 0 },
  });
  try {
    const base = await getSidecarBaseUrl();
    const response = await fetch(
      new URL(`/agents/${encodeURIComponent(launch.agentId)}/runs`, base).toString(),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: launch.prompt,
          context_snapshot: launch.contextSnapshot
            ? {
                focused_source: launch.contextSnapshot.focusedSource,
                by_source: launch.contextSnapshot.bySource,
                captured_at: launch.contextSnapshot.capturedAt,
              }
            : null,
          provider: launch.provider,
          model: launch.model,
          api_key: launch.apiKey,
          budget: {
            max_tokens: launch.budget.maxTokens,
            max_spend_usd: launch.budget.maxSpendUsd,
            max_wall_seconds: launch.budget.maxWallSeconds,
            max_steps: launch.budget.maxSteps,
          },
          options: launch.options ?? {},
        }),
      },
    );
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) detail = body.detail;
      } catch {
        // ignore
      }
      useAgentRunsStore.getState().endRun(localId, "error", `Could not start: ${detail}`);
      return;
    }
    const body = (await response.json()) as { runId?: string; run_id?: string };
    const sidecarRunId = body.runId ?? body.run_id;
    useAgentRunsStore.getState().updateRun(localId, {
      sidecarRunId,
      abort: sidecarRunId ? () => void cancelDelegateRun(sidecarRunId) : undefined,
    });
    ensurePolling();
  } catch (err) {
    useAgentRunsStore
      .getState()
      .endRun(localId, "error", err instanceof Error ? err.message : "launch failed");
  }
}

/** Poll the sidecar runs and sync cost/status into the rail. */
export async function pollDelegateRuns(): Promise<void> {
  const active = useAgentRunsStore
    .getState()
    .runs.some((r) => r.sidecarRunId && (r.status === "running" || r.status === "paused"));
  if (!active) {
    return;
  }
  let runs: RunWire[];
  try {
    const base = await getSidecarBaseUrl();
    const response = await fetch(new URL("/runs", base).toString());
    if (!response.ok) {
      throw new Error(`/runs HTTP ${response.status}`);
    }
    const wire = (await response.json()) as { runs?: RunWire[] } | RunWire[];
    runs = Array.isArray(wire) ? wire : (wire.runs ?? []);
  } catch {
    // A single dropped poll is fine; sustained failure means we've lost the
    // sidecar — badge the runs stale rather than showing a frozen live readout.
    pollFailures += 1;
    if (pollFailures >= POLL_FAIL_THRESHOLD) {
      markRunsStale();
    }
    return;
  }
  pollFailures = 0; // a successful poll clears the staleness state
  const store = useAgentRunsStore.getState();
  for (const w of runs) {
    const local = store.bySidecarId(w.id);
    if (!local) continue;
    const cost = w.cost
      ? {
          tokens: w.cost.tokens ?? 0,
          spendUsd: w.cost.spend_usd ?? 0,
          steps: w.cost.steps ?? 0,
        }
      : local.cost;
    if (w.status === "running" || w.status === "paused") {
      store.updateRun(local.id, { status: w.status, cost, detail: w.detail, question: w.question });
    } else {
      store.updateRun(local.id, { cost, detail: w.detail });
      store.endRun(local.id, w.status, w.detail);
    }
  }
}

export async function cancelDelegateRun(sidecarRunId: string): Promise<void> {
  try {
    const base = await getSidecarBaseUrl();
    await fetch(new URL(`/runs/${encodeURIComponent(sidecarRunId)}/cancel`, base).toString(), {
      method: "POST",
    });
  } catch {
    // Best-effort; the poll will reconcile.
  }
}

/** The result of a run control action — `ok:false` carries a human reason so the
 *  caller can surface it instead of silently dropping a failed submit (A6). */
export interface RunActionResult {
  ok: boolean;
  error?: string;
}

/** Answer a human-in-the-loop question a paused run is waiting on (FR-028). */
export async function answerDelegateRun(
  sidecarRunId: string,
  answer: string,
): Promise<RunActionResult> {
  try {
    const base = await getSidecarBaseUrl();
    const response = await fetch(
      new URL(`/runs/${encodeURIComponent(sidecarRunId)}/answer`, base).toString(),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer }),
      },
    );
    if (!response.ok) {
      return { ok: false, error: `Couldn't send your answer (HTTP ${response.status}).` };
    }
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Couldn't send your answer." };
  }
}

/** Resume a paused/checkpointed run (FR-028). */
export async function resumeDelegateRun(sidecarRunId: string): Promise<RunActionResult> {
  try {
    const base = await getSidecarBaseUrl();
    const response = await fetch(
      new URL(`/runs/${encodeURIComponent(sidecarRunId)}/resume`, base).toString(),
      { method: "POST" },
    );
    if (!response.ok) {
      return { ok: false, error: `Couldn't resume the run (HTTP ${response.status}).` };
    }
    ensurePolling();
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Couldn't resume the run." };
  }
}

/** Test helper: stop the poll timer. */
export function stopDelegatePolling(): void {
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}
