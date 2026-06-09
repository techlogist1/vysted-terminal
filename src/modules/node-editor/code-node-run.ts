/**
 * Hybrid run path for code nodes — pure functions the panel's run
 * lifecycle wraps.
 *
 * THE REAL EXECUTION PATH (documented for R7): `NodeEditorPanel.handleRun`
 * serializes the canvas (`flowToSpec`) and POSTs `/workflow/run`; the
 * sidecar (`routers/workflow.py` → `services/workflow_engine.py`)
 * validates the DAG against its module-level handler registry, runs ready
 * waves concurrently, and streams `WorkflowRunEvent` SSE frames back,
 * which `applyEvent` reduces into the run overlay.
 *
 * The sidecar registry has NO handler for `transform.code` (mathjs is a
 * frontend dependency), so the engine would reject any spec containing
 * one at `_validate_spec`. Until the Python parity handler lands (see
 * docs/redesign/INTEGRATION_NOTES_R7_HACK.md) the run path is HYBRID:
 *
 *   1. `partitionWorkflow` splits the spec — server nodes + the edges
 *      among them go to `/workflow/run` unchanged; code nodes stay local.
 *   2. The streamed `node-output` outputs are collected by node id.
 *   3. After the server stream ends, `evaluateCodeNodes` walks the code
 *      nodes in topological order, wiring `inputs[targetPort] =
 *      outputs[sourceNode][sourcePort]` exactly like the engine does, and
 *      evaluates each expression in the mathjs sandbox, emitting the same
 *      `WorkflowRunEvent` shapes into the overlay reducer.
 *
 * Constraints enforced honestly, before the run starts: an edge FROM a
 * code node INTO a server-executed node is rejected — the sidecar cannot
 * see client-side outputs mid-run — and a cycle ANYWHERE in the spec
 * (server-only cycles included) is rejected, because the engine raises in
 * `_validate_spec` before emitting a single frame and the stream would
 * otherwise close empty. Code → code chains are fine (local topological
 * evaluation); server → code is the designed direction. Failed upstreams
 * propagate as "upstream node failed", mirroring
 * `workflow_engine.run_workflow` semantics.
 */

import type { WorkflowRunEvent, WorkflowSpec } from "../../../types/workflow";
import {
  CODE_NODE_ID,
  CODE_NODE_OUTPUT_PORT,
  codeNodeBindings,
  codeNodeExpression,
  evaluateCodeExpression,
} from "./code-node";

// ---------------------------------------------------------------------------
// Partition
// ---------------------------------------------------------------------------

export interface WorkflowPartition {
  /** The spec to POST to `/workflow/run` — code nodes + their edges removed. */
  server: WorkflowSpec;
  /** Code node ids in dependency order (code → code subgraph, Kahn). */
  codeOrder: string[];
  /** Pre-run validation error; when set the run must not start. */
  error?: string;
}

/** Split a spec into the server-executed sub-spec and the local code plan. */
export function partitionWorkflow(spec: WorkflowSpec): WorkflowPartition {
  const codeIds = new Set(spec.nodes.filter((n) => n.type === CODE_NODE_ID).map((n) => n.id));

  for (const edge of spec.edges) {
    if (codeIds.has(edge.sourceNode) && !codeIds.has(edge.targetNode)) {
      return {
        server: spec,
        codeOrder: [],
        error:
          `code node "${edge.sourceNode}" feeds server node "${edge.targetNode}" — ` +
          "code outputs can only feed other code nodes (code nodes evaluate " +
          "client-side after the sidecar run)",
      };
    }
  }

  // Cycle check over the FULL graph, not just the code subgraph. A cycle
  // among server nodes makes the engine raise in `_validate_spec` BEFORE
  // it emits run-start; routers/workflow.py swallows the exception, so the
  // SSE stream closes with zero frames — reject honestly here instead of
  // letting the run start at all. The full topological order restricted to
  // the code ids is still a valid topological order of the code subgraph,
  // so it doubles as the local evaluation plan.
  const fullOrder = topoOrder(new Set(spec.nodes.map((n) => n.id)), spec.edges);
  if (fullOrder === null) {
    return {
      server: spec,
      codeOrder: [],
      error: "workflow contains a cycle — break the loop before running",
    };
  }

  const server: WorkflowSpec = {
    ...spec,
    nodes: spec.nodes.filter((n) => !codeIds.has(n.id)),
    edges: spec.edges.filter((e) => !codeIds.has(e.sourceNode) && !codeIds.has(e.targetNode)),
  };
  return { server, codeOrder: fullOrder.filter((id) => codeIds.has(id)) };
}

