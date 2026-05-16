/**
 * Angel One broker plugin — frontend shell on the locked `VystedPlugin`
 * contract. Mirrors :mod:`plugins/brokers/dhan/index.ts` — the only
 * differences are the broker id in every route URL, the slash command
 * trigger words, and the data-source ids. See the Dhan plugin's docstring
 * for the architecture; the sidecar adapter lives in
 * `sidecar/services/brokers/angelone.py`.
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

interface AngelOneState {
  sidecarBaseUrl: string | null;
  hostVersion: string | null;
}

const state: AngelOneState = {
  sidecarBaseUrl: null,
  hostVersion: null,
};

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
    id: "angelone-account",
    label: "Angel One — account + positions",
    kinds: ["custom"],
    realtime: false,
    description:
      "Read-only account summary + open positions, fetched through the sidecar's /brokers/angelone/account route.",
  },
];

const commands: CommandSpec[] = [
  {
    id: "angelone.connect",
    trigger: "connect angelone",
    title: "Angel One: Connect",
    description: "Open an Angel One session using the BYOK credentials + TOTP in plugin settings.",
    icon: "plug",
    commandId: "connect",
  },
  {
    id: "angelone.account",
    trigger: "angelone-account",
    title: "Angel One: Refresh Account",
    description: "Fetch the latest account summary + positions from Angel One.",
    icon: "wallet",
    commandId: "account",
  },
  {
    id: "angelone.halt",
    trigger: "angelone-halt",
    title: "Angel One: Halt Trading",
    description: "Toggle Angel One into read-only mode.",
    icon: "octagon-x",
    commandId: "halt-trading",
  },
];

async function postJson(url: string, body: Record<string, unknown>): Promise<unknown> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(text || `HTTP ${response.status}`);
  return text ? JSON.parse(text) : null;
}

async function getJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  const text = await response.text();
  if (!response.ok) throw new Error(text || `HTTP ${response.status}`);
  return text ? JSON.parse(text) : null;
}

export const angelOnePlugin: VystedPlugin = {
  pluginId: "vysted-angelone",
  pluginName: "Angel One",
  pluginType: "trading-bot",
  version: "0.1.0",
  capabilities,

  async initialize(config: PluginConfig): Promise<void> {
    state.sidecarBaseUrl = config.sidecarBaseUrl;
    state.hostVersion = config.hostVersion;
  },

  async shutdown(): Promise<void> {
    state.sidecarBaseUrl = null;
    state.hostVersion = null;
  },

  async healthCheck(): Promise<HealthStatus> {
    if (!state.sidecarBaseUrl) {
      return { status: "unavailable", message: "Plugin not initialised.", checkedAt: Date.now() };
    }
    try {
      const body = (await getJson(
        new URL("/brokers/angelone/state", state.sidecarBaseUrl).toString(),
      )) as { status: string; mode: string };
      return {
        status: body.status === "connected" ? "healthy" : "degraded",
        message: `Angel One mode=${body.mode} status=${body.status}`,
        checkedAt: Date.now(),
      };
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      return { status: "unavailable", message: `Sidecar unreachable: ${detail}`, checkedAt: Date.now() };
    }
  },

  getDataSources(): DataSource[] {
    return dataSources.map((source) => ({ ...source }));
  },

  getCommands(): CommandSpec[] {
    return commands.map((cmd) => ({ ...cmd }));
  },

  async executeCommand(commandId: string, args: unknown): Promise<CommandResult> {
    if (!state.sidecarBaseUrl) return { ok: false, error: "Plugin not initialised." };
    const base = state.sidecarBaseUrl;
    try {
      if (commandId === "connect") {
        const credentials = (args as { credentials?: Record<string, string> })?.credentials ?? {};
        const data = await postJson(new URL("/brokers/angelone/connect", base).toString(), {
          broker: "angelone",
          credentials,
        });
        return { ok: true, data };
      }
      if (commandId === "account") {
        return { ok: true, data: await getJson(new URL("/brokers/angelone/account", base).toString()) };
      }
      if (commandId === "place-order") {
        const data = await postJson(
          new URL("/brokers/angelone/orders", base).toString(),
          args as Record<string, unknown>,
        );
        return { ok: true, data };
      }
      if (commandId === "place-order-confirm") {
        const payload = args as { proposalId: string; humanConfirmed: boolean; confirmNote?: string };
        const data = await postJson(
          new URL(`/brokers/angelone/orders/${payload.proposalId}/confirm`, base).toString(),
          { humanConfirmed: payload.humanConfirmed, confirmNote: payload.confirmNote },
        );
        return { ok: true, data };
      }
      if (commandId === "halt-trading" || commandId === "set-read-only") {
        const readOnly = commandId === "halt-trading"
          ? true
          : Boolean((args as { readOnly?: boolean })?.readOnly);
        const data = await postJson(new URL("/brokers/angelone/read-only", base).toString(), {
          readOnly,
        });
        return { ok: true, data };
      }
      if (commandId === "set-mode") {
        const mode = (args as { mode?: string })?.mode ?? "paper";
        const data = await postJson(new URL("/brokers/angelone/mode", base).toString(), { mode });
        return { ok: true, data };
      }
      return { ok: false, error: `unknown command: ${commandId}` };
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      return { ok: false, error: detail };
    }
  },
};

export default angelOnePlugin;
