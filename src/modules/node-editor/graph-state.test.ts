import { describe, expect, it } from "vitest";

import {
  coerceConfigValue,
  createFlowEdge,
  createFlowNode,
  flowToSpec,
  generateId,
  removeNodeAndEdges,
  specToFlow,
  updateNodeConfig,
  type FlowNodeData,
} from "./graph-state";
import type { WorkflowSpec } from "../../../types/workflow";

function aNode(id: string, nodeTypeId = "data.fetch_quote") {
  return createFlowNode({
    id,
    nodeTypeId,
    label: nodeTypeId,
    position: { x: 0, y: 0 },
    config: { symbol: "AAPL" },
  });
}

describe("graph-state: createFlowNode", () => {
  it("constructs a react-flow node with the vystedNode type and data payload", () => {
    const node = aNode("n1");
    expect(node.id).toBe("n1");
    expect(node.type).toBe("vystedNode");
    expect(node.data.nodeTypeId).toBe("data.fetch_quote");
    expect(node.data.config).toEqual({ symbol: "AAPL" });
  });
});

describe("graph-state: flowToSpec round-trip", () => {
  const fetchNode = aNode("n1", "data.fetch_quote");
  const indicatorNode = createFlowNode({
    id: "n2",
    nodeTypeId: "compute.indicator",
    label: "compute.indicator",
    position: { x: 200, y: 0 },
    config: { indicator: "rsi", period: 14 },
  });
  const edge = createFlowEdge({
    id: "e1",
    source: "n1",
    target: "n2",
    sourceHandle: "quote",
    targetHandle: "series",
  });

  it("serialises canvas state into a WorkflowSpec preserving ports + config + position", () => {
    const spec = flowToSpec({
      id: "wf-1",
      name: "Test",
      description: "round-trip test",
      nodes: [fetchNode, indicatorNode],
      edges: [edge],
      updatedAt: 100,
    });
    expect(spec.id).toBe("wf-1");
    expect(spec.name).toBe("Test");
    expect(spec.version).toBe(1);
    expect(spec.nodes).toHaveLength(2);
    expect(spec.nodes[0]).toEqual({
      id: "n1",
      type: "data.fetch_quote",
      position: { x: 0, y: 0 },
      config: { symbol: "AAPL" },
    });
    expect(spec.edges[0]).toEqual({
      id: "e1",
      sourceNode: "n1",
      sourcePort: "quote",
      targetNode: "n2",
      targetPort: "series",
    });
    expect(spec.updatedAt).toBe(100);
  });

  it("falls back to 'out'/'in' when an edge has no source/target handle", () => {
    const handleless = createFlowEdge({
      id: "e2",
      source: "n1",
      target: "n2",
    });
    const spec = flowToSpec({
      id: "wf-2",
      name: "Test",
      nodes: [fetchNode, indicatorNode],
      edges: [handleless],
    });
    expect(spec.edges[0].sourcePort).toBe("out");
    expect(spec.edges[0].targetPort).toBe("in");
  });

  it("re-hydrates a sidecar WorkflowSpec back into a react-flow node + edge array", () => {
    const persisted: WorkflowSpec = {
      id: "wf-load",
      name: "Loaded",
      version: 1,
      nodes: [
        {
          id: "n1",
          type: "data.fetch_quote",
          position: { x: 10, y: 20 },
          config: { symbol: "MSFT" },
        },
        {
          id: "n2",
          type: "action.log",
          position: { x: 200, y: 20 },
          config: { level: "info" },
        },
      ],
      edges: [
        {
          id: "e1",
          sourceNode: "n1",
          sourcePort: "quote",
          targetNode: "n2",
          targetPort: "value",
        },
      ],
      updatedAt: 0,
    };
    const { nodes, edges } = specToFlow(persisted, (id) => `lbl:${id}`);
    expect(nodes).toHaveLength(2);
    expect(nodes[0].data.label).toBe("lbl:data.fetch_quote");
    expect(nodes[0].data.config).toEqual({ symbol: "MSFT" });
    expect(edges[0].source).toBe("n1");
    expect(edges[0].sourceHandle).toBe("quote");
  });

  it("save → load → save preserves the WorkflowSpec shape exactly", () => {
    const spec = flowToSpec({
      id: "wf-rt",
      name: "Round trip",
      nodes: [fetchNode, indicatorNode],
      edges: [edge],
      updatedAt: 123,
    });
    const { nodes, edges } = specToFlow(spec, (id) => id);
    const reEncoded = flowToSpec({
      id: spec.id,
      name: spec.name,
      description: spec.description,
      nodes: nodes as FlowNodeData extends Record<string, unknown> ? typeof nodes : never,
      edges,
      updatedAt: spec.updatedAt,
    });
    expect(reEncoded.nodes).toEqual(spec.nodes);
    expect(reEncoded.edges).toEqual(spec.edges);
  });
});

