/**
 * OpenBB ODP plugin — first real third-party-shaped data plugin on the
 * locked `types/plugin.ts` contract.
 *
 * The plugin is a thin TypeScript front for the sidecar's `/openbb/*` router
 * (`sidecar/routers/openbb.py`). Every accessor defers to the sidecar so all
 * the OpenBB-specific Python machinery (router-loader + command-runner) stays
 * inside the bundled sidecar binary — the plugin layer is data-shaping only.
 *
 * Capability flags: `contributesData = true`. The other five capabilities
 * (panels, commands, agents, nodes, control plane) stay false in v0.3.0;
 * Phase 3+ may add an OpenBB macro panel and slash commands.
 *
 * Lifecycle:
 *
 * - `initialize(config)` caches the sidecar base URL and probes
 *   `/openbb/status` so a degraded/unavailable build is detected early. The
 *   probe never throws — `healthCheck()` reports "unavailable" instead.
 * - `shutdown()` clears the cached state.
 * - `healthCheck()` re-runs the status probe with a 2s timeout and surfaces
 *   the result for the plugin manager UI.
 *
 * Per the v0.3.0 plan, the plugin runtime (Teammate B) imports this module
 * statically once the manifest validates; the runtime then calls
 * `getDataSources()` and forwards results to its data-source registry.
 */

import type {
  DataSource,
  HealthStatus,
  PluginCapabilities,
  PluginConfig,
  VystedPlugin,
} from "../../types/plugin";

interface OpenBBPluginState {
  sidecarBaseUrl: string | null;
  hostVersion: string | null;
  /** Last health probe result — also returned from `healthCheck()` between probes. */
  lastHealth: HealthStatus | null;
}

const state: OpenBBPluginState = {
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
    id: "openbb-equity",
    label: "OpenBB — equity quotes & history",
    kinds: ["equity"],
    realtime: false,
    description: "OpenBB Platform-backed equity quotes and OHLCV history (yfinance upstream).",
  },
  {
    id: "openbb-fundamentals",
    label: "OpenBB — fundamentals & ratings",
    kinds: ["fundamentals"],
    realtime: false,
    description:
      "OpenBB Platform-backed valuation ratios, financial statements, and analyst ratings.",
  },
  {
    id: "openbb-macro",
    label: "OpenBB — macro series (FRED)",
    kinds: ["macro"],
    realtime: false,
    description: "OpenBB Platform-backed macroeconomic time-series via FRED, ECB, IMF, OECD.",
  },
];

/** Status payload returned by the sidecar's `/openbb/status` probe. */
interface OpenBBStatus {
  available: boolean;
  provider: string;
}

/**
 * Probe the sidecar's `/openbb/status` endpoint with a hard timeout. Returns a
 * `HealthStatus` regardless of network outcome — the plugin manager surfaces
 * the message so the user can see *why* OpenBB is degraded.
 */
async function probeSidecarHealth(baseUrl: string): Promise<HealthStatus> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const response = await fetch(new URL("/openbb/status", baseUrl).toString(), {
      signal: controller.signal,
    });
    if (!response.ok) {
      return {
        status: "degraded",
        message: `Sidecar /openbb/status returned ${response.status}`,
        checkedAt: Date.now(),
      };
    }
    const body = (await response.json()) as OpenBBStatus;
    if (!body.available) {
      return {
        status: "unavailable",
        message: "OpenBB is not bundled in this sidecar build — falling back to yfinance.",
        checkedAt: Date.now(),
      };
    }
    return {
      status: "healthy",
      message: `OpenBB available via ${body.provider}`,
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

/** Build the `VystedPlugin` instance the plugin runtime imports. */
const openbbPlugin: VystedPlugin = {
  pluginId: "openbb-odp",
  pluginName: "OpenBB Open Data Platform",
  pluginType: "data-source",
  version: "0.1.0",
  capabilities,

  async initialize(config: PluginConfig): Promise<void> {
    state.sidecarBaseUrl = config.sidecarBaseUrl;
    state.hostVersion = config.hostVersion;
    // Eagerly probe — surfaces an immediate health snapshot for the plugin
    // manager UI without waiting for the first scheduled `healthCheck`.
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

export default openbbPlugin;

// Named export for tooling that prefers explicit imports (the runtime accepts
// either; both shapes resolve to the same `VystedPlugin` instance).
export { openbbPlugin };
