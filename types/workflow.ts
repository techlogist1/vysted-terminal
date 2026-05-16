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
  /** Schema version; the engine refuses unknown majors. v0.5.0 ships `1`. */
  version: number;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  /** Epoch milliseconds when this workflow was last saved. */
  updatedAt: number;
}

// ---------------------------------------------------------------------------
// Run protocol
// ---------------------------------------------------------------------------

/** `POST /workflow/run` request body. */
export interface WorkflowRunRequest {
  spec: WorkflowSpec;
  /** Run-time inputs threaded into source nodes (e.g. a focused symbol). */
  inputs?: Record<string, unknown>;
  /**
   * Run mode. `"full"` walks the whole graph; `"resume-from"` restarts from
   * a previously failed node id using captured upstream outputs. Phase-4
   * default is `"full"` — `"resume-from"` is the partial-replay path.
   */
  mode?: "full" | "resume-from";
  /** Node id to resume from when `mode === "resume-from"`. */
  resumeFrom?: string;
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
      outputs: Record<string, unknown>;
      durationMs: number;
    }
  | { kind: "node-error"; runId: string; nodeId: string; message: string; durationMs: number }
  | { kind: "run-complete"; runId: string; durationMs: number }
  | { kind: "run-error"; runId: string; message: string; durationMs: number };

/** Per-node result captured for replay + the run-log display. */
export interface NodeRunResult {
  nodeId: string;
  nodeType: string;
  status: "ok" | "error";
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
