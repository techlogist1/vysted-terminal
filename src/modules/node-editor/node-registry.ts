/**
 * Node-editor registry — combines the 10 built-in node types (mirroring
 * `sidecar/services/workflow_nodes/builtin.py`, Teammate W) with
 * plugin-contributed node types surfaced through `usePluginsStore.nodes`
 * (via the locked `VystedPlugin.contributesNodes` capability in
 * `types/plugin.ts`).
 *
 * The registry is the single source of truth used by both the palette
 * (drag-source labels + categories) and the canvas node renderer
 * (ports + config-form schema). The 10 built-in specs are defined as
 * `NodeSpec` so plugin-contributed nodes drop in without a shape diff —
 * the palette renders both lists identically.
 *
 * Why the config schema lives here and not on `NodeSpec`: `NodeSpec` is
 * a wire-serialisable contract (`types/plugin.ts`) and cannot grow form
 * shape without breaking every plugin. The `BUILT_IN_NODE_CONFIG_FIELDS`
 * map is a host-side companion that the node-editor uses to render a
 * typed properties panel. Plugin-contributed nodes fall back to a
 * key/value textarea editor (free-form `Record<string, unknown>`).
 */

import type { NodePort, NodeSpec } from "../../../types/plugin";

// ---------------------------------------------------------------------------
// Config-field schema
// ---------------------------------------------------------------------------

/** A single field rendered in the properties panel's config form. */
export interface ConfigField {
  /** Object key inside `WorkflowNode.config`. */
  key: string;
  /** Display label rendered next to the input. */
  label: string;
  /** Input control kind — drives the rendered widget. */
  kind: "string" | "number" | "boolean" | "textarea" | "select";
  /** Placeholder shown when the field is empty. */
  placeholder?: string;
  /** Options for `kind === "select"`. */
  options?: readonly string[];
  /** Default applied when a new node of this type is dropped onto the canvas. */
  defaultValue?: string | number | boolean;
}

// ---------------------------------------------------------------------------
// Built-in node specs (mirror sidecar/services/workflow_nodes/builtin.py)
// ---------------------------------------------------------------------------

/**
 * The 10 built-in node ids — duplicated as exported constants so the test
 * suite and the palette can iterate them without restating the literal.
 */
export const BUILT_IN_NODE_IDS = [
  "data.fetch_quote",
  "data.fetch_history",
  "compute.indicator",
  "ai.agent_invoke",
  "logic.branch",
  "logic.compare",
  "action.log",
  "action.notify_desktop",
  "transform.json_path",
  "flow.sleep",
] as const;

export type BuiltInNodeId = (typeof BUILT_IN_NODE_IDS)[number];

const PORT = (id: string, label: string, type: NodePort["type"] = "any"): NodePort => ({
  id,
  label,
  type,
});

/**
 * Static registry of the 10 built-in node specs. Each spec mirrors
 * `NodeSpec` from `types/plugin.ts` so plugin-contributed nodes drop in
 * without a shape diff.
 *
 * Categories are deliberately mapped to the five `NodeSpec.category`
 * values defined in the plugin contract: `trigger | action | transform |
 * condition | output`. There is no `compute` or `data` category in the
 * contract — `data.fetch_*` nodes are `trigger`s (they originate data),
 * `compute.indicator` is a `transform`, etc.
 */
