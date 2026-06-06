"use client";

/**
 * Single custom react-flow node renderer.
 *
 * Every node type in the registry — built-in or plugin — renders through
 * this component. The renderer reads the node's display label from
 * `data.label` and the port shape from the registry (via `usePluginsStore`
 * for plugin nodes, the static built-in map for first-party nodes), then
 * draws one `<Handle>` per port.
 */

import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { memo, useMemo } from "react";

import { cn } from "@/lib/utils";
import { usePluginsStore } from "@/store/plugins";

import type { FlowNodeData } from "./graph-state";
import { BUILT_IN_NODE_SPECS, buildRegistry, findEntry } from "./node-registry";

function VystedNodeImpl({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const pluginNodes = usePluginsStore((s) => s.nodes);
  const spec = useMemo(() => {
    const builtIn = (
      BUILT_IN_NODE_SPECS as Record<
        string,
        (typeof BUILT_IN_NODE_SPECS)[keyof typeof BUILT_IN_NODE_SPECS] | undefined
      >
    )[data.nodeTypeId];
    if (builtIn !== undefined) {
      return builtIn;
    }
    const registry = buildRegistry(pluginNodes);
    return findEntry(registry, data.nodeTypeId)?.spec;
  }, [data.nodeTypeId, pluginNodes]);

  const minHeight = Math.max(
    48,
    24 + Math.max(spec?.inputs.length ?? 0, spec?.outputs.length ?? 0) * 16 + 8,
  );

  return (
    <div
      data-testid={`vysted-node-${data.nodeTypeId}`}
      style={{ minHeight }}
      className={cn(
        "border-charcoal-700 bg-charcoal-850 rounded-control min-w-[140px] border px-3 py-2 font-mono",
        selected && "border-amber-500",
      )}
    >
      {/* Input handles on the left */}
      {spec?.inputs.map((port, idx) => (
        <Handle
          key={`in-${port.id}`}
          type="target"
          position={Position.Left}
          id={port.id}
          style={{ top: 24 + idx * 16 }}
          className="!h-2 !w-2 !border-amber-400 !bg-amber-400"
        />
      ))}
      <div className="text-charcoal-100 text-caption">{data.label}</div>
      <div className="text-charcoal-500 text-micro mt-0.5">{data.nodeTypeId}</div>
      {/* Output handles on the right */}
      {spec?.outputs.map((port, idx) => (
        <Handle
          key={`out-${port.id}`}
          type="source"
          position={Position.Right}
          id={port.id}
          style={{ top: 24 + idx * 16 }}
          className="!h-2 !w-2 !border-amber-400 !bg-amber-400"
        />
      ))}
    </div>
  );
}

export const VystedNode = memo(VystedNodeImpl);
