/**
 * Vysted Terminal — plugin contract.
 *
 * Every plugin is a self-contained module that implements `VystedPlugin` and
 * declares which of the six capabilities it contributes (data, panels, commands,
 * agents, nodes, control plane). Capability negotiation means the host gracefully
 * omits anything a plugin does not provide.
 *
 * THIS IS THE HIGHEST-RISK FILE IN THE PROJECT. Every plugin and every future
 * phase plugs into these types — changing them is a breaking change for the whole
 * ecosystem. The top-level `VystedPlugin` interface is specified verbatim by
 * blueprint §3.3; the supporting types are designed from blueprint context
 * (§3.4 agent format, the §4 module catalog, the Tradesa V2 capability list).
 *
 * Note: blueprint §3.3 writes `any` for the `subscribe` event and `executeCommand`
 * args. This contract uses `unknown` instead — a deliberate, flagged hardening so
 * type safety is not lost at every plugin boundary.
 */

// ---------------------------------------------------------------------------
// Identity
// ---------------------------------------------------------------------------

/** Broad category a plugin declares itself as. */
export type PluginType = "trading-bot" | "data-source" | "agent-collection" | "analytics";

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

/** Configuration the host hands a plugin at `initialize()` time. */
export interface PluginConfig {
  /** Absolute path to the plugin's private, host-created data directory. */
  dataDir: string;
  /** Host-persisted settings for this plugin, keyed by setting id. Opaque to the host. */
  settings: Record<string, unknown>;
  /** Localhost base URL of the Python sidecar, e.g. "http://127.0.0.1:51763". */
  sidecarBaseUrl: string;
  /** Semver of the Vysted Terminal host the plugin is running inside. */
  hostVersion: string;
  /** Secrets resolved from the OS keychain, keyed by secret id. Empty if none granted. */
  secrets: Record<string, string>;
}

/** Liveness/health summary returned by a plugin's `healthCheck()`. */
export interface HealthStatus {
  status: "healthy" | "degraded" | "unavailable";
  /** Human-readable detail surfaced in the plugin-manager UI. */
  message?: string;
  /** Epoch milliseconds when this status was produced. */
  checkedAt: number;
}

// ---------------------------------------------------------------------------
// Capability declaration
// ---------------------------------------------------------------------------

/** The six capabilities a plugin may contribute. Each flag gates the matching getter. */
export interface PluginCapabilities {
  contributesData: boolean;
  contributesPanels: boolean;
  contributesCommands: boolean;
  contributesAgents: boolean;
  contributesNodes: boolean;
  supportsControlPlane: boolean;
}

// ---------------------------------------------------------------------------
// Capability: data
// ---------------------------------------------------------------------------

/** Classes of data a contributed source can serve. */
export type DataSourceKind = "equity" | "crypto" | "macro" | "news" | "fundamentals" | "custom";

/** A data provider contributed by a plugin (`capabilities.contributesData`). */
export interface DataSource {
  /** Stable identifier, e.g. "tradesa-decisions", "openbb-equity". */
  id: string;
  /** Display name shown in the data-source picker. */
  label: string;
  /** Data classes this source can serve. */
  kinds: DataSourceKind[];
  /** Whether this source can push real-time updates via `subscribe()`. */
  realtime: boolean;
  /** Optional free-form description. */
  description?: string;
}

// ---------------------------------------------------------------------------
// Capability: panels
// ---------------------------------------------------------------------------

/** A panel contributed by a plugin (`capabilities.contributesPanels`). */
export interface PanelSpec {
  /** Stable identifier, e.g. "tradesa-decisions-feed". */
  id: string;
  /** Title shown in the panel header and the "add panel" menu. */
  title: string;
  /** Lucide icon name or plugin-relative asset path. */
  icon?: string;
  /** Default size hint for the layout engine, in grid units. */
  defaultSize?: { w: number; h: number };
  /** Whether the user may open more than one instance of this panel. */
  singleton?: boolean;
  /**
   * Identifier the host passes back to the plugin's registered panel renderer.
   * The actual React component is resolved by the host at mount time — the
   * contract stays serializable and free of framework types.
   */
  component: string;
}

// ---------------------------------------------------------------------------
// Capability: commands
// ---------------------------------------------------------------------------

