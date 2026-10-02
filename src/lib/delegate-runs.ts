/**
 * Durable Delegate runs — the frontend half (FR-026/027/028, US9).
 *
 * A Delegate run is launched on the sidecar (`POST /agents/{id}/runs`) where it
 * runs detached under a BudgetGuard. This module mirrors each run into the
 * agent-runs store and POLLS `GET /runs` so the agents rail shows live
 * cost-so-far + status even after the launching connection closes (durability).
 * Cancel, resume, and human-in-the-loop answers route to the run routes. A run
 * that breaches its budget comes back as `error` with the breach reason (SC-008).
 *
 * The sidecar, not this store, decides which runs exist (R15-UI-040): the rail
 * adopts every live sidecar run on mount (a webview reload loses the in-memory
 * mirror, never the run), and a cancel shows `cancelled` only once the sidecar
 * confirmed it.
 *
 * When a run ends (`done` or `error`) its output is delivered ONCE to the chat
 * thread it was launched from (R15-AGENT-013): the answer is appended to that
 * thread (live or archived), and the host actions and the brief it produced go
 * through the normal proposed-changes gate, exactly like a foreground reply's.
 */

import { KEYCHAIN_NAMESPACES, getSecret } from "@/lib/keychain";
import { sidecarGet, sidecarRequest } from "@/lib/sidecar-client";
import { useAgentSpacesStore } from "@/store/agent-spaces";
import {
  type AgentRun,
  type AgentRunActivity,
  type AgentRunBudget,
  type AgentRunPlan,
  type AgentRunStatus,
  isLiveRun,
  useAgentRunsStore,
} from "@/store/agent-runs";
import { useProposedChangesStore } from "@/store/proposed-changes";

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
  /** The agent space (chat thread) the run was launched from; its answer lands
   *  there. Without one it lands in the live transcript. */
  threadId?: string;
}

/** Where each launched (or resumed) run delivers its output, keyed by sidecar
 *  run id. An entry is consumed by its one delivery. */
const origins = new Map<
  string,
  { threadId?: string; agentId: string; agentName: string; messageId: string }
>();

/** `GET /runs/{id}` output fields. The runs wire is snake_case only, both
 *  ways (`sidecar/models/run.py`, R15-CODE-AGENT-031). */
interface RunOutputWire {
  answer?: string | null;
  brief?: Record<string, unknown> | null;
  host_actions?: HostActionWire[];
}

interface HostActionWire {
  tool_call_id: string;
  name: string;
  input: Record<string, unknown>;
}

/** Wire shape of a run from `GET /runs` (snake_case from the sidecar). */
interface RunWire {
  id: string;
  agent_id: string | null;
  agent_name?: string;
  status: AgentRunStatus;
  cost?: { tokens?: number; spend_usd?: number; steps?: number };
  provider?: string | null;
  plan?: AgentRunPlan | null;
  activity?: AgentRunActivity[];
  detail?: string;
  question?: string;
}

/** A `/runs` read that has not answered in this long is aborted (a failed poll). */
const FETCH_RUNS_TIMEOUT_MS = 8000;

/** `GET /runs` — the newest runs the sidecar knows, newest first. */
async function fetchRuns(): Promise<RunWire[]> {
  const wire = await sidecarRequest<{ runs?: RunWire[] } | RunWire[]>("GET", "/runs", {
    signal: AbortSignal.timeout(FETCH_RUNS_TIMEOUT_MS),
  });
  return Array.isArray(wire) ? wire : (wire.runs ?? []);
}

/** The human reason of a failed run request (a `SidecarError` already carries
 *  the sidecar's own sentence). */
function reasonOf(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

function costOf(w: RunWire) {
  return {
    tokens: w.cost?.tokens ?? 0,
    spendUsd: w.cost?.spend_usd ?? 0,
    steps: w.cost?.steps ?? 0,
  };
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
    if (run.sidecarRunId && isLiveRun(run.status)) {
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
    provider: launch.provider,
    threadId: launch.threadId,
  });
  try {
    const body = await sidecarRequest<{ run_id?: string }>(
      "POST",
      `/agents/${encodeURIComponent(launch.agentId)}/runs`,
      {
        body: {
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
        },
      },
    );
    const sidecarRunId = body.run_id;
    useAgentRunsStore.getState().updateRun(localId, { sidecarRunId });
    if (sidecarRunId) {
      origins.set(sidecarRunId, {
        threadId: launch.threadId,
        agentId: launch.agentId,
        agentName: launch.agentName,
        messageId: `delegate-${sidecarRunId}`,
      });
    }
    ensurePolling();
  } catch (err) {
    useAgentRunsStore.getState().endRun(localId, "error", `Could not start: ${reasonOf(err)}`);
  }
}

