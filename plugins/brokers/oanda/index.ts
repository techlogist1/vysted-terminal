/**
 * OANDA v20 broker plugin — Phase 5 v0.5.0.
 *
 * Frontend shell over the sidecar's OANDA broker routes. Identical
 * pattern to the Alpaca + IB shells: the plugin surfaces commands +
 * a data source, and every order proposal round-trips through the
 * sidecar where the §6.5 safety layer enforces the two-step gate.
 *
 * Paper-mode default is OANDA's "practice" demo environment. Live
 * mode requires a funded fxTrade account; the host MUST surface the
 * live-mode disclaimer before the user toggles to live.
 *
 * SDK maintenance note: oandapyV20 0.7.2 was last released in
 * 2021-08. The library is stable but low-maintenance; users should
 * monitor security advisories independently. Documented in
 * docs/BROKER_INTEGRATIONS.md.
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

interface OandaPluginState {
  sidecarBaseUrl: string | null;
  hostVersion: string | null;
  lastHealth: HealthStatus | null;
}

const state: OandaPluginState = {
  sidecarBaseUrl: null,
  hostVersion: null,
  lastHealth: null,
};

const HEALTH_TIMEOUT_MS = 2_000;
const BROKER_ID = "oanda";

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
    id: "broker-oanda-account",
    label: "OANDA — account & positions",
    kinds: ["custom"],
    realtime: false,
    description:
      "Live account summary + open forex positions read from OANDA fxTrade through the sidecar.",
  },
];

const commands: CommandSpec[] = [
  {
    id: "oanda.connect",
    trigger: "oanda connect",
    title: "OANDA: Connect",
    description:
      "Connect OANDA using the access_token + account_id stored in the OS keychain. Demo environment by default.",
    icon: "plug",
    commandId: "oanda.connect",
  },
  {
    id: "oanda.account",
    trigger: "oanda account",
    title: "OANDA: Show account",
    description: "Fetch the OANDA account summary + forex positions.",
    icon: "wallet",
    commandId: "oanda.account",
  },
  {
    id: "oanda.set-mode-paper",
    trigger: "oanda demo",
    title: "OANDA: Set demo (paper) mode",
    description:
      "Force the OANDA adapter into demo/practice mode (the default — free fxTrade demo account).",
    icon: "shield",
    commandId: "oanda.set-mode-paper",
  },
  {
    id: "oanda.set-mode-live",
    trigger: "oanda live",
    title: "OANDA: Set live mode (gated by disclaimer)",
    description:
      "Switch the OANDA adapter to the live fxTrade environment. Requires a funded account + the live-mode disclaimer.",
    icon: "alert-triangle",
    commandId: "oanda.set-mode-live",
  },
  {
    id: "oanda.halt",
    trigger: "oanda halt",
    title: "OANDA: Halt trading (read-only)",
    description: "Toggle the OANDA adapter into read-only mode.",
    icon: "octagon",
    commandId: "oanda.halt",
  },
];

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
      message: "Sidecar reachable; OANDA routes available.",
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

const oandaPlugin: VystedPlugin = {
  pluginId: "broker-oanda",
  pluginName: "OANDA v20 (forex)",
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
      case "oanda.connect":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/connect`, {
          broker: BROKER_ID,
          credentials: (argsObj.credentials as Record<string, string>) ?? {},
        });
      case "oanda.account":
        return getBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/account`);
      case "oanda.set-mode-paper":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/mode`, { mode: "paper" });
      case "oanda.set-mode-live":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/mode`, { mode: "live" });
      case "oanda.halt":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/read-only`, { readOnly: true });
      default:
        return { ok: false, error: `unknown command: ${commandId}` };
    }
  },
};

export default oandaPlugin;
export { oandaPlugin };
