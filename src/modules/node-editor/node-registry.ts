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
import { CODE_NODE_ID, CODE_NODE_OUTPUT_PORT } from "./code-node";

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

// ---------------------------------------------------------------------------
// Code node (client-evaluated mathjs expression — R7 hackability pillar)
// ---------------------------------------------------------------------------

/**
 * The `transform.code` spec. Its input ports are DYNAMIC — derived from
 * `config.inputs` by the canvas renderer (`VystedNode`) — so the static
 * ports here only describe the default config's bindings. Evaluation is
 * client-side (sandboxed mathjs); see `code-node-run.ts`.
 */
export const CODE_NODE_SPEC: NodeSpec = {
  id: CODE_NODE_ID,
  label: "Code",
  category: "transform",
  description: "Evaluate a sandboxed math expression over named inputs.",
  inputs: [PORT("a", "a"), PORT("b", "b")],
  outputs: [PORT(CODE_NODE_OUTPUT_PORT, "Value", "any")],
};

// ---------------------------------------------------------------------------
// v0.6.0 sidecar node kinds (mirror sidecar/services/workflow_nodes/*_nodes.py)
// ---------------------------------------------------------------------------

/**
 * The 12 Phase-6 node ids registered server-side by
 * `workflow_nodes/registry_v0_6_0.py` (macro, SEC, quant, research,
 * screener domains). They were always RUNNABLE by the engine but never
 * surfaced in the palette — the frontend registry only mirrored the 10
 * v0.5.0 built-ins. Mirrored here so every registered kind is composable.
 */
export const SIDECAR_NODE_IDS = [
  "data.fetch_macro_series",
  "data.fetch_sec_filing",
  "data.fetch_insider_transactions",
  "data.fetch_earnings_calendar",
  "data.fetch_earnings_history",
  "data.fetch_analyst_history",
  "data.fetch_price_target_history",
  "quant.price_option",
  "quant.compute_greeks",
  "quant.price_bond",
  "quant.yield_curve",
  "analysis.screener_query",
] as const;

export type SidecarNodeId = (typeof SIDECAR_NODE_IDS)[number];

/**
 * Specs for the v0.6.0 sidecar kinds. Input ports mirror each handler's
 * input-overrides-config contract — every port name is an exact key the
 * handler (or its pydantic request model, for the quant nodes' `_merge`)
 * reads. Output ports mirror the handlers' returned dict keys.
 */
