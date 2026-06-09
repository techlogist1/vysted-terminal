import { describe, expect, it } from "vitest";

import type { WorkflowRunEvent, WorkflowSpec } from "../../../types/workflow";
import { evaluateCodeNodes, partitionWorkflow } from "./code-node-run";

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

describe("partitionWorkflow", () => {
  it("passes a code-free spec through unchanged", () => {
    const s = spec({
      nodes: [
        { id: "n1", type: "data.fetch_quote" },
        { id: "n2", type: "action.log" },
      ],
      edges: [{ id: "e1", from: "n1", fromPort: "quote", to: "n2", toPort: "value" }],
    });
    const partition = partitionWorkflow(s);
    expect(partition.error).toBeUndefined();
    expect(partition.codeOrder).toEqual([]);
    expect(partition.server.nodes).toHaveLength(2);
    expect(partition.server.edges).toHaveLength(1);
  });

  it("strips code nodes and their edges from the server sub-spec", () => {
    const s = spec({
      nodes: [
        { id: "n1", type: "data.fetch_quote" },
        { id: "c1", type: "transform.code", config: codeConfig("q.price", ["q"]) },
      ],
      edges: [{ id: "e1", from: "n1", fromPort: "quote", to: "c1", toPort: "q" }],
    });
    const partition = partitionWorkflow(s);
    expect(partition.error).toBeUndefined();
    expect(partition.server.nodes.map((n) => n.id)).toEqual(["n1"]);
    expect(partition.server.edges).toEqual([]);
    expect(partition.codeOrder).toEqual(["c1"]);
  });

  it("orders code -> code chains topologically", () => {
    const s = spec({
      nodes: [
        { id: "c2", type: "transform.code", config: codeConfig("x * 2", ["x"]) },
        { id: "c1", type: "transform.code", config: codeConfig("1 + 1", []) },
      ],
      edges: [{ id: "e1", from: "c1", fromPort: "value", to: "c2", toPort: "x" }],
    });
    expect(partitionWorkflow(s).codeOrder).toEqual(["c1", "c2"]);
  });

  it("rejects an edge from a code node into a server node, honestly", () => {
    const s = spec({
      nodes: [
        { id: "c1", type: "transform.code", config: codeConfig("1", []) },
        { id: "n1", type: "action.log" },
      ],
      edges: [{ id: "e1", from: "c1", fromPort: "value", to: "n1", toPort: "value" }],
    });
    const partition = partitionWorkflow(s);
    expect(partition.error).toMatch(/code outputs can only feed other code nodes/);
  });

  it("rejects a cycle among code nodes", () => {
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
    expect(partitionWorkflow(s).error).toMatch(/cycle/);
  });

  it("rejects a cycle among SERVER nodes — the engine raises pre-run-start on those", () => {
    // Without the full-graph Kahn pass this spec went to the sidecar, where
    // `_validate_spec` raised before emitting a single frame and the SSE
    // stream closed empty — the panel then reported a false "ok".
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
    expect(partitionWorkflow(s).error).toMatch(/cycle/);
  });

  it("rejects a mixed server cycle in a spec that also has valid code nodes", () => {
    const s = spec({
      nodes: [
        { id: "n1", type: "data.fetch_quote" },
        { id: "n2", type: "action.log" },
        { id: "c1", type: "transform.code", config: codeConfig("1 + 1", []) },
      ],
      edges: [
        { id: "e1", from: "n1", fromPort: "quote", to: "n2", toPort: "value" },
        { id: "e2", from: "n2", fromPort: "value", to: "n1", toPort: "symbol" },
      ],
    });
    const partition = partitionWorkflow(s);
    expect(partition.error).toMatch(/cycle/);
    expect(partition.codeOrder).toEqual([]);
  });

  it("still orders code nodes when acyclic server nodes coexist", () => {
    const s = spec({
      nodes: [
        { id: "n1", type: "data.fetch_quote" },
        { id: "c2", type: "transform.code", config: codeConfig("x * 2", ["x"]) },
        { id: "c1", type: "transform.code", config: codeConfig("q.price", ["q"]) },
      ],
      edges: [
        { id: "e1", from: "n1", fromPort: "quote", to: "c1", toPort: "q" },
        { id: "e2", from: "c1", fromPort: "value", to: "c2", toPort: "x" },
      ],
    });
    const partition = partitionWorkflow(s);
    expect(partition.error).toBeUndefined();
    expect(partition.codeOrder).toEqual(["c1", "c2"]);
    expect(partition.server.nodes.map((n) => n.id)).toEqual(["n1"]);
  });
});

