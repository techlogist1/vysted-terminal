import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

const setSecretMock = vi.hoisted(() =>
  vi.fn<(account: string, value: string) => Promise<void>>(async () => undefined),
);
const getSecretMock = vi.hoisted(() => vi.fn(async (): Promise<string | null> => null));
const deleteSecretMock = vi.hoisted(() => vi.fn(async () => undefined));
// sidecarGet is generic (sidecarGet<T>) — this mock stands in for calls that
// return different shapes (newsapi probe, /data-sources), so it's typed
// `unknown` rather than pinned to one caller's response shape.
const sidecarGetMock = vi.hoisted(() => vi.fn(async (): Promise<unknown> => ({ newsapi: "ok" })));

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

import { MARKETPLACE_CATALOG } from "@/lib/marketplace";
import { PluginRuntime } from "@/lib/plugin-runtime";
import { resetMarketplaceStoreForTests, useMarketplaceStore } from "@/store/marketplace";
import { useModulesStore } from "@/store/modules";
import { usePluginsStore } from "@/store/plugins";
import { MarketplacePanel } from "./MarketplacePanel";

let detach: (() => void) | null = null;

function attachFreshRuntime(): void {
  const runtime = new PluginRuntime({ hostVersion: "0.8.0" });
  detach = usePluginsStore.getState().attachRuntime(runtime);
}

// Every current catalog row is preinstalled, so the Remove control never
// renders against real data yet (it's reachable once a non-preinstalled row
// exists, e.g. after a marketplace install of a genuinely-external plugin).
// Flip one row for this test to exercise the confirm-guard the UI already
// implements for that case.
const exampleEntry = MARKETPLACE_CATALOG.find((entry) => entry.pluginId === "vysted-example")!;
const originalPreinstalled = exampleEntry.preinstalled;

describe("MarketplacePanel — Remove is confirm-guarded (R15-UI-018)", () => {
  beforeEach(async () => {
    exampleEntry.preinstalled = false;
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
    await useMarketplaceStore.getState().install("vysted-example");
  });

  afterEach(() => {
    cleanup();
    detach?.();
    detach = null;
    exampleEntry.preinstalled = originalPreinstalled;
  });

  it("a single click on Remove does not remove the plugin; a second click confirms it", async () => {
    render(<MarketplacePanel />);
    const removeButton = await screen.findByRole("button", {
      name: /remove example data source/i,
    });

    fireEvent.click(removeButton);
    expect(useMarketplaceStore.getState().stateFor("vysted-example").installed).toBe(true);

    const confirmButton = screen.getByRole("button", {
      name: /confirm: this cannot be undone/i,
    });
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(useMarketplaceStore.getState().stateFor("vysted-example").installed).toBe(false);
    });
  });
});

describe("MarketplacePanel — India data lanes derive from live /data-sources (R15-CODE-PLATFORM-072/R15-DATA-077)", () => {
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
    sidecarGetMock.mockClear();
    attachFreshRuntime();
    await useMarketplaceStore.getState().refresh();
  });

  afterEach(() => {
    cleanup();
    detach?.();
    detach = null;
  });

  it("renders an India lane row from the /data-sources fixture", async () => {
    sidecarGetMock.mockResolvedValue({
      providers: [
        {
          id: "nse_direct",
          keys: ["quote", "ohlcv"],
          rank: 15,
          available: true,
          asset_classes: ["equity"],
          region: ["IN"],
        },
      ],
    });

    render(<MarketplacePanel />);

    const row = await screen.findByTestId("data-lane-nse_direct");
    expect(row.textContent).toContain("NSE (direct)");
    expect(row.textContent).toContain("Available");
    expect(row.textContent).toContain("Serves: quote, ohlcv");
    expect(row.textContent).toContain("region: IN");
  });

  it("renders no India-lanes section when the sidecar is offline", async () => {
    sidecarGetMock.mockRejectedValue(new Error("offline"));

    render(<MarketplacePanel />);

    await waitFor(() => expect(sidecarGetMock).toHaveBeenCalled());
    expect(screen.queryByLabelText("India data lanes")).toBeNull();
  });
});
