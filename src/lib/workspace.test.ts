import type { SerializedDockview } from "dockview";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AGENT_DOCK_DEFAULT_WIDTH, useAgentDockStore } from "@/store/agent-dock";
import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useAgentModeStore } from "@/store/agent-mode";
import { resetChartCommandStoreForTests, useChartCommandStore } from "@/store/chart-command";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useNotesStore } from "@/store/notes";
import { resetKeybindingsStoreForTests, useKeybindingsStore } from "@/store/keybindings";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { DEFAULT_MODEL_BY_PROVIDER, useModelSelectionStore } from "@/store/model-selection";
import { useModulesStore } from "@/store/modules";
import { DEFAULT_SETTINGS, resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import type { DrawingSpec } from "../../types/drawings";

// The sidecar client reaches into Tauri's `invoke`; stub it so `getSidecarBaseUrl`
// resolves without a desktop runtime.
vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

import {
  createResearchSpace,
  deserializeWorkspace,
  loadWorkspace,
  researchSpaceName,
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
    // `applyPlan` (research-space layout) reads `panels` + `width` and may
    // exit a maximized group; an empty panel list + a comfortable width + these
    // no-op spies keep the fake good enough for it.
    panels: [] as { id: string }[],
    width: 1440,
    hasMaximizedGroup: vi.fn(() => false),
    exitMaximizedGroup: vi.fn(),
    maximizeGroup: vi.fn(),
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
    useAgentModeStore.setState({ mode: "agent" });
    useAgentAutonomyStore.setState({ autonomy: "ask" });
    useAgentDockStore.setState({ collapsed: false, width: AGENT_DOCK_DEFAULT_WIDTH });
    useModelSelectionStore.setState({ overrides: {} });
    resetKeybindingsStoreForTests();
    resetSettingsStoreForTests();
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
      portfolios: {
        list: [{ id: "default", name: "Portfolio", holdings: [] }],
        activeId: "default",
      },
      agentMode: "agent",
      autonomyMode: "ask",
      agentDock: { collapsed: false, width: AGENT_DOCK_DEFAULT_WIDTH },
      modelOverrides: {},
      modelOverridesV: 2,
      keybindingOverrides: {},
      settings: DEFAULT_SETTINGS,
      searchSettings: { tier: "native", searxngUrl: "" },
      brief: null,
      notes: { general: "", bySymbol: {}, focusSymbol: "" },
    });
  });

  it("round-trips keybinding overrides and the settings bundle (FR-037/038/039)", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });

    // Set some non-default keybindings + preferences, then serialize.
    useKeybindingsStore.getState().setBinding("palette.open", "mod+shift+p");
    useSettingsStore.getState().setDefaultAgentId("buffett");
    useSettingsStore.getState().setProviderPreferenceOrder(["groq", "ollama", "anthropic"]);
    useSettingsStore.getState().setPaletteRecentsEnabled(false);

    const saved = serializeWorkspace("research");
    expect(saved.keybindingOverrides).toEqual({ "palette.open": "mod+shift+p" });
    expect(saved.settings?.defaultAgentId).toBe("buffett");
    expect(saved.settings?.providerPreferenceOrder).toEqual(["groq", "ollama", "anthropic"]);
    expect(saved.settings?.paletteRecentsEnabled).toBe(false);

    // Mutate the live state away…
    resetKeybindingsStoreForTests();
    resetSettingsStoreForTests();
    expect(useKeybindingsStore.getState().overrides).toEqual({});
    expect(useSettingsStore.getState().defaultAgentId).toBeNull();

    // …then deserialize — the remaps + preferences come back exactly.
    deserializeWorkspace(saved);
    expect(useKeybindingsStore.getState().bindingFor("palette.open")).toBe("mod+shift+p");
    expect(useSettingsStore.getState().defaultAgentId).toBe("buffett");
    expect(useSettingsStore.getState().providerPreferenceOrder).toEqual([
      "groq",
      "ollama",
      "anthropic",
    ]);
    expect(useSettingsStore.getState().paletteRecentsEnabled).toBe(false);
  });

  it("deserializeWorkspace tolerates an older blob with no keybindings/settings", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useKeybindingsStore.getState().setBinding("palette.open", "mod+shift+p");

    // An old blob (no keybindingOverrides / settings) must leave the live
    // stores untouched, not wipe them.
    deserializeWorkspace({ name: "old", layout: LAYOUT_A, enabledModules: {} });

    expect(useKeybindingsStore.getState().bindingFor("palette.open")).toBe("mod+shift+p");
  });

  it("round-trips the agent mode, dock geometry, and model overrides (FR-003/004)", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    deserializeWorkspace({
      name: "saved",
      layout: LAYOUT_A,
      enabledModules: {},
      // A legacy persisted value (pre-collapse) — deliberately not a current
      // AgentMode; the restore path coerces it. Cast to feed it as an old blob.
      agentMode: "build" as never,
      autonomyMode: "auto",
      agentDock: { collapsed: true, width: 520 },
      modelOverrides: { anthropic: "claude-sonnet-4-6" },
      modelOverridesV: 2,
    });
    // Track B: a legacy "build" blob folds into the single inferred "agent" surface.
    expect(useAgentModeStore.getState().mode).toBe("agent");
    expect(useAgentAutonomyStore.getState().autonomy).toBe("auto");
    expect(useAgentDockStore.getState().collapsed).toBe(true);
    expect(useAgentDockStore.getState().width).toBe(520);
    expect(useModelSelectionStore.getState().overrides.anthropic).toBe("claude-sonnet-4-6");
  });

  it("keeps a current-blob live-catalog model override the static list can't know", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    // The persistence bug: a model the user picked from the LIVE catalog (e.g. a
    // newer OpenAI id) is NOT in the static KNOWN_MODELS_BY_PROVIDER list, so the
    // old restore pruned it back to the default. A current (trusted) blob must
    // restore it verbatim — the version gate already covers the legacy case.
    deserializeWorkspace({
      name: "current",
      layout: LAYOUT_A,
      enabledModules: {},
      modelOverrides: { openai: "gpt-5-pro-2026" },
      modelOverridesV: 2,
    });
    expect(useModelSelectionStore.getState().modelFor("openai")).toBe("gpt-5-pro-2026");
  });

  it("drops a legacy model override with no trust marker (llama3.1:8b shadowing fix)", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    // A blob written before the trust marker existed captured the then-default
    // ollama model as a pseudo-override. On restore it must be ignored so the
    // live default (qwen2.5:7b) is shown, not the stale captured id.
    deserializeWorkspace({
      name: "legacy",
      layout: LAYOUT_A,
      enabledModules: {},
      modelOverrides: { ollama: "llama3.1:8b" },
      // no modelOverridesV → legacy, untrusted
    });
    expect(useModelSelectionStore.getState().overrides.ollama).toBeUndefined();
    expect(useModelSelectionStore.getState().modelFor("ollama")).toBe(
      DEFAULT_MODEL_BY_PROVIDER.ollama,
    );
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

  it("createResearchSpace builds a per-stock cockpit and saves it under 'Research: TICKER'", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    resetChartCommandStoreForTests();
    useNotesStore.getState().fromBundle(null);

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 200 }));

    const name = await createResearchSpace("nvda");

    // Named + returned as a research space.
    expect(name).toBe("Research: NVDA");
    expect(researchSpaceName("nvda")).toBe("Research: NVDA");
    // Built a clean layout: cleared then tiled the research panels.
    expect(fakeApi.clear).toHaveBeenCalled();
    expect(fakeApi.addPanel).toHaveBeenCalled();
    const addedComponents = fakeApi.addPanel.mock.calls.map(
      (c) => (c[0] as { component?: string }).component,
    );
    expect(addedComponents).toContain("chart-panel");
    expect(addedComponents).toContain("brief-panel");
    expect(addedComponents).toContain("notes-panel");
    // Loaded the symbol into the chart (via the chart-command channel) + scoped
    // the notes to it.
    expect(useChartCommandStore.getState().command?.symbol).toBe("NVDA");
    expect(useNotesStore.getState().focusSymbol).toBe("NVDA");
    // Persisted under the research-space name.
    const saved = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(saved).toBeDefined();
    const body = JSON.parse(saved![1]?.body as string) as { name: string };
    expect(body.name).toBe("Research: NVDA");
  });

  it("createResearchSpace rejects an empty ticker", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    await expect(createResearchSpace("   ")).rejects.toThrow(/ticker is required/);
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