export const SIDECAR_NODE_SPECS: Readonly<Record<SidecarNodeId, NodeSpec>> = {
  "data.fetch_macro_series": {
    id: "data.fetch_macro_series",
    label: "Fetch Macro Series",
    category: "trigger",
    description: "Fetch one macro series (FRED / ECB / IMF / World Bank).",
    inputs: [PORT("series_id", "Series ID", "string"), PORT("provider", "Provider", "string")],
    outputs: [PORT("series", "Series", "object")],
  },
  "data.fetch_sec_filing": {
    id: "data.fetch_sec_filing",
    label: "Fetch SEC Filing",
    category: "trigger",
    description: "Pull a parsed SEC filing by accession + CIK/symbol.",
    inputs: [PORT("accession", "Accession", "string"), PORT("identifier", "CIK/Symbol", "string")],
    outputs: [PORT("filing", "Filing", "object")],
  },
  "data.fetch_insider_transactions": {
    id: "data.fetch_insider_transactions",
    label: "Insider Transactions",
    category: "trigger",
    description: "Form 3/4/5 insider transactions for an issuer.",
    inputs: [
      PORT("identifier", "CIK/Symbol", "string"),
      PORT("form", "Form", "string"),
      PORT("limit", "Limit", "number"),
    ],
    outputs: [PORT("transactions", "Transactions", "object")],
  },
  "data.fetch_earnings_calendar": {
    id: "data.fetch_earnings_calendar",
    label: "Earnings Calendar",
    category: "trigger",
    description: "Upcoming earnings events in a day window.",
    inputs: [PORT("days", "Days", "number"), PORT("watchlist", "Watchlist", "any")],
    outputs: [
      PORT("events", "Events", "object"),
      PORT("start_date", "Start", "string"),
      PORT("end_date", "End", "string"),
    ],
  },
  "data.fetch_earnings_history": {
    id: "data.fetch_earnings_history",
    label: "Earnings History",
    category: "trigger",
    description: "Past earnings results for a symbol.",
    inputs: [PORT("symbol", "Symbol", "string")],
    outputs: [PORT("symbol", "Symbol", "string"), PORT("history", "History", "object")],
  },
  "data.fetch_analyst_history": {
    id: "data.fetch_analyst_history",
    label: "Analyst Ratings",
    category: "trigger",
    description: "Analyst rating changes for a symbol (newest-first).",
    inputs: [PORT("symbol", "Symbol", "string")],
    outputs: [PORT("symbol", "Symbol", "string"), PORT("history", "History", "object")],
  },
  "data.fetch_price_target_history": {
    id: "data.fetch_price_target_history",
    label: "Price Targets",
    category: "trigger",
    description: "Price-target timeline for a symbol (newest-first).",
    inputs: [PORT("symbol", "Symbol", "string")],
    outputs: [PORT("symbol", "Symbol", "string"), PORT("history", "History", "object")],
  },
  "quant.price_option": {
    id: "quant.price_option",
    label: "Price Option",
    category: "transform",
    description: "Price an option (Black-Scholes / binomial / Monte Carlo).",
    inputs: [
      PORT("spot", "Spot", "number"),
      PORT("strike", "Strike", "number"),
      PORT("volatility", "Volatility", "number"),
      PORT("risk_free_rate", "Rate", "number"),
    ],
    outputs: [PORT("result", "Result", "object")],
  },
  "quant.compute_greeks": {
    id: "quant.compute_greeks",
    label: "Compute Greeks",
    category: "transform",
    description: "Analytic Greeks for a European vanilla option.",
    inputs: [
      PORT("spot", "Spot", "number"),
      PORT("strike", "Strike", "number"),
      PORT("volatility", "Volatility", "number"),
      PORT("risk_free_rate", "Rate", "number"),
    ],
    outputs: [PORT("result", "Result", "object")],
  },
  "quant.price_bond": {
    id: "quant.price_bond",
    label: "Price Bond",
    category: "transform",
    description: "Fixed-rate bond pricing from yield to maturity.",
    inputs: [
      PORT("coupon_rate", "Coupon", "number"),
      PORT("yield_to_maturity", "YTM", "number"),
      PORT("face_value", "Face Value", "number"),
    ],
    outputs: [PORT("result", "Result", "object")],
  },
  "quant.yield_curve": {
    id: "quant.yield_curve",
    label: "Yield Curve",
    category: "transform",
    description: "Bootstrap a zero curve from deposits + swaps.",
    inputs: [PORT("instruments", "Instruments", "object")],
    outputs: [PORT("result", "Result", "object")],
  },
  "analysis.screener_query": {
    id: "analysis.screener_query",
    label: "Screener Query",
    category: "transform",
    description: "Run the screener over a universe with criteria.",
    inputs: [
      PORT("universe", "Universe", "string"),
      PORT("criteria", "Criteria", "object"),
      PORT("custom_symbols", "Symbols", "object"),
      PORT("limit", "Limit", "number"),
    ],
    outputs: [
      PORT("rows", "Rows", "object"),
      PORT("result_count", "Result Count", "number"),
      PORT("evaluated_count", "Evaluated Count", "number"),
    ],
  },
};

/**
 * Typed config forms for the sidecar kinds with flat scalar configs. The
 * quant nodes and the screener query are deliberately ABSENT — their
 * configs are nested request models (dates, enums, criteria lists), so
 * the free-form JSON editor is the honest fit.
 */
const SIDECAR_NODE_CONFIG_FIELDS: Readonly<Record<string, readonly ConfigField[]>> = {
  "data.fetch_macro_series": [
    { key: "series_id", label: "Series ID", kind: "string", placeholder: "GDPC1" },
    {
      key: "provider",
      label: "Provider",
      kind: "select",
      options: ["fred", "ecb", "imf", "world-bank"],
      defaultValue: "fred",
    },
  ],
  "data.fetch_sec_filing": [
    { key: "accession", label: "Accession", kind: "string", placeholder: "0000320193-24-000123" },
    { key: "identifier", label: "CIK / Symbol", kind: "string", placeholder: "AAPL" },
  ],
  "data.fetch_insider_transactions": [
    { key: "identifier", label: "CIK / Symbol", kind: "string", placeholder: "AAPL" },
    { key: "form", label: "Form", kind: "select", options: ["3", "4", "5"] },
    { key: "limit", label: "Limit", kind: "number", placeholder: "30", defaultValue: 30 },
  ],
  "data.fetch_earnings_calendar": [
    { key: "days", label: "Days", kind: "number", placeholder: "7", defaultValue: 7 },
    { key: "watchlist", label: "Watchlist", kind: "string", placeholder: "AAPL, MSFT" },
  ],
  "data.fetch_earnings_history": [
    { key: "symbol", label: "Symbol", kind: "string", placeholder: "AAPL" },
  ],
  "data.fetch_analyst_history": [
    { key: "symbol", label: "Symbol", kind: "string", placeholder: "AAPL" },
  ],
  "data.fetch_price_target_history": [
    { key: "symbol", label: "Symbol", kind: "string", placeholder: "AAPL" },
  ],
};

