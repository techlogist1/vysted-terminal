import type { SerializedDockview } from "dockview";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AGENT_DOCK_DEFAULT_WIDTH, useAgentDockStore } from "@/store/agent-dock";
import { useAgentSpacesStore } from "@/store/agent-spaces";
import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { resetBriefStoreForTests, useBriefStore } from "@/store/brief";
import { useAgentModeStore } from "@/store/agent-mode";
import { resetChartCommandStoreForTests, useChartCommandStore } from "@/store/chart-command";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useNotesStore } from "@/store/notes";
import { usePortfoliosStore } from "@/store/portfolios";
import { resetKeybindingsStoreForTests, useKeybindingsStore } from "@/store/keybindings";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { DEFAULT_MODEL_BY_PROVIDER, useModelSelectionStore } from "@/store/model-selection";
import { useModulesStore } from "@/store/modules";
import { useChatHistoryStore } from "@/store/chat-history";
import { useResearchSpacesStore } from "@/store/research-spaces";
import { useScreenerStore } from "@/store/screener";
import { resetSearchSettingsStoreForTests, useSearchSettingsStore } from "@/store/search-settings";
import { DEFAULT_SETTINGS, resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import type { DrawingSpec } from "../../types/drawings";

// The sidecar client reaches into Tauri's `invoke`; stub it so `getSidecarBaseUrl`
// resolves without a desktop runtime.
vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

// Keychain: the search-settings tier_b migration confirmation reads the
// OpenRouter slot; stub the Tauri-backed reads (default: no key stored) so the
// async demotion path is deterministic in jsdom.
vi.mock("@/lib/keychain", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/keychain")>();
  return {
    ...actual,
    getSecret: vi.fn(() => Promise.resolve(null)),
    setSecret: vi.fn(() => Promise.resolve()),
    deleteSecret: vi.fn(() => Promise.resolve()),
  };
});