describe("evaluateCodeNodes", () => {
  const collect = () => {
    const events: WorkflowRunEvent[] = [];
    return { events, emit: (e: WorkflowRunEvent) => events.push(e) };
  };

  it("evaluates a code node fed by streamed server outputs", () => {
    const s = spec({
      nodes: [
        { id: "n1", type: "data.fetch_quote" },
        { id: "c1", type: "transform.code", config: codeConfig("q.price * 2", ["q"]) },
      ],
      edges: [{ id: "e1", from: "n1", fromPort: "quote", to: "c1", toPort: "q" }],
    });
    const outputs = new Map<string, Record<string, unknown>>([["n1", { quote: { price: 21 } }]]);
    const { events, emit } = collect();
    const result = evaluateCodeNodes(s, ["c1"], outputs, "run-1", emit);
    expect(result.failedNodeIds).toEqual([]);
    expect(outputs.get("c1")).toEqual({ value: 42 });
    expect(events.map((e) => e.kind)).toEqual(["node-start", "node-output"]);
    const out = events[1];
    if (out.kind === "node-output") {
      expect(out.outputs).toEqual({ value: 42 });
      expect(out.runId).toBe("run-1");
    }
  });

  it("chains code -> code through accumulated outputs", () => {
    const s = spec({
      nodes: [
        { id: "c1", type: "transform.code", config: codeConfig("10", []) },
        { id: "c2", type: "transform.code", config: codeConfig("x + 5", ["x"]) },
      ],
      edges: [{ id: "e1", from: "c1", fromPort: "value", to: "c2", toPort: "x" }],
    });
    const outputs = new Map<string, Record<string, unknown>>();
    const { emit } = collect();
    const result = evaluateCodeNodes(s, ["c1", "c2"], outputs, "run-1", emit);
    expect(result.failedNodeIds).toEqual([]);
    expect(outputs.get("c2")).toEqual({ value: 15 });
  });

  it("emits node-error with the sandbox message on a bad expression", () => {
    const s = spec({
      nodes: [{ id: "c1", type: "transform.code", config: codeConfig("a +", ["a"]) }],
    });
    const { events, emit } = collect();
    const result = evaluateCodeNodes(s, ["c1"], new Map(), "run-1", emit);
    expect(result.failedNodeIds).toEqual(["c1"]);
    const err = events.find((e) => e.kind === "node-error");
    expect(err).toBeDefined();
  });

  it("propagates an upstream failure as 'upstream node failed' (engine parity)", () => {
    const s = spec({
      nodes: [
        { id: "n1", type: "data.fetch_quote" },
        { id: "c1", type: "transform.code", config: codeConfig("q.price", ["q"]) },
        { id: "c2", type: "transform.code", config: codeConfig("x + 1", ["x"]) },
      ],
      edges: [
        { id: "e1", from: "n1", fromPort: "quote", to: "c1", toPort: "q" },
        { id: "e2", from: "c1", fromPort: "value", to: "c2", toPort: "x" },
      ],
    });
    // n1 failed server-side — no outputs collected for it.
    const { events, emit } = collect();
    const result = evaluateCodeNodes(s, ["c1", "c2"], new Map(), "run-1", emit);
    expect(result.failedNodeIds).toEqual(["c1", "c2"]);
    const errors = events.filter((e) => e.kind === "node-error");
    expect(errors).toHaveLength(2);
    if (errors[0].kind === "node-error") {
      expect(errors[0].message).toBe("upstream node failed");
    }
  });

  it("surfaces an unwired binding as an Undefined symbol error, never a silent zero", () => {
    const s = spec({
      nodes: [{ id: "c1", type: "transform.code", config: codeConfig("a + b", ["a", "b"]) }],
    });
    const { events, emit } = collect();
    const result = evaluateCodeNodes(s, ["c1"], new Map(), "run-1", emit);
    expect(result.failedNodeIds).toEqual(["c1"]);
    const err = events.find((e) => e.kind === "node-error");
    if (err !== undefined && err.kind === "node-error") {
      expect(err.message).toMatch(/Undefined symbol/);
    }
  });

  it("ignores edge values targeting ports that are not declared bindings", () => {
    const s = spec({
      nodes: [
        { id: "c1", type: "transform.code", config: codeConfig("7", []) },
        { id: "c2", type: "transform.code", config: codeConfig("3", []) },
      ],
      edges: [{ id: "e1", from: "c1", fromPort: "value", to: "c2", toPort: "ghost" }],
    });
    const outputs = new Map<string, Record<string, unknown>>();
    const { emit } = collect();
    const result = evaluateCodeNodes(s, ["c1", "c2"], outputs, "run-1", emit);
    expect(result.failedNodeIds).toEqual([]);
    expect(outputs.get("c2")).toEqual({ value: 3 });
  });
});