// ---------------------------------------------------------------------------
// First-party union
// ---------------------------------------------------------------------------

/** Every first-party node id the palette offers (built-ins + code + sidecar kinds). */
export const FIRST_PARTY_NODE_IDS: readonly string[] = [
  ...BUILT_IN_NODE_IDS,
  CODE_NODE_ID,
  ...SIDECAR_NODE_IDS,
];

/** Spec lookup across every first-party node id. */
export const FIRST_PARTY_NODE_SPECS: Readonly<Record<string, NodeSpec>> = {
  ...BUILT_IN_NODE_SPECS,
  [CODE_NODE_ID]: CODE_NODE_SPEC,
  ...SIDECAR_NODE_SPECS,
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

/**
 * Config-field schemas across ALL first-party node ids — a PARTIAL map by
 * design. Ids present render the typed properties form; ids absent (and
 * plugin nodes) fall back to the free-form JSON config editor, which is
 * the honest fit for nodes whose config is a nested request model (the
 * quant pricing nodes, the screener query). The code node never reads
 * this map — it has its own inspector (`code-node-inspector.tsx`).
 */
export const NODE_CONFIG_FIELDS: Readonly<Record<string, readonly ConfigField[]>> = {
  ...BUILT_IN_NODE_CONFIG_FIELDS,
  ...SIDECAR_NODE_CONFIG_FIELDS,
};

/**
 * Structural config defaults for nodes whose default config is not
 * expressible as flat `ConfigField.defaultValue`s (arrays / nested
 * objects). Checked by `defaultConfigFor` before the field-map path.
 */
const STRUCTURAL_DEFAULT_CONFIGS: Readonly<Record<string, Record<string, unknown>>> = {
  [CODE_NODE_ID]: { expression: "a + b", inputs: ["a", "b"] },
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

/** Resolve every first-party spec (built-ins + code node) as a `RegistryEntry`. */
export function firstPartyEntries(): RegistryEntry[] {
  return FIRST_PARTY_NODE_IDS.map((id) => ({
    spec: FIRST_PARTY_NODE_SPECS[id],
    source: "built-in" as const,
  }));
}

/**
 * Combine first-party entries with plugin-contributed `NodeSpec`s.
 *
 * Plugin specs whose ids collide with a first-party id are dropped — the
 * first-party spec wins. The collision is silent (not an error) to keep
 * the palette robust against accidentally-misnamed plugin nodes; the
 * plugin manager UI surfaces the duplicate-id case elsewhere.
 */
export function buildRegistry(pluginNodes: readonly NodeSpec[]): RegistryEntry[] {
  const firstParty = firstPartyEntries();
  const firstPartyIds = new Set<string>(FIRST_PARTY_NODE_IDS);
  const pluginEntries: RegistryEntry[] = pluginNodes
    .filter((spec) => !firstPartyIds.has(spec.id))
    .map((spec) => ({
      spec,
      source: "plugin" as const,
    }));
  return [...firstParty, ...pluginEntries];
}

/**
 * Build the default `config` payload for a freshly-dropped node.
 * Structural defaults (code node) win; otherwise `defaultValue`s are
 * pulled from `NODE_CONFIG_FIELDS`; plugin / schema-less nodes get an
 * empty object (the user fills the free-form JSON editor).
 */
export function defaultConfigFor(nodeTypeId: string): Record<string, unknown> {
  const structural = STRUCTURAL_DEFAULT_CONFIGS[nodeTypeId];
  if (structural !== undefined) {
    return structuredClone(structural);
  }
  const fields = NODE_CONFIG_FIELDS[nodeTypeId];
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
