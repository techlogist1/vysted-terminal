/**
 * Kite Connect (Zerodha) broker plugin — the static-IP-aware India broker.
 *
 * Same surface as the Dhan + Angel One plugin shells (data + commands +
 * control plane), with two extras for the SEBI/NSE static-IP UX path:
 *
 *   - The `kite.static-ip-status` slash command opens the static-IP panel
 *     so the user can configure their registered static IP + see the
 *     detected-vs-configured comparison.
 *   - The `set-static-ip` control-plane command posts to
 *     `/brokers/kite/static-ip` so the sidecar adapter persists the
 *     user's static IP in memory before the live-mode toggle audit-logs
 *     the comparison.
 *
 * The broker-connect panel embeds the `<KiteStaticIpBanner />` component
 * (`src/modules/broker-connect/kite-static-ip-banner.tsx`) which polls
 * `GET /safety/static-ip-status?configured=<configured-ip>` and surfaces
 * the mismatch visually.
 *
 * The sidecar adapter (`sidecar/services/brokers/kite.py`) does NOT
 * pre-block order placement on an IP mismatch — the user may be behind a
 * VPN/VPS whose public IP matches the broker-registered static IP even
 * when the detected default-route IP differs. Kite's rejection at order
 * time surfaces through the audit log + the order-confirmation dialog.
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

interface KiteState {
  sidecarBaseUrl: string | null;
  hostVersion: string | null;
}

const state: KiteState = {
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
    id: "kite-account",
    label: "Kite Connect — account + positions",
    kinds: ["custom"],
    realtime: false,
    description:
      "Read-only account summary + open positions, fetched through the sidecar's /brokers/kite/account route.",
  },
];

const commands: CommandSpec[] = [
  {
    id: "kite.connect",
    trigger: "connect kite",
    title: "Kite Connect: Connect",
    description: "Open a Kite Connect session using the daily access token in plugin settings.",
    icon: "plug",
    commandId: "connect",
  },
  {
    id: "kite.account",
    trigger: "kite-account",
    title: "Kite Connect: Refresh Account",
    description: "Fetch the latest account summary + positions from Kite.",
    icon: "wallet",
    commandId: "account",
  },
  {
    id: "kite.halt",
    trigger: "kite-halt",
    title: "Kite Connect: Halt Trading",
    description: "Toggle Kite into read-only mode.",
    icon: "octagon-x",
    commandId: "halt-trading",
  },
  {
    id: "kite.static-ip-status",
    trigger: "kite-static-ip",
    title: "Kite Connect: Static IP Status",
    description: "Show the detected public IP and the configured static IP comparison.",
    icon: "globe",
    commandId: "static-ip-status",
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

export const kitePlugin: VystedPlugin = {
  pluginId: "vysted-kite",
  pluginName: "Kite Connect",
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
        new URL("/brokers/kite/state", state.sidecarBaseUrl).toString(),
      )) as { status: string; mode: string };
      return {
        status: body.status === "connected" ? "healthy" : "degraded",
        message: `Kite mode=${body.mode} status=${body.status}`,
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
        const data = await postJson(new URL("/brokers/kite/connect", base).toString(), {
          broker: "kite",
          credentials,
        });
        return { ok: true, data };
      }
      if (commandId === "account") {
        return { ok: true, data: await getJson(new URL("/brokers/kite/account", base).toString()) };
      }
      if (commandId === "place-order") {
        const data = await postJson(
          new URL("/brokers/kite/orders", base).toString(),
          args as Record<string, unknown>,
        );
        return { ok: true, data };
      }
      if (commandId === "place-order-confirm") {
        const payload = args as { proposalId: string; humanConfirmed: boolean; confirmNote?: string };
        const data = await postJson(
          new URL(`/brokers/kite/orders/${payload.proposalId}/confirm`, base).toString(),
          { humanConfirmed: payload.humanConfirmed, confirmNote: payload.confirmNote },
        );
        return { ok: true, data };
      }
      if (commandId === "halt-trading" || commandId === "set-read-only") {
        const readOnly = commandId === "halt-trading"
          ? true
          : Boolean((args as { readOnly?: boolean })?.readOnly);
        const data = await postJson(new URL("/brokers/kite/read-only", base).toString(), {
          readOnly,
        });
        return { ok: true, data };
      }
      if (commandId === "set-mode") {
        const mode = (args as { mode?: string })?.mode ?? "paper";
        const data = await postJson(new URL("/brokers/kite/mode", base).toString(), { mode });
        return { ok: true, data };
      }
      if (commandId === "set-static-ip") {
        const staticIp = (args as { staticIp?: string | null })?.staticIp ?? null;
        const data = await postJson(new URL("/brokers/kite/static-ip", base).toString(), {
          staticIp,
        });
        return { ok: true, data };
      }
      if (commandId === "static-ip-status") {
        // Pulls the current configured IP from the adapter, then the
        // detected-vs-configured comparison from the safety router. The
        // panel renders the result via <KiteStaticIpBanner />.
        const configured = (await getJson(
          new URL("/brokers/kite/static-ip", base).toString(),
        )) as { configuredIp: string | null };
        const url = new URL("/safety/static-ip-status", base);
        if (configured.configuredIp) url.searchParams.set("configured", configured.configuredIp);
        const status = await getJson(url.toString());
        return { ok: true, data: { configured: configured.configuredIp, status } };
      }
      return { ok: false, error: `unknown command: ${commandId}` };
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      return { ok: false, error: detail };
    }
  },
};

export default kitePlugin;
