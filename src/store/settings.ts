/**
 * Settings store — the local preferences bundle (FR-037/FR-038, SC-011).
 *
 * Everything here is a *preference* the user can set in the Settings panel and
 * carry between machines via export/import. It is deliberately separate from:
 *  - keybinding overrides (own store, `keybindings.ts`, persisted alongside),
 *  - secrets (OS keychain only — NEVER in this bundle, FR-036/SC-010),
 *  - the dockview layout + module-enabled map (the workspace blob proper).
 *
 * R9 (settings-truth): every field here has a DEMONSTRABLE consumer — a
 * preference that nothing reads is theater and dies (defect V6 and friends).
 * The killed fields (`themeKnobs`, `paletteRecentsEnabled`,
 * `paletteScopedToPanel`, `starterCockpitPanelIds`, `panelDefaults`,
 * `providerPreferenceOrder`) are silently DROPPED from older blobs on restore
 * — see the kill list in `docs/redesign/verification/R9_DEFECT_CATALOGUE.md`.
 * What survives:
 *  - `defaultAgentId` — now actually wired: it seeds the active-agent store at
 *    boot restore and applies immediately when changed in Settings;
 *  - `region` — locale/currency formatting, the `X-Vysted-Region` header, the
 *    region-first news feed;
 *  - `deepResearchBackend` — the deep-research engine selection threaded into
 *    agent-invoke requests (`native` is the only user-facing engine);
 *  - `providerOrder` — the chat's provider fallback order (ChatSidebar);
 *  - `startLayout` — which cockpit the launch opens on (PanelHost);
 *  - `paletteShowRecents` / `paletteSymbolScope` — the command palette's
 *    recents-first empty state and its instrument-search scope (CommandPalette).
 * (R15-UI-087 rebuilt FR-038's preference depth WITH its consumers; the killed
 * legacy names stay dropped — their written-never-read values carry no intent.)
 *
 * Persistence: the bundle rides the workspace blob; its autosave trigger is
 * the `settings` slice in `src/lib/workspace.ts` `PERSISTED_SLICES`.
 *
 * SSR-safe: no `window`/`navigator` at module load.
 */

import { create } from "zustand";

import { type Region, DEFAULT_REGION, isRegion } from "@/lib/region";
import { DEFAULT_AGENT_ID, useActiveAgentStore } from "@/store/active-agent";
import { DEFAULT_CHART_SYMBOL, DEFAULT_CHART_TIMEFRAME } from "@/store/chart-drawings";
import { REGISTRY_PROVIDERS } from "@/store/model-selection";
import type { LLMProviderId } from "../../types/ai";

/**
 * The DEEP research engine the agent drives (Track 5). `native` is Vysted's own
 * bounded IterResearch loop on the configured model — always available, no extra
 * key. `perplexity` is an opt-in, paid backend the agent can select with its own
 * Perplexity key; it is never auto-selected and is not offered in Settings (native
 * is the only user-facing engine).
 */
export type DeepResearchBackend = "native" | "perplexity";

/**
 * The chart's default symbol/timeframe/indicators (R15-UI-048) — what a FRESH
 * chart panel (no persisted per-panel view) opens on. Set from the chart
 * toolbar's "Make default" control; read once at panel mount.
 */
export interface ChartDefaults {
  symbol: string;
  timeframe: string;
  indicators: string[];
}

/** Which instruments the command palette searches: the watchlist only, or the
 *  watchlist plus the live symbol resolver (every listed instrument). */
export type PaletteSymbolScope = "watchlist" | "all";

/**
 * The serialisable preferences bundle. This is exactly what rides the workspace
 * blob's `settings` field and what export/import round-trips. NO secrets.
 */
export interface SettingsBundle {
  /**
   * Default agent/persona id the chat surface starts on each session.
   * `null` = raw chat (no persona). On the wire an explicit raw-chat choice is
   * serialized as {@link RAW_CHAT_SENTINEL} so it stays distinguishable from a
   * legacy blob's dead `null` (the pre-R9 control was written-never-read; its
   * `null` was a meaningless seed and coerces to the Copilot default).
   */
  defaultAgentId: string | null;
  /**
   * Region / locale (Pass A item 8 seam). Defaults to `US`; drives locale-aware
   * formatting today and is the read point a later pass uses to make data/feeds
   * region-first. See `src/lib/region.ts` + EXTENSION_SEAMS.md.
   */
  region: Region;
  /** The selected DEEP research engine (Track 5). Default `native` — Vysted's own
   *  IterResearch loop. */
  deepResearchBackend: DeepResearchBackend;
  /** The chart's default symbol/timeframe/indicators (R15-UI-048). */
  chartDefaults: ChartDefaults;
  /** Provider preference order (FR-038): when a chat turn's provider fails
   *  before answering, the next configured provider in this order answers. */
  providerOrder: LLMProviderId[];
  /** The cockpit the launch opens on: `null` = the last session, else the name
   *  of a saved layout (a missing one falls back to the last session). */
  startLayout: string | null;
  /** Show the "Recent" group first on an empty palette query. */
  paletteShowRecents: boolean;
  /** Which instruments a palette query searches. */
  paletteSymbolScope: PaletteSymbolScope;
}

