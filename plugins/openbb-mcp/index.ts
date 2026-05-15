/**
 * openbb-mcp plugin — Phase-3 replacement for the Phase-2 in-process OpenBB plugin.
 *
 * Architecturally identical surface (same `DataSource` shape, same plugin
 * capability flags, same `healthCheck()` contract), wired to the new MCP
 * backend instead of the retired bespoke subprocess. The Tauri Rust core
 * spawns the `openbb-mcp-server` binary as a Tauri-managed child (see
 * `src-tauri/src/openbb_mcp.rs`) — the architectural fix for the Phase-2
 * Windows `subprocess.Popen` deadlock (CLAUDE.md Gotcha). The main Vysted
 * sidecar consumes the child as an MCP client via
 * `sidecar/services/openbb_mcp_provider.py`.
 *
 * The plugin only proxies through the sidecar — the sidecar's
 * `/openbb-mcp/status` endpoint surfaces child-process health, the
 * `/fundamentals/*` and `/macro/*` routes route through `openbb_mcp_provider`
 * with a yfinance fallback when the child is unavailable.
 */

import type {
  DataSource,
  HealthStatus,
  PluginCapabilities,
  PluginConfig,
  VystedPlugin,
} from "../../types/plugin";

interface OpenBBMcpPluginState {
  sidecarBaseUrl: string | null;
  hostVersion: string | null;
  /** Last health probe result — also returned from `healthCheck()` between probes. */
  lastHealth: HealthStatus | null;
}

const state: OpenBBMcpPluginState = {
  sidecarBaseUrl: null,
  hostVersion: null,
  lastHealth: null,
};

const HEALTH_TIMEOUT_MS = 2_000;

const capabilities: PluginCapabilities = {
  contributesData: true,
  contributesPanels: false,
  contributesCommands: false,
  contributesAgents: false,
  contributesNodes: false,
  supportsControlPlane: false,
};

const dataSources: DataSource[] = [
  {
    id: "openbb-mcp-equity",
    label: "OpenBB MCP — equity quotes & history",
    kinds: ["equity"],
    realtime: false,
    description: "OpenBB Platform equity quotes and OHLCV history via the openbb-mcp-server.",
  },
  {
    id: "openbb-mcp-fundamentals",
    label: "OpenBB MCP — fundamentals & ratings",
    kinds: ["fundamentals"],
    realtime: false,
    description:
      "OpenBB Platform valuation ratios, financial statements, and analyst ratings via the openbb-mcp-server.",
  },
  {
    id: "openbb-mcp-macro",
    label: "OpenBB MCP — macro series (FRED)",
    kinds: ["macro"],
    realtime: false,
    description: "OpenBB Platform macroeconomic series via the openbb-mcp-server.",
  },
];

/** Status payload returned by the sidecar's `/openbb-mcp/status` probe. */
interface OpenBBMcpStatus {
  available: boolean;
  provider: string;
  endpoint: string | null;
  lastToolCallOk: boolean | null;
  lastError: string | null;
}

/**
 * Probe the sidecar's `/openbb-mcp/status` endpoint with a hard timeout.
 * Returns a `HealthStatus` regardless of network outcome — the plugin manager
 * surfaces the message so the user can see *why* OpenBB MCP is degraded.
 */
async function probeSidecarHealth(baseUrl: string): Promise<HealthStatus> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const response = await fetch(new URL("/openbb-mcp/status", baseUrl).toString(), {
      signal: controller.signal,
    });
    if (!response.ok) {
      return {
        status: "degraded",
        message: `Sidecar /openbb-mcp/status returned ${response.status}`,
        checkedAt: Date.now(),
      };
    }
    const body = (await response.json()) as OpenBBMcpStatus;
    if (!body.available) {
      return {
        status: "unavailable",
        message: "openbb-mcp subprocess not running — falling back to yfinance for OpenBB routes.",
        checkedAt: Date.now(),
      };
    }
    if (body.lastToolCallOk === false) {
      const detail = body.lastError ?? "unknown error";
      return {
        status: "degraded",
        message: `Last openbb-mcp tool call failed: ${detail}`,
        checkedAt: Date.now(),
      };
    }
    return {
      status: "healthy",
      message: `openbb-mcp running at ${body.endpoint ?? "unknown"}`,
      checkedAt: Date.now(),
    };
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    return {
      status: "unavailable",
      message: `Sidecar unreachable: ${detail}`,
      checkedAt: Date.now(),
    };
  } finally {
    clearTimeout(timer);
  }
}

const openbbMcpPlugin: VystedPlugin = {
  pluginId: "openbb-mcp",
  pluginName: "OpenBB (MCP)",
  pluginType: "data-source",
  version: "0.1.0",
  capabilities,

  async initialize(config: PluginConfig): Promise<void> {
    state.sidecarBaseUrl = config.sidecarBaseUrl;
    state.hostVersion = config.hostVersion;
    state.lastHealth = await probeSidecarHealth(config.sidecarBaseUrl);
  },

  async shutdown(): Promise<void> {
    state.sidecarBaseUrl = null;
    state.hostVersion = null;
    state.lastHealth = null;
  },

  async healthCheck(): Promise<HealthStatus> {
    if (!state.sidecarBaseUrl) {
      return {
        status: "unavailable",
        message: "Plugin not initialised.",
        checkedAt: Date.now(),
      };
    }
    state.lastHealth = await probeSidecarHealth(state.sidecarBaseUrl);
    return state.lastHealth;
  },

  getDataSources(): DataSource[] {
    // Defensive copy so the runtime can't mutate the plugin's source list.
    return dataSources.map((source) => ({ ...source }));
  },
};

export default openbbMcpPlugin;

export { openbbMcpPlugin };
