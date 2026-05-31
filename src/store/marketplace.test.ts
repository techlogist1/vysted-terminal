import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Keychain is the only credential path; mock it so configure() doesn't touch a
// real OS keychain. getSecret returns null by default (broker unconfigured).
const setSecretMock = vi.hoisted(() =>
  vi.fn<(account: string, value: string) => Promise<void>>(async () => undefined),
);
const getSecretMock = vi.hoisted(() => vi.fn(async (): Promise<string | null> => null));
const deleteSecretMock = vi.hoisted(() => vi.fn(async () => undefined));

vi.mock("@/lib/keychain", async () => {
  const actual = await vi.importActual<typeof import("@/lib/keychain")>("@/lib/keychain");
  return {
    ...actual,
    getSecret: getSecretMock,
    setSecret: setSecretMock,
    deleteSecret: deleteSecretMock,
  };
});

import { PluginRuntime } from "@/lib/plugin-runtime";
import { resetMarketplaceStoreForTests, useMarketplaceStore } from "@/store/marketplace";
import { useModulesStore } from "@/store/modules";
import { usePluginsStore } from "@/store/plugins";

let detach: (() => void) | null = null;

function attachFreshRuntime(): void {
  // Default in-memory persistence; host version matches HOST_VERSION so every
  // catalog plugin satisfies requiredHostVersion.
  const runtime = new PluginRuntime({ hostVersion: "0.8.0" });
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
    attachFreshRuntime();
    await useMarketplaceStore.getState().refresh();
  });

  afterEach(() => {
    detach?.();
    detach = null;
  });

  it("defaults: brokers are NOT installed at boot; first-party data IS (FR-051)", () => {
    expect(useMarketplaceStore.getState().stateFor("vysted-kite").installed).toBe(false);
    expect(useMarketplaceStore.getState().stateFor("vysted-yfinance").installed).toBe(true);
  });

  it("installs a broker through the marketplace — zero host code change (SC-013)", async () => {
    await useMarketplaceStore.getState().install("vysted-kite");
    const state = useMarketplaceStore.getState().stateFor("vysted-kite");
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

  it("removing a broker marks it not-installed (its capabilities disappear)", async () => {
    await useMarketplaceStore.getState().install("vysted-kite");
    await useMarketplaceStore.getState().remove("vysted-kite");
    expect(useMarketplaceStore.getState().stateFor("vysted-kite").installed).toBe(false);
    // Its plugin module is disabled in the registry projection.
    expect(useModulesStore.getState().enabled["plugin:vysted-kite"]).toBe(false);
  });

  it("configure writes BYOK creds to the keychain under the broker namespace (FR-034/FR-036)", async () => {
    await useMarketplaceStore.getState().install("vysted-kite");
    setSecretMock.mockClear();
    await useMarketplaceStore.getState().configure("vysted-kite", {
      api_key: "my-key",
      api_secret: "my-secret",
    });
    const accounts = setSecretMock.mock.calls.map((c) => c[0]);
    expect(accounts).toContain("broker:kite:api_key");
    expect(accounts).toContain("broker:kite:api_secret");
    // The secret values are passed to the keychain only — never elsewhere.
    expect(setSecretMock).toHaveBeenCalledWith("broker:kite:api_secret", "my-secret");
  });
});