describe("graph-state: removeNodeAndEdges", () => {
  it("removes the node and every edge touching it", () => {
    const n1 = aNode("n1");
    const n2 = aNode("n2");
    const n3 = aNode("n3");
    const e12 = createFlowEdge({ id: "e12", source: "n1", target: "n2" });
    const e23 = createFlowEdge({ id: "e23", source: "n2", target: "n3" });
    const e13 = createFlowEdge({ id: "e13", source: "n1", target: "n3" });

    const result = removeNodeAndEdges([n1, n2, n3], [e12, e23, e13], "n2");
    expect(result.nodes.map((n) => n.id)).toEqual(["n1", "n3"]);
    expect(result.edges.map((e) => e.id)).toEqual(["e13"]);
  });

  it("is a no-op when the target node id is unknown", () => {
    const n1 = aNode("n1");
    const e1 = createFlowEdge({ id: "e1", source: "n1", target: "n1" });
    const result = removeNodeAndEdges([n1], [e1], "missing");
    expect(result.nodes).toEqual([n1]);
    expect(result.edges).toEqual([e1]);
  });
});

describe("graph-state: updateNodeConfig", () => {
  it("merges the patch into a single node's config without mutating siblings", () => {
    const n1 = aNode("n1");
    const n2 = aNode("n2");
    const out = updateNodeConfig([n1, n2], "n1", { period: "5d" });
    expect(out[0].data.config).toEqual({ symbol: "AAPL", period: "5d" });
    expect(out[1].data.config).toEqual({ symbol: "AAPL" });
    // immutable
    expect(n1.data.config).toEqual({ symbol: "AAPL" });
  });
});

describe("graph-state: coerceConfigValue", () => {
  it("coerces number inputs but falls back on non-numeric strings", () => {
    expect(coerceConfigValue("number", "14", 0)).toBe(14);
    expect(coerceConfigValue("number", "", 99)).toBe(99);
    expect(coerceConfigValue("number", "not-a-number", 99)).toBe(99);
  });
  it("coerces boolean from 'true'/'false' literal", () => {
    expect(coerceConfigValue("boolean", "true", null)).toBe(true);
    expect(coerceConfigValue("boolean", "false", null)).toBe(false);
  });
  it("passes string + textarea + select through unchanged", () => {
    expect(coerceConfigValue("string", "AAPL", "")).toBe("AAPL");
    expect(coerceConfigValue("select", "rsi", "")).toBe("rsi");
    expect(coerceConfigValue("textarea", "hi", "")).toBe("hi");
  });
});

describe("graph-state: generateId", () => {
  it("produces unique ids across rapid successive calls", () => {
    const ids = new Set<string>();
    for (let i = 0; i < 100; i++) {
      ids.add(generateId("test"));
    }
    expect(ids.size).toBe(100);
  });
  it("prefixes the id so test consumers can tell origin at a glance", () => {
    expect(generateId("node")).toMatch(/^node-/);
    expect(generateId("edge")).toMatch(/^edge-/);
  });
});
