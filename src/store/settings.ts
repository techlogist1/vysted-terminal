/**
 * Settings store — the local preferences bundle (FR-037/FR-038, SC-011).
 *
 * Everything here is a *preference* the user can set in the Settings panel and
 * carry between machines via export/import. It is deliberately separate from:
 *  - keybinding overrides (own store, `keybindings.ts`, persisted alongside),
 *  - secrets (OS keychain only — NEVER in this bundle, FR-036/SC-010),
 *  - the dockview layout + module-enabled map (the workspace blob proper).
 *
 * The values that already have a home in a dedicated store (the default
 * provider in `llm-providers`, the per-provider model in `model-selection`,
 * the agent mode in `agent-mode`) stay owned by those stores; this store holds
 * the preferences with no other home: the default agent/persona, the provider
 * *preference order*, command-palette behaviour, the FR-032 starter-cockpit
 * composition, per-panel defaults, and the dark-only theme knobs.
 *
 * Persistence: every setter rides the workspace autosave slot. A preference
 * change isn't a layout change, so the store self-persists by calling
 * `void autosaveLayout()` directly (no `page.tsx` subscription needed) — the
 * same approach the "Set default provider" button already uses.
 *
 * SSR-safe: no `window`/`navigator` at module load; `autosaveLayout` already
 * no-ops before the dockview layout mounts.
 */

import { create } from "zustand";

import { autosaveLayout } from "@/lib/workspace";
import type { LLMProviderId } from "../../types/ai";

/** Accent intensity for the dark theme — modest, dark-only knob (FR reskin). */
export type AccentIntensity = "muted" | "normal" | "vivid";

/** Row density for list-heavy panels — the other dark-only knob. */
export type Density = "comfortable" | "compact";

/** Dark-only theming knobs. We never leave the dark language; these tune it. */
export interface ThemeKnobs {
  accentIntensity: AccentIntensity;
  density: Density;
}

/**
 * Per-panel default preferences. A small, open map keyed by panel id — each
 * panel reads the keys it cares about (e.g. `{ "chart-panel": { interval:
 * "1D" } }`). Kept `unknown`-valued so a panel owns its own shape without this
 * store knowing every panel's options.
 */
export type PanelDefaults = Record<string, Record<string, unknown>>;

/**
 * The serialisable preferences bundle. This is exactly what rides the workspace
 * blob's `settings` field and what export/import round-trips. NO secrets.
 */
export interface SettingsBundle {
  /** Default agent/persona id the chat sidebar selects on a fresh session. */
  defaultAgentId: string | null;
  /**
   * Preferred provider ordering — the order providers are offered in pickers.
   * A subset/superset of the live provider list is tolerated; the UI unions it
   * with the live list so a provider added in a later release still appears.
   */
  providerPreferenceOrder: LLMProviderId[];
  /** Whether the command palette surfaces a recents section. */
  paletteRecentsEnabled: boolean;
  /** Whether the command palette opens scoped to the focused panel's commands. */
  paletteScopedToPanel: boolean;
  /** Panel component ids that open in the FR-032 first-run starter cockpit. */
  starterCockpitPanelIds: string[];
  /** Per-panel default preferences (open map). */
  panelDefaults: PanelDefaults;
  /** Dark-only theme knobs. */
  themeKnobs: ThemeKnobs;
}

/** The default starter-cockpit composition — mirrors `config/default-layout`. */
export const DEFAULT_STARTER_COCKPIT_PANEL_IDS: readonly string[] = [
  "chart-panel",
  "equity-overview-panel",
  "watchlist-panel",
  "news-panel",
  "portfolio-panel",
];

/** The immutable seed bundle — what a fresh install (or a reset) starts from. */
export const DEFAULT_SETTINGS: Readonly<SettingsBundle> = Object.freeze<SettingsBundle>({
  defaultAgentId: null,
  providerPreferenceOrder: ["anthropic", "openai", "gemini", "groq", "ollama", "deepseek", "xai"],
  paletteRecentsEnabled: true,
  paletteScopedToPanel: false,
  starterCockpitPanelIds: [...DEFAULT_STARTER_COCKPIT_PANEL_IDS],
  panelDefaults: {},
  themeKnobs: { accentIntensity: "normal", density: "comfortable" },
});

interface SettingsState extends SettingsBundle {
  setDefaultAgentId: (agentId: string | null) => void;
  setProviderPreferenceOrder: (order: LLMProviderId[]) => void;
  /** Move one provider up or down in the preference order by one slot. */
  moveProviderPreference: (id: LLMProviderId, direction: "up" | "down") => void;
  setPaletteRecentsEnabled: (enabled: boolean) => void;
  setPaletteScopedToPanel: (enabled: boolean) => void;
  setStarterCockpitPanelIds: (ids: string[]) => void;
  /** Toggle one panel id into / out of the starter-cockpit composition. */
  toggleStarterCockpitPanel: (panelId: string, on: boolean) => void;
  setPanelDefault: (panelId: string, prefs: Record<string, unknown>) => void;
  setThemeKnobs: (knobs: Partial<ThemeKnobs>) => void;
  /** Replace the entire bundle (workspace/settings restore + import). */
  setAll: (bundle: Partial<SettingsBundle>) => void;
  /** Snapshot the current preferences as a plain bundle (for export). */
  toBundle: () => SettingsBundle;
}

