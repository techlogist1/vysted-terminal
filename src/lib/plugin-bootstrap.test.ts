import { afterEach, describe, expect, it, vi } from "vitest";

const { syncPluginAgentsMock, sidecarGetMock } = vi.hoisted(() => ({
  syncPluginAgentsMock: vi.fn<(pluginId: string, register: boolean) => Promise<void>>(
    async () => undefined,
  ),
  sidecarGetMock: vi.fn(),
}));

vi.mock("@/lib/plugin-agents", () => ({ syncPluginAgents: syncPluginAgentsMock }));

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
    sidecarGet: sidecarGetMock,
  };
});

import { bootstrapPlugins } from "@/lib/plugin-bootstrap";
import { CATALOG_ROWS } from "@/lib/marketplace";
import { SidecarError } from "@/lib/sidecar-client";

/** Persisted plugin configs as the sidecar returns them; unknown ids 404 (defaults). */
function persistedConfigs(configs: Record<string, { enabled: boolean }>): void {
  sidecarGetMock.mockImplementation(async (path: string) => {
    const id = decodeURIComponent(path.split("/")[2] ?? "");
    const config = configs[id];
    if (!config) {
      throw new SidecarError(404, "not found");
    }
    return {
      plugin_id: id,
      installed: true,
      enabled: config.enabled,
      settings: {},
      granted_secret_ids: [],
    };
  });
}

describe("bootstrapPlugins — plugin agents at boot", () => {
  afterEach(() => {
    syncPluginAgentsMock.mockClear();
    sidecarGetMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("registers a pre-installed agent pack's agents once; a disabled one is not synced", async () => {
    // The sidecar accepts every config save (first-seen plugins persist their default).
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, status: 200, json: async () => ({}) })),
    );
    persistedConfigs({});
    const teardown = await bootstrapPlugins();
    teardown();
    const lenses = syncPluginAgentsMock.mock.calls.filter((c) => c[0] === "vysted-lenses");
    expect(lenses).toEqual([["vysted-lenses", true]]);

    syncPluginAgentsMock.mockClear();
    persistedConfigs({ "vysted-lenses": { enabled: false } });
    const teardownDisabled = await bootstrapPlugins();
    teardownDisabled();
    expect(syncPluginAgentsMock.mock.calls.some((c) => c[0] === "vysted-lenses")).toBe(false);
  });
});

// R15-LIFECYCLE-027: the boot loop used to read each plugin's persisted config
// once to decide whether to load it, then loadPlugin() re-fetched the SAME
// row again, serially, for every installed+enabled plugin.
describe("bootstrapPlugins — reads persisted config once per plugin", () => {
  afterEach(() => {
    sidecarGetMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("persistence.load is called exactly once per catalog plugin", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, status: 200, json: async () => ({}) })),
    );
    persistedConfigs({});

    const teardown = await bootstrapPlugins();
    teardown();

    const configReads = sidecarGetMock.mock.calls.filter((c) => String(c[0]).endsWith("/config"));
    expect(configReads).toHaveLength(CATALOG_ROWS.length);
  });
});
