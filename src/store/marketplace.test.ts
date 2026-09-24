import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Keychain is the only credential path; mock it so configure() doesn't touch a
// real OS keychain. getSecret returns null by default (plugin unconfigured).
const setSecretMock = vi.hoisted(() =>
  vi.fn<(account: string, value: string) => Promise<void>>(async () => undefined),
);
const getSecretMock = vi.hoisted(() => vi.fn(async (): Promise<string | null> => null));
const deleteSecretMock = vi.hoisted(() => vi.fn(async () => undefined));
// R15-DATA-094: configure() probes a NewsAPI key against the sidecar before
// saving it — defaults to "ok" so every test but the probe-specific ones below
// behaves as if the sidecar accepted the key.
const sidecarGetMock = vi.hoisted(() =>
  vi.fn(async (): Promise<{ newsapi: string }> => ({ newsapi: "ok" })),
);

vi.mock("@/lib/keychain", async () => {
  const actual = await vi.importActual<typeof import("@/lib/keychain")>("@/lib/keychain");
  return {
    ...actual,
    getSecret: getSecretMock,
    setSecret: setSecretMock,
    deleteSecret: deleteSecretMock,
  };
});

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return { ...actual, sidecarGet: sidecarGetMock };
});

import { pluginHost } from "@/lib/plugin-bootstrap";
import { PluginRuntime } from "@/lib/plugin-runtime";
import { resetMarketplaceStoreForTests, useMarketplaceStore } from "@/store/marketplace";
import { useModulesStore } from "@/store/modules";
import { usePluginsStore } from "@/store/plugins";

let detach: (() => void) | null = null;

function attachFreshRuntime(): void {
  // Default in-memory persistence; host version matches HOST_VERSION so every
  // catalog plugin satisfies requiredHostVersion. The production host bridge,
  // since the runtime (not this store) bridges panels/commands/agents.
  const runtime = new PluginRuntime({ hostVersion: "0.8.0", host: pluginHost });
  detach = usePluginsStore.getState().attachRuntime(runtime);
}

describe("marketplace store — install/enable/configure/remove (FR-050/US10/SC-013)", () => {
  beforeEach(async () => {
    resetMarketplaceStoreForTests();
    useModulesStore.setState({ modules: [], enabled: {} });
    usePluginsStore.setState({
      plugins: [],
      dataSources: [],
      agents: [],
      nodes: [],
      runtime: null,
    });
    setSecretMock.mockClear();
    getSecretMock.mockClear();
    sidecarGetMock.mockClear();
    sidecarGetMock.mockResolvedValue({ newsapi: "ok" });
    attachFreshRuntime();
    await useMarketplaceStore.getState().refresh();
  });

  afterEach(() => {
    detach?.();
    detach = null;
  });

  it("defaults: first-party data is installed at boot", () => {
    expect(useMarketplaceStore.getState().stateFor("vysted-yfinance").installed).toBe(true);
  });

  it("installs a plugin through the marketplace — zero host code change (SC-013)", async () => {
    await useMarketplaceStore.getState().remove("vysted-example");
    expect(useMarketplaceStore.getState().stateFor("vysted-example").installed).toBe(false);
    await useMarketplaceStore.getState().install("vysted-example");
    const state = useMarketplaceStore.getState().stateFor("vysted-example");
    expect(state.installed).toBe(true);
    expect(state.enabled).toBe(true);
    expect(state.runtimeState).toBe("active");
  });

  it("disable then re-enable a plugin toggles its runtime state", async () => {
    await useMarketplaceStore.getState().enable("vysted-yfinance");
    expect(useMarketplaceStore.getState().stateFor("vysted-yfinance").runtimeState).toBe("active");
    await useMarketplaceStore.getState().disable("vysted-yfinance");
    const disabled = useMarketplaceStore.getState().stateFor("vysted-yfinance");
    expect(disabled.enabled).toBe(false);
    expect(disabled.runtimeState).toBe("stopped");
    await useMarketplaceStore.getState().enable("vysted-yfinance");
    expect(useMarketplaceStore.getState().stateFor("vysted-yfinance").runtimeState).toBe("active");
  });

  it("removing a plugin marks it not-installed (its capabilities disappear)", async () => {
    await useMarketplaceStore.getState().install("vysted-example");
    await useMarketplaceStore.getState().remove("vysted-example");
    expect(useMarketplaceStore.getState().stateFor("vysted-example").installed).toBe(false);
    // Its plugin module is disabled in the registry projection.
    expect(useModulesStore.getState().enabled["plugin:vysted-example"]).toBe(false);
  });

  it("configure writes BYOK creds to the keychain under the plugin-secret namespace (FR-034/FR-036)", async () => {
    await useMarketplaceStore.getState().install("vysted-news");
    setSecretMock.mockClear();
    await useMarketplaceStore.getState().configure("vysted-news", {
      newsapi_key: "my-secret",
    });
    const accounts = setSecretMock.mock.calls.map((c) => c[0]);
    expect(accounts).toContain("plugin-secret:vysted-news:newsapi_key");
    // The secret values are passed to the keychain only — never elsewhere.
    expect(setSecretMock).toHaveBeenCalledWith(
      "plugin-secret:vysted-news:newsapi_key",
      "my-secret",
    );
  });

  it("configure() rejects a NewsAPI key the sidecar reports unauthorized (R15-DATA-094)", async () => {
    await useMarketplaceStore.getState().install("vysted-news");
    setSecretMock.mockClear();
    sidecarGetMock.mockResolvedValueOnce({ newsapi: "unauthorized" });

    await expect(
      useMarketplaceStore.getState().configure("vysted-news", { newsapi_key: "bad-key" }),
    ).rejects.toThrow("NewsAPI rejected this key");

    expect(setSecretMock).not.toHaveBeenCalled();
    expect(useMarketplaceStore.getState().busy["vysted-news"]).toBe(false);
  });

  it("configure() keeps an earlier valid grant when a re-configure attempt is rejected (R15-DATA-094)", async () => {
    await useMarketplaceStore.getState().install("vysted-news");
    await useMarketplaceStore.getState().configure("vysted-news", { newsapi_key: "good-key" });
    const runtime = usePluginsStore.getState().runtime;
    if (!runtime) throw new Error("runtime not attached");
    expect((await runtime.readConfig("vysted-news"))?.grantedSecretIds).toContain(
      "plugin-secret:vysted-news:newsapi_key",
    );

    sidecarGetMock.mockResolvedValueOnce({ newsapi: "unauthorized" });
    await expect(
      useMarketplaceStore.getState().configure("vysted-news", { newsapi_key: "bad-key" }),
    ).rejects.toThrow("NewsAPI rejected this key");

    // A failed re-configure must not un-grant the still-valid earlier secret.
    expect((await runtime.readConfig("vysted-news"))?.grantedSecretIds).toContain(
      "plugin-secret:vysted-news:newsapi_key",
    );
  });
});
