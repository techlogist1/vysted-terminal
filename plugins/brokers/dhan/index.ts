/**
 * Dhan broker plugin — frontend shell on the locked `VystedPlugin` contract.
 *
 * The heavy lifting lives in the Python sidecar's
 * `services/brokers/dhan.py`. This plugin is the user-visible surface:
 *
 *   - `getDataSources()` exposes the read-only account endpoint so the
 *     plugin manager lists a Dhan account source the cmd+K can target.
 *   - `getCommands()` registers the `/connect dhan` + `/dhan-account` slash
 *     commands that route through `executeCommand` to the sidecar.
 *   - `executeCommand()` implements the control plane verbs the
 *     order-entry UI calls — `place-order` (propose), `halt-trading`,
 *     `set-read-only`, `set-mode`.
 *
 * Capability flags reflect the implemented surface; capability negotiation
 * means the host omits anything not set to true.
 *
 * Every order placement here is a PROPOSE call. The sidecar's
 * `BrokerAdapter.propose_order` writes the audit row + position-limit
 * checks; the UI then opens the confirmation dialog and the user clicks
 * Confirm before `confirm_and_place` runs. There is no path from this
 * plugin to a placed order that skips the human-confirmation gate.
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

interface DhanState {
  sidecarBaseUrl: string | null;
  hostVersion: string | null;
}

const state: DhanState = {
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
    id: "dhan-account",
    label: "Dhan — account + positions",
    kinds: ["custom"],
    realtime: false,
    description:
      "Read-only account summary + open positions, fetched through the sidecar's /brokers/dhan/account route.",
  },
];

const commands: CommandSpec[] = [
  {
    id: "dhan.connect",
    trigger: "connect dhan",
    title: "Dhan: Connect",
    description: "Open a Dhan session using the BYOK credentials in plugin settings.",
    icon: "plug",
    commandId: "connect",
  },
  {
    id: "dhan.account",
    trigger: "dhan-account",
    title: "Dhan: Refresh Account",
    description: "Fetch the latest account summary + positions from Dhan.",
    icon: "wallet",
    commandId: "account",
  },
  {
    id: "dhan.halt",
    trigger: "dhan-halt",
    title: "Dhan: Halt Trading",
    description: "Toggle Dhan into read-only mode (no new orders accepted).",
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
  if (!response.ok) {
    throw new Error(text || `HTTP ${response.status}`);
  }
  return text ? JSON.parse(text) : null;
}

async function getJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(text || `HTTP ${response.status}`);
  }
  return text ? JSON.parse(text) : null;
}

export const dhanPlugin: VystedPlugin = {
  pluginId: "vysted-dhan",
  pluginName: "Dhan",
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
      return {
        status: "unavailable",
        message: "Plugin not initialised.",
        checkedAt: Date.now(),
      };
    }
    try {
      const stateResponse = await getJson(
        new URL("/brokers/dhan/state", state.sidecarBaseUrl).toString(),
      );
      const broker = stateResponse as { status: string; mode: string };
      const status = broker.status === "connected" ? "healthy" : "degraded";
      return {
        status,
        message: `Dhan mode=${broker.mode} status=${broker.status}`,
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

  getCommands(): CommandSpec[] {
    return commands.map((cmd) => ({ ...cmd }));
  },

  async executeCommand(commandId: string, args: unknown): Promise<CommandResult> {
    if (!state.sidecarBaseUrl) {
      return { ok: false, error: "Plugin not initialised." };
    }
    const base = state.sidecarBaseUrl;
    try {
      if (commandId === "connect") {
        const credentials = (args as { credentials?: Record<string, string> })?.credentials ?? {};
        const data = await postJson(new URL("/brokers/dhan/connect", base).toString(), {
          broker: "dhan",
          credentials,
        });
        return { ok: true, data };
      }
      if (commandId === "account") {
        const data = await getJson(new URL("/brokers/dhan/account", base).toString());
        return { ok: true, data };
      }
      if (commandId === "place-order") {
        // The order-entry UI calls this with the proposal-shaped payload.
        // We hit the propose endpoint; the UI then opens the confirmation
        // dialog and calls `place-order-confirm` on user click.
        const data = await postJson(
          new URL("/brokers/dhan/orders", base).toString(),
          args as Record<string, unknown>,
        );
        return { ok: true, data };
      }
      if (commandId === "place-order-confirm") {
        const payload = args as {
          proposalId: string;
          humanConfirmed: boolean;
          confirmNote?: string;
        };
        const data = await postJson(
          new URL(`/brokers/dhan/orders/${payload.proposalId}/confirm`, base).toString(),
          { humanConfirmed: payload.humanConfirmed, confirmNote: payload.confirmNote },
        );
        return { ok: true, data };
      }
      if (commandId === "halt-trading" || commandId === "set-read-only") {
        const readOnly =
          commandId === "halt-trading" ? true : Boolean((args as { readOnly?: boolean })?.readOnly);
        const data = await postJson(new URL("/brokers/dhan/read-only", base).toString(), {
          readOnly,
        });
        return { ok: true, data };
      }
      if (commandId === "set-mode") {
        const mode = (args as { mode?: string })?.mode ?? "paper";
        const data = await postJson(new URL("/brokers/dhan/mode", base).toString(), { mode });
        return { ok: true, data };
      }
      return { ok: false, error: `unknown command: ${commandId}` };
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      return { ok: false, error: detail };
    }
  },
};

export default dhanPlugin;
