/**
 * Yahoo Finance data plugin — the keyless equity + fundamentals default.
 *
 * The "works out of the box, zero credentials" guarantee (spec Session
 * 2026-05-31b): yfinance is delivered as a PRE-INSTALLED, enabled data-provider
 * marketplace plugin — the reference instance of the data slice of the one
 * extension model (FR-053). The actual data flows through the sidecar's
 * `provider_registry` (this plugin is a thin declaration of the source + its
 * standard-model coverage, like the openbb-mcp plugin); declaring it as a plugin
 * is what makes the data layer a real marketplace extension surface, not a
 * hardcoded path. Needs no key (`require_credentials = false`).
 */

import type {
  DataSource,
  HealthStatus,
  PluginCapabilities,
  PluginConfig,
  VystedPlugin,
} from "../../types/plugin";

const state: { sidecarBaseUrl: string | null } = { sidecarBaseUrl: null };

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
    id: "yfinance-equity",
    label: "Yahoo Finance — equities + fundamentals",
    kinds: ["equity", "fundamentals"],
    realtime: false,
    description:
      "Keyless equity quotes, OHLCV history, and valuation fundamentals via the sidecar provider registry. No API key required.",
  },
];

export const yfinancePlugin: VystedPlugin = {
  pluginId: "vysted-yfinance",
  pluginName: "Yahoo Finance (keyless equities)",
  pluginType: "data-source",
  version: "1.0.0",
  capabilities,

  async initialize(config: PluginConfig): Promise<void> {
    state.sidecarBaseUrl = config.sidecarBaseUrl;
  },

  async shutdown(): Promise<void> {
    state.sidecarBaseUrl = null;
  },

  async healthCheck(): Promise<HealthStatus> {
    if (!state.sidecarBaseUrl) {
      return { status: "unavailable", message: "Plugin not initialised.", checkedAt: Date.now() };
    }
    try {
      const response = await fetch(new URL("/health", state.sidecarBaseUrl).toString());
      return {
        status: response.ok ? "healthy" : "degraded",
        message: response.ok
          ? "Sidecar reachable; yfinance is the keyless equity default."
          : `HTTP ${response.status}`,
        checkedAt: Date.now(),
      };
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      return {
        status: "unavailable",
        message: `Sidecar unreachable: ${detail}`,
        checkedAt: Date.now(),
      };
    }
  },

  getDataSources(): DataSource[] {
    return dataSources.map((source) => ({ ...source }));
  },
};

export default yfinancePlugin;
