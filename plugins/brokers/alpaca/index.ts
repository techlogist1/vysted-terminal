/**
 * Alpaca broker plugin — Phase 5 v0.5.0.
 *
 * Thin frontend shell over the sidecar's safety-gated broker routes
 * (owned by Teammate I). The plugin's only job is to surface Alpaca
 * to the cmd+K bar + the broker-connect UI; ALL order placement
 * round-trips through the sidecar, which enforces the §6.5 propose →
 * confirm two-step + audit log + kill switch + position limits.
 *
 * What the plugin contributes:
 *   - getCommands: connect / set-mode / paper-test slash commands
 *   - executeCommand: control-plane handlers that drive the sidecar
 *     POST /brokers/alpaca/* routes
 *   - getDataSources: the Alpaca account-info data source (so other
 *     panels can render the account snapshot through the registry)
 *
 * What the plugin does NOT do:
 *   - Place orders directly. Order proposals come from the UI / agent
 *     flows and land in the order inbox; the user clicks Confirm and
 *     the sidecar route does the broker call.
 *   - Cache credentials. BYOK keychain values resolve at sidecar
 *     connect time through Tauri's `keychain_get` command.
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

interface AlpacaPluginState {
  sidecarBaseUrl: string | null;
  hostVersion: string | null;
  lastHealth: HealthStatus | null;
}

const state: AlpacaPluginState = {
  sidecarBaseUrl: null,
  hostVersion: null,
  lastHealth: null,
};

const HEALTH_TIMEOUT_MS = 2_000;
const BROKER_ID = "alpaca";

const capabilities: PluginCapabilities = {
  contributesData: true,
  contributesPanels: false,
  contributesCommands: true,
  contributesAgents: false,
  contributesNodes: false,
  supportsControlPlane: true,
};

const dataSources: DataSource[] = [
  {
    id: "broker-alpaca-account",
    label: "Alpaca — account & positions",
    kinds: ["custom"],
    realtime: false,
    description:
      "Live account summary + open positions read from Alpaca through the sidecar safety layer.",
  },
];

const commands: CommandSpec[] = [
  {
    id: "alpaca.connect",
    trigger: "alpaca connect",
    title: "Alpaca: Connect",
    description: "Connect Alpaca using the api_key + api_secret stored in the OS keychain.",
    icon: "plug",
    commandId: "alpaca.connect",
  },
  {
    id: "alpaca.account",
    trigger: "alpaca account",
    title: "Alpaca: Show account",
    description: "Fetch the Alpaca account summary + positions.",
    icon: "wallet",
    commandId: "alpaca.account",
  },
  {
    id: "alpaca.set-mode-paper",
    trigger: "alpaca paper",
    title: "Alpaca: Set paper mode",
    description: "Force the Alpaca adapter into paper mode (the default).",
    icon: "shield",
    commandId: "alpaca.set-mode-paper",
  },
  {
    id: "alpaca.set-mode-live",
    trigger: "alpaca live",
    title: "Alpaca: Set live mode (gated by disclaimer)",
    description:
      "Switch the Alpaca adapter to live mode. The host MUST surface the live-mode disclaimer first.",
    icon: "alert-triangle",
    commandId: "alpaca.set-mode-live",
  },
  {
    id: "alpaca.halt",
    trigger: "alpaca halt",
    title: "Alpaca: Halt trading (read-only)",
    description: "Toggle the Alpaca adapter into read-only mode.",
    icon: "octagon",
    commandId: "alpaca.halt",
  },
];

/** Sidecar health probe — checks the broker router is online. */
async function probeSidecarHealth(baseUrl: string): Promise<HealthStatus> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const response = await fetch(new URL("/health", baseUrl).toString(), {
      signal: controller.signal,
    });
    if (!response.ok) {
      return {
        status: "degraded",
        message: `Sidecar /health returned ${response.status}`,
        checkedAt: Date.now(),
      };
    }
    return {
      status: "healthy",
      message: "Sidecar reachable; Alpaca routes available.",
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

/**
 * POST to a sidecar broker route and return a CommandResult. Centralised
 * here so every Alpaca command surfaces the same error shape — the
 * cmd+K bar relies on `CommandResult.ok` to render success vs error.
 */
async function postBrokerRoute(
  baseUrl: string,
  path: string,
  body?: unknown,
): Promise<CommandResult> {
  try {
    const response = await fetch(new URL(path, baseUrl).toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const text = await response.text();
    const data = text ? (JSON.parse(text) as unknown) : undefined;
    if (!response.ok) {
      return {
        ok: false,
        error: `${path} returned ${response.status}: ${text || "(empty)"}`,
        data,
      };
    }
    return { ok: true, data };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

async function getBrokerRoute(baseUrl: string, path: string): Promise<CommandResult> {
  try {
    const response = await fetch(new URL(path, baseUrl).toString());
    const text = await response.text();
    const data = text ? (JSON.parse(text) as unknown) : undefined;
    if (!response.ok) {
      return {
        ok: false,
        error: `${path} returned ${response.status}: ${text || "(empty)"}`,
        data,
      };
    }
    return { ok: true, data };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

const alpacaPlugin: VystedPlugin = {
  pluginId: "broker-alpaca",
  pluginName: "Alpaca (US equities + options + crypto)",
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

  async executeCommand(commandId: string, args: unknown): Promise<CommandResult> {
    if (!state.sidecarBaseUrl) {
      return { ok: false, error: "Plugin not initialised — call initialize() first." };
    }
    const baseUrl = state.sidecarBaseUrl;
    const argsObj = (args ?? {}) as Record<string, unknown>;

    switch (commandId) {
      case "alpaca.connect":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/connect`, {
          broker: BROKER_ID,
          credentials: (argsObj.credentials as Record<string, string>) ?? {},
        });
      case "alpaca.account":
        return getBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/account`);
      case "alpaca.set-mode-paper":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/mode`, { mode: "paper" });
      case "alpaca.set-mode-live":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/mode`, { mode: "live" });
      case "alpaca.halt":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/read-only`, { readOnly: true });
      default:
        return { ok: false, error: `unknown command: ${commandId}` };
    }
  },
};

export default alpacaPlugin;
export { alpacaPlugin };
