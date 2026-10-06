import { describe, expect, it } from "vitest";

import type { WorkflowSpec } from "../../../types/workflow";
import { validateWorkflow } from "./code-node-run";

function spec(args: {
  nodes: Array<{ id: string; type: string; config?: Record<string, unknown> }>;
  edges?: Array<{ id: string; from: string; fromPort: string; to: string; toPort: string }>;
}): WorkflowSpec {
  return {
    id: "wf-test",
    name: "test",
    version: 1,
    updatedAt: 0,
    nodes: args.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: { x: 0, y: 0 },
      config: n.config ?? {},
    })),
    edges: (args.edges ?? []).map((e) => ({
      id: e.id,
      sourceNode: e.from,
      sourcePort: e.fromPort,
      targetNode: e.to,
      targetPort: e.toPort,
    })),
  };
}

const codeConfig = (expression: string, inputs: string[]) => ({ expression, inputs });

describe("validateWorkflow (R15-CODE-PLATFORM-017)", () => {
  it("passes an acyclic spec through with no error", () => {
    const s = spec({
      nodes: [
        { id: "n1", type: "data.fetch_quote" },
        { id: "n2", type: "action.log" },
      ],
      edges: [{ id: "e1", from: "n1", fromPort: "quote", to: "n2", toPort: "value" }],
    });
    expect(validateWorkflow(s).error).toBeUndefined();
  });

  it("accepts a code node feeding a server node — the old partition restriction is gone", () => {
    // Before this fix, an edge from transform.code into a server node was
    // rejected client-side ("code outputs can only feed other code nodes").
    // Now every node runs in the same server-side DAG pass, so that
    // restriction no longer applies — only a cycle is still rejected.
    const s = spec({
      nodes: [
        { id: "c1", type: "transform.code", config: codeConfig("1 + 1", []) },
        { id: "n1", type: "action.log" },
      ],
      edges: [{ id: "e1", from: "c1", fromPort: "value", to: "n1", toPort: "value" }],
    });
    expect(validateWorkflow(s).error).toBeUndefined();
  });

  it("rejects a cycle, code nodes and server nodes alike", () => {
    const s = spec({
      nodes: [
        { id: "c1", type: "transform.code", config: codeConfig("x", ["x"]) },
        { id: "c2", type: "transform.code", config: codeConfig("y", ["y"]) },
      ],
      edges: [
        { id: "e1", from: "c1", fromPort: "value", to: "c2", toPort: "y" },
        { id: "e2", from: "c2", fromPort: "value", to: "c1", toPort: "x" },
      ],
    });
    expect(validateWorkflow(s).error).toMatch(/cycle/);
  });

  it("rejects a cycle among SERVER nodes — the engine raises pre-run-start on those", () => {
    // Without this pre-check this spec would reach the sidecar, where
    // `_validate_spec` raises before emitting a single frame and the SSE
    // stream closes empty — the panel would then report a false "ok".
    const s = spec({
      nodes: [
        { id: "n1", type: "data.fetch_quote" },
        { id: "n2", type: "action.log" },
      ],
      edges: [
        { id: "e1", from: "n1", fromPort: "quote", to: "n2", toPort: "value" },
        { id: "e2", from: "n2", fromPort: "value", to: "n1", toPort: "symbol" },
      ],
    });
    expect(validateWorkflow(s).error).toMatch(/cycle/);
  });
});