/**
 * Kahn's algorithm over the subgraph induced by `ids` (edges with an
 * endpoint outside the set are ignored); null on a cycle.
 */
function topoOrder(ids: ReadonlySet<string>, edges: WorkflowSpec["edges"]): string[] | null {
  const inDegree = new Map<string, number>();
  const children = new Map<string, string[]>();
  for (const id of ids) {
    inDegree.set(id, 0);
    children.set(id, []);
  }
  for (const edge of edges) {
    if (ids.has(edge.sourceNode) && ids.has(edge.targetNode)) {
      inDegree.set(edge.targetNode, (inDegree.get(edge.targetNode) ?? 0) + 1);
      children.get(edge.sourceNode)!.push(edge.targetNode);
    }
  }
  const ready = [...ids].filter((id) => inDegree.get(id) === 0).sort();
  const order: string[] = [];
  while (ready.length > 0) {
    const id = ready.shift()!;
    order.push(id);
    for (const child of children.get(id)!.sort()) {
      const next = inDegree.get(child)! - 1;
      inDegree.set(child, next);
      if (next === 0) {
        ready.push(child);
      }
    }
    ready.sort();
  }
  return order.length === ids.size ? order : null;
}

// ---------------------------------------------------------------------------
// Evaluation
// ---------------------------------------------------------------------------

export interface CodeEvaluationResult {
  /** Code node ids whose evaluation failed (eval error or failed upstream). */
  failedNodeIds: string[];
  /** Outputs per code node id — `{ value: <result> }` on the output port. */
  outputsByNode: Map<string, Record<string, unknown>>;
}

/**
 * Evaluate every code node in `codeOrder` against the collected upstream
 * outputs, emitting `node-start` + `node-output` / `node-error` events
 * (the same shapes the sidecar streams) through `emit`.
 *
 * `outputsByNode` carries the server nodes' streamed outputs on entry and
 * accumulates code-node outputs as the walk proceeds, so code → code
 * chains resolve. A node whose upstream produced no outputs (server
 * failure or earlier code failure) errors with "upstream node failed",
 * mirroring the engine. An unwired binding evaluates with the symbol
 * missing from scope — mathjs surfaces "Undefined symbol …" honestly.
 */
export function evaluateCodeNodes(
  spec: WorkflowSpec,
  codeOrder: readonly string[],
  outputsByNode: Map<string, Record<string, unknown>>,
  runId: string,
  emit: (event: WorkflowRunEvent) => void,
): CodeEvaluationResult {
  const nodesById = new Map(spec.nodes.map((n) => [n.id, n]));
  const failedNodeIds: string[] = [];

  for (const nodeId of codeOrder) {
    const node = nodesById.get(nodeId);
    if (node === undefined) {
      continue;
    }
    const startedAt = Date.now();
    const startedMark = performance.now();
    emit({ kind: "node-start", runId, nodeId, nodeType: CODE_NODE_ID, startedAt });

    const inputEdges = spec.edges.filter((e) => e.targetNode === nodeId);
    const upstreamFailed = inputEdges.some((e) => !outputsByNode.has(e.sourceNode));
    if (upstreamFailed) {
      failedNodeIds.push(nodeId);
      emit({ kind: "node-error", runId, nodeId, message: "upstream node failed", durationMs: 0 });
      continue;
    }

    const bindings = new Set(codeNodeBindings(node.config));
    const scope: Record<string, unknown> = {};
    for (const edge of inputEdges) {
      if (bindings.has(edge.targetPort)) {
        scope[edge.targetPort] = outputsByNode.get(edge.sourceNode)?.[edge.sourcePort];
      }
    }

    const result = evaluateCodeExpression(codeNodeExpression(node.config), scope);
    const durationMs = performance.now() - startedMark;
    if (result.ok) {
      const outputs = { [CODE_NODE_OUTPUT_PORT]: result.value };
      outputsByNode.set(nodeId, outputs);
      emit({ kind: "node-output", runId, nodeId, outputs, durationMs });
    } else {
      failedNodeIds.push(nodeId);
      emit({ kind: "node-error", runId, nodeId, message: result.error, durationMs });
    }
  }

  return { failedNodeIds, outputsByNode };
}
