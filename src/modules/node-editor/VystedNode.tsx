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

import {
  CODE_NODE_ID,
  codeNodeBindings,
  codeNodeExpression,
  compileCodeExpression,
} from "./code-node";
import type { FlowNodeData } from "./graph-state";
import { FIRST_PARTY_NODE_SPECS, buildRegistry, findEntry } from "./node-registry";

function VystedNodeImpl({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const pluginNodes = usePluginsStore((s) => s.nodes);
  const spec = useMemo(() => {
    const firstParty = FIRST_PARTY_NODE_SPECS[data.nodeTypeId];
    if (firstParty !== undefined) {
      return firstParty;
    }
    const registry = buildRegistry(pluginNodes);
    return findEntry(registry, data.nodeTypeId)?.spec;
  }, [data.nodeTypeId, pluginNodes]);

  // Code nodes derive their input ports from config.inputs — each binding
  // name is a port AND a variable in the sandboxed expression scope.
  const isCodeNode = data.nodeTypeId === CODE_NODE_ID;
  const inputs = useMemo(() => {
    if (!isCodeNode) {
      return spec?.inputs ?? [];
    }
    return codeNodeBindings(data.config).map((name) => ({
      id: name,
      label: name,
      type: "any" as const,
    }));
  }, [data.config, isCodeNode, spec]);

  const expression = isCodeNode ? codeNodeExpression(data.config) : "";
  const expressionError = useMemo(
    () => (isCodeNode ? compileCodeExpression(expression).error : undefined),
    [expression, isCodeNode],
  );

  const minHeight = Math.max(48, 24 + Math.max(inputs.length, spec?.outputs.length ?? 0) * 16 + 8);

  return (
    <div
      data-testid={`vysted-node-${data.nodeTypeId}`}
      style={{ minHeight }}
      className={cn(
        "border-charcoal-700 bg-charcoal-850 rounded-control min-w-[140px] border px-3 py-2 font-mono",
        selected && "border-charcoal-600",
      )}
    >
      {/* Input handles on the left */}
      {inputs.map((port, idx) => (
        <Handle
          key={`in-${port.id}`}
          type="target"
          position={Position.Left}
          id={port.id}
          style={{ top: 24 + idx * 16 }}
          className="!border-charcoal-600 !bg-charcoal-400 !h-2 !w-2"
        />
      ))}
      <div className="text-charcoal-100 text-caption">{data.label}</div>
      <div className="text-charcoal-500 text-micro mt-0.5">{data.nodeTypeId}</div>
      {isCodeNode && (
        <div
          data-testid="code-node-expression-preview"
          className={cn(
            "text-micro mt-1 max-w-[180px] truncate font-mono",
            expressionError !== undefined ? "text-negative" : "text-charcoal-300",
          )}
        >
          {expressionError !== undefined ? `! ${expressionError}` : expression}
        </div>
      )}
      {/* Output handles on the right */}
      {spec?.outputs.map((port, idx) => (
        <Handle
          key={`out-${port.id}`}
          type="source"
          position={Position.Right}
          id={port.id}
          style={{ top: 24 + idx * 16 }}
          className="!border-charcoal-600 !bg-charcoal-400 !h-2 !w-2"
        />
      ))}
    </div>
  );
}

export const VystedNode = memo(VystedNodeImpl);
