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

import {
  extractSidecarDetail,
  getSidecarBaseUrl,
  SIDECAR_REQUEST_TIMEOUT_MS,
  SidecarError,
  sidecarFetch,
  sidecarRequest,
  sidecarRequestInit,
  type SidecarMethod,
  type SidecarRequestOptions,
} from "@/lib/sidecar-client";

import type {
  SavedWorkflows,
  ScheduleCreate,
  WebhookRefs,
  WorkflowRunEvent,
  WorkflowRunRequest,
  WorkflowSchedule,
  WorkflowSpec,
} from "../../types/workflow";

/** Per-run options for {@link WorkflowState.runWorkflow}. */
export interface RunWorkflowOptions extends Pick<
  WorkflowRunRequest,
  "provider" | "model" | "apiKey"
> {
  /** Aborts the request and the stream (panel Stop / unmount). */
  signal?: AbortSignal;
  /** Called with every server event after it lands in the store. */
  onEvent?: (event: WorkflowRunEvent) => void;
}

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
  /** Atomically return and clear the pending intents (take before send). */
  takeNotifications: () => DesktopNotificationIntent[];

  /**
   * POST the spec to ``/workflow/run`` and consume the SSE stream — the one
   * client for this wire (the node editor runs through it).
   *
   * Every event is appended to the store (so notification intents reach the
   * desktop bridge) and handed to ``options.onEvent``. Resolves with the run
   * id once the stream ends on a terminal frame. Per-node errors land as
   * ``node-error`` events and DO NOT reject — the engine reported them.
   * Rejects when the request fails (network / non-2xx / abort) or the stream
   * ends or breaks without a terminal frame; after ``run-start`` it first
   * appends a terminal ``run-error`` row so the run log never reads as live.
   */
  runWorkflow: (
    spec: WorkflowSpec,
    inputs?: Record<string, unknown>,
    options?: RunWorkflowOptions,
  ) => Promise<string>;
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
    case "node-skipped":
      return {
        kind: "node-skipped",
        runId,
        nodeId: String(raw.nodeId ?? raw.node_id ?? ""),
        nodeType: String(raw.nodeType ?? raw.node_type ?? ""),
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

  takeNotifications: () => {
    const taken = get().pendingNotifications;
    set({ pendingNotifications: [] });
    return taken;
  },

  runWorkflow: async (spec, inputs, options = {}) => {
    const { signal, onEvent, provider, model, apiKey } = options;
    const base = await getSidecarBaseUrl();
    const url = new URL("/workflow/run", base);
    // The shared transport: the session region + search headers ride the run
    // so its data/research nodes route like a chat turn does. No deadline —
    // the stream lives as long as the run.
    const response = await sidecarFetch(
      url.toString(),
      await sidecarRequestInit("POST", {
        body: { spec, inputs: inputs ?? {}, provider, model, apiKey },
        headers: { Accept: "text/event-stream" },
        signal,
      }),
    );

    if (!response.ok || !response.body) {
      const fallback = `sidecar returned ${response.status}`;
      const parsed: unknown = await response.json().catch(() => null);
      throw new SidecarError(response.status, extractSidecarDetail(parsed, fallback));
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    // Written from the frame callback, so widen past the initialiser narrowing.
    let runId = null as string | null;
    let terminal = false as boolean;
    const handleEvent = (event: WorkflowRunEvent) => {
      get().appendEvent(event);
      if (event.kind === "run-start") runId = event.runId;
      if (_isTerminal(event)) terminal = true;
      onEvent?.(event);
    };

    let failure = null as string | null;
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
    } catch (err) {
      failure = `workflow stream failed: ${err instanceof Error ? err.message : String(err)}`;
    } finally {
      reader.releaseLock();
    }
    if (runId === null) {
      throw new Error(
        failure ??
          "workflow stream ended without a terminal frame (no run-start event) — the " +
            "sidecar rejected the spec before starting (e.g. a node type with no " +
            "server-side handler)",
      );
    }
    if (!terminal) {
      const message =
        failure ?? "workflow stream ended without a terminal frame — the sidecar crashed mid-run";
      get().appendEvent({ kind: "run-error", runId, message, durationMs: 0 });
      throw new Error(message);
    }
    return runId;
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

// ---------------------------------------------------------------------------
// Schedules + webhook URLs (R15-AGENT-023)
// ---------------------------------------------------------------------------

/** Local CRUD through the shared verb, under the list/CRUD deadline. */
function _sidecarJson<T>(
  method: SidecarMethod,
  path: string,
  opts: Pick<SidecarRequestOptions, "body" | "headers"> = {},
): Promise<T> {
  return sidecarRequest<T>(method, path, { ...opts, timeoutMs: SIDECAR_REQUEST_TIMEOUT_MS });
}

export function listSchedules(): Promise<WorkflowSchedule[]> {
  return _sidecarJson<WorkflowSchedule[]>("GET", "/workflow/schedules");
}

export function createSchedule(body: ScheduleCreate): Promise<WorkflowSchedule> {
  return _sidecarJson<WorkflowSchedule>("POST", "/workflow/schedules", { body });
}

export function setScheduleEnabled(id: string, enabled: boolean): Promise<WorkflowSchedule> {
  return _sidecarJson<WorkflowSchedule>("PATCH", `/workflow/schedules/${encodeURIComponent(id)}`, {
    body: { enabled },
  });
}

export async function deleteSchedule(id: string): Promise<void> {
  await _sidecarJson("DELETE", `/workflow/schedules/${encodeURIComponent(id)}`);
}

/**
 * Hold a webhook URL for `ref` in sidecar process memory. The URL rides a
 * header (the BYOK transport), never the body or path, and is never returned.
 */
export async function registerWebhookUrl(ref: string, url: string): Promise<void> {
  await _sidecarJson<WebhookRefs>("PUT", `/workflow/webhooks/${encodeURIComponent(ref)}`, {
    headers: { "X-Vysted-Webhook-Url": url },
  });
}

/**
 * Boot: register the keychain-held URL of every saved workflow's
 * `action.webhook` node, so a scheduled fire can deliver without the editor
 * open. A ref with no stored URL is skipped (its node errors honestly).
 */
export async function registerSavedWebhooks(
  readSecret: (ref: string) => Promise<string | null>,
): Promise<void> {
  const saved = await _sidecarJson<SavedWorkflows>("GET", "/workflow/saved");
  const refs = new Set<string>();
  for (const spec of saved.workflows) {
    for (const node of spec.nodes) {
      const ref = node.config.secret_ref;
      if (node.type === "action.webhook" && typeof ref === "string" && ref !== "") refs.add(ref);
    }
  }
  for (const ref of refs) {
    const url = await readSecret(ref);
    if (url) await registerWebhookUrl(ref, url);
  }
}

/** Select every captured desktop-notification intent (for the Tauri dispatcher). */
export function selectPendingNotifications(
  state: WorkflowState,
): readonly DesktopNotificationIntent[] {
  return state.pendingNotifications;
}