/** True while a poll is running; the 2 s timer skips a tick rather than stack
 *  a second `/runs` read (and a second delivery) behind a slow one. */
let pollInFlight = false;

/** Poll the sidecar runs and sync cost/status into the rail. */
export async function pollDelegateRuns(): Promise<void> {
  if (pollInFlight) return;
  pollInFlight = true;
  try {
    await syncRuns();
  } finally {
    pollInFlight = false;
  }
}

async function syncRuns(): Promise<void> {
  const active = useAgentRunsStore
    .getState()
    .runs.some((r) => r.sidecarRunId && isLiveRun(r.status));
  if (!active) {
    // No active runs — clear any residual failure count so a NEW run can't
    // inherit a near-threshold count and badge stale on its very first dropped
    // poll (adversarial-review finding).
    pollFailures = 0;
    return;
  }
  let runs: RunWire[];
  try {
    runs = await fetchRuns();
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
    const cost = w.cost ? costOf(w) : local.cost;
    const plan = w.plan ?? undefined;
    const activity = w.activity ?? local.activity;
    if (w.status === "running" || w.status === "paused" || w.status === "planned") {
      store.updateRun(local.id, {
        status: w.status,
        cost,
        detail: w.detail,
        question: w.question,
        plan,
        activity,
      });
    } else {
      store.updateRun(local.id, { cost, detail: w.detail, activity });
      store.endRun(local.id, w.status, w.detail);
      if (w.status === "done" || w.status === "error") {
        await deliverRunOutput(w.id, w.status, w.detail);
      }
    }
  }
}

/**
 * Deliver a finished run's output to its originating thread, once: the answer
 * (with the error, if the run failed) is appended there, then each proposed
 * host action and the brief are enqueued through the proposed-changes gate.
 */
async function deliverRunOutput(
  sidecarRunId: string,
  status: "done" | "error",
  detail?: string,
): Promise<void> {
  const origin = origins.get(sidecarRunId);
  if (!origin) {
    return;
  }
  origins.delete(sidecarRunId);
  let output: RunOutputWire;
  try {
    output = await sidecarGet<RunOutputWire>(`/runs/${encodeURIComponent(sidecarRunId)}`);
  } catch (err) {
    output = {};
    detail = `The run finished but its answer could not be fetched (${reasonOf(err)}).`;
    status = "error";
  }
  const messageId = origin.messageId;
  if (output.answer || status === "error") {
    useAgentSpacesStore.getState().deliverTo(origin.threadId, {
      id: messageId,
      role: "assistant",
      content: output.answer ?? "",
      agentId: origin.agentId,
      createdAt: Date.now(),
      ...(status === "error" ? { error: detail ?? "The run failed." } : {}),
      ...(output.brief ? { briefPublished: true } : {}),
    });
  }
  const enqueue = useProposedChangesStore.getState().enqueue;
  const gate = { batchId: messageId, agentId: origin.agentId, agentName: origin.agentName };
  for (const action of output.host_actions ?? []) {
    enqueue({ toolCallId: action.tool_call_id, name: action.name, input: action.input, ...gate });
  }
  if (output.brief) {
    enqueue({
      toolCallId: `${messageId}-brief`,
      name: "publish_brief",
      input: output.brief,
      ...gate,
    });
  }
}

/**
 * Adopt every live sidecar run the rail does not mirror yet (R15-UI-040) —
 * after a webview reload the store is empty while the runs keep spending. An
 * adopted run's answer lands in the live transcript (its thread is unknown).
 */
export async function adoptSidecarRuns(): Promise<void> {
  let runs: RunWire[];
  try {
    runs = await fetchRuns();
  } catch {
    return; // the sidecar is down; the next mount (or launch) adopts
  }
  const store = useAgentRunsStore.getState();
  for (const w of runs) {
    if (!isLiveRun(w.status) || store.bySidecarId(w.id)) continue;
    const id = store.startRun({
      agentId: w.agent_id,
      agentName: w.agent_name ?? w.agent_id ?? "Agent",
      mode: "delegate",
      cost: costOf(w),
      sidecarRunId: w.id,
      provider: w.provider ?? undefined,
    });
    store.updateRun(id, {
      status: w.status,
      detail: w.detail,
      question: w.question,
      plan: w.plan ?? undefined,
      activity: w.activity,
    });
    origins.set(w.id, {
      agentId: w.agent_id ?? "",
      agentName: w.agent_name ?? w.agent_id ?? "Agent",
      messageId: `delegate-${w.id}`,
    });
  }
  ensurePolling();
}