export const BUILT_IN_NODE_SPECS: Readonly<Record<BuiltInNodeId, NodeSpec>> = {
  "data.fetch_quote": {
    id: "data.fetch_quote",
    label: "Fetch Quote",
    category: "trigger",
    description: "Fetch the latest equity quote for a symbol.",
    inputs: [],
    outputs: [PORT("quote", "Quote", "object")],
  },
  "data.fetch_history": {
    id: "data.fetch_history",
    label: "Fetch History",
    category: "trigger",
    description: "Fetch OHLCV candles for a symbol over a period.",
    inputs: [],
    outputs: [PORT("series", "OHLCV Series", "object")],
  },
  "compute.indicator": {
    id: "compute.indicator",
    label: "Compute Indicator",
    category: "transform",
    description: "Compute a technical indicator over a price series.",
    inputs: [PORT("series", "Series", "object")],
    outputs: [PORT("values", "Values", "object")],
  },
  "ai.agent_invoke": {
    id: "ai.agent_invoke",
    label: "Invoke Agent",
    category: "action",
    description: "Invoke a first-party or custom AI agent with a prompt.",
    inputs: [PORT("context", "Context", "any")],
    outputs: [PORT("response", "Response", "string")],
  },
  "logic.branch": {
    id: "logic.branch",
    label: "Branch",
    category: "condition",
    description: "Route execution down the true or false branch.",
    inputs: [PORT("condition", "Condition", "boolean")],
    outputs: [PORT("true", "True", "signal"), PORT("false", "False", "signal")],
  },
  "logic.compare": {
    id: "logic.compare",
    label: "Compare",
    category: "condition",
    description: "Compare two values and emit a boolean.",
    inputs: [PORT("left", "Left", "any"), PORT("right", "Right", "any")],
    outputs: [PORT("result", "Result", "boolean")],
  },
  "action.log": {
    id: "action.log",
    label: "Log",
    category: "action",
    description: "Write a workflow log entry.",
    inputs: [PORT("value", "Value", "any")],
    outputs: [PORT("logged", "Logged", "signal")],
  },
  "action.notify_desktop": {
    id: "action.notify_desktop",
    label: "Notify Desktop",
    category: "action",
    description: "Show a native desktop notification.",
    inputs: [PORT("message", "Message", "string")],
    outputs: [PORT("notified", "Notified", "signal")],
  },
  "transform.json_path": {
    id: "transform.json_path",
    label: "JSON Path",
    category: "transform",
    description: "Extract a value from an object via a dotted path.",
    inputs: [PORT("input", "Input", "object")],
    outputs: [PORT("value", "Value", "any")],
  },
  "flow.sleep": {
    id: "flow.sleep",
    label: "Sleep",
    category: "transform",
    description: "Pause the workflow for a fixed number of milliseconds.",
    inputs: [PORT("trigger", "Trigger", "signal")],
    outputs: [PORT("done", "Done", "signal")],
  },
};

/**
 * Properties-panel field schemas per built-in node type. The properties
 * panel reads this map to render typed inputs for the selected node;
 * plugin nodes (no entry here) fall back to a free-form key/value
 * editor.
 */
export const BUILT_IN_NODE_CONFIG_FIELDS: Readonly<Record<BuiltInNodeId, readonly ConfigField[]>> =
  {
    "data.fetch_quote": [
      { key: "symbol", label: "Symbol", kind: "string", placeholder: "AAPL", defaultValue: "" },
    ],
    "data.fetch_history": [
      { key: "symbol", label: "Symbol", kind: "string", placeholder: "AAPL", defaultValue: "" },
      {
        key: "period",
        label: "Period",
        kind: "select",
        options: ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y", "max"],
        defaultValue: "1y",
      },
      {
        key: "interval",
        label: "Interval",
        kind: "select",
        options: ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
        defaultValue: "1d",
      },
    ],
    "compute.indicator": [
      {
        key: "indicator",
        label: "Indicator",
        kind: "select",
        options: ["sma", "ema", "rsi", "macd", "bollinger", "atr", "stoch", "obv"],
        defaultValue: "rsi",
      },
      { key: "period", label: "Period", kind: "number", placeholder: "14", defaultValue: 14 },
    ],
    "ai.agent_invoke": [
      {
        key: "agent_id",
        label: "Agent ID",
        kind: "string",
        placeholder: "researcher",
        defaultValue: "",
      },
      {
        key: "prompt",
        label: "Prompt",
        kind: "textarea",
        placeholder: "What is the technical outlook for {symbol}?",
        defaultValue: "",
      },
    ],
    "logic.branch": [],
    "logic.compare": [
      {
        key: "op",
        label: "Operator",
        kind: "select",
        options: ["eq", "ne", "lt", "lte", "gt", "gte"],
        defaultValue: "gt",
      },
    ],
    "action.log": [
      {
        key: "level",
        label: "Level",
        kind: "select",
        options: ["debug", "info", "warning", "error"],
        defaultValue: "info",
      },
    ],
    "action.notify_desktop": [
      {
        key: "title",
        label: "Title",
        kind: "string",
        placeholder: "Vysted Workflow",
        defaultValue: "",
      },
    ],
    "transform.json_path": [
      {
        key: "path",
        label: "Path",
        kind: "string",
        placeholder: "data.results[0].close",
        defaultValue: "",
      },
    ],
    "flow.sleep": [
      {
        key: "duration_ms",
        label: "Duration (ms)",
        kind: "number",
        placeholder: "1000",
        defaultValue: 1000,
      },
    ],
  };

