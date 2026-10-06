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
  migrateWorkspace,
  PERSISTED_SLICES,
  researchSpaceName,
  researchSymbolOf,
  resetWorkspacePersistenceForTests,
  restoreLastSessionOrDefault,
  saveWorkspace,
  serializeWorkspace,
  type SerializedWorkspace,
  wireAutosaveTriggers,
  WORKSPACE_SCHEMA_VERSION,
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

describe("vs0 fresh variants", () => {
  let unwire: (() => void) | null = null;
  beforeEach(() => {
    vi.useFakeTimers();
    resetWorkspacePersistenceForTests();
    useModulesStore.setState({ modules: [], enabled: {} });
    useWorkspaceStore.setState({ name: "default", researchSymbol: null, dockviewApi: null });
    useSymbolsStore.setState({ entries: [{ symbol: "AAPL", assetClass: "equity" }] });
    usePortfoliosStore.getState().setAll([], undefined);
    useResearchSpacesStore.setState({ byName: {} });
    useChatHistoryStore.getState().clear();
    useNotesStore.getState().fromBundle(null);
    useScreenerStore.getState().__resetForTests();
  });
  afterEach(() => {
    unwire?.();
    unwire = null;
    resetWorkspacePersistenceForTests();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  function blob(): SerializedWorkspace {
    useScreenerStore.getState().saveScreen("Deep value IN");
    const savedScreens = useScreenerStore.getState().savedScreens;
    useScreenerStore.getState().__resetForTests();
    return {
      schemaVersion: WORKSPACE_SCHEMA_VERSION,
      name: "__autosave__",
      // no contentComponent -> not stripped -> fromJSON is attempted
      layout: { grid: { root: "zz" }, panels: { weird: {} } } as unknown as SerializedDockview,
      enabledModules: {},
      watchlist: [{ symbol: "TCS", assetClass: "equity" }],
      portfolios: {
        list: [{ id: "p9", name: "IN", holdings: [{ id: "h", symbol: "TCS", quantity: 3, costBasis: 3100, assetClass: "equity" }] }],
        activeId: "p9",
      },
      notes: { general: "kept note", bySymbol: {} },
      savedScreens,
      researchSpaces: { byName: {} },
      researchSymbol: "NVDA",
    } as unknown as SerializedWorkspace;
  }

  it("LIFECYCLE-002 fresh: fromJSON THROWS on a registered layout -> every data slice still restored, no default POST", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    api.fromJSON.mockImplementation(() => {
      throw new Error("dockview exploded");
    });
    useWorkspaceStore.setState({ dockviewApi: api as never });
    const b = blob();
    const posts = stubSidecar(b);
    vi.spyOn(console, "warn").mockImplementation(() => {});
    unwire = wireAutosaveTriggers();
    const restored = await restoreLastSessionOrDefault(api as never, new Set(["chart"]));
    expect(restored).toBe(false);
    expect(api.fromJSON).toHaveBeenCalled();
    expect(usePortfoliosStore.getState().portfolios[0].holdings.map((h) => h.symbol)).toEqual(["TCS"]);
    expect(useNotesStore.getState().general).toBe("kept note");
    expect(useSymbolsStore.getState().entries.map((e) => e.symbol)).toEqual(["TCS"]);
    expect(useScreenerStore.getState().savedScreens.map((s) => s.name)).toEqual(["Deep value IN"]);
    expect(posts.length).toBe(0);
    // any later save carries the restored data, never defaults
    useSymbolsStore.setState({ entries: [...useSymbolsStore.getState().entries, { symbol: "INFY", assetClass: "equity" }] });
    await vi.advanceTimersByTimeAsync(700);
    expect(posts.length).toBe(1);
    expect((posts[0] as unknown as { portfolios: { list: { holdings: unknown[] }[] } }).portfolios.list[0].holdings.length).toBe(1);
    expect((posts[0] as unknown as { notes: { general: string } }).notes.general).toBe("kept note");
  });

  it("LIFECYCLE-003 fresh: zero POSTs during restore; a burst after restore coalesces into ONE POST with researchSymbol + archive", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    const b = blob();
    (b as unknown as { layout: unknown }).layout = LAYOUT_B;
    (b as unknown as { researchSpaces: unknown }).researchSpaces = {
      byName: { "Research: NVDA": { symbol: "NVDA", transcript: [{ role: "user", content: "earlier q", createdAt: 1 }], summary: "s", updatedAt: 1 } },
    };
    const posts = stubSidecar(b);
    unwire = wireAutosaveTriggers();
    // a change fired BEFORE the restore (pre-restore window) must not save
    useSymbolsStore.setState({ entries: [{ symbol: "PRE", assetClass: "equity" }] });
    await vi.advanceTimersByTimeAsync(700);
    expect(posts.length).toBe(0);
    await restoreLastSessionOrDefault(api as never, new Set(["chart"]));
    await vi.advanceTimersByTimeAsync(700);
    const duringRestore = posts.length;
    for (let i = 0; i < 5; i++) {
      useNotesStore.getState().fromBundle({ general: `n${i}`, bySymbol: {} });
      await vi.advanceTimersByTimeAsync(100);
    }
    await vi.advanceTimersByTimeAsync(700);
    const after = posts.slice(duringRestore);
    console.log("POSTS during restore:", duringRestore, "after burst:", after.length);
    expect(duringRestore).toBe(0);
    expect(after.length).toBe(1);
    const p = after[0] as unknown as { researchSymbol?: string; researchSpaces: { byName: Record<string, unknown> }; notes: { general: string } };
    expect(p.researchSymbol).toBe("NVDA");
    expect(Object.keys(p.researchSpaces.byName)).toContain("Research: NVDA");
    expect(p.notes.general).toBe("n4");
  });

  it("FRONTEND-018 fresh: a saved screen survives a relaunch AND a named-workspace load", async () => {
    const api = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: api as never });
    const b = blob();
    stubSidecar({ ...b, layout: LAYOUT_B, researchSymbol: undefined } as unknown as SerializedWorkspace);
    await restoreLastSessionOrDefault(api as never, new Set(["chart"]));
    expect(useScreenerStore.getState().savedScreens.map((s) => s.name)).toEqual(["Deep value IN"]);
    stubSidecar({ schemaVersion: WORKSPACE_SCHEMA_VERSION, name: "swing", layout: LAYOUT_A, enabledModules: {} } as unknown as SerializedWorkspace);
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ schemaVersion: WORKSPACE_SCHEMA_VERSION, name: "swing", layout: LAYOUT_A, enabledModules: {}, savedScreens: [] }) }) as unknown as Response));
    await loadWorkspace("swing");
    console.log("screens after named load:", JSON.stringify(useScreenerStore.getState().savedScreens.map((s) => s.name)));
    expect(useScreenerStore.getState().savedScreens.map((s) => s.name)).toEqual(["Deep value IN"]);
  });
});