/** A slash command contributed to the cmd+K bar (`capabilities.contributesCommands`). */
export interface CommandSpec {
  /** Stable identifier, e.g. "tradesa.kill-switch". */
  id: string;
  /** Text typed after the leading slash, e.g. "tradesa kill". */
  trigger: string;
  /** Title shown in the command palette. */
  title: string;
  /** Optional longer description shown beneath the title. */
  description?: string;
  /** Optional Lucide icon name. */
  icon?: string;
  /** Command id forwarded to `executeCommand()` when invoked (control-plane commands). */
  commandId?: string;
  /** Panel id to open when invoked, as an alternative to `commandId`. */
  opensPanel?: string;
}

// ---------------------------------------------------------------------------
// Capability: agents
// ---------------------------------------------------------------------------

/**
 * An AI agent contributed by a plugin (`capabilities.contributesAgents`).
 * Mirrors the config-driven agent format in blueprint §3.4.
 */
export interface AgentSpec {
  /** Stable identifier, e.g. "tradesa-decision-reviewer". */
  id: string;
  /** Display name, e.g. "Decision Reviewer". */
  name: string;
  /** One-line description of the agent's lens or role. */
  philosophy: string;
  /** System prompt that defines the agent's behavior. */
  systemPrompt: string;
  /** Tool ids the agent is permitted to call (resolved by the host). */
  tools: string[];
  /** Preferred LLM provider id; the user may override. */
  defaultProvider: string;
  /** Lucide icon name or plugin-relative asset path. */
  icon?: string;
}

// ---------------------------------------------------------------------------
// Capability: nodes
// ---------------------------------------------------------------------------

/** Data type carried by a node-editor port; used for connection validation. */
export type NodePortType = "any" | "number" | "string" | "boolean" | "object" | "signal";

/** A single input or output port on a node-editor node. */
export interface NodePort {
  id: string;
  label: string;
  type: NodePortType;
}

/** A node-editor node contributed by a plugin (`capabilities.contributesNodes`). */
export interface NodeSpec {
  /** Stable identifier, e.g. "tradesa.wait-for-decision". */
  id: string;
  /** Display label in the node palette and on the node. */
  label: string;
  /** Functional grouping in the node palette. */
  category: "trigger" | "action" | "transform" | "condition" | "output";
  /** Named input ports. */
  inputs: NodePort[];
  /** Named output ports. */
  outputs: NodePort[];
  /** Optional description shown in the node palette. */
  description?: string;
}

// ---------------------------------------------------------------------------
// Capability: control plane + real-time
// ---------------------------------------------------------------------------

/** Returned by `subscribe()`; call it to cancel the subscription. */
export type Unsubscribe = () => void;

/** Result of a control-plane `executeCommand()` call. */
export interface CommandResult {
  /** Whether the command succeeded. */
  ok: boolean;
  /** Structured payload on success. */
  data?: unknown;
  /** Human-readable error message on failure. */
  error?: string;
}

// ---------------------------------------------------------------------------
// The plugin contract
// ---------------------------------------------------------------------------

/**
 * The contract every Vysted Terminal plugin implements. Optional getters are
 * present only when the matching `capabilities` flag is `true` — the host checks
 * the flag, not the method, so capability negotiation stays explicit.
 */
export interface VystedPlugin {
  // --- Identity ---
  /** Stable plugin identifier, e.g. "tradesa-v2", "openbb-odp", "forge-bot". */
  pluginId: string;
  /** Human-readable plugin name, e.g. "Tradesa V2 (Bybit testnet)". */
  pluginName: string;
  /** Broad plugin category. */
  pluginType: PluginType;
  /** Plugin semver. */
  version: string;

  // --- Lifecycle ---
  initialize(config: PluginConfig): Promise<void>;
  shutdown(): Promise<void>;
  healthCheck(): Promise<HealthStatus>;

  // --- Capability declaration (graceful degradation) ---
  capabilities: PluginCapabilities;

  // --- Data contribution ---
  getDataSources?(): DataSource[];

  // --- Panel contribution ---
  getPanels?(): PanelSpec[];

  // --- Command-bar contribution (slash commands) ---
  getCommands?(): CommandSpec[];

  // --- AI agent contribution ---
  getAgents?(): AgentSpec[];

  // --- Node editor contribution ---
  getNodes?(): NodeSpec[];

  // --- Real-time subscriptions (if supported) ---
  subscribe?(channel: string, callback: (event: unknown) => void): Unsubscribe;

  // --- Control plane (if supported) ---
  executeCommand?(commandId: string, args: unknown): Promise<CommandResult>;
}
