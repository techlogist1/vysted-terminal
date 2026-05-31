import type { SerializedDockview } from "dockview";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AGENT_DOCK_DEFAULT_WIDTH, useAgentDockStore } from "@/store/agent-dock";
import { useAgentModeStore } from "@/store/agent-mode";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelSelectionStore } from "@/store/model-selection";
import { useModulesStore } from "@/store/modules";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import type { DrawingSpec } from "../../types/drawings";

// The sidecar client reaches into Tauri's `invoke`; stub it so `getSidecarBaseUrl`
// resolves without a desktop runtime.
vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

import {
  deserializeWorkspace,
  loadWorkspace,
  restoreLastSessionOrDefault,
  saveWorkspace,
  serializeWorkspace,
  type SerializedWorkspace,
} from "@/lib/workspace";

/** A minimal fake dockview layout — `toJSON`/`fromJSON` round-trip its state;
 *  `addPanel`/`clear`/`getPanel` are spies so the restore-path guards can be
 *  asserted without a real dockview engine. */
function createFakeDockviewApi(initial: SerializedDockview) {
  let layout = initial;
  return {
    toJSON: () => layout,
    fromJSON: vi.fn((next: SerializedDockview) => {
      layout = next;
    }),
    addPanel: vi.fn(),
    clear: vi.fn(),
    getPanel: vi.fn(),
    get current() {
      return layout;
    },
  };
}

const LAYOUT_A = { grid: { root: "a" }, panels: { chart: {} } } as unknown as SerializedDockview;
const LAYOUT_B = { grid: { root: "b" }, panels: { news: {} } } as unknown as SerializedDockview;

describe("workspace serialization", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useWorkspaceStore.setState({ name: "default", dockviewApi: null });
    useChartDrawingsStore.setState({ byPanel: {} });
    useLLMProvidersStore.setState({ defaultProviderId: "anthropic" });
    useSymbolsStore.setState({ entries: [{ symbol: "AAPL", assetClass: "equity" }] });
    useAgentModeStore.setState({ mode: "ask" });
    useAgentDockStore.setState({ collapsed: false, width: AGENT_DOCK_DEFAULT_WIDTH });
    useModelSelectionStore.setState({ overrides: {} });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("serializeWorkspace captures the layout, enabled map, drawings, default provider, and watchlist", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useModulesStore.setState({ enabled: { chart: true, news: false, platform: true } });

    const workspace = serializeWorkspace("research");

    expect(workspace).toEqual({
      name: "research",
      layout: LAYOUT_A,
      enabledModules: { chart: true, news: false, platform: true },
      chartDrawings: { byPanel: {} },
      defaultProviderId: "anthropic",
      watchlist: [{ symbol: "AAPL", assetClass: "equity" }],
      agentMode: "ask",
      agentDock: { collapsed: false, width: AGENT_DOCK_DEFAULT_WIDTH },
      modelOverrides: {},
    });
  });

  it("round-trips the agent mode, dock geometry, and model overrides (FR-003/004)", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    deserializeWorkspace({
      name: "saved",
      layout: LAYOUT_A,
      enabledModules: {},
      agentMode: "build",
      agentDock: { collapsed: true, width: 520 },
      modelOverrides: { anthropic: "claude-sonnet-4-5" },
    });
    expect(useAgentModeStore.getState().mode).toBe("build");
    expect(useAgentDockStore.getState().collapsed).toBe(true);
    expect(useAgentDockStore.getState().width).toBe(520);
    expect(useModelSelectionStore.getState().overrides.anthropic).toBe("claude-sonnet-4-5");
  });

  it("deserializeWorkspace restores a persisted watchlist", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    deserializeWorkspace({
      name: "saved",
      layout: LAYOUT_A,
      enabledModules: {},
      watchlist: [
        { symbol: "TSLA", assetClass: "equity" },
        { symbol: "BTC/USDT", assetClass: "crypto" },
      ],
    });
    const entries = useSymbolsStore.getState().entries;
    expect(entries.map((e) => e.symbol)).toEqual(["TSLA", "BTC/USDT"]);
  });

  it("round-trips: serialize then deserialize restores the layout and enabled map", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useModulesStore.setState({ enabled: { chart: true, news: false, platform: true } });

    const saved = serializeWorkspace("research");

    // Mutate the live state away from what was saved...
    fakeApi.fromJSON(LAYOUT_B);
    useModulesStore.setState({ enabled: { chart: false, news: true, platform: true } });
    useWorkspaceStore.setState({ name: "scratch" });

    // ...then deserialize and assert the saved state is restored exactly.
    deserializeWorkspace(saved);

    expect(fakeApi.current).toEqual(LAYOUT_A);
    expect(useModulesStore.getState().enabled).toEqual(saved.enabledModules);
    expect(useWorkspaceStore.getState().name).toBe("research");
  });

  it("serializeWorkspace throws when the dockview layout is not ready", () => {
    expect(() => serializeWorkspace("research")).toThrow(/not ready/);
  });

  it("saveWorkspace POSTs the serialized workspace to the sidecar", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useModulesStore.setState({ enabled: { chart: true, platform: true } });

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 200 }));

    await saveWorkspace("research");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("http://127.0.0.1:51763/workspace");
    expect(init?.method).toBe("POST");
    const body = JSON.parse(init?.body as string) as {
      name: string;
      workspace: SerializedWorkspace;
    };
    expect(body.name).toBe("research");
    expect(body.workspace.layout).toEqual(LAYOUT_A);
    expect(body.workspace.enabledModules).toEqual({ chart: true, platform: true });
  });

  it("loadWorkspace fetches from the sidecar and applies the workspace", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_B);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });

    const stored: SerializedWorkspace = {
      name: "research",
      layout: LAYOUT_A,
      enabledModules: { chart: true, news: false, platform: true },
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(stored), { status: 200 }),
    );

    await loadWorkspace("research");

    expect(fakeApi.current).toEqual(LAYOUT_A);
    expect(useModulesStore.getState().enabled).toEqual(stored.enabledModules);
    expect(useWorkspaceStore.getState().name).toBe("research");
  });

  it("saveWorkspace rejects an empty name", async () => {
    await expect(saveWorkspace("   ")).rejects.toThrow(/name is required/);
  });

  it("round-trips chart drawings through workspace JSON (Phase 2)", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useModulesStore.setState({ enabled: { chart: true } });

    const trendline: DrawingSpec = {
      id: "draw-trend",
      panelId: "chart-1",
      kind: "trendline",
      points: [
        { time: 1700000000, price: 100 },
        { time: 1700100000, price: 110 },
      ],
      style: { color: "#e9a94d", lineWidth: 1, lineStyle: "solid" },
      createdAt: 1700000000_000,
    };
    const fib: DrawingSpec = {
      id: "draw-fib",
      panelId: "chart-2",
      kind: "fib-retracement",
      points: [
        { time: 1700000000, price: 100 },
        { time: 1700100000, price: 200 },
      ],
      style: { color: "#8fa67c", lineWidth: 1, lineStyle: "dashed" },
      createdAt: 1700000000_001,
    };
    useChartDrawingsStore.getState().addDrawing("chart-1", trendline);
    useChartDrawingsStore.getState().addDrawing("chart-2", fib);

    const saved = serializeWorkspace("with-drawings");

    // Mutate the live state away…
    useChartDrawingsStore.setState({ byPanel: {} });
    expect(useChartDrawingsStore.getState().getDrawings("chart-1")).toHaveLength(0);

    // …then reload — drawings come back exactly as saved.
    deserializeWorkspace(saved);
    expect(useChartDrawingsStore.getState().getDrawings("chart-1")).toEqual([trendline]);
    expect(useChartDrawingsStore.getState().getDrawings("chart-2")).toEqual([fib]);
  });

  it("loadWorkspace without chartDrawings clears any pre-existing drawings", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useModulesStore.setState({ enabled: { chart: true } });
    useChartDrawingsStore.getState().addDrawing("chart-x", {
      id: "leftover",
      panelId: "chart-x",
      kind: "rectangle",
      points: [
        { time: 1, price: 1 },
        { time: 2, price: 2 },
      ],
      style: { color: "#fff", lineWidth: 1 },
      createdAt: 0,
    });

    deserializeWorkspace({
      name: "old",
      layout: LAYOUT_A,
      enabledModules: { chart: true },
    });

    expect(useChartDrawingsStore.getState().getDrawings("chart-x")).toHaveLength(0);
  });
});

