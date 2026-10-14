/**
 * Market-news data plugin — the sentiment-scored news source.
 *
 * News is the second pre-installed first-party data provider (alongside
 * yfinance). It works KEYLESS over RSS feeds; supplying a BYOK NewsAPI key
 * (declared as an OPTIONAL credential on this plugin's marketplace entry, the
 * "needs no key" opt-out of FR-034) upgrades it to RSS + NewsAPI breadth. The
 * key rides each `/news` request as the `X-Vysted-Newsapi-Key` header, read
 * from the OS keychain under `plugin-secret:vysted-news:newsapi_key` — never
 * the body, never persisted (the read-only-plugin credential pattern). The
 * actual fetch + lexicon sentiment scoring happens in the sidecar `/news`
 * router; this plugin is a thin declaration of the source so news is a real
 * marketplace data extension (FR-050/FR-053), not a hardcoded path.
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
    id: "vysted-news-feed",
    label: "Market news — RSS + optional NewsAPI",
    kinds: ["news"],
    realtime: false,
    description:
      "Sentiment-scored, symbol-tagged market news. Keyless over RSS; an optional BYOK NewsAPI key adds NewsAPI breadth.",
  },
];

export const newsPlugin: VystedPlugin = {
  pluginId: "vysted-news",
  pluginName: "Market News (RSS + optional NewsAPI)",
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
          ? "Sidecar reachable; news is keyless over RSS (NewsAPI key optional)."
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

export default newsPlugin;