import {
  autosaveLayout,
  createResearchSpace,
  deleteWorkspace,
  deserializeWorkspace,
  isResearchSpace,
  listWorkspaces,
  loadWorkspace,
  PERSISTED_SLICES,
  researchSpaceName,
  researchSymbolOf,
  resetWorkspacePersistenceForTests,
  restoreLastSessionOrDefault,
  saveWorkspace,
  serializeWorkspace,
  type SerializedWorkspace,
  wireAutosaveTriggers,
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
    useWorkspaceStore.setState({ name: "default", researchSymbol: null, dockviewApi: null });
    useChartDrawingsStore.setState({ byPanel: {}, views: {} });
    useLLMProvidersStore.setState({ defaultProviderId: "anthropic" });
    useSymbolsStore.setState({ entries: [{ symbol: "AAPL", assetClass: "equity" }] });
    useAgentModeStore.setState({ mode: "agent" });
    useAgentAutonomyStore.setState({ autonomy: "ask" });
    useAgentDockStore.setState({ collapsed: false, width: AGENT_DOCK_DEFAULT_WIDTH });
    useModelSelectionStore.setState({ overrides: {} });
    useResearchSpacesStore.setState({ byName: {} });
    useChatHistoryStore.getState().clear();
    resetKeybindingsStoreForTests();
    resetSettingsStoreForTests();
    resetSearchSettingsStoreForTests();
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
      chartViews: {},
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
      modelOverridesV: 3,
      keybindingOverrides: {},
      settings: DEFAULT_SETTINGS,
      searchSettings: {
        researchTier: "tier_a",
        searxngUrl: "",
        researchModels: {
          normal: "perplexity/sonar",
          deep: "perplexity/sonar-reasoning-pro",
          ultra: "perplexity/sonar-deep-research",
        },
      },
      brief: null,
      notes: { general: "", bySymbol: {}, focusSymbol: "" },
      // A non-research workspace omits `researchSymbol` but always carries the
      // (empty) per-space memory archive (S-19).
      researchSpaces: { byName: {} },
      savedScreens: [],
    });
  });

  it("round-trips keybinding overrides and the settings bundle (FR-037/038/039)", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });

    // Set some non-default keybindings + preferences, then serialize.
    useKeybindingsStore.getState().setBinding("palette.open", "mod+shift+p");
    useSettingsStore.getState().setDefaultAgentId("buffett");
    useSettingsStore.getState().setRegion("IN");

    const saved = serializeWorkspace("research");
    expect(saved.keybindingOverrides).toEqual({ "palette.open": "mod+shift+p" });
    expect(saved.settings?.defaultAgentId).toBe("buffett");
    expect(saved.settings?.region).toBe("IN");

    // Mutate the live state away…
    resetKeybindingsStoreForTests();
    resetSettingsStoreForTests();
    expect(useKeybindingsStore.getState().overrides).toEqual({});
    expect(useSettingsStore.getState().defaultAgentId).toBe(DEFAULT_SETTINGS.defaultAgentId);
    expect(useSettingsStore.getState().region).toBe(DEFAULT_SETTINGS.region);

    // …then deserialize — the remaps + preferences come back exactly.
    deserializeWorkspace(saved);
    expect(useKeybindingsStore.getState().bindingFor("palette.open")).toBe("mod+shift+p");
    expect(useSettingsStore.getState().defaultAgentId).toBe("buffett");
    expect(useSettingsStore.getState().region).toBe("IN");
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

  it("migrates pre-R9 searchSettings blobs into the two-tier vocabulary on restore", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });

    // Pre-R8 byok-exa → provisional tier_b; no OpenRouter key in the (stubbed)
    // keychain → the async confirmation demotes to tier_a.
    deserializeWorkspace({
      name: "pre-r8",
      layout: LAYOUT_A,
      enabledModules: {},
      searchSettings: { tier: "byok-exa", searxngUrl: "" } as never,
    });
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_b");
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_a");

    // local-searxng → tier_a, custom URL preserved.
    deserializeWorkspace({
      name: "pre-r8",
      layout: LAYOUT_A,
      enabledModules: {},
      searchSettings: { tier: "local-searxng", searxngUrl: "http://localhost:8080" } as never,
    });
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_a");
    expect(useSearchSettingsStore.getState().searxngUrl).toBe("http://localhost:8080");

    // R7-era t1/t2 ids fold into tier_a; the legacy fields die from the state.
    deserializeWorkspace({
      name: "r7",
      layout: LAYOUT_A,
      enabledModules: {},
      searchSettings: { tier: "native", searxngUrl: "", researchTier: "t2_searxng" } as never,
    });
    const state = useSearchSettingsStore.getState() as unknown as Record<string, unknown>;
    expect(state.researchTier).toBe("tier_a");
    expect(state.tier).toBeUndefined();
    expect(state.exaDirect).toBeUndefined();
    expect(state.hostedEngine).toBeUndefined();
  });

  it("an R9-era blob restores its researchTier + models verbatim — never rerouted", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    deserializeWorkspace({
      name: "r9",
      layout: LAYOUT_A,
      enabledModules: {},
      searchSettings: {
        researchTier: "tier_b",
        searxngUrl: "",
        researchModels: {
          normal: "perplexity/sonar",
          deep: "perplexity/sonar-reasoning-pro",
          ultra: "openai/o3-deep-research",
        },
      },
    });
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_b");
    expect(useSearchSettingsStore.getState().researchModels.ultra).toBe("openai/o3-deep-research");
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
      modelOverridesV: 3,
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
      modelOverridesV: 3,
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

  it("drops a model override from a pre-current trust version (the R3 v2->v3 bump)", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    // The R3 default-model change bumped MODEL_OVERRIDES_VERSION 2->3 so a blob that
    // captured the OLD keyless default (minimax/minimax-m3 at trust version 2) is now
    // STALE — its override drops so the workspace adopts the current default instead
    // of shadowing it.
    deserializeWorkspace({
      name: "pre-r3",
      layout: LAYOUT_A,
      enabledModules: {},
      modelOverrides: { openrouter: "minimax/minimax-m3" },
      modelOverridesV: 2, // an OLD numbered version < current → dropped
    });
    expect(useModelSelectionStore.getState().overrides.openrouter).toBeUndefined();
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

  it("opening a research space mid-stream stops the reply and parks it, stopped, under the chat tab (R15-CODE-FRONTEND-002)", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useAgentSpacesStore.setState({
      spaces: [{ id: "t1", title: "Chat 1" }],
      activeId: "t1",
      archived: {},
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 200 }));
    const chat = useChatHistoryStore.getState();
    chat.appendUserMessage("what about NVDA?");
    const replyId = chat.beginAssistantMessage({});
    chat.appendAssistantDelta(replyId, "Partial ");
    const abort = vi.fn();
    chat.setLiveAbort(abort);

    await createResearchSpace("nvda");

    expect(abort).toHaveBeenCalledTimes(1);
    expect(useChatHistoryStore.getState().streamingMessageId).toBeNull();
    const parked = useAgentSpacesStore.getState().archived.t1 ?? [];
    expect(parked.map((m) => m.content)).toEqual(["what about NVDA?", "Partial "]);
    expect(parked[1]).toMatchObject({ pending: false, stopped: true });
  });

  it("createResearchSpace rejects an empty ticker", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    await expect(createResearchSpace("   ")).rejects.toThrow(/ticker is required/);
  });

  it("a failed research-space save puts the cockpit back and surfaces the sidecar's reason (R15-CODE-FRONTEND-004)", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    resetChartCommandStoreForTests();
    useNotesStore.getState().fromBundle(null);
    useChatHistoryStore
      .getState()
      .loadMessages([{ id: "m1", role: "user", content: "ambient question", createdAt: 1 }]);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "No space left on device." }), { status: 500 }),
    );

    await expect(createResearchSpace("nvda")).rejects.toThrow(
      'Could not save workspace "Research: NVDA" (HTTP 500: No space left on device.).',
    );

    expect(fakeApi.fromJSON).toHaveBeenLastCalledWith(LAYOUT_A);
    expect(useWorkspaceStore.getState().researchSymbol).toBeNull();
    expect(useWorkspaceStore.getState().name).toBe("default");
    expect(useChatHistoryStore.getState().messages.map((m) => m.content)).toEqual([
      "ambient question",
    ]);
    expect(useResearchSpacesStore.getState().byName).toEqual({});
    expect(useNotesStore.getState().focusSymbol).toBe("");
    expect(useChartCommandStore.getState().command).toBeNull();
  });

  it("loading a named workspace never rolls back portfolios or notes (R15-CODE-FRONTEND-001)", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    usePortfoliosStore.getState().setAll([], undefined);
    useNotesStore.getState().fromBundle({ general: "week 1", bySymbol: {} });
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 200 }));
    await saveWorkspace("Swing");
    const saved = JSON.parse(String(fetchMock.mock.calls[0]![1]?.body)) as {
      workspace: SerializedWorkspace;
    };

    // Week 2: new holdings, new notes, a different layout.
    usePortfoliosStore.getState().addHolding("default", {
      symbol: "TCS",
      quantity: 5,
      costBasis: 3600,
      assetClass: "equity",
    });
    useNotesStore.getState().setGeneral("week 2");
    fakeApi.fromJSON(LAYOUT_B);
    fetchMock.mockResolvedValue(new Response(JSON.stringify(saved.workspace), { status: 200 }));

    await loadWorkspace("Swing");

    expect(fakeApi.current).toEqual(LAYOUT_A);
    expect(usePortfoliosStore.getState().portfolios[0].holdings.map((h) => h.symbol)).toEqual([
      "TCS",
    ]);
    expect(useNotesStore.getState().general).toBe("week 2");
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
      symbol: "SPY",
      timeframe: "1d",
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
      symbol: "TCS.NS",
      timeframe: "1wk",
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
    useChartDrawingsStore.setState({ byPanel: {}, views: {} });
    expect(useChartDrawingsStore.getState().getDrawings("chart-1")).toHaveLength(0);

    // …then reload — drawings come back exactly as saved.
    deserializeWorkspace(saved);
    expect(useChartDrawingsStore.getState().getDrawings("chart-1")).toEqual([trendline]);
    expect(useChartDrawingsStore.getState().getDrawings("chart-2")).toEqual([fib]);
  });

  it("round-trips each chart panel's view and adopts an older blob's drawings (R15-UI-020)", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    const view = { symbol: "RELIANCE.NS", timeframe: "1h", indicators: ["rsi"], compare: "TCS.NS" };
    useChartDrawingsStore.getState().setView("chart", view);

    const saved = serializeWorkspace("with-view");
    useChartDrawingsStore.setState({ views: {} });
    deserializeWorkspace(saved);
    expect(useChartDrawingsStore.getState().views["chart"]).toEqual(view);

    // A blob from before drawings carried symbol/timeframe: its drawings belong
    // to the panel's restored view, or the chart defaults when it has none.
    const legacyDrawing = {
      id: "old",
      panelId: "chart",
      kind: "horizontal-line",
      points: [{ time: null, price: 2450 }],
      style: { color: "#fff", lineWidth: 1 },
      createdAt: 0,
    };
    deserializeWorkspace({
      name: "old",
      layout: LAYOUT_A,
      enabledModules: {},
      chartViews: { chart: view },
      chartDrawings: { byPanel: { chart: [legacyDrawing], other: [legacyDrawing] } },
    } as unknown as SerializedWorkspace);
    const restored = useChartDrawingsStore.getState();
    expect(restored.getDrawings("chart")[0]).toMatchObject({
      symbol: "RELIANCE.NS",
      timeframe: "1h",
    });
    expect(restored.getDrawings("other")[0]).toMatchObject({ symbol: "SPY", timeframe: "1d" });

    // The oldest blobs have no chartViews: the panels open on their defaults.
    deserializeWorkspace({ name: "older", layout: LAYOUT_A, enabledModules: {} });
    expect(useChartDrawingsStore.getState().views).toEqual({});
  });

  it("loadWorkspace without chartDrawings clears any pre-existing drawings", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useModulesStore.setState({ enabled: { chart: true } });
    useChartDrawingsStore.getState().addDrawing("chart-x", {
      id: "leftover",
      panelId: "chart-x",
      symbol: "SPY",
      timeframe: "1d",
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

describe("research-space typed field + per-space memory (S-19)", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useWorkspaceStore.setState({ name: "default", researchSymbol: null, dockviewApi: null });
    useChartDrawingsStore.setState({ byPanel: {}, views: {} });
    useResearchSpacesStore.setState({ byName: {} });
    useChatHistoryStore.getState().clear();
    resetSettingsStoreForTests();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("detects a research space by the TYPED researchSymbol field, not the name", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });

    deserializeWorkspace({
      name: "Anything goes here", // NOT prefixed — detection rides the field
      layout: LAYOUT_A,
      enabledModules: {},
      researchSymbol: "nvda",
    });

    // The store's typed marker is set + normalised to upper-case.
    expect(useWorkspaceStore.getState().researchSymbol).toBe("NVDA");
  });

  it("BACK-COMPAT: an OLD prefix-only blob (no field) still resolves the symbol", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });

    // An old blob saved before the typed field existed — only the "Research: "
    // name prefix identifies it.
    deserializeWorkspace({
      name: researchSpaceName("MSFT"), // "Research: MSFT"
      layout: LAYOUT_A,
      enabledModules: {},
      // no researchSymbol field
    });

    expect(useWorkspaceStore.getState().researchSymbol).toBe("MSFT");
  });

  it("a literal 'Research: ' with a blank suffix is NOT a research space", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });

    deserializeWorkspace({ name: "Research: ", layout: LAYOUT_A, enabledModules: {} });
    expect(useWorkspaceStore.getState().researchSymbol).toBeNull();

    // A plain workspace clears the marker too.
    deserializeWorkspace({ name: "my cockpit", layout: LAYOUT_A, enabledModules: {} });
    expect(useWorkspaceStore.getState().researchSymbol).toBeNull();
  });

  it("isResearchSpace / researchSymbolOf prefer the field, fall back to the prefix", () => {
    // Typed field wins even when the name is non-prefixed.
    expect(researchSymbolOf({ name: "scratch", researchSymbol: "tsla" })).toBe("TSLA");
    expect(isResearchSpace({ name: "scratch", researchSymbol: "tsla" })).toBe(true);
    // Field absent → prefix fall-back recovers the symbol.
    expect(researchSymbolOf({ name: "Research: AMD" })).toBe("AMD");
    expect(isResearchSpace({ name: "Research: AMD" })).toBe(true);
    // Neither → not a research space.
    expect(researchSymbolOf({ name: "default" })).toBeNull();
    expect(isResearchSpace({ name: "default" })).toBe(false);
  });

  it("serializeWorkspace emits the typed field while IN a research space", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never, researchSymbol: "NVDA" });

    const saved = serializeWorkspace(researchSpaceName("NVDA"));
    expect(saved.researchSymbol).toBe("NVDA");
    // A plain workspace omits the field.
    useWorkspaceStore.setState({ researchSymbol: null });
    expect(serializeWorkspace("plain").researchSymbol).toBeUndefined();
  });

  it("AUTOSAVE path: memory keys by the canonical space name, not the file name", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never, researchSymbol: "NVDA" });
    useChatHistoryStore
      .getState()
      .loadMessages([{ id: "m1", role: "user", content: "nvda?", createdAt: 1 }]);

    // The autosave slot persists under "__autosave__" (not "Research: NVDA"), but
    // the per-space memory must still key under the canonical research name so it
    // converges with an explicit save / a typed-field reload.
    const autosaved = serializeWorkspace("__autosave__");
    expect(autosaved.researchSpaces?.byName[researchSpaceName("NVDA")]?.transcript).toHaveLength(1);
    // Reload via the TYPED field even under the neutral "__autosave__" name — the
    // archived transcript resolves and restores.
    useChatHistoryStore.getState().clear();
    useWorkspaceStore.setState({ researchSymbol: null });
    deserializeWorkspace({ ...autosaved, name: "default", researchSymbol: "NVDA" });
    expect(useChatHistoryStore.getState().messages.map((m) => m.content)).toEqual(["nvda?"]);
    expect(useWorkspaceStore.getState().researchSymbol).toBe("NVDA");
  });

  it("persists a research space's chat transcript and restores it on re-entry", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never, researchSymbol: "NVDA" });

    // Have a conversation in the NVDA research space.
    useChatHistoryStore.getState().loadMessages([
      { id: "m1", role: "user", content: "is NVDA overvalued?", createdAt: 1 },
      { id: "m2", role: "assistant", content: "It trades at a premium…", createdAt: 2 },
    ]);

    // Saving the workspace folds the live transcript into the space's memory.
    const saved = serializeWorkspace(researchSpaceName("NVDA"));
    expect(saved.researchSpaces?.byName[researchSpaceName("NVDA")]?.transcript).toHaveLength(2);
    expect(saved.researchSpaces?.byName[researchSpaceName("NVDA")]?.symbol).toBe("NVDA");

    // Wander off to a plain workspace — the live chat clears.
    deserializeWorkspace({ name: "scratch", layout: LAYOUT_B, enabledModules: {} });
    expect(useChatHistoryStore.getState().messages).toHaveLength(0);
    expect(useWorkspaceStore.getState().researchSymbol).toBeNull();

    // Re-enter the NVDA research space from the saved blob — the transcript
    // comes back, restoring the agent's per-space memory.
    deserializeWorkspace(saved);
    const restored = useChatHistoryStore.getState().messages;
    expect(restored.map((m) => m.content)).toEqual([
      "is NVDA overvalued?",
      "It trades at a premium…",
    ]);
    expect(useWorkspaceStore.getState().researchSymbol).toBe("NVDA");
  });

  it("switching from one research space to another swaps their transcripts", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never, researchSymbol: "NVDA" });

    // NVDA space transcript, saved.
    useChatHistoryStore
      .getState()
      .loadMessages([{ id: "n1", role: "user", content: "nvda question", createdAt: 1 }]);
    const nvda = serializeWorkspace(researchSpaceName("NVDA"));

    // Enter a fresh MSFT space (empty), have a different conversation, save it.
    deserializeWorkspace({
      name: researchSpaceName("MSFT"),
      layout: LAYOUT_B,
      enabledModules: {},
      researchSymbol: "MSFT",
      researchSpaces: nvda.researchSpaces,
    });
    expect(useChatHistoryStore.getState().messages).toHaveLength(0); // MSFT is fresh
    useChatHistoryStore
      .getState()
      .loadMessages([{ id: "s1", role: "user", content: "msft question", createdAt: 3 }]);
    const msft = serializeWorkspace(researchSpaceName("MSFT"));

    // Both transcripts are retained in the archive.
    expect(msft.researchSpaces?.byName[researchSpaceName("NVDA")]?.transcript[0]?.content).toBe(
      "nvda question",
    );
    expect(msft.researchSpaces?.byName[researchSpaceName("MSFT")]?.transcript[0]?.content).toBe(
      "msft question",
    );

    // Switch back to NVDA — its (not MSFT's) transcript is live again.
    deserializeWorkspace(nvda);
    expect(useChatHistoryStore.getState().messages.map((m) => m.content)).toEqual([
      "nvda question",
    ]);
  });
});

