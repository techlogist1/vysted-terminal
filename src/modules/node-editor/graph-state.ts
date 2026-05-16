/**
 * Graph-state helpers — pure data-model functions the canvas wraps.
 *
 * react-flow stores its nodes/edges as `Node[]` / `Edge[]` (see
 * `@xyflow/react`'s `useNodesState` / `useEdgesState` hooks). The
 * sidecar persists `WorkflowSpec.nodes[]` / `WorkflowSpec.edges[]`
 * (see `types/workflow.ts`). The two shapes are similar but not
 * identical:
 *
 * - react-flow `Node.data` is free-form per-node payload; we stash the
 *   node-type id + config + (cached) palette label there so the
 *   custom-node renderer can read them without an extra registry lookup.
 * - react-flow `Edge.source` / `target` are node ids; the workflow
 *   contract distinguishes ports (`sourcePort` / `targetPort`).
 *
 * These pure functions are unit-tested in `graph-state.test.ts`;
 * `NodeEditorPanel` calls them at save/load boundaries.
 */

import type { Edge, Node } from "@xyflow/react";

import type { WorkflowEdge, WorkflowNode, WorkflowSpec } from "../../../types/workflow";
import type { ConfigField } from "./node-registry";

/** Data stored on every react-flow node so the renderer + save round-trip work. */
export interface FlowNodeData extends Record<string, unknown> {
  /** Stable node-type id (e.g. `"data.fetch_quote"`). */
  nodeTypeId: string;
  /** Display label shown on the node body (resolved from the registry). */
  label: string;
  /** Free-form per-node configuration (round-tripped to/from the sidecar). */
  config: Record<string, unknown>;
}

/** react-flow node type id this module uses for its single custom node renderer. */
export const FLOW_NODE_TYPE = "vystedNode";

/** Build a freshly-spawned node at the given canvas position. */
export function createFlowNode(args: {
  id: string;
  nodeTypeId: string;
  label: string;
  position: { x: number; y: number };
  config?: Record<string, unknown>;
}): Node<FlowNodeData> {
  return {
    id: args.id,
    type: FLOW_NODE_TYPE,
    position: args.position,
    data: {
      nodeTypeId: args.nodeTypeId,
      label: args.label,
      config: args.config ?? {},
    },
  };
}

/** Build a fresh react-flow edge connecting two nodes' ports. */
export function createFlowEdge(args: {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  targetHandle?: string | null;
}): Edge {
  return {
    id: args.id,
    source: args.source,
    target: args.target,
    sourceHandle: args.sourceHandle ?? undefined,
    targetHandle: args.targetHandle ?? undefined,
  };
}

/** Generate a UUID-shaped id without the `crypto.randomUUID` dependency. */
export function generateId(prefix: string): string {
  const rand = Math.random().toString(36).slice(2, 10);
  const time = Date.now().toString(36);
  return `${prefix}-${time}-${rand}`;
}

// ---------------------------------------------------------------------------
// Flow ↔ Workflow round-trip
// ---------------------------------------------------------------------------

/** Convert the current canvas state to a `WorkflowSpec` ready for `POST /workflow/save`. */
export function flowToSpec(args: {
  id: string;
  name: string;
  description?: string;
  nodes: readonly Node<FlowNodeData>[];
  edges: readonly Edge[];
  updatedAt?: number;
}): WorkflowSpec {
  const nodes: WorkflowNode[] = args.nodes.map((node) => ({
    id: node.id,
    type: node.data.nodeTypeId,
    position: { x: node.position.x, y: node.position.y },
    config: node.data.config,
  }));
  const edges: WorkflowEdge[] = args.edges.map((edge) => ({
    id: edge.id,
    sourceNode: edge.source,
    sourcePort: edge.sourceHandle ?? "out",
    targetNode: edge.target,
    targetPort: edge.targetHandle ?? "in",
  }));
  return {
    id: args.id,
    name: args.name,
    description: args.description,
    version: 1,
    nodes,
    edges,
    updatedAt: args.updatedAt ?? Date.now(),
  };
}

/**
 * Hydrate a `WorkflowSpec` into the react-flow node/edge arrays. The
 * registry is consulted to resolve each node-type id's display label.
 */
export function specToFlow(
  spec: WorkflowSpec,
  resolveLabel: (nodeTypeId: string) => string,
): { nodes: Node<FlowNodeData>[]; edges: Edge[] } {
  const nodes: Node<FlowNodeData>[] = spec.nodes.map((node) =>
    createFlowNode({
      id: node.id,
      nodeTypeId: node.type,
      label: resolveLabel(node.type),
      position: node.position,
      config: node.config,
    }),
  );
  const edges: Edge[] = spec.edges.map((edge) =>
    createFlowEdge({
      id: edge.id,
      source: edge.sourceNode,
      target: edge.targetNode,
      sourceHandle: edge.sourcePort,
      targetHandle: edge.targetPort,
    }),
  );
  return { nodes, edges };
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/** Remove a node and any edges touching it. */
export function removeNodeAndEdges(
  nodes: readonly Node<FlowNodeData>[],
  edges: readonly Edge[],
  nodeId: string,
): { nodes: Node<FlowNodeData>[]; edges: Edge[] } {
  return {
    nodes: nodes.filter((node) => node.id !== nodeId),
    edges: edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId),
  };
}

/** Update the config of a single node (immutable copy). */
export function updateNodeConfig(
  nodes: readonly Node<FlowNodeData>[],
  nodeId: string,
  patch: Record<string, unknown>,
): Node<FlowNodeData>[] {
  return nodes.map((node) =>
    node.id === nodeId
      ? {
          ...node,
          data: {
            ...node.data,
            config: { ...node.data.config, ...patch },
          },
        }
      : node,
  );
}

/**
 * Coerce a config-form input value (always `string` from a DOM input)
 * into the typed shape declared by its `ConfigField.kind`. Numeric
 * fields fall back to the previous value if the user types a non-numeric
 * string; boolean fields parse `"true"`/`"false"`.
 */
export function coerceConfigValue(
  kind: ConfigField["kind"],
  raw: string,
  previous: unknown,
): unknown {
  switch (kind) {
    case "number": {
      if (raw === "") {
        return previous;
      }
      const parsed = Number(raw);
      return Number.isFinite(parsed) ? parsed : previous;
    }
    case "boolean":
      return raw === "true";
    default:
      return raw;
  }
}
