/**
 * Tradesa V2 wrapper plugin (v0.6.5) — first-party trading-system wrapper.
 *
 * Surfaces Lokavya's existing Tradesa V2 multi-agent LLM crypto perp
 * trading bot (techlogist1/tradesa) as a Vysted Terminal plugin. The bot
 * keeps running unchanged on Oracle VPS, paper-trading on Bybit Demo —
 * this plugin is observation-only. Control stays on the bot side
 * (Telegram operator interface, VPS CLI).
 *
 * **READ-ONLY in v0.6.5 by operator decision.** No commands flow from
 * Vysted Terminal to the bot. ``supportsControlPlane=false`` enforces
 * this at the contract level: the runtime never invokes ``executeCommand``
 * because the capability flag is false. Adding any write is a Tier-4
 * change. Write capability is v0.6.6+ scope when the bot stabilizes.
 *
 * This plugin is the canonical reference for the **trading-system
 * wrapper** plugin pattern (documented in ``docs/PLUGIN_DEVELOPMENT.md``).
 * Future trading bots (TauricResearch named explicitly in the v0.6.5
 * operator brief) plug in the same way:
 *
 *   1. Provide a ``connection.ts`` implementing
 *      ``TradingBotReadAdapter`` against the bot's data surface (REST,
 *      Supabase, MCP, etc.).
 *   2. Provide a ``panels.ts`` exporting a
 *      ``Record<string, FunctionComponent>`` map (consumed by the
 *      bootstrap glue in ``src/lib/plugin-bootstrap.ts``).
 *   3. Declare ``contributesPanels`` + ``contributesData`` +
 *      ``contributesCommands`` on the locked ``VystedPlugin`` contract.
 *      Never extend the contract — the platform stays plug-and-play
 *      because the contract is stable.
 */

import type {
  CommandSpec,
  DataSource,
  HealthStatus,
  PanelSpec,
  PluginCapabilities,
  PluginConfig,
  VystedPlugin,
} from "../../types/plugin";

import { getTradesaAdapter } from "./connection";
import { useTradesaStore } from "./store";

// ---------------------------------------------------------------------------
// Identity
// ---------------------------------------------------------------------------

const PLUGIN_ID = "tradesa-v2";
const PLUGIN_NAME = "Tradesa V2";
const PLUGIN_VERSION = "0.1.0";

// ---------------------------------------------------------------------------
// Capabilities
// ---------------------------------------------------------------------------

/**
 * Capability flags for v0.6.5 — READ-ONLY.
 *
 * ``supportsControlPlane=false`` is load-bearing: it tells the runtime
 * NOT to invoke ``executeCommand`` on this plugin even if (by some
 * future refactor) the method exists. Combined with the read-only API
 * surface on the sidecar (``services/tradesa_v2_provider`` has no write
 * methods, ``routers/tradesa_v2`` has no non-GET routes), this is the
 * third defense-in-depth layer enforcing the v0.6.5 contract.
 *
 * v0.6.5 deliberately keeps ``contributesAgents=false`` /
 * ``contributesNodes=false`` even though some Vysted-side agents could
 * ingest Tradesa V2's decision log read-only — those are v0.6.6+ scope
 * (chat-sidebar integration risk) and the operator brief is explicit
 * about not over-scoping this sprint.
 */
const capabilities: PluginCapabilities = {
  contributesData: true,
  contributesPanels: true,
  contributesCommands: true,
  contributesAgents: false,
  contributesNodes: false,
  supportsControlPlane: false,
};

// ---------------------------------------------------------------------------
// Data sources (read-only)
// ---------------------------------------------------------------------------

const dataSources: DataSource[] = [
  {
    id: "tradesa-v2-decisions",
    label: "Tradesa V2 — Brain Decisions",
    kinds: ["custom"],
    realtime: false,
    description:
      "Director-LLM brain decisions emitted by Tradesa V2's reasoning DAG (Market + Pattern + Social + News analysts → Director). Read-only.",
  },
  {
    id: "tradesa-v2-trades",
    label: "Tradesa V2 — Trades",
    kinds: ["crypto"],
    realtime: false,
    description:
      "Open + closed trades the bot placed on Bybit Demo (paper). Realized P&L and stop-loss prices per row. Read-only — Vysted never executes against the bot's account.",
  },
  {
    id: "tradesa-v2-health",
    label: "Tradesa V2 — Health",
    kinds: ["custom"],
    realtime: false,
    description:
      "Bot heartbeat + kill-switch events. Heartbeat staleness >5 minutes flags the wrapper to render 'bot-offline' UX.",
  },
];