describe("restoreLastSessionOrDefault — boot-crash guards", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useWorkspaceStore.setState({ name: "default", dockviewApi: null });
    useChartDrawingsStore.setState({ byPanel: {}, views: {} });
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
    // No modules registered → "ghost-plugin-x" is an unknown panel component,
    // the case where dockview's fromJSON would throw mid-deserialize and
    // corrupt the grid. We must skip straight to applyDefaultLayout instead.
    stubFetchResolving({
      name: "x",
      layout: { grid: { root: "a" }, panels: { p1: { contentComponent: "ghost-plugin-x" } } },
      enabledModules: {},
    });

    const restored = await restoreLastSessionOrDefault(api as never, new Set(["chart"]));

    expect(restored).toBe(false);
    expect(api.fromJSON).not.toHaveBeenCalled(); // never risked the throwing deserialize
    expect(api.addPanel).toHaveBeenCalled(); // applyDefaultLayout ran instead
  });

  it("restores holdings, notes and watchlist even when the saved layout has an unregistered panel (R15-LIFECYCLE-002)", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    usePortfoliosStore.getState().setAll([], undefined);
    useNotesStore.getState().fromBundle(null);
    useSymbolsStore.setState({ entries: [{ symbol: "SPY", assetClass: "equity" }] });
    const fetchMock = vi.fn(
      async () =>
        ({
          ok: true,
          json: async () => ({
            name: "__autosave__",
            // A removed panel (the broker connect panel) is docked in the blob.
            layout: {
              grid: { root: "a" },
              panels: { broker: { contentComponent: "broker-connect-panel" } },
            },
            enabledModules: {},
            watchlist: [{ symbol: "INFY", assetClass: "equity" }],
            portfolios: {
              list: [
                {
                  id: "p1",
                  name: "Long-term",
                  holdings: [
                    {
                      id: "h1",
                      symbol: "INFY",
                      quantity: 10,
                      costBasis: 1500,
                      assetClass: "equity",
                    },
                  ],
                },
              ],
              activeId: "p1",
            },
            notes: { general: "thesis notes", bySymbol: { INFY: "margin watch" } },
          }),
        }) as unknown as Response,
    );
    vi.stubGlobal("fetch", fetchMock);

    const restored = await restoreLastSessionOrDefault(api as never, new Set(["chart"]));

    expect(restored).toBe(false);
    expect(api.fromJSON).not.toHaveBeenCalled(); // never risked the throwing deserialize
    expect(api.addPanel).toHaveBeenCalled(); // default layout applied instead
    const portfolios = usePortfoliosStore.getState();
    expect(portfolios.activeId).toBe("p1");
    expect(
      portfolios.portfolios[0].holdings.map((h) => [h.symbol, h.quantity, h.costBasis]),
    ).toEqual([["INFY", 10, 1500]]);
    expect(useNotesStore.getState().general).toBe("thesis notes");
    expect(useNotesStore.getState().bySymbol.INFY).toBe("margin watch");
    expect(useSymbolsStore.getState().entries.map((e) => e.symbol)).toEqual(["INFY"]);
    expect(useWorkspaceStore.getState().name).toBe("default");
    // Only the restore GET went out — no default-state POST overwrote the blob.
    const methods = (fetchMock.mock.calls as unknown as [string, RequestInit?][]).map(
      ([, init]) => init?.method ?? "GET",
    );
    expect(methods).toEqual(["GET"]);
  });

  it("loadWorkspace falls back to the default layout when no saved panel is registered, leaving the notes alone", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    useNotesStore.getState().fromBundle({ general: "live notes", bySymbol: {} });
    stubFetchResolving({
      name: "old",
      layout: { grid: { root: "a" }, panels: { p1: { contentComponent: "audit-log-viewer" } } },
      enabledModules: {},
      notes: { general: "stale notes", bySymbol: {} },
    });

    await loadWorkspace("old");

    expect(api.fromJSON).not.toHaveBeenCalled();
    expect(api.clear).toHaveBeenCalled();
    expect(useNotesStore.getState().general).toBe("live notes");
    expect(useWorkspaceStore.getState().name).toBe("old");
  });

  it("strips an unregistered panel from the saved layout and restores the rest, with every data slice and no autosave (R15-LIFECYCLE-002)", async () => {
    vi.useFakeTimers();
    resetWorkspacePersistenceForTests();
    const unwire = wireAutosaveTriggers();
    try {
      const api = createFakeDockviewApi(LAYOUT_A);
      useWorkspaceStore.setState({ dockviewApi: api as never });
      useModulesStore.setState({
        modules: [{ id: "chart", panelComponents: { "chart-panel": () => null } } as never],
      });
      usePortfoliosStore.getState().setAll([], undefined);
      useNotesStore.getState().fromBundle(null);
      useSymbolsStore.setState({ entries: [{ symbol: "SPY", assetClass: "equity" }] });
      const posts: unknown[] = [];
      vi.stubGlobal(
        "fetch",
        vi.fn(async (_url: string, init?: RequestInit) => {
          if (init?.method === "POST") {
            posts.push(init.body);
          }
          return {
            ok: true,
            json: async () => ({
              name: "__autosave__",
              layout: {
                grid: {
                  root: {
                    type: "branch",
                    size: 600,
                    data: [
                      {
                        type: "leaf",
                        size: 600,
                        data: { id: "g1", views: ["chart", "broker"], activeView: "broker" },
                      },
                      {
                        type: "leaf",
                        size: 300,
                        data: { id: "g2", views: ["orders"], activeView: "orders" },
                      },
                    ],
                  },
                  width: 900,
                  height: 600,
                  orientation: "HORIZONTAL",
                },
                panels: {
                  chart: { id: "chart", contentComponent: "chart-panel" },
                  broker: { id: "broker", contentComponent: "broker-connect-panel" },
                  orders: { id: "orders", contentComponent: "broker-order-entry-panel" },
                },
              },
              enabledModules: {},
              watchlist: [{ symbol: "INFY", assetClass: "equity" }],
              portfolios: {
                list: [
                  {
                    id: "p1",
                    name: "Long-term",
                    holdings: [
                      {
                        id: "h1",
                        symbol: "INFY",
                        quantity: 10,
                        costBasis: 1500,
                        assetClass: "equity",
                      },
                    ],
                  },
                ],
                activeId: "p1",
              },
              notes: { general: "thesis notes", bySymbol: { INFY: "margin watch" } },
            }),
          } as unknown as Response;
        }),
      );

      const restored = await restoreLastSessionOrDefault(api as never, new Set(["chart"]));
      await vi.advanceTimersByTimeAsync(5_000);

      expect(restored).toBe(true);
      expect(api.fromJSON).toHaveBeenCalledOnce();
      const applied = api.fromJSON.mock.calls[0]![0] as unknown as {
        panels: Record<string, unknown>;
        grid: { root: { data: { data: { views: string[]; activeView?: string } }[] } };
      };
      expect(Object.keys(applied.panels)).toEqual(["chart"]);
      expect(applied.grid.root.data.map((leaf) => leaf.data)).toEqual([
        { id: "g1", views: ["chart"], activeView: "chart" },
      ]);
      expect(
        usePortfoliosStore
          .getState()
          .portfolios[0].holdings.map((h) => [h.symbol, h.quantity, h.costBasis]),
      ).toEqual([["INFY", 10, 1500]]);
      expect(useNotesStore.getState().bySymbol.INFY).toBe("margin watch");
      expect(useSymbolsStore.getState().entries.map((e) => e.symbol)).toEqual(["INFY"]);
      expect(posts).toEqual([]);
    } finally {
      unwire();
      resetWorkspacePersistenceForTests();
      vi.useRealTimers();
    }
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

// ── brief restore is ALWAYS archival (R10 D39) ──────────────────────────────

describe("workspace restore archives the brief (R10 D39)", () => {
  it("a restored blob's brief lands archived('restored') — never as current", () => {
    resetBriefStoreForTests();
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    deserializeWorkspace({
      name: "x",
      layout: LAYOUT_A,
      enabledModules: {},
      brief: {
        query: "reliance Q4",
        symbol: "RELIANCE.NS",
        mode: "DEEP",
        depth: "deep",
        markdown: "## report [1]",
        sources: [{ url: "https://nseindia.com/x", title: "filing", excerpt: "" }],
        sourceCount: 1,
        webAvailable: true,
        execution: { runId: "run-old", requestedDepth: "deep", loop: "iter" },
        createdAt: 1_700_000_000_000,
      },
    });
    const panel = useBriefStore.getState().panel;
    expect(panel.phase).toBe("archived");
    expect(panel.phase === "archived" && panel.reason).toBe("restored");
    // The mirror still serves the artifact for legacy consumers + re-serialize.
    expect(useBriefStore.getState().brief?.query).toBe("reliance Q4");
    resetBriefStoreForTests();
  });

  it("an OLDER blob's brief (no execution record) restores fine — archived too", () => {
    resetBriefStoreForTests();
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    deserializeWorkspace({
      name: "x",
      layout: LAYOUT_A,
      enabledModules: {},
      brief: {
        query: "legacy brief",
        mode: "FAST",
        markdown: "## old",
        sources: [],
        sourceCount: 0,
        webAvailable: false,
        createdAt: 1_600_000_000_000,
      },
    });
    expect(useBriefStore.getState().panel.phase).toBe("archived");
    expect(useBriefStore.getState().brief?.query).toBe("legacy brief");
    resetBriefStoreForTests();
  });
});

// ── one persisted-slice registry drives payload, restore and autosave ───────

/** The keys `SerializedWorkspace` declares (its index signature excluded). */
type DeclaredWorkspaceKey = keyof {
  [K in keyof SerializedWorkspace as string extends K ? never : number extends K ? never : K]: true;
};

/** Every declared key; the compiler rejects this map when the interface gains one. */
const DECLARED_KEYS: Record<DeclaredWorkspaceKey, true> = {
  name: true,
  layout: true,
  enabledModules: true,
  chartDrawings: true,
  chartViews: true,
  defaultProviderId: true,
  watchlist: true,
  portfolios: true,
  agentMode: true,
  autonomyMode: true,
  agentDock: true,
  modelOverrides: true,
  modelOverridesV: true,
  keybindingOverrides: true,
  settings: true,
  searchSettings: true,
  brief: true,
  notes: true,
  researchSymbol: true,
  researchSpaces: true,
  savedScreens: true,
};

/** Route a stubbed sidecar: GET `/workspace/__autosave__` answers `autosave`
 *  (404 when null), every POST body is captured, any other GET is a 404. */
function stubSidecar(autosave: SerializedWorkspace | null): SerializedWorkspace[] {
  const posts: SerializedWorkspace[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        posts.push((JSON.parse(String(init.body)) as { workspace: SerializedWorkspace }).workspace);
        return { ok: true, status: 200, json: async () => ({}) } as unknown as Response;
      }
      if (autosave && String(url).endsWith("/workspace/__autosave__")) {
        return { ok: true, status: 200, json: async () => autosave } as unknown as Response;
      }
      return { ok: false, status: 404, json: async () => ({}) } as unknown as Response;
    }),
  );
  return posts;
}