/**
 * Wire form of an EXPLICIT raw-chat default. A legacy blob's `defaultAgentId:
 * null` predates the wiring (the control was dead, so its null carried no
 * intent) and coerces to the Copilot default; a user who deliberately picks
 * "Raw chat" after R9 persists this sentinel instead, so the choice survives
 * the round-trip unambiguously.
 */
export const RAW_CHAT_SENTINEL = "__raw-chat__";

/** The immutable seed bundle — what a fresh install (or a reset) starts from. */
export const DEFAULT_SETTINGS: Readonly<SettingsBundle> = Object.freeze<SettingsBundle>({
  defaultAgentId: DEFAULT_AGENT_ID,
  region: DEFAULT_REGION,
  deepResearchBackend: "native",
  chartDefaults: {
    symbol: DEFAULT_CHART_SYMBOL,
    timeframe: DEFAULT_CHART_TIMEFRAME,
    indicators: [],
  },
  providerOrder: REGISTRY_PROVIDERS.map((row) => row.id),
  startLayout: null,
  paletteShowRecents: true,
  paletteSymbolScope: "all",
});

interface SettingsState extends SettingsBundle {
  /** Set the default persona — applies to the active chat lens immediately. */
  setDefaultAgentId: (agentId: string | null) => void;
  setRegion: (region: Region) => void;
  setDeepResearchBackend: (backend: DeepResearchBackend) => void;
  /** Replace the chart defaults — called by the chart toolbar's "Make default". */
  setChartDefaults: (defaults: ChartDefaults) => void;
  setProviderOrder: (order: LLMProviderId[]) => void;
  setStartLayout: (name: string | null) => void;
  setPaletteShowRecents: (show: boolean) => void;
  setPaletteSymbolScope: (scope: PaletteSymbolScope) => void;
  /** Replace the entire bundle (workspace/settings restore + import). */
  setAll: (bundle: Partial<SettingsBundle>) => void;
  /** Snapshot the current preferences as a plain bundle (for export). */
  toBundle: () => SettingsBundle;
}

/** Clone the seed so no caller can mutate the frozen default in place. */
function seed(): SettingsBundle {
  return {
    defaultAgentId: DEFAULT_SETTINGS.defaultAgentId,
    region: DEFAULT_SETTINGS.region,
    deepResearchBackend: DEFAULT_SETTINGS.deepResearchBackend,
    chartDefaults: {
      ...DEFAULT_SETTINGS.chartDefaults,
      indicators: [...DEFAULT_SETTINGS.chartDefaults.indicators],
    },
    providerOrder: [...DEFAULT_SETTINGS.providerOrder],
    startLayout: DEFAULT_SETTINGS.startLayout,
    paletteShowRecents: DEFAULT_SETTINGS.paletteShowRecents,
    paletteSymbolScope: DEFAULT_SETTINGS.paletteSymbolScope,
  };
}

/** Parse a persisted/imported `providerOrder`: known provider ids, each once.
 *  A malformed value keeps the CURRENT order (R15-UI-058). */
function parseProviderOrder(value: unknown, current: LLMProviderId[]): LLMProviderId[] {
  if (!Array.isArray(value)) {
    return current;
  }
  const known = new Set<string>(REGISTRY_PROVIDERS.map((row) => row.id));
  const order = value.filter((id): id is LLMProviderId => typeof id === "string" && known.has(id));
  return order.length > 0 ? [...new Set(order)] : current;
}

/** Parse a persisted/imported `chartDefaults` field; anything malformed (an
 * older blob predating R15-UI-048, a hand-edited import) falls back to the
 * CURRENT value, never silently resets to the seed (same rule as `setAll`'s
 * other fields — R15-UI-058). */
function parseChartDefaults(value: unknown, current: ChartDefaults): ChartDefaults {
  if (
    value !== null &&
    typeof value === "object" &&
    typeof (value as { symbol?: unknown }).symbol === "string" &&
    typeof (value as { timeframe?: unknown }).timeframe === "string" &&
    Array.isArray((value as { indicators?: unknown }).indicators) &&
    (value as { indicators: unknown[] }).indicators.every((i) => typeof i === "string")
  ) {
    const v = value as ChartDefaults;
    return { symbol: v.symbol, timeframe: v.timeframe, indicators: [...v.indicators] };
  }
  return current;
}

/**
 * Parse a persisted/imported `defaultAgentId` into the in-state shape:
 * sentinel → explicit raw chat (`null`); a non-empty agent id → itself;
 * anything else (legacy dead `null`, absent, garbled) → the Copilot seed.
 */
function parseDefaultAgentId(value: unknown): string | null {
  if (value === RAW_CHAT_SENTINEL) {
    return null;
  }
  if (typeof value === "string" && value !== "") {
    return value;
  }
  return DEFAULT_SETTINGS.defaultAgentId;
}

