import { beforeEach, describe, expect, it } from "vitest";

import {
  type DiscoveredPlugin,
  type PluginPersistenceAdapter,
  PluginRuntime,
} from "@/lib/plugin-runtime";

import type { PluginPersistedConfig } from "../../types/plugin-runtime";

/** A controllable in-memory persistence so the test can read what was saved. */
function makePersistence(): PluginPersistenceAdapter & {
  configs: Map<string, PluginPersistedConfig>;
} {
  const configs = new Map<string, PluginPersistedConfig>();
  return {
    configs,
    async load(id) {
      return configs.get(id) ?? null;
    },
    async save(config) {
      configs.set(config.pluginId, { ...config });
    },
  };
}

function fakePlugin(id: string): DiscoveredPlugin {
  return {
    manifest: { id, version: "1.0.0", name: id, entry: "index.ts", requiredHostVersion: "0.0.0" },
    instance: {
      pluginId: id,
      pluginName: id,
      pluginType: "data-source",
      version: "1.0.0",
      capabilities: {
        contributesData: true,
        contributesPanels: false,
        contributesCommands: false,
        contributesAgents: false,
        contributesNodes: false,
        supportsControlPlane: false,
      },
      async initialize() {},
      async shutdown() {},
      async healthCheck() {
        return { status: "healthy", checkedAt: 0 } as const;
      },
      getDataSources() {
        return [];
      },
    },
  };
}

describe("marketplace lifecycle on the plugin runtime (FR-050/SC-013)", () => {
  let persistence: ReturnType<typeof makePersistence>;
  let runtime: PluginRuntime;

  beforeEach(() => {
    persistence = makePersistence();
    runtime = new PluginRuntime({ hostVersion: "1.0.0", persistence });
  });

  it("install loads the plugin and persists installed+enabled", async () => {
    const snap = await runtime.installPlugin(fakePlugin("p"));
    expect(snap.state).toBe("active");
    expect(persistence.configs.get("p")).toMatchObject({ installed: true, enabled: true });
  });

  it("disable unloads and persists enabled:false (stays installed)", async () => {
    await runtime.installPlugin(fakePlugin("p"));
    await runtime.disablePlugin("p");
    expect(runtime.getPlugin("p")?.state).toBe("stopped");
    expect(persistence.configs.get("p")).toMatchObject({ installed: true, enabled: false });
  });

  it("remove persists installed:false and a subsequent load contributes nothing", async () => {
    const plugin = fakePlugin("p");
    await runtime.installPlugin(plugin);
    await runtime.removePlugin("p");
    expect(persistence.configs.get("p")).toMatchObject({ installed: false, enabled: false });
    // A boot-style reload of a removed plugin must NOT initialize it.
    const snap = await runtime.loadPlugin(plugin);
    expect(snap.state).toBe("stopped");
    expect(runtime.activePlugins()).toHaveLength(0);
  });

  it("a not-installed persisted plugin is never initialized at load (FR-051 broker-at-boot guard)", async () => {
    persistence.configs.set("broker", {
      pluginId: "broker",
      installed: false,
      enabled: false,
      settings: {},
      grantedSecretIds: [],
    });
    const plugin = fakePlugin("broker");
    const init = plugin.instance.initialize;
    let initialized = false;
    plugin.instance.initialize = async (c) => {
      initialized = true;
      return init.call(plugin.instance, c);
    };
    const snap = await runtime.loadPlugin(plugin);
    expect(snap.state).toBe("stopped");
    expect(initialized).toBe(false);
  });

  it("re-enabling a removed plugin reloads it", async () => {
    const plugin = fakePlugin("p");
    await runtime.installPlugin(plugin);
    await runtime.removePlugin("p");
    const snap = await runtime.enablePlugin(plugin);
    expect(snap.state).toBe("active");
    expect(persistence.configs.get("p")).toMatchObject({ installed: true, enabled: true });
  });
});