describe("persisted-slice registry + gated autosave (R15-LIFECYCLE-003, CODE-FRONTEND-005/018)", () => {
  let unwire: (() => void) | null = null;

  beforeEach(() => {
    vi.useFakeTimers();
    resetWorkspacePersistenceForTests();
    useModulesStore.setState({ modules: [], enabled: {} });
    useWorkspaceStore.setState({ name: "default", researchSymbol: null, dockviewApi: null });
    useChartDrawingsStore.setState({ byPanel: {}, views: {} });
    useLLMProvidersStore.setState({ defaultProviderId: "anthropic" });
    useSymbolsStore.setState({ entries: [{ symbol: "AAPL", assetClass: "equity" }] });
    usePortfoliosStore.getState().setAll([], undefined);
    useAgentModeStore.setState({ mode: "agent" });
    useAgentAutonomyStore.setState({ autonomy: "ask" });
    useAgentDockStore.setState({ collapsed: false, width: AGENT_DOCK_DEFAULT_WIDTH });
    useModelSelectionStore.setState({ overrides: {} });
    useResearchSpacesStore.setState({ byName: {} });
    useChatHistoryStore.getState().clear();
    useNotesStore.getState().fromBundle(null);
    useScreenerStore.getState().__resetForTests();
    resetBriefStoreForTests();
    resetKeybindingsStoreForTests();
    resetSettingsStoreForTests();
    resetSearchSettingsStoreForTests();
  });

  afterEach(() => {
    unwire?.();
    unwire = null;
    resetWorkspacePersistenceForTests();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows a not-saving error after 3 failed autosaves in a row and clears it on success (R15-CODE-FRONTEND-019)", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never, lastAutosaveError: null });
    stubSidecar(null);
    await restoreLastSessionOrDefault(api as never, new Set());
    let ok = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        ok
          ? ({ ok: true, status: 200, json: async () => ({}) } as unknown as Response)
          : ({
              ok: false,
              status: 507,
              json: async () => ({ detail: "Could not write the workspace: Disk full" }),
            } as unknown as Response),
      ),
    );
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const failOnce = async () => {
      autosaveLayout();
      await vi.advanceTimersByTimeAsync(600);
    };

    await failOnce();
    await failOnce();
    expect(useWorkspaceStore.getState().lastAutosaveError).toBeNull();
    await failOnce();
    expect(useWorkspaceStore.getState().lastAutosaveError).toBe(
      "Autosave failed (HTTP 507: Could not write the workspace: Disk full).",
    );

    ok = true;
    await failOnce();
    expect(useWorkspaceStore.getState().lastAutosaveError).toBeNull();
  });

  it("hides the reserved __autosave__ slot and refuses reserved names (R15-UI-046)", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ["__autosave__", "Research: NVDA", "swing"],
    }));
    vi.stubGlobal("fetch", fetchMock);

    expect(await listWorkspaces()).toEqual(["Research: NVDA", "swing"]);
    fetchMock.mockClear();
    await expect(saveWorkspace("__mine")).rejects.toThrow(/reserved/);
    await expect(deleteWorkspace("__autosave__")).rejects.toThrow(/reserved/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("autosaves nothing during the launch restore; the first save after it carries the research space", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    const posts = stubSidecar({
      name: "__autosave__",
      layout: LAYOUT_A,
      enabledModules: {},
      watchlist: [{ symbol: "RELIANCE", assetClass: "equity" }],
      portfolios: {
        list: [
          {
            id: "pf-1",
            name: "Core",
            holdings: [
              { id: "h1", symbol: "TCS", quantity: 10, costBasis: 3500, assetClass: "equity" },
            ],
          },
        ],
        activeId: "pf-1",
      },
      notes: { general: "thesis", bySymbol: { TCS: "buy < 3400" }, focusSymbol: "TCS" },
      researchSymbol: "TCS",
      researchSpaces: {
        byName: {
          "Research: TCS": {
            symbol: "TCS",
            transcript: [{ role: "user", content: "what is TCS margin", createdAt: 1 }],
            updatedAt: 1,
          },
        },
      },
    });
    // Wired at mount, BEFORE the restore resolves — exactly as page.tsx does.
    unwire = wireAutosaveTriggers();

    await restoreLastSessionOrDefault(api as never, new Set(["chart"]));
    await vi.advanceTimersByTimeAsync(5_000);
    expect(posts).toHaveLength(0);

    useSymbolsStore.getState().addSymbol("INFY", "equity");
    await vi.advanceTimersByTimeAsync(5_000);

    expect(posts).toHaveLength(1);
    const [first] = posts;
    expect(first.researchSymbol).toBe("TCS");
    expect(first.researchSpaces?.byName["Research: TCS"]?.transcript).toHaveLength(1);
    expect(first.portfolios?.list[0]?.holdings.map((h) => h.symbol)).toEqual(["TCS"]);
    expect(first.notes?.general).toBe("thesis");
    expect(first.watchlist?.map((e) => e.symbol)).toEqual(["RELIANCE", "INFY"]);
  });

  it("every declared blob key is written by a registered slice, and each slice's change autosaves", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never, researchSymbol: "NVDA" });
    const written = new Set(PERSISTED_SLICES.flatMap((slice) => Object.keys(slice.read())));
    const declared = Object.keys(DECLARED_KEYS).filter((key) => key !== "name" && key !== "layout");
    expect([...written].sort()).toEqual(declared.sort());
    useWorkspaceStore.setState({ researchSymbol: null });

    const posts = stubSidecar(null);
    await restoreLastSessionOrDefault(api as never, new Set());
    unwire = wireAutosaveTriggers();
    const mutations: Record<string, (() => void)[]> = {
      enabledModules: [() => useModulesStore.getState().setEnabledMap({ chart: false })],
      chartDrawings: [
        () =>
          useChartDrawingsStore.getState().addDrawing("chart", {
            id: "d1",
            panelId: "chart",
            symbol: "SPY",
            timeframe: "1d",
            kind: "trendline",
            points: [
              { time: 1, price: 1 },
              { time: 2, price: 2 },
            ],
            style: { color: "#fff", lineWidth: 1 },
            createdAt: 0,
          }),
      ],
      chartViews: [
        () =>
          useChartDrawingsStore
            .getState()
            .setView("chart", { symbol: "TCS.NS", timeframe: "1d", indicators: [], compare: null }),
      ],
      defaultProviderId: [() => useLLMProvidersStore.getState().setDefaultProviderId("openrouter")],
      watchlist: [() => useSymbolsStore.getState().addSymbol("INFY", "equity")],
      portfolios: [
        () => usePortfoliosStore.getState().createPortfolio("Swing"),
        () => usePortfoliosStore.getState().setActive("default"),
      ],
      agentMode: [() => useAgentModeStore.getState().setMode("delegate")],
      autonomyMode: [() => useAgentAutonomyStore.getState().setAutonomy("auto")],
      agentDock: [
        () => useAgentDockStore.getState().setCollapsed(true),
        () => useAgentDockStore.getState().setWidth(AGENT_DOCK_DEFAULT_WIDTH + 40),
      ],
      modelOverrides: [
        () => useModelSelectionStore.getState().setModel("anthropic", "claude-sonnet-4-6"),
      ],
      keybindingOverrides: [
        () => useKeybindingsStore.getState().setBinding("palette.open", "mod+shift+p"),
      ],
      settings: [
        () => useSettingsStore.getState().setDefaultAgentId("buffett"),
        () => useSettingsStore.getState().setRegion("US"),
        () => useSettingsStore.getState().setDeepResearchBackend("perplexity"),
      ],
      searchSettings: [
        () => useSearchSettingsStore.getState().setResearchTier("tier_b"),
        () => useSearchSettingsStore.getState().setSearxngUrl("http://127.0.0.1:8080"),
        () =>
          useSearchSettingsStore
            .getState()
            .setResearchModel("deep", "openai/o4-mini-deep-research"),
      ],
      brief: [
        () =>
          useBriefStore.getState().setBrief({
            query: "q",
            mode: "FAST",
            markdown: "m",
            sources: [],
            sourceCount: 0,
            webAvailable: false,
            createdAt: 1,
          }),
        () => useBriefStore.getState().clearBrief(),
      ],
      notes: [
        () => useNotesStore.getState().setGeneral("thesis"),
        () => useNotesStore.getState().setSymbolNote("NVDA", "watch margins"),
        () => useNotesStore.getState().setFocusSymbol("NVDA"),
      ],
      savedScreens: [() => useScreenerStore.getState().saveScreen("Cheap tech")],
      researchSpaces: [
        () =>
          useResearchSpacesStore.getState().replaceAll({
            byName: { "Research: AMD": { symbol: "AMD", transcript: [], updatedAt: 1 } },
          }),
      ],
      researchSymbol: [() => useWorkspaceStore.getState().setResearchSymbol("NVDA")],
    };

    for (const slice of PERSISTED_SLICES) {
      expect(mutations[slice.key], `no mutation covers slice ${slice.key}`).toBeDefined();
      for (const mutate of mutations[slice.key]) {
        const before = posts.length;
        mutate();
        await vi.advanceTimersByTimeAsync(1_000);
        expect(posts.length, `slice ${slice.key} did not autosave`).toBeGreaterThan(before);
      }
    }
  });

  it("a setter that rejects its input schedules no autosave", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    const posts = stubSidecar(null);
    await restoreLastSessionOrDefault(api as never, new Set());
    unwire = wireAutosaveTriggers();
    await vi.advanceTimersByTimeAsync(1_000);
    const before = posts.length;

    useSearchSettingsStore.getState().setResearchModel("deep", "has spaces!!");
    await vi.advanceTimersByTimeAsync(1_000);

    expect(posts).toHaveLength(before);
  });

  it("saved screens survive serialize, a fresh store and deserialize", () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    useScreenerStore.getState().saveScreen("Cheap tech");

    const saved = serializeWorkspace("screens");
    useScreenerStore.getState().__resetForTests();
    expect(useScreenerStore.getState().savedScreens).toEqual([]);
    deserializeWorkspace(saved);

    const screens = useScreenerStore.getState().savedScreens;
    expect(screens.map((screen) => screen.name)).toEqual(["Cheap tech"]);
    expect(screens[0]?.universe).toBe("sp500");
  });
});