// ---------------------------------------------------------------------------
// Panels (UI components live in ./panels.ts, wired by the bootstrap glue)
// ---------------------------------------------------------------------------

const panels: PanelSpec[] = [
  {
    id: "tradesa-v2.positions",
    title: "Tradesa V2 · Live Positions",
    icon: "activity",
    component: "tradesa-v2-positions",
    singleton: true,
    defaultSize: { w: 8, h: 6 },
  },
  {
    id: "tradesa-v2.trade-history",
    title: "Tradesa V2 · Trade History",
    icon: "history",
    component: "tradesa-v2-trade-history",
    singleton: true,
    defaultSize: { w: 8, h: 6 },
  },
  {
    id: "tradesa-v2.brain",
    title: "Tradesa V2 · Brain Decisions",
    icon: "brain",
    component: "tradesa-v2-brain",
    singleton: true,
    defaultSize: { w: 8, h: 7 },
  },
  {
    id: "tradesa-v2.sentinel",
    title: "Tradesa V2 · Sentinel",
    icon: "shield",
    component: "tradesa-v2-sentinel",
    singleton: true,
    defaultSize: { w: 6, h: 5 },
  },
  {
    id: "tradesa-v2.health",
    title: "Tradesa V2 · Health",
    icon: "heart-pulse",
    component: "tradesa-v2-health",
    singleton: true,
    defaultSize: { w: 6, h: 5 },
  },
  {
    id: "tradesa-v2.settings",
    title: "Tradesa V2 · Settings & Drift",
    icon: "sliders-horizontal",
    component: "tradesa-v2-settings",
    singleton: true,
    defaultSize: { w: 7, h: 6 },
  },
  {
    id: "tradesa-v2.meta-agents",
    title: "Tradesa V2 · Meta-Agents",
    icon: "sparkles",
    component: "tradesa-v2-meta-agents",
    singleton: true,
    defaultSize: { w: 8, h: 7 },
  },
];

// ---------------------------------------------------------------------------
// Commands (cmd+K shortcuts to open each panel)
// ---------------------------------------------------------------------------

const commands: CommandSpec[] = [
  {
    id: "tradesa-v2.open-positions",
    trigger: "tradesa positions",
    title: "Tradesa V2: Open Positions",
    description: "Live open positions from the Tradesa V2 bot.",
    icon: "activity",
    opensPanel: "tradesa-v2.positions",
  },
  {
    id: "tradesa-v2.open-trade-history",
    trigger: "tradesa history",
    title: "Tradesa V2: Trade History",
    description: "Closed trades + P&L summary.",
    icon: "history",
    opensPanel: "tradesa-v2.trade-history",
  },
  {
    id: "tradesa-v2.open-brain",
    trigger: "tradesa brain",
    title: "Tradesa V2: Brain Decisions",
    description: "DirectorDecision stream + LLM cost ledger.",
    icon: "brain",
    opensPanel: "tradesa-v2.brain",
  },
  {
    id: "tradesa-v2.open-sentinel",
    trigger: "tradesa sentinel",
    title: "Tradesa V2: Sentinel",
    description: "Sentinel-gate decline tallies (today + total).",
    icon: "shield",
    opensPanel: "tradesa-v2.sentinel",
  },
  {
    id: "tradesa-v2.open-health",
    trigger: "tradesa health",
    title: "Tradesa V2: Health",
    description: "Heartbeat freshness + kill-switch history.",
    icon: "heart-pulse",
    opensPanel: "tradesa-v2.health",
  },
  {
    id: "tradesa-v2.open-settings",
    trigger: "tradesa settings",
    title: "Tradesa V2: Settings & Drift",
    description: "Live bot_settings snapshot + drift detection.",
    icon: "sliders-horizontal",
    opensPanel: "tradesa-v2.settings",
  },
  {
    id: "tradesa-v2.open-meta-agents",
    trigger: "tradesa meta",
    title: "Tradesa V2: Meta-Agents",
    description: "Self-tuning proposals + discovery hypotheses + reflection notes.",
    icon: "sparkles",
    opensPanel: "tradesa-v2.meta-agents",
  },
];

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

