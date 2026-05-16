/**
 * ccxt-exec plugin — Phase-5 crypto execution surface.
 *
 * Wraps the sidecar's `CcxtExecutionAdapter` (in
 * `sidecar/services/brokers/ccxt_exec.py`) which extends the Phase-1
 * `ccxt_provider.py` data layer to execution. Each ccxt exchange counts
 * as a distinct `BrokerId` so the broker-connect UI can list Bybit,
 * Binance, Kraken, and Coinbase independently. The plugin contributes:
 *
 *   - One slash command per exchange to open the matching broker-connect
 *     credentials dialog (`/connect ccxt-bybit`, etc.).
 *   - One slash command to halt all crypto exchanges at once (fires the
 *     global kill switch — convenience for the user inside the command
 *     palette; the always-visible toolbar button remains the primary
 *     surface).
 *
 * Order entry routes through Teammate S's `BrokerOrderEntry.tsx` →
 * `OrderConfirmationDialog.tsx` → sidecar `/brokers/{id}/orders/propose`
 * + `/brokers/{id}/orders/{proposal-id}/confirm`. This plugin does NOT
 * implement `executeCommand("place-order")` itself — the safety-layer
 * routes are the only path. The plugin's `supportsControlPlane` flag
 * stays `false` accordingly; once Teammate S exposes the sidecar
 * commands publicly, future versions can flip it to `true`.
 *
 * Health: the plugin proxies the sidecar `/brokers/ccxt-bybit/state`
 * endpoint (representative of all four; the broker-connect panel reads
 * the per-broker state directly). If the sidecar is unreachable, the
 * plugin reports `unavailable`.
 */

import type {
  CommandResult,
  CommandSpec,
  DataSource,
  HealthStatus,
  PluginCapabilities,
  PluginConfig,
  VystedPlugin,
} from "../../../types/plugin";

const HEALTH_TIMEOUT_MS = 2_000;

/**
 * The four ccxt-backed broker ids this plugin surfaces. Mirrors the
 * sidecar's `EXCHANGE_TO_BROKER_ID` map in `services/brokers/ccxt_exec.py`
 * and the `BrokerId` union in `types/broker.ts`. Kept as a constant array
 * so the contributed commands stay in sync with the sidecar's whitelist.
 */
const CCXT_BROKER_IDS = ["ccxt-bybit", "ccxt-binance", "ccxt-kraken", "ccxt-coinbase"] as const;

type CcxtBrokerId = (typeof CCXT_BROKER_IDS)[number];

interface CcxtExecPluginState {
  sidecarBaseUrl: string | null;
  hostVersion: string | null;
  lastHealth: HealthStatus | null;
}

const state: CcxtExecPluginState = {
  sidecarBaseUrl: null,
  hostVersion: null,
  lastHealth: null,
};

const capabilities: PluginCapabilities = {
  contributesData: true,
  contributesPanels: false,
  contributesCommands: true,
  contributesAgents: false,
  contributesNodes: false,
  // Order execution does NOT route through executeCommand — it goes
  // through the safety-layer routes only. See module docstring.
  supportsControlPlane: false,
};

/**
 * One `DataSource` per exchange. The ccxt-exec plugin re-exposes the
 * Phase-1 ccxt data sources so the data-picker surfaces them in the
 * execution context (e.g. "current Bybit price" while filling an order).
 * The actual `kinds` set is just `["crypto"]`; per-exchange filtering
 * happens at the data-source-id level.
 */
const dataSources: DataSource[] = CCXT_BROKER_IDS.map((brokerId) => ({
  id: `${brokerId}-account`,
  label: `${formatExchangeLabel(brokerId)} — account + balances`,
  kinds: ["crypto"],
  realtime: false,
  description: `Account summary and balances for ${formatExchangeLabel(brokerId)} via ccxt.`,
}));

/**
 * Per-exchange `/connect <broker-id>` commands + a single `halt all ccxt`
 * convenience. The host's broker-connect UI is the canonical surface; the
 * commands let power users reach the same flow from cmd+K.
 */