// ── one-time import of the pre-blob positions ledger (R15-LIFECYCLE-009) ───

describe("legacy positions import (R15-LIFECYCLE-009)", () => {
  /** v0.8.0 rows, as `GET /portfolio/positions` returns them. */
  const LEDGER = [
    {
      id: 1,
      symbol: "RELIANCE.NS",
      quantity: 10,
      cost_basis: 2890.55,
      asset_class: "equity",
      opened_at: null,
      note: "core",
    },
    {
      id: 2,
      symbol: "TCS.NS",
      quantity: 5,
      cost_basis: 3400,
      asset_class: "equity",
      opened_at: null,
      note: null,
    },
    {
      id: 3,
      symbol: "BTC/USDT",
      quantity: 0.05,
      cost_basis: 60000,
      asset_class: "crypto",
      opened_at: null,
      note: null,
    },
  ];

  /** Stub the sidecar: the autosave slot answers `autosave` (404 when null),
   *  the ledger answers LEDGER; returns every request as "METHOD path". */
  function stubLedger(autosave: unknown, posts: SerializedWorkspace[]): string[] {
    const requests: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const path = new URL(url).pathname;
        requests.push(`${init?.method ?? "GET"} ${path}`);
        if (init?.method === "POST") {
          posts.push(
            (JSON.parse(String(init.body)) as { workspace: SerializedWorkspace }).workspace,
          );
          return { ok: true, status: 200, json: async () => ({}) } as unknown as Response;
        }
        if (path === "/portfolio/positions") {
          return { ok: true, status: 200, json: async () => LEDGER } as unknown as Response;
        }
        if (path === "/workspace/__autosave__" && autosave) {
          return { ok: true, status: 200, json: async () => autosave } as unknown as Response;
        }
        return { ok: false, status: 404, json: async () => ({}) } as unknown as Response;
      }),
    );
    return requests;
  }

  const holdings = () =>
    usePortfoliosStore
      .getState()
      .portfolios.flatMap((p) => p.holdings)
      .map((h) => [h.symbol, h.quantity, h.costBasis, h.assetClass, h.note ?? null]);

  beforeEach(() => {
    vi.useFakeTimers();
    resetWorkspacePersistenceForTests();
    useModulesStore.setState({ modules: [], enabled: {} });
    useWorkspaceStore.setState({ name: "default", researchSymbol: null, dockviewApi: null });
    usePortfoliosStore.getState().setAll([], undefined);
  });

  afterEach(() => {
    resetWorkspacePersistenceForTests();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("imports the ledger once into a blob that never carried portfolios, and saves the import", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    const posts: SerializedWorkspace[] = [];
    const legacyBlob = { name: "__autosave__", layout: LAYOUT_A, enabledModules: {} };
    stubLedger(legacyBlob, posts);

    await restoreLastSessionOrDefault(api as never, new Set(["chart"]));
    await vi.advanceTimersByTimeAsync(1_000);

    const expected = [
      ["RELIANCE.NS", 10, 2890.55, "equity", "core"],
      ["TCS.NS", 5, 3400, "equity", null],
      ["BTC/USDT", 0.05, 60000, "crypto", null],
    ];
    expect(holdings()).toEqual(expected);
    expect(posts).toHaveLength(1);
    expect(posts[0].portfolios?.list.flatMap((p) => p.holdings).map((h) => h.symbol)).toEqual([
      "RELIANCE.NS",
      "TCS.NS",
      "BTC/USDT",
    ]);

    // Relaunch on the same portfolios-less blob (quit before the save landed):
    // the import runs again but never duplicates.
    resetWorkspacePersistenceForTests();
    await restoreLastSessionOrDefault(api as never, new Set(["chart"]));
    expect(holdings()).toEqual(expected);

    // Relaunch on the saved blob: it carries portfolios, so the ledger is not read.
    resetWorkspacePersistenceForTests();
    usePortfoliosStore.getState().setAll([], undefined);
    const requests = stubLedger(posts[0], []);
    await restoreLastSessionOrDefault(api as never, new Set(["chart"]));
    expect(requests).toEqual(["GET /workspace/__autosave__"]);
    expect(holdings()).toEqual(expected);
  });

  it("never reads the ledger for a blob whose portfolios the user emptied", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    const requests = stubLedger(
      {
        name: "__autosave__",
        layout: LAYOUT_A,
        enabledModules: {},
        portfolios: {
          list: [{ id: "default", name: "Portfolio", holdings: [] }],
          activeId: "default",
        },
      },
      [],
    );

    await restoreLastSessionOrDefault(api as never, new Set(["chart"]));

    expect(requests).toEqual(["GET /workspace/__autosave__"]);
    expect(holdings()).toEqual([]);
  });
});
