/**
 * Workflow run store — consumes the sidecar's ``POST /workflow/run`` SSE
 * stream and projects the per-event observability surface React renders.
 *
 * Phase-4 node-editor concerns and the v0.5.0 workflow engine talk through
 * the wire shape in ``types/workflow.ts``; this store narrows on
 * ``WorkflowRunEvent.kind`` and accumulates the events keyed by ``runId``
 * so the per-node observability overlay (Teammate N's node editor) can
 * render timings, partial outputs, and errors as the run progresses.
 *
 * Selector contract (the CLAUDE.md ``useSyncExternalStore`` Gotcha):
 * components subscribe via :func:`selectRunLog`, which returns a stable
 * frozen empty array reference when the run id is unknown so a render
 * loop does not mint a fresh ``[]`` on every read. Same pattern as
 * Phase-2's ``chart-sync`` and Phase-3's ``agents`` stores.
 *
 * The notify-desktop intent (``action.notify_desktop`` node output) is
 * detected during event consumption; when the sidecar emits a
 * ``node-output`` whose outputs carry ``intent === "desktop-notification"``
 * the store records the intent in a separate slice so a Tauri-side
 * notification dispatcher (frontend integration) can fire the OS
 * notification. The store itself does NOT call Tauri — that wire is the
 * dispatcher's responsibility.
 *
 * No ``localStorage`` / ``sessionStorage`` per the CLAUDE.md constraint
 * (sidecar owns persistence).
 */

import { create } from "zustand";

import { getSidecarBaseUrl } from "@/lib/sidecar-client";

import type { WorkflowRunEvent, WorkflowSpec } from "../../types/workflow";

// ---------------------------------------------------------------------------
// Desktop notification intent — the node-output sentinel
// ---------------------------------------------------------------------------

/** One desktop-notification intent captured from a workflow run. */
export interface DesktopNotificationIntent {
  runId: string;
  nodeId: string;
  title: string;
  message: string;
  /** Epoch ms at which the intent was recorded. */
  capturedAt: number;
}

// ---------------------------------------------------------------------------
// Run state
// ---------------------------------------------------------------------------

/** Pull the ``WorkflowRunEvent`` ``runId`` field safely — every variant carries it. */
function _runIdOf(event: WorkflowRunEvent): string {
  return event.runId;
}

/** True when the event indicates the run reached a terminal state. */
function _isTerminal(event: WorkflowRunEvent): boolean {
  return event.kind === "run-complete" || event.kind === "run-error";
}

interface WorkflowState {
  /** Accumulated event log keyed by run id; new events append to the tail. */
  runs: Record<string, WorkflowRunEvent[]>;
  /** The most-recently-started run id, or ``null`` if no run is in flight. */
  activeRun: string | null;
  /** Desktop notification intents the consumer dispatcher should drain. */
  pendingNotifications: DesktopNotificationIntent[];

  /** Append one event to its run's log; track active + notification intents. */
  appendEvent: (event: WorkflowRunEvent) => void;
  /** Drop one run's accumulated events — used to free memory after dispatch. */
  clearRun: (runId: string) => void;
  /** Drop every accumulated run. */
  clearAll: () => void;
  /** Remove pending-notification intents the dispatcher has consumed. */
  drainNotifications: () => DesktopNotificationIntent[];

  /**
   * POST the spec to ``/workflow/run`` and consume the SSE stream.
   *
   * Returns a promise that resolves with the run id once the ``run-start``
   * event arrives (so callers can await knowing-they-can-render-now). The
   * SSE stream continues to flow into the store after the promise resolves;
   * the consumer rejects with a structured error if the request itself
   * fails (network error / non-2xx). Per-node errors land as ``node-error``
   * events in the run log and DO NOT reject the outer promise — the run
   * still ran, the engine just reported some failed nodes.
   */
  runWorkflow: (spec: WorkflowSpec, inputs?: Record<string, unknown>) => Promise<string>;
}