/** Clone the seed so no caller can mutate the frozen default in place. */
function seed(): SettingsBundle {
  return {
    defaultAgentId: DEFAULT_SETTINGS.defaultAgentId,
    providerPreferenceOrder: [...DEFAULT_SETTINGS.providerPreferenceOrder],
    paletteRecentsEnabled: DEFAULT_SETTINGS.paletteRecentsEnabled,
    paletteScopedToPanel: DEFAULT_SETTINGS.paletteScopedToPanel,
    starterCockpitPanelIds: [...DEFAULT_SETTINGS.starterCockpitPanelIds],
    panelDefaults: {},
    themeKnobs: { ...DEFAULT_SETTINGS.themeKnobs },
  };
}

/**
 * Self-persist a preference change into the autosave slot. Fire-and-forget —
 * `autosaveLayout` is best-effort and no-ops before the layout mounts, so a
 * preference set in a unit test (no dockview) is a silent no-op.
 */
function persist(): void {
  void autosaveLayout();
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  ...seed(),

  setDefaultAgentId: (agentId) => {
    set({ defaultAgentId: agentId });
    persist();
  },

  setProviderPreferenceOrder: (order) => {
    set({ providerPreferenceOrder: [...order] });
    persist();
  },

  moveProviderPreference: (id, direction) => {
    set((state) => {
      const order = [...state.providerPreferenceOrder];
      const idx = order.indexOf(id);
      if (idx === -1) {
        return state;
      }
      const swapWith = direction === "up" ? idx - 1 : idx + 1;
      if (swapWith < 0 || swapWith >= order.length) {
        return state;
      }
      [order[idx], order[swapWith]] = [order[swapWith]!, order[idx]!];
      return { providerPreferenceOrder: order };
    });
    persist();
  },

  setPaletteRecentsEnabled: (enabled) => {
    set({ paletteRecentsEnabled: enabled });
    persist();
  },

  setPaletteScopedToPanel: (enabled) => {
    set({ paletteScopedToPanel: enabled });
    persist();
  },

  setStarterCockpitPanelIds: (ids) => {
    set({ starterCockpitPanelIds: [...ids] });
    persist();
  },

  toggleStarterCockpitPanel: (panelId, on) => {
    set((state) => {
      const has = state.starterCockpitPanelIds.includes(panelId);
      if (on && !has) {
        return { starterCockpitPanelIds: [...state.starterCockpitPanelIds, panelId] };
      }
      if (!on && has) {
        return {
          starterCockpitPanelIds: state.starterCockpitPanelIds.filter((id) => id !== panelId),
        };
      }
      return state;
    });
    persist();
  },

  setPanelDefault: (panelId, prefs) => {
    set((state) => ({
      panelDefaults: { ...state.panelDefaults, [panelId]: { ...prefs } },
    }));
    persist();
  },

  setThemeKnobs: (knobs) => {
    set((state) => ({ themeKnobs: { ...state.themeKnobs, ...knobs } }));
    persist();
  },

  setAll: (bundle) => {
    // Merge over the seed so a partial blob (older export, hand-edited import)
    // can't strip a field — every key keeps a sane value.
    const base = seed();
    set({
      defaultAgentId:
        typeof bundle.defaultAgentId === "string" || bundle.defaultAgentId === null
          ? bundle.defaultAgentId
          : base.defaultAgentId,
      providerPreferenceOrder: Array.isArray(bundle.providerPreferenceOrder)
        ? [...bundle.providerPreferenceOrder]
        : base.providerPreferenceOrder,
      paletteRecentsEnabled:
        typeof bundle.paletteRecentsEnabled === "boolean"
          ? bundle.paletteRecentsEnabled
          : base.paletteRecentsEnabled,
      paletteScopedToPanel:
        typeof bundle.paletteScopedToPanel === "boolean"
          ? bundle.paletteScopedToPanel
          : base.paletteScopedToPanel,
      starterCockpitPanelIds: Array.isArray(bundle.starterCockpitPanelIds)
        ? [...bundle.starterCockpitPanelIds]
        : base.starterCockpitPanelIds,
      panelDefaults:
        bundle.panelDefaults && typeof bundle.panelDefaults === "object"
          ? { ...bundle.panelDefaults }
          : base.panelDefaults,
      themeKnobs:
        bundle.themeKnobs && typeof bundle.themeKnobs === "object"
          ? { ...base.themeKnobs, ...bundle.themeKnobs }
          : base.themeKnobs,
    });
    persist();
  },

  toBundle: () => {
    const s = get();
    return {
      defaultAgentId: s.defaultAgentId,
      providerPreferenceOrder: [...s.providerPreferenceOrder],
      paletteRecentsEnabled: s.paletteRecentsEnabled,
      paletteScopedToPanel: s.paletteScopedToPanel,
      starterCockpitPanelIds: [...s.starterCockpitPanelIds],
      panelDefaults: { ...s.panelDefaults },
      themeKnobs: { ...s.themeKnobs },
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
}
