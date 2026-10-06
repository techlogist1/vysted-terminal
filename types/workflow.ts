/**
 * Vysted Terminal — workflow engine wire contract.
 *
 * Phase 4 ships a visual node-editor (react-flow via `@xyflow/react`) that
 * lets users compose research → analyze → decide flows without code. The
 * graph executes in the Python sidecar via `services/workflow_engine.py`
 * (asyncio + per-node observability + SSE event stream).
 *
 * This file is foundation-tier. Teammate W (concrete engine + 10 built-in
 * nodes) and Teammate N (node-editor frontend + run overlay) both import
 * from here. The 10 built-in node TYPES are NOT enumerated in this file —
 * the engine treats node types as free-form strings keyed into a runtime
 * registry, so plugins can contribute custom nodes via the locked
 * `VystedPlugin.getNodes()` capability without contract changes.
 *
 * Run-time observability piggybacks on the AI-layer's SSE protocol shape
 * (see `LLMStreamEvent` in `types/ai.ts`): discriminated union on `kind`
 * so the run-overlay UI can dispatch each event narrowly.
 */

import type { LLMProviderId } from "./ai";

// ---------------------------------------------------------------------------
// Graph
// ---------------------------------------------------------------------------

/** A node in a workflow graph. */
export interface WorkflowNode {
  /** Stable identifier unique within the workflow (e.g. UUID v4). */
  id: string;
  /**
   * Node-type identifier; resolved at run time against the registry in
   * `services/workflow_nodes`. Built-in types are `data.fetch_quote`,
   * `data.fetch_history`, `compute.indicator`, `ai.agent_invoke`,
   * `logic.branch`, `logic.compare`, `action.log`, `action.notify_desktop`,
   * `transform.json_path`, `flow.sleep`. Plugin-contributed types use the
   * id from the matching `NodeSpec` in `types/plugin.ts`.
   */
  type: string;
  /** Canvas position — node-editor only; engine ignores. */
  position: { x: number; y: number };
  /**
   * Free-form per-node configuration (e.g. `{"symbol": "AAPL", "period": "1y"}`).
   * Schema is owned by each node type's handler; the engine treats it as opaque.
   */
  config: Record<string, unknown>;
}

/** An edge connecting two nodes' ports. */
export interface WorkflowEdge {
  /** Stable identifier unique within the workflow. */
  id: string;
  sourceNode: string;
  sourcePort: string;
  targetNode: string;
  targetPort: string;
}

/** A complete workflow — the unit of save / load / run. */
export interface WorkflowSpec {
  /** Stable identifier; assigned by the sidecar on first save. */
  id: string;
  /** Display name shown in the node-editor toolbar + workflow list. */
  name: string;
  /** Optional one-line description shown in the workflow list. */
  description?: string;
  /**
   * Schema version; v0.5.0 ships `1`. The sidecar refuses to load a saved
   * spec of another major (409) and lists it under `unreadable`.
   */
  version: number;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  /** Epoch milliseconds when this workflow was last saved. */
  updatedAt: number;
}

/** A saved row this build cannot open (invalid spec or another schema major). */
export interface UnreadableWorkflow {
  id: string;
  name: string;
  reason: string;
}

/** `GET /workflow/saved` — the openable specs plus the rows that are not. */
export interface SavedWorkflows {
  workflows: WorkflowSpec[];
  unreadable: UnreadableWorkflow[];
}

// ---------------------------------------------------------------------------
// Run protocol
// ---------------------------------------------------------------------------

/** `POST /workflow/run` request body. */
export interface WorkflowRunRequest {
  spec: WorkflowSpec;
  /** Run-time inputs threaded into source nodes (e.g. a focused symbol). */
  inputs?: Record<string, unknown>;
  /** Run mode — only `"full"` (walk the whole graph); the sidecar answers 400 to any other. */
  mode?: "full";
  /**
   * Foreground BYOK creds for `ai.agent_invoke` nodes (the chat selection),
   * the same names as the agent-invoke request. Held for the run only; never
   * persisted. A node config never carries a key (the sidecar rejects it).
   */
  provider?: LLMProviderId;
  model?: string;
  apiKey?: string;
}

/**
 * One event in a workflow run's SSE stream. Mirrors `LLMStreamEvent`'s
 * discriminated-union shape so the run-overlay UI handles each kind
 * narrowly.
 */
export type WorkflowRunEvent =
  | { kind: "run-start"; runId: string; startedAt: number }
  | { kind: "node-start"; runId: string; nodeId: string; nodeType: string; startedAt: number }
  | {
      kind: "node-output";
      runId: string;
      nodeId: string;
      /** A port on an un-taken branch path is omitted (not `null`). */
      outputs: Record<string, unknown>;
      durationMs: number;
    }
  | { kind: "node-error"; runId: string; nodeId: string; message: string; durationMs: number }
  /** Every input came from an un-taken branch path, so the node did not run. */
  | { kind: "node-skipped"; runId: string; nodeId: string; nodeType: string }
  | { kind: "run-complete"; runId: string; durationMs: number }
  | { kind: "run-error"; runId: string; message: string; durationMs: number };

/** Per-node result captured for replay + the run-log display. */
export interface NodeRunResult {
  nodeId: string;
  nodeType: string;
  status: "ok" | "error" | "skipped";
  outputs: Record<string, unknown>;
  error?: string;
  durationMs: number;
  startedAt: number;
}

/** Final result of a workflow run, returned by `GET /workflow/runs/{id}`. */
export interface WorkflowRunResult {
  runId: string;
  workflowId: string;
  status: "ok" | "error";
  startedAt: number;
  durationMs: number;
  nodes: NodeRunResult[];
  error?: string;
}

// ---------------------------------------------------------------------------
// Schedules (R15-AGENT-023) — mirror of `sidecar/models/workflow.py`
// ---------------------------------------------------------------------------

/** The shortest interval a schedule may fire on (the sidecar rejects less). */
export const MIN_SCHEDULE_INTERVAL_MINUTES = 5;

/** Fire every `everyMinutes` (>= 5) after the last fire (or creation). */
export interface IntervalTrigger {
  kind: "interval";
  everyMinutes: number;
}

/**
 * Fire once per new exchange announcement for `symbol` whose headline contains
 * `phrase` (case-insensitive); the announcement is the run's input.
 */
export interface AnnouncementTrigger {
  kind: "announcement";
  symbol: string;
  phrase: string;
}

export type ScheduleTrigger = IntervalTrigger | AnnouncementTrigger;

/** `POST /workflow/schedules` body. */
export interface ScheduleCreate {
  workflowId: string;
  trigger: ScheduleTrigger;
  enabled?: boolean;
}

/** One persisted schedule plus its last outcome. Fires only while the app is open. */
export interface WorkflowSchedule {
  id: string;
  workflowId: string;
  trigger: ScheduleTrigger;
  enabled: boolean;
  createdAt: number;
  /** Epoch ms of the last fire; `null` until the first. */
  lastFiredAt: number | null;
  /** Announcement trigger: ISO timestamp of the newest announcement fired on. */
  lastSeen: string | null;
  lastStatus: "running" | "ok" | "error" | null;
  lastDetail: string | null;
}

/** `GET /workflow/webhooks` — the refs with a URL held in sidecar memory (never the URLs). */
export interface WebhookRefs {
  refs: string[];
}