// ---------------------------------------------------------------------------
// Snake_case → camelCase event normalisation (sidecar wire shape)
// ---------------------------------------------------------------------------

interface RawEvent {
  kind?: string;
  runId?: string;
  run_id?: string;
  nodeId?: string;
  node_id?: string;
  nodeType?: string;
  node_type?: string;
  startedAt?: number;
  started_at?: number;
  outputs?: Record<string, unknown>;
  message?: string;
  durationMs?: number;
  duration_ms?: number;
}

function _normalizeEvent(raw: RawEvent): WorkflowRunEvent | null {
  const kind = raw.kind;
  const runId = raw.runId ?? raw.run_id;
  if (!kind || !runId) {
    return null;
  }
  switch (kind) {
    case "run-start":
      return {
        kind: "run-start",
        runId,
        startedAt: Number(raw.startedAt ?? raw.started_at ?? 0),
      };
    case "node-start":
      return {
        kind: "node-start",
        runId,
        nodeId: String(raw.nodeId ?? raw.node_id ?? ""),
        nodeType: String(raw.nodeType ?? raw.node_type ?? ""),
        startedAt: Number(raw.startedAt ?? raw.started_at ?? 0),
      };
    case "node-output":
      return {
        kind: "node-output",
        runId,
        nodeId: String(raw.nodeId ?? raw.node_id ?? ""),
        outputs: (raw.outputs ?? {}) as Record<string, unknown>,
        durationMs: Number(raw.durationMs ?? raw.duration_ms ?? 0),
      };
    case "node-error":
      return {
        kind: "node-error",
        runId,
        nodeId: String(raw.nodeId ?? raw.node_id ?? ""),
        message: String(raw.message ?? "node error"),
        durationMs: Number(raw.durationMs ?? raw.duration_ms ?? 0),
      };
    case "run-complete":
      return {
        kind: "run-complete",
        runId,
        durationMs: Number(raw.durationMs ?? raw.duration_ms ?? 0),
      };
    case "run-error":
      return {
        kind: "run-error",
        runId,
        message: String(raw.message ?? "run error"),
        durationMs: Number(raw.durationMs ?? raw.duration_ms ?? 0),
      };
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Desktop-notification intent capture
// ---------------------------------------------------------------------------

function _captureNotificationIntent(event: WorkflowRunEvent): DesktopNotificationIntent | null {
  if (event.kind !== "node-output") {
    return null;
  }
  const outputs = event.outputs;
  if (
    typeof outputs.intent !== "string" ||
    outputs.intent !== "desktop-notification" ||
    outputs.notified !== true
  ) {
    return null;
  }
  return {
    runId: event.runId,
    nodeId: event.nodeId,
    title: typeof outputs.title === "string" ? outputs.title : "Workflow",
    message: typeof outputs.message === "string" ? outputs.message : "",
    capturedAt: Date.now(),
  };
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  runs: {},
  activeRun: null,
  pendingNotifications: [],

  appendEvent: (event) => {
    const runId = _runIdOf(event);
    const intent = _captureNotificationIntent(event);
    set((state) => {
      const next = (state.runs[runId] ?? []).concat(event);
      const runs = { ...state.runs, [runId]: next };
      const pendingNotifications = intent
        ? [...state.pendingNotifications, intent]
        : state.pendingNotifications;
      const activeRun =
        event.kind === "run-start"
          ? runId
          : _isTerminal(event) && state.activeRun === runId
            ? null
            : state.activeRun;
      return { runs, activeRun, pendingNotifications };
    });
  },

  clearRun: (runId) =>
    set((state) => {
      if (!(runId in state.runs)) {
        return state;
      }
      const next: Record<string, WorkflowRunEvent[]> = { ...state.runs };
      delete next[runId];
      return { runs: next };
    }),

  clearAll: () => set({ runs: {}, activeRun: null, pendingNotifications: [] }),

  drainNotifications: () => {
    const drained = get().pendingNotifications;
    set({ pendingNotifications: [] });
    return drained;
  },

  runWorkflow: async (spec, inputs) => {
    const base = await getSidecarBaseUrl();
    const url = new URL("/workflow/run", base);
    const body = JSON.stringify({ spec, inputs: inputs ?? {} });

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body,
    });

    if (!response.ok || !response.body) {
      const detail = await _safeText(response);
      throw new Error(detail ?? `sidecar returned ${response.status}`);
    }

    // Consume the stream until we see ``run-start`` (resolve the outer
    // promise) and continue draining the rest into the store in the
    // background. The first event the engine emits is always ``run-start``;
    // we resolve the moment it lands so the UI can render the run shell.
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let resolvedRunId: string | null = null;

    return await new Promise<string>((resolve, reject) => {
      const handleEvent = (event: WorkflowRunEvent) => {
        get().appendEvent(event);
        if (!resolvedRunId && event.kind === "run-start") {
          resolvedRunId = event.runId;
          resolve(event.runId);
        }
      };

      const consume = async () => {
        try {
          for (;;) {
            const { done, value } = await reader.read();
            if (done) {
              break;
            }
            buffer += decoder.decode(value, { stream: true });
            let sep = buffer.indexOf("\n\n");
            while (sep !== -1) {
              const frame = buffer.slice(0, sep);
              buffer = buffer.slice(sep + 2);
              _dispatchFrame(frame, handleEvent);
              sep = buffer.indexOf("\n\n");
            }
          }
          if (buffer.trim()) {
            _dispatchFrame(buffer, handleEvent);
          }
          if (!resolvedRunId) {
            reject(new Error("workflow stream closed before run-start event"));
          }
        } catch (err) {
          if (!resolvedRunId) {
            reject(err instanceof Error ? err : new Error(String(err)));
          }
        } finally {
          reader.releaseLock();
        }
      };

      void consume();
    });
  },
}));

