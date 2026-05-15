import { beforeEach, describe, expect, it, vi } from "vitest";

import { type DiscoveredPlugin, HEALTH_HISTORY_LIMIT, PluginRuntime } from "@/lib/plugin-runtime";

import type {
  AgentSpec,
  CommandSpec,
  DataSource,
  HealthStatus,
  NodeSpec,
  PanelSpec,
  PluginCapabilities,
  PluginConfig,
  VystedPlugin,
} from "../../types/plugin";
import type { PluginManifest, PluginPersistedConfig } from "../../types/plugin-runtime";

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

const NO_CAPABILITIES: PluginCapabilities = {
  contributesData: false,
  contributesPanels: false,
  contributesCommands: false,
  contributesAgents: false,
  contributesNodes: false,
  supportsControlPlane: false,
};

function manifest(overrides: Partial<PluginManifest> = {}): PluginManifest {
  return {
    id: "test-plugin",
    version: "1.0.0",
    name: "Test Plugin",
    entry: "index.ts",
    requiredHostVersion: "0.0.0",
    ...overrides,
  };
}

interface FakePluginOverrides {
  capabilities?: Partial<PluginCapabilities>;
  initialize?: (config: PluginConfig) => Promise<void> | void;
  shutdown?: () => Promise<void> | void;
  healthCheck?: () => Promise<HealthStatus> | HealthStatus;
  getDataSources?: () => DataSource[];
  getPanels?: () => PanelSpec[];
  getCommands?: () => CommandSpec[];
  getAgents?: () => AgentSpec[];
  getNodes?: () => NodeSpec[];
}

function fakePlugin(id: string, overrides: FakePluginOverrides = {}): VystedPlugin {
  const baseHealth: HealthStatus = {
    status: "healthy",
    checkedAt: Date.now(),
  };
  return {
    pluginId: id,
    pluginName: id,
    pluginType: "data-source",
    version: "1.0.0",
    capabilities: { ...NO_CAPABILITIES, ...overrides.capabilities },
    initialize: async (config) => {
      await overrides.initialize?.(config);
    },
    shutdown: async () => {
      await overrides.shutdown?.();
    },
    healthCheck: async () => (await overrides.healthCheck?.()) ?? baseHealth,
    getDataSources: overrides.getDataSources,
    getPanels: overrides.getPanels,
    getCommands: overrides.getCommands,
    getAgents: overrides.getAgents,
    getNodes: overrides.getNodes,
  };
}