/**
 * Cancel a durable run. The mirror flips to `cancelled` only once the sidecar
 * confirmed; a refused or failed cancel leaves it running and returns the
 * reason for the rail's retry note (R15-UI-040 — the run may still be spending).
 */
export async function cancelDelegateRun(sidecarRunId: string): Promise<RunActionResult> {
  try {
    await sidecarRequest("POST", `/runs/${encodeURIComponent(sidecarRunId)}/cancel`);
  } catch (err) {
    return { ok: false, error: `Cancel failed (${reasonOf(err)}) — retry.` };
  }
  const local = useAgentRunsStore.getState().bySidecarId(sidecarRunId);
  if (local) useAgentRunsStore.getState().endRun(local.id, "cancelled", "cancelled by user");
  return { ok: true };
}

/** The result of a run control action — `ok:false` carries a human reason so the
 *  caller can surface it instead of silently dropping a failed submit (A6). */
export interface RunActionResult {
  ok: boolean;
  error?: string;
}

/** The run's provider key as the `X-LLM-Api-Key` header — read from the OS
 *  keychain like a launch's, never sent in a body (R15-AGENT-035). A keyless
 *  provider (local Ollama) sends none. */
async function providerKeyHeader(provider?: string): Promise<Record<string, string>> {
  if (!provider) return {};
  const key = await getSecret(KEYCHAIN_NAMESPACES.llmProvider(provider));
  return key ? { "X-LLM-Api-Key": key } : {};
}

/** Answer a human-in-the-loop question a paused run is waiting on (FR-028). */
export async function answerDelegateRun(
  sidecarRunId: string,
  answer: string,
  provider?: string,
): Promise<RunActionResult> {
  try {
    await sidecarRequest("POST", `/runs/${encodeURIComponent(sidecarRunId)}/answer`, {
      headers: await providerKeyHeader(provider),
      body: { answer },
    });
    return { ok: true };
  } catch (err) {
    return { ok: false, error: `Couldn't send your answer (${reasonOf(err)}).` };
  }
}

/** Start a `planned` run: the user approved its plan (R15-AGENT-039). The
 *  provider key crosses in a header, like a resume's. */
export async function startDelegateRun(run: AgentRun): Promise<RunActionResult> {
  const sidecarRunId = run.sidecarRunId;
  if (!sidecarRunId) return { ok: false, error: "This run has no sidecar run to start." };
  try {
    await sidecarRequest("POST", `/runs/${encodeURIComponent(sidecarRunId)}/start`, {
      headers: await providerKeyHeader(run.provider),
    });
  } catch (err) {
    return { ok: false, error: `Couldn't start the run (${reasonOf(err)}).` };
  }
  useAgentRunsStore.getState().updateRun(run.id, { status: "running", detail: "started" });
  ensurePolling();
  return { ok: true };
}

/** Resume an errored run from its checkpoint on its launch provider/model
 *  (FR-028, R15-AGENT-035); its answer is delivered to its thread again. */
export async function resumeDelegateRun(run: AgentRun): Promise<RunActionResult> {
  const sidecarRunId = run.sidecarRunId;
  if (!sidecarRunId) return { ok: false, error: "This run has no sidecar run to resume." };
  try {
    await sidecarRequest("POST", `/runs/${encodeURIComponent(sidecarRunId)}/resume`, {
      headers: await providerKeyHeader(run.provider),
    });
  } catch (err) {
    return { ok: false, error: `Couldn't resume the run (${reasonOf(err)}).` };
  }
  useAgentRunsStore
    .getState()
    .updateRun(run.id, { status: "running", endedAt: undefined, detail: "resumed" });
  origins.set(sidecarRunId, {
    threadId: run.threadId,
    agentId: run.agentId ?? "",
    agentName: run.agentName,
    messageId: `delegate-${sidecarRunId}-${Date.now()}`,
  });
  ensurePolling();
  return { ok: true };
}

/** Test helper: stop the poll timer. */
export function stopDelegatePolling(): void {
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}
