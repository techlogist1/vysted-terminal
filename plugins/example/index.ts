/**
 * Vysted Example Plugin — proves the locked `VystedPlugin` contract end-to-end.
 *
 * This plugin is the minimal possible third-party-shaped consumer of the
 * runtime: it declares two capabilities (data + commands), exports one fake
 * `DataSource`, exports one slash command, and runs real `initialize` /
 * `shutdown` / `healthCheck` lifecycle methods. The plugin manager loads it
 * automatically at host startup so the user always sees a working example
 * before installing anything else.
 *
 * NOTE: this plugin must continue to work as long as `types/plugin.ts` is
 * stable. If it stops compiling, the contract was broken — investigate
 * `types/plugin.ts` first.
 */

import type {
  CommandResult,
  CommandSpec,
  DataSource,
  HealthStatus,
  PluginConfig,
  VystedPlugin,
} from "../../types/plugin";

let initialized = false;
let initializedAt = 0;

const dataSources: DataSource[] = [
  {
    id: "example-prices",
    label: "Example Prices",
    kinds: ["equity"],
    realtime: false,
    description: "A fake data source bundled with the runtime to prove the plugin contract.",
  },
];

const commands: CommandSpec[] = [
  {
    id: "example.hello",
    trigger: "example",
    title: "Example: Hello",
    description: "Print a greeting from the example plugin to the console.",
    icon: "smile",
    commandId: "example.hello",
  },
];

/**
 * The exported plugin instance. `pluginType: "data-source"` matches the
 * primary capability; the secondary capability (commands) is independent.
 *
 * Capability flags MUST mirror the methods that are implemented — see
 * `types/plugin.ts` for the negotiation rule the host enforces.
 */
export const examplePlugin: VystedPlugin = {
  pluginId: "vysted-example",
  pluginName: "Vysted Example Plugin",
  pluginType: "data-source",
  version: "0.1.0",

  capabilities: {
    contributesData: true,
    contributesPanels: false,
    contributesCommands: true,
    contributesAgents: false,
    contributesNodes: false,
    supportsControlPlane: true,
  },

  async initialize(config: PluginConfig): Promise<void> {
    initialized = true;
    initializedAt = Date.now();
    // Pedagogical diagnostics — gated to development so the example plugin's
    // demonstration of the lifecycle wiring is visible while developing
    // against it, but silent in production builds.
    if (process.env.NODE_ENV === "development") {
      console.info("[vysted-example] initialize", {
        dataDir: config.dataDir,
        sidecarBaseUrl: config.sidecarBaseUrl,
        hostVersion: config.hostVersion,
        hasSettings: Object.keys(config.settings).length > 0,
        secretIds: Object.keys(config.secrets),
      });
    }
  },

  async shutdown(): Promise<void> {
    if (process.env.NODE_ENV === "development") {
      console.info("[vysted-example] shutdown", {
        uptimeMs: Date.now() - initializedAt,
      });
    }
    initialized = false;
  },

  async healthCheck(): Promise<HealthStatus> {
    return {
      status: initialized ? "healthy" : "unavailable",
      message: initialized ? "running" : "not initialized",
      checkedAt: Date.now(),
    };
  },

  getDataSources(): DataSource[] {
    return dataSources;
  },

  getCommands(): CommandSpec[] {
    return commands;
  },

  async executeCommand(commandId: string): Promise<CommandResult> {
    if (commandId === "example.hello") {
      if (process.env.NODE_ENV === "development") {
        console.info("[vysted-example] hello — invoked from cmd+K");
      }
      return { ok: true, data: { greeting: "Hello from the example plugin." } };
    }
    return { ok: false, error: `unknown command: ${commandId}` };
  },
};

export default examplePlugin;