function discovered(plugin: VystedPlugin, version = "1.0.0"): DiscoveredPlugin {
  return {
    manifest: manifest({ id: plugin.pluginId, version, name: plugin.pluginName }),
    instance: plugin,
  };
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

describe("PluginRuntime — lifecycle", () => {
  let runtime: PluginRuntime;
  beforeEach(() => {
    runtime = new PluginRuntime({ now: () => 1000 });
  });

  it("discover transitions a plugin to `discovered`", () => {
    const snapshot = runtime.discover(discovered(fakePlugin("a")));
    expect(snapshot.state).toBe("discovered");
    expect(snapshot.healthHistory).toEqual([]);
    expect(runtime.getPlugins()).toHaveLength(1);
  });

  it("discover is idempotent — re-discovery returns the existing record", () => {
    const plugin = fakePlugin("a");
    runtime.discover(discovered(plugin));
    runtime.discover(discovered(plugin));
    expect(runtime.getPlugins()).toHaveLength(1);
  });

  it("loadPlugin runs initialize and transitions to `active`", async () => {
    const initialize = vi.fn();
    const snapshot = await runtime.loadPlugin(discovered(fakePlugin("a", { initialize })));
    expect(snapshot.state).toBe("active");
    expect(initialize).toHaveBeenCalledOnce();
  });

  it("loadPlugin captures init errors and transitions to `error`", async () => {
    const snapshot = await runtime.loadPlugin(
      discovered(
        fakePlugin("a", {
          initialize: () => {
            throw new Error("boom");
          },
        }),
      ),
    );
    expect(snapshot.state).toBe("error");
    expect(snapshot.errorMessage).toContain("boom");
    expect(snapshot.errorMessage).toContain("initialize");
  });

  it("loadPlugin honours a persisted disabled config (no initialize)", async () => {
    const initialize = vi.fn();
    const persistence = {
      load: async (): Promise<PluginPersistedConfig> => ({
        pluginId: "a",
        enabled: false,
        settings: {},
        grantedSecretIds: [],
      }),
      save: vi.fn(async () => {}),
    };
    const runtime2 = new PluginRuntime({ now: () => 1, persistence });
    const snapshot = await runtime2.loadPlugin(discovered(fakePlugin("a", { initialize })));
    expect(snapshot.state).toBe("stopped");
    expect(initialize).not.toHaveBeenCalled();
  });

  it("loadPlugin persists a default config the first time it runs", async () => {
    const saved: PluginPersistedConfig[] = [];
    const persistence = {
      load: async (): Promise<PluginPersistedConfig | null> => null,
      save: async (config: PluginPersistedConfig): Promise<void> => {
        saved.push(config);
      },
    };
    const runtime2 = new PluginRuntime({ now: () => 1, persistence });
    await runtime2.loadPlugin(discovered(fakePlugin("a")));
    expect(saved).toHaveLength(1);
    expect(saved[0].pluginId).toBe("a");
    expect(saved[0].enabled).toBe(true);
  });

  it("loadPlugin is idempotent — re-loading an active plugin is a no-op", async () => {
    const initialize = vi.fn();
    const plugin = fakePlugin("a", { initialize });
    await runtime.loadPlugin(discovered(plugin));
    await runtime.loadPlugin(discovered(plugin));
    expect(initialize).toHaveBeenCalledOnce();
  });

  it("unloadPlugin runs shutdown and transitions to `stopped`", async () => {
    const shutdown = vi.fn();
    const plugin = fakePlugin("a", { shutdown });
    await runtime.loadPlugin(discovered(plugin));
    const snapshot = await runtime.unloadPlugin("a");
    expect(snapshot?.state).toBe("stopped");
    expect(shutdown).toHaveBeenCalledOnce();
  });

  it("unloadPlugin captures shutdown errors and transitions to `error`", async () => {
    const plugin = fakePlugin("a", {
      shutdown: () => {
        throw new Error("crashy");
      },
    });
    await runtime.loadPlugin(discovered(plugin));
    const snapshot = await runtime.unloadPlugin("a");
    expect(snapshot?.state).toBe("error");
    expect(snapshot?.errorMessage).toContain("crashy");
  });

  it("unloadPlugin returns undefined for unknown ids", async () => {
    expect(await runtime.unloadPlugin("never-loaded")).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Capability negotiation
// ---------------------------------------------------------------------------

describe("PluginRuntime — capability negotiation", () => {
  it("only calls getDataSources when contributesData is true", async () => {
    const getDataSources = vi.fn(() => [
      { id: "ds-1", label: "DS1", kinds: ["equity"], realtime: false } as DataSource,
    ]);
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(
      discovered(
        fakePlugin("flagged-off", {
          capabilities: { contributesData: false },
          getDataSources,
        }),
      ),
    );
    expect(runtime.collectDataSources()).toEqual([]);
    expect(getDataSources).not.toHaveBeenCalled();
  });

  it("calls getDataSources when contributesData is true", async () => {
    const ds: DataSource = { id: "ds-1", label: "DS1", kinds: ["equity"], realtime: false };
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(
      discovered(
        fakePlugin("flagged-on", {
          capabilities: { contributesData: true },
          getDataSources: () => [ds],
        }),
      ),
    );
    expect(runtime.collectDataSources()).toEqual([ds]);
  });

  it("calls getCommands only when contributesCommands is true", async () => {
    const cmd: CommandSpec = { id: "c1", trigger: "c", title: "C", commandId: "c" };
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(
      discovered(
        fakePlugin("cmds", {
          capabilities: { contributesCommands: true },
          getCommands: () => [cmd],
        }),
      ),
    );
    await runtime.loadPlugin(
      discovered(
        fakePlugin("no-cmds", {
          capabilities: { contributesCommands: false },
          getCommands: () => [{ ...cmd, id: "c2" }],
        }),
      ),
    );
    expect(runtime.collectCommands()).toEqual([cmd]);
  });

  it("calls getPanels only when contributesPanels is true", async () => {
    const panel: PanelSpec = { id: "p1", title: "P", component: "p-component" };
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(
      discovered(
        fakePlugin("panels", {
          capabilities: { contributesPanels: true },
          getPanels: () => [panel],
        }),
      ),
    );
    expect(runtime.collectPanels()).toEqual([panel]);
  });

  it("flag set with missing getter emits an `errored` event but does not throw", async () => {
    const events: string[] = [];
    const runtime = new PluginRuntime();
    runtime.subscribe((event) => {
      if (event.kind === "errored") events.push(event.message ?? "");
    });
    await runtime.loadPlugin(
      discovered(
        fakePlugin("missing-getter", {
          capabilities: { contributesAgents: true },
        }),
      ),
    );
    expect(runtime.collectAgents()).toEqual([]);
    expect(events.some((message) => message.includes("getAgents"))).toBe(true);
  });

  it("inactive plugins contribute nothing", async () => {
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(
      discovered(
        fakePlugin("nodes", {
          capabilities: { contributesNodes: true },
          getNodes: () =>
            [
              {
                id: "n1",
                label: "N1",
                category: "trigger",
                inputs: [],
                outputs: [],
              },
            ] as NodeSpec[],
        }),
      ),
    );
    await runtime.unloadPlugin("nodes");
    expect(runtime.collectNodes()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Health history
// ---------------------------------------------------------------------------

describe("PluginRuntime — health checks", () => {
  it("appends each healthCheck sample to the rolling history", async () => {
    let now = 0;
    const runtime = new PluginRuntime({ now: () => now });
    await runtime.loadPlugin(discovered(fakePlugin("a")));
    now = 100;
    await runtime.healthCheckAll();
    now = 200;
    await runtime.healthCheckAll();
    const snapshot = runtime.getPlugin("a");
    expect(snapshot?.healthHistory).toHaveLength(2);
    expect(snapshot?.healthHistory.map((sample) => sample.recordedAt)).toEqual([100, 200]);
  });

  it("rolls history off the oldest end at HEALTH_HISTORY_LIMIT samples", async () => {
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(discovered(fakePlugin("a")));
    for (let i = 0; i < HEALTH_HISTORY_LIMIT + 5; i++) {
      await runtime.healthCheckAll();
    }
    const snapshot = runtime.getPlugin("a");
    expect(snapshot?.healthHistory).toHaveLength(HEALTH_HISTORY_LIMIT);
  });

  it("emits `health-changed` only when the latest sample's status differs", async () => {
    let status: HealthStatus["status"] = "healthy";
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(
      discovered(
        fakePlugin("a", {
          healthCheck: () => ({ status, checkedAt: 0 }),
        }),
      ),
    );
    const events: string[] = [];
    runtime.subscribe((event) => {
      if (event.kind === "health-changed") events.push(event.kind);
    });
    await runtime.healthCheckAll();
    await runtime.healthCheckAll();
    status = "degraded";
    await runtime.healthCheckAll();
    await runtime.healthCheckAll();
    status = "unavailable";
    await runtime.healthCheckAll();
    // First sample triggers (no prior), then degraded transition, then unavailable transition.
    expect(events).toHaveLength(3);
  });

  it("a healthCheck that throws transitions the plugin to `error`", async () => {
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(
      discovered(
        fakePlugin("a", {
          healthCheck: () => {
            throw new Error("boom");
          },
        }),
      ),
    );
    await runtime.healthCheckAll();
    const snapshot = runtime.getPlugin("a");
    expect(snapshot?.state).toBe("error");
    expect(snapshot?.errorMessage).toContain("boom");
  });
});

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

describe("PluginRuntime — events", () => {
  it("emits discovered → loaded → started → stopped across the lifecycle", async () => {
    const runtime = new PluginRuntime();
    const events: string[] = [];
    runtime.subscribe((event) => {
      events.push(event.kind);
    });
    await runtime.loadPlugin(discovered(fakePlugin("a")));
    await runtime.unloadPlugin("a");
    expect(events).toContain("discovered");
    expect(events).toContain("loaded");
    expect(events).toContain("started");
    expect(events).toContain("stopped");
  });

  it("listener errors do not break runtime state", async () => {
    const runtime = new PluginRuntime();
    runtime.subscribe(() => {
      throw new Error("listener crashed");
    });
    await expect(runtime.loadPlugin(discovered(fakePlugin("a")))).resolves.toBeDefined();
    expect(runtime.getPlugin("a")?.state).toBe("active");
  });

  it("subscribe returns an unsubscribe function", async () => {
    const runtime = new PluginRuntime();
    const events: string[] = [];
    const unsubscribe = runtime.subscribe((event) => events.push(event.kind));
    await runtime.loadPlugin(discovered(fakePlugin("a")));
    unsubscribe();
    await runtime.unloadPlugin("a");
    // Loaded events captured; unload events not.
    expect(events).toContain("loaded");
    expect(events).not.toContain("stopped");
  });
});

// ---------------------------------------------------------------------------
// Config wiring
// ---------------------------------------------------------------------------

describe("PluginRuntime — config wiring", () => {
  it("hands initialize() the resolved data dir, sidecar URL, host version, secrets", async () => {
    let capturedConfig: PluginConfig | undefined;
    const runtime = new PluginRuntime({
      resolveDataDir: (id) => `/tmp/${id}`,
      sidecarBaseUrl: "http://127.0.0.1:51763",
      hostVersion: "0.3.0",
      resolveSecrets: async (ids) => Object.fromEntries(ids.map((id) => [id, `value-of-${id}`])),
      persistence: {
        load: async () => ({
          pluginId: "a",
          enabled: true,
          settings: { theme: "dark" },
          grantedSecretIds: ["api-key"],
        }),
        save: async () => {},
      },
    });
    await runtime.loadPlugin(
      discovered(
        fakePlugin("a", {
          initialize: (config) => {
            capturedConfig = config;
          },
        }),
      ),
    );
    expect(capturedConfig).toBeDefined();
    expect(capturedConfig?.dataDir).toBe("/tmp/a");
    expect(capturedConfig?.sidecarBaseUrl).toBe("http://127.0.0.1:51763");
    expect(capturedConfig?.hostVersion).toBe("0.3.0");
    expect(capturedConfig?.settings).toEqual({ theme: "dark" });
    expect(capturedConfig?.secrets).toEqual({ "api-key": "value-of-api-key" });
  });
});
