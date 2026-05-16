/**
 * Interactive Brokers plugin — Phase 5 v0.5.0.
 *
 * Frontend shell over the sidecar's IB broker routes. Like the Alpaca
 * shell, this plugin never places orders directly — every order
 * proposal round-trips through the sidecar where the §6.5 safety
 * layer enforces the propose → confirm two-step + audit log + kill
 * switch + position limits.
 *
 * Hard dependency note: IB requires TWS or IB Gateway running locally.
 * The plugin surfaces a graceful "TWS not detected" health message
 * when the sidecar fails to reach IB on the configured port, so the
 * broker-connect UI can render a recovery hint rather than a stack
 * trace. Documented in docs/BROKER_INTEGRATIONS.md.
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

interface IBPluginState {
  sidecarBaseUrl: string | null;
  hostVersion: string | null;
  lastHealth: HealthStatus | null;
}

const state: IBPluginState = {
  sidecarBaseUrl: null,
  hostVersion: null,
  lastHealth: null,
};

const HEALTH_TIMEOUT_MS = 2_000;
const BROKER_ID = "ib";

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
    id: "broker-ib-account",
    label: "Interactive Brokers — account & positions",
    kinds: ["custom"],
    realtime: false,
    description:
      "Live account summary + open positions read from Interactive Brokers via TWS / IB Gateway.",
  },
];

const commands: CommandSpec[] = [
  {
    id: "ib.connect",
    trigger: "ib connect",
    title: "Interactive Brokers: Connect to TWS / IB Gateway",
    description:
      "Connect to a locally-running TWS or IB Gateway. Paper port 7497 (TWS) or 4002 (Gateway) by default.",
    icon: "plug",
    commandId: "ib.connect",
  },
  {
    id: "ib.account",
    trigger: "ib account",
    title: "Interactive Brokers: Show account",
    description: "Fetch the IB account summary + positions.",
    icon: "wallet",
    commandId: "ib.account",
  },
  {
    id: "ib.set-mode-paper",
    trigger: "ib paper",
    title: "Interactive Brokers: Set paper mode",
    description: "Force the IB adapter into paper mode (the default).",
    icon: "shield",
    commandId: "ib.set-mode-paper",
  },
  {
    id: "ib.set-mode-live",
    trigger: "ib live",
    title: "Interactive Brokers: Set live mode (gated by disclaimer)",
    description:
      "Switch the IB adapter to live mode. The host MUST surface the live-mode disclaimer first.",
    icon: "alert-triangle",
    commandId: "ib.set-mode-live",
  },
  {
    id: "ib.halt",
    trigger: "ib halt",
    title: "Interactive Brokers: Halt trading (read-only)",
    description: "Toggle the IB adapter into read-only mode.",
    icon: "octagon",
    commandId: "ib.halt",
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
      message:
        "Sidecar reachable; IB routes available. TWS / IB Gateway must be running for connect to succeed.",
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

const ibPlugin: VystedPlugin = {
  pluginId: "broker-ib",
  pluginName: "Interactive Brokers (TWS / IB Gateway)",
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
      case "ib.connect":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/connect`, {
          broker: BROKER_ID,
          credentials: (argsObj.credentials as Record<string, string>) ?? {},
        });
      case "ib.account":
        return getBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/account`);
      case "ib.set-mode-paper":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/mode`, { mode: "paper" });
      case "ib.set-mode-live":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/mode`, { mode: "live" });
      case "ib.halt":
        return postBrokerRoute(baseUrl, `/brokers/${BROKER_ID}/read-only`, { readOnly: true });
      default:
        return { ok: false, error: `unknown command: ${commandId}` };
    }
  },
};

export default ibPlugin;
export { ibPlugin };