describe("restoreLastSessionOrDefault — boot-crash guards", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useWorkspaceStore.setState({ name: "default", dockviewApi: null });
    useChartDrawingsStore.setState({ byPanel: {} });
    useLLMProvidersStore.setState({ defaultProviderId: "anthropic" });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function stubFetchResolving(workspace: unknown) {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => workspace }) as unknown as Response),
    );
  }

  it("skips to default (no mutation) when the api was replaced during the fetch", async () => {
    // The api passed in is NOT the store's live api — simulates StrictMode
    // disposing/replacing the dockview instance while the restore fetch awaited.
    const passedApi = createFakeDockviewApi(LAYOUT_A);
    const liveApi = createFakeDockviewApi(LAYOUT_B);
    useWorkspaceStore.setState({ dockviewApi: liveApi as never });
    stubFetchResolving({ name: "x", layout: LAYOUT_A, enabledModules: {} });

    const restored = await restoreLastSessionOrDefault(passedApi as never, new Set(["chart"]));

    expect(restored).toBe(false);
    expect(passedApi.fromJSON).not.toHaveBeenCalled();
    expect(passedApi.addPanel).not.toHaveBeenCalled();
    expect(passedApi.clear).not.toHaveBeenCalled();
  });

  it("skips to a clean default when the saved layout references an unregistered component", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    // No modules registered → "tradesa-x" is an unknown panel component, the
    // case where dockview's fromJSON would throw mid-deserialize and corrupt
    // the grid. We must skip straight to applyDefaultLayout instead.
    stubFetchResolving({
      name: "x",
      layout: { grid: { root: "a" }, panels: { p1: { contentComponent: "tradesa-x" } } },
      enabledModules: {},
    });

    const restored = await restoreLastSessionOrDefault(api as never, new Set(["chart"]));

    expect(restored).toBe(false);
    expect(api.fromJSON).not.toHaveBeenCalled(); // never risked the throwing deserialize
    expect(api.addPanel).toHaveBeenCalled(); // applyDefaultLayout ran instead
  });

  it("re-bases on a clean grid when the restore fetch fails", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("Load failed"); // sidecar not ready
      }),
    );

    const restored = await restoreLastSessionOrDefault(api as never, new Set(["chart"]));

    expect(restored).toBe(false);
    expect(api.clear).toHaveBeenCalled(); // clean grid before the default layout
    expect(api.addPanel).toHaveBeenCalled();
  });
});