// ---------------------------------------------------------------------------
// Palette assembly
// ---------------------------------------------------------------------------

/** A registry entry as rendered by the palette and the canvas. */
export interface RegistryEntry {
  spec: NodeSpec;
  /** `"built-in"` for the 10 first-party types, `"plugin"` for plugin contributions. */
  source: "built-in" | "plugin";
  /** Plugin id when `source === "plugin"`. */
  pluginId?: string;
}

/** Resolve every built-in spec as a `RegistryEntry`. */
export function builtInEntries(): RegistryEntry[] {
  return BUILT_IN_NODE_IDS.map((id) => ({
    spec: BUILT_IN_NODE_SPECS[id],
    source: "built-in" as const,
  }));
}

/**
 * Combine built-in entries with plugin-contributed `NodeSpec`s.
 *
 * Plugin specs whose ids collide with a built-in are dropped — the
 * built-in wins. The collision is silent (not an error) to keep the
 * palette robust against accidentally-misnamed plugin nodes; the
 * plugin manager UI surfaces the duplicate-id case elsewhere.
 */
export function buildRegistry(pluginNodes: readonly NodeSpec[]): RegistryEntry[] {
  const builtIns = builtInEntries();
  const builtInIds = new Set<string>(BUILT_IN_NODE_IDS);
  const pluginEntries: RegistryEntry[] = pluginNodes
    .filter((spec) => !builtInIds.has(spec.id))
    .map((spec) => ({
      spec,
      source: "plugin" as const,
    }));
  return [...builtIns, ...pluginEntries];
}

/**
 * Build the default `config` payload for a freshly-dropped node. Pulls
 * `defaultValue`s from `BUILT_IN_NODE_CONFIG_FIELDS`; returns an empty
 * object for plugin nodes (the user fills the free-form key/value
 * editor).
 */
export function defaultConfigFor(nodeTypeId: string): Record<string, unknown> {
  const fields = (
    BUILT_IN_NODE_CONFIG_FIELDS as Record<string, readonly ConfigField[] | undefined>
  )[nodeTypeId];
  if (fields === undefined) {
    return {};
  }
  const out: Record<string, unknown> = {};
  for (const field of fields) {
    if (field.defaultValue !== undefined) {
      out[field.key] = field.defaultValue;
    }
  }
  return out;
}

/** Find a registry entry by node-type id. */
export function findEntry(
  registry: readonly RegistryEntry[],
  nodeTypeId: string,
): RegistryEntry | undefined {
  return registry.find((entry) => entry.spec.id === nodeTypeId);
}

/** Group entries by their `NodeSpec.category`, preserving registry order within each group. */
export function groupByCategory(
  entries: readonly RegistryEntry[],
): Record<NodeSpec["category"], RegistryEntry[]> {
  const groups: Record<NodeSpec["category"], RegistryEntry[]> = {
    trigger: [],
    action: [],
    transform: [],
    condition: [],
    output: [],
  };
  for (const entry of entries) {
    groups[entry.spec.category].push(entry);
  }
  return groups;
}