/**
 * Whether the boot restore already seeded the active-agent store. The default
 * persona applies on the FIRST `setAll` (the launch workspace restore) and on
 * every explicit `setDefaultAgentId`; a mid-session layout load or settings
 * import must NOT yank the user's current lens — the imported default takes
 * effect next session, exactly as the Settings hint states.
 */
let defaultAgentApplied = false;

export const useSettingsStore = create<SettingsState>((set, get) => ({
  ...seed(),

  setDefaultAgentId: (agentId) => {
    set({ defaultAgentId: agentId });
    // The wiring that makes this control true (R9 D4): the default persona IS
    // the active lens — applied now, and re-applied at every boot restore.
    useActiveAgentStore.getState().setActiveAgent(agentId);
    defaultAgentApplied = true;
  },

  setRegion: (region) => {
    set({ region });
  },

  setDeepResearchBackend: (backend) => {
    set({ deepResearchBackend: backend });
  },

  setChartDefaults: (defaults) => {
    set({
      chartDefaults: {
        symbol: defaults.symbol,
        timeframe: defaults.timeframe,
        indicators: [...defaults.indicators],
      },
    });
  },

  setProviderOrder: (order) => {
    set({ providerOrder: [...order] });
  },

  setStartLayout: (name) => {
    set({ startLayout: name });
  },

  setPaletteShowRecents: (show) => {
    set({ paletteShowRecents: show });
  },

  setPaletteSymbolScope: (scope) => {
    set({ paletteSymbolScope: scope });
  },

  setAll: (bundle) => {
    // A field ABSENT from the bundle merges over the CURRENT live state, not
    // the seed — an older export or a hand-edited/partial import can't strip
    // a field the user already set (R15-UI-058: importing a bundle lacking
    // `region` used to silently reset it to the default). A field that IS
    // present keeps its existing full validation, falling back to the
    // current value (not the seed) when the value is garbled. Unknown/killed
    // keys (themeKnobs, palette*, starterCockpitPanelIds, panelDefaults,
    // providerPreferenceOrder) are silently dropped by construction.
    const current = get();
    const defaultAgentId =
      "defaultAgentId" in bundle
        ? parseDefaultAgentId(bundle.defaultAgentId)
        : current.defaultAgentId;
    const region =
      "region" in bundle
        ? isRegion(bundle.region)
          ? bundle.region
          : current.region
        : current.region;
    const deepResearchBackend =
      "deepResearchBackend" in bundle
        ? bundle.deepResearchBackend === "native" || bundle.deepResearchBackend === "perplexity"
          ? bundle.deepResearchBackend
          : current.deepResearchBackend // legacy "tongyi" blobs coerce to the current value
        : current.deepResearchBackend;
    const chartDefaults =
      "chartDefaults" in bundle
        ? parseChartDefaults(bundle.chartDefaults, current.chartDefaults)
        : current.chartDefaults;
    const providerOrder =
      "providerOrder" in bundle
        ? parseProviderOrder(bundle.providerOrder, current.providerOrder)
        : current.providerOrder;
    const startLayout =
      "startLayout" in bundle
        ? bundle.startLayout === null ||
          (typeof bundle.startLayout === "string" && bundle.startLayout !== "")
          ? bundle.startLayout
          : current.startLayout
        : current.startLayout;
    const paletteShowRecents =
      typeof bundle.paletteShowRecents === "boolean"
        ? bundle.paletteShowRecents
        : current.paletteShowRecents;
    const paletteSymbolScope =
      bundle.paletteSymbolScope === "watchlist" || bundle.paletteSymbolScope === "all"
        ? bundle.paletteSymbolScope
        : current.paletteSymbolScope;
    set({
      defaultAgentId,
      region,
      deepResearchBackend,
      chartDefaults,
      providerOrder,
      startLayout,
      paletteShowRecents,
      paletteSymbolScope,
    });
    if (!defaultAgentApplied) {
      // Boot restore: seed the chat lens with the persisted default persona.
      useActiveAgentStore.getState().setActiveAgent(defaultAgentId);
      defaultAgentApplied = true;
    }
  },

  toBundle: () => {
    const s = get();
    return {
      // Explicit raw chat rides the sentinel (see RAW_CHAT_SENTINEL).
      defaultAgentId: s.defaultAgentId === null ? RAW_CHAT_SENTINEL : s.defaultAgentId,
      region: s.region,
      deepResearchBackend: s.deepResearchBackend,
      chartDefaults: { ...s.chartDefaults, indicators: [...s.chartDefaults.indicators] },
      providerOrder: [...s.providerOrder],
      startLayout: s.startLayout,
      paletteShowRecents: s.paletteShowRecents,
      paletteSymbolScope: s.paletteSymbolScope,
    };
  },
}));

/** Non-reactive snapshot of the preferences bundle (for serialize/export). */
export function settingsBundle(): SettingsBundle {
  return useSettingsStore.getState().toBundle();
}

/** Test helper: reset the settings store to its seed (defaults). */
export function resetSettingsStoreForTests(): void {
  useSettingsStore.setState(seed());
  defaultAgentApplied = false;
}