const commands: CommandSpec[] = [
  ...CCXT_BROKER_IDS.map<CommandSpec>((brokerId) => ({
    id: `ccxt-exec.connect.${brokerId}`,
    trigger: `connect ${brokerId}`,
    title: `Connect ${formatExchangeLabel(brokerId)}`,
    description: `Open the credentials dialog to connect ${formatExchangeLabel(brokerId)} via ccxt.`,
    icon: "key",
    opensPanel: "broker-connect",
  })),
  {
    id: "ccxt-exec.halt-all",
    trigger: "halt ccxt",
    title: "Halt all crypto exchanges",
    description: "Fire the global kill switch — halts all ccxt-backed brokers immediately.",
    icon: "octagon-x",
    commandId: "ccxt-exec.halt-all",
  },
];

/** Pretty-print a broker id as "Bybit", "Binance", etc. */
function formatExchangeLabel(brokerId: CcxtBrokerId): string {
  const raw = brokerId.replace(/^ccxt-/, "");
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

/**
 * Probe the sidecar's `/brokers/ccxt-bybit/state` endpoint with a hard
 * timeout. We probe Bybit specifically because (a) the four ccxt adapters
 * share the same code path so the result is representative, and (b)
 * sidecar-broker registry semantics guarantee Bybit is always registered.
 * The broker-connect panel reads each adapter's state independently — the
 * plugin's health check only answers "is the sidecar listening?".
 */
async function probeSidecarHealth(baseUrl: string): Promise<HealthStatus> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const response = await fetch(new URL("/brokers/ccxt-bybit/state", baseUrl).toString(), {
      signal: controller.signal,
    });
    if (response.status === 404) {
      // Sidecar is up but the broker registry hasn't booted the ccxt
      // adapters — surface a degraded state so the UI explains why.
      return {
        status: "degraded",
        message:
          "Sidecar /brokers/ccxt-bybit/state returned 404 — ccxt adapters not registered yet.",
        checkedAt: Date.now(),
      };
    }
    if (!response.ok) {
      return {
        status: "degraded",
        message: `Sidecar /brokers/ccxt-bybit/state returned ${response.status}`,
        checkedAt: Date.now(),
      };
    }
    return {
      status: "healthy",
      message: "ccxt execution adapters reachable through the sidecar.",
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

const ccxtExecPlugin: VystedPlugin = {
  pluginId: "ccxt-exec",
  pluginName: "ccxt Crypto Execution",
  pluginType: "trading-bot",
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
    return dataSources.map((source) => ({ ...source }));
  },

  getCommands(): CommandSpec[] {
    return commands.map((command) => ({ ...command }));
  },

  async executeCommand(commandId: string): Promise<CommandResult> {
    // Control-plane path is intentionally narrow: order placement NEVER
    // routes through here. The only command we surface is "halt-all" —
    // and even that delegates to the sidecar's `/safety/kill-switch`
    // endpoint via the host runtime; the plugin only reports the result.
    if (commandId === "ccxt-exec.halt-all") {
      if (!state.sidecarBaseUrl) {
        return { ok: false, error: "Plugin not initialised — cannot reach sidecar." };
      }
      try {
        const response = await fetch(
          new URL("/safety/kill-switch", state.sidecarBaseUrl).toString(),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              reason: "user-command: halt all ccxt exchanges",
              firedBy: "user-command",
            }),
          },
        );
        if (!response.ok) {
          return { ok: false, error: `Sidecar returned ${response.status}` };
        }
        return { ok: true, data: { halted: true, brokerIds: [...CCXT_BROKER_IDS] } };
      } catch (err) {
        const detail = err instanceof Error ? err.message : String(err);
        return { ok: false, error: `Sidecar unreachable: ${detail}` };
      }
    }
    return { ok: false, error: `unknown command: ${commandId}` };
  },
};

export default ccxtExecPlugin;

export { CCXT_BROKER_IDS, ccxtExecPlugin };
export type { CcxtBrokerId };