interface PluginRuntimeState {
  initialized: boolean;
  initializedAt: number;
  /** Cached last health result so healthCheck() does not always re-probe. */
  lastHealth: HealthStatus | null;
}

const state: PluginRuntimeState = {
  initialized: false,
  initializedAt: 0,
  lastHealth: null,
};

const HEALTH_RECHECK_INTERVAL_MS = 5_000;

/** Map a connection state (panel-side enum) to a HealthStatus (host-side enum). */
function probeToHealth(
  status:
    | "healthy"
    | "connecting"
    | "unauthenticated"
    | "bot-offline"
    | "supabase-error"
    | "partial",
  message: string,
): HealthStatus {
  // The host-side HealthStatus only distinguishes healthy / degraded /
  // unavailable. Map the wrapper's six panel-side states onto those:
  //   healthy        → healthy
  //   connecting     → degraded (probe in flight; not yet healthy)
  //   partial        → degraded (some endpoints succeeding)
  //   bot-offline    → degraded (Supabase reachable; bot not)
  //   supabase-error → unavailable (root upstream down)
  //   unauthenticated→ unavailable (the plugin cannot do its job yet)
  if (status === "healthy") {
    return { status: "healthy", message, checkedAt: Date.now() };
  }
  if (status === "supabase-error" || status === "unauthenticated") {
    return { status: "unavailable", message, checkedAt: Date.now() };
  }
  return { status: "degraded", message, checkedAt: Date.now() };
}

const tradesaPlugin: VystedPlugin = {
  pluginId: PLUGIN_ID,
  pluginName: PLUGIN_NAME,
  pluginType: "trading-bot",
  version: PLUGIN_VERSION,
  capabilities,

  async initialize(config: PluginConfig): Promise<void> {
    state.initialized = true;
    state.initializedAt = Date.now();
    state.lastHealth = null;
    // Reset the store so a re-enable starts with a clean slate.
    useTradesaStore.getState().reset();
    // Eagerly probe so the plugin-manager UI shows a real health
    // sample on first render.
    try {
      const probe = await getTradesaAdapter().probeStatus();
      useTradesaStore.getState().setConnection(probe);
      state.lastHealth = probeToHealth(probe.status, probe.message);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      state.lastHealth = {
        status: "unavailable",
        message: `Initial probe failed: ${message}`,
        checkedAt: Date.now(),
      };
    }
    // Reference config so static analysis doesn't flag it as unused — the
    // wrapper does not read dataDir / settings / secrets in v0.6.5 (creds
    // arrive from keychain on every fetch, not via the granted-secrets
    // map). Will use config.secrets in v0.6.6+ when granted-secret routing
    // lands.
    void config;
  },

  async shutdown(): Promise<void> {
    state.initialized = false;
    state.lastHealth = null;
    useTradesaStore.getState().reset();
  },

  async healthCheck(): Promise<HealthStatus> {
    if (!state.initialized) {
      return {
        status: "unavailable",
        message: "Plugin not initialized.",
        checkedAt: Date.now(),
      };
    }
    // Avoid probing the sidecar more than once every 5s — the
    // useTradesaConnectionState hook already polls /tradesa-v2/status on
    // a 30s cadence for the panels, so the plugin-manager's 30s healthCheck
    // can ride that cadence too without doubling the request rate.
    if (state.lastHealth && Date.now() - state.lastHealth.checkedAt < HEALTH_RECHECK_INTERVAL_MS) {
      return state.lastHealth;
    }
    try {
      const probe = await getTradesaAdapter().probeStatus();
      useTradesaStore.getState().setConnection(probe);
      state.lastHealth = probeToHealth(probe.status, probe.message);
      return state.lastHealth;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      state.lastHealth = {
        status: "unavailable",
        message,
        checkedAt: Date.now(),
      };
      return state.lastHealth;
    }
  },

  getDataSources(): DataSource[] {
    return dataSources.map((d) => ({ ...d }));
  },

  getPanels(): PanelSpec[] {
    return panels.map((p) => ({ ...p }));
  },

  getCommands(): CommandSpec[] {
    return commands.map((c) => ({ ...c }));
  },
};

export default tradesaPlugin;
export { tradesaPlugin };
