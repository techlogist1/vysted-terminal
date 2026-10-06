/**
 * Pre-run validation for the node editor (`NodeEditorPanel.handleRun`).
 *
 * R15-CODE-PLATFORM-017: code nodes (`transform.code`) used to evaluate
 * CLIENT-side in a mathjs sandbox after the server's SSE stream ended, while
 * an agent/MCP-triggered run of the SAME spec evaluated the SAME node
 * server-side in Python `ast` (`sidecar/services/workflow_nodes/code_node.py`)
 * — two evaluators silently disagreeing on `round(2.5)`, `^` and ternaries.
 * The server evaluator is now canonical for EVERY run path (the sidecar
 * registry has carried a `transform.code` handler since v0.6.0, so nothing
 * about routing a spec that contains one needs to stay local); the editor
 * sends the full spec straight to `/workflow/run`, and mathjs
 * (`code-node.ts`) is used only for the inline syntax check and the
 * inspector's live preview, never to compute a run's real output.
 *
 * The one thing still worth checking BEFORE the POST: a cycle anywhere in
 * the graph makes the engine raise in `_validate_spec` before emitting a
 * single frame, and `routers/workflow.py` swallows that exception — the SSE
 * stream closes with zero frames, which the panel would otherwise report as
 * a false "ok". `validateWorkflow` catches that honestly, pre-run.
 */

import type { WorkflowSpec } from "../../../types/workflow";

export interface WorkflowValidation {
  /** Pre-run validation error; when set the run must not start. */
  error?: string;
}

/** Reject a spec whose graph contains a cycle. */
export function validateWorkflow(spec: WorkflowSpec): WorkflowValidation {
  const ids = new Set(spec.nodes.map((n) => n.id));
  if (topoOrder(ids, spec.edges) === null) {
    return { error: "workflow contains a cycle — break the loop before running" };
  }
  return {};
}

/**
 * Kahn's algorithm over the full graph (`edges` with an endpoint outside
 * `ids` are ignored); null on a cycle.
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