// ---------------------------------------------------------------------------
// SSE frame dispatch
// ---------------------------------------------------------------------------

function _dispatchFrame(frame: string, onEvent: (event: WorkflowRunEvent) => void): void {
  const dataLines = frame
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());
  if (dataLines.length === 0) {
    return;
  }
  const payload = dataLines.join("\n");
  try {
    const parsed = JSON.parse(payload) as RawEvent;
    const event = _normalizeEvent(parsed);
    if (event) {
      onEvent(event);
    }
  } catch {
    // Swallow unparseable frames — better to drop a bad frame than to
    // crash the consumer; the engine controls the wire shape end-to-end.
  }
}

async function _safeText(response: Response): Promise<string | null> {
  try {
    const text = await response.text();
    return text.slice(0, 500);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Selectors — referentially-stable per the useSyncExternalStore Gotcha
// ---------------------------------------------------------------------------

/** Stable empty event list — reused so an unknown run id does not mint fresh arrays. */
const EMPTY_LOG: readonly WorkflowRunEvent[] = Object.freeze([]);

/** Select one run's accumulated event log, returning a stable empty ref for unknown ids. */
export function selectRunLog(
  state: WorkflowState,
  runId: string | null | undefined,
): readonly WorkflowRunEvent[] {
  if (!runId) {
    return EMPTY_LOG;
  }
  return state.runs[runId] ?? EMPTY_LOG;
}

/** Select the active run's log, or the stable empty list when no run is in flight. */
export function selectActiveRunLog(state: WorkflowState): readonly WorkflowRunEvent[] {
  return selectRunLog(state, state.activeRun);
}

/** Select every captured desktop-notification intent (for the Tauri dispatcher). */
export function selectPendingNotifications(
  state: WorkflowState,
): readonly DesktopNotificationIntent[] {
  return state.pendingNotifications;
}
