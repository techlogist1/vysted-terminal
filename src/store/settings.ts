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
 *    agent-invoke requests (`native` is the only user-facing engine).
 *
 * Persistence: every setter rides the workspace autosave slot. A preference
 * change isn't a layout change, so the store self-persists by calling
 * `void autosaveLayout()` directly (no `page.tsx` subscription needed).
 *
 * SSR-safe: no `window`/`navigator` at module load; `autosaveLayout` already
 * no-ops before the dockview layout mounts.
 */

import { create } from "zustand";

import { type Region, DEFAULT_REGION, isRegion } from "@/lib/region";
import { autosaveLayout } from "@/lib/workspace";
import { DEFAULT_AGENT_ID, useActiveAgentStore } from "@/store/active-agent";

/**
 * The DEEP research engine the agent drives (Track 5). `native` is Vysted's own
 * bounded IterResearch loop on the configured model — always available, no extra
 * key. `perplexity` is an opt-in, paid backend the agent can select with its own
 * Perplexity key; it is never auto-selected and is not offered in Settings (native
 * is the only user-facing engine).
 */
export type DeepResearchBackend = "native" | "perplexity";

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
});

interface SettingsState extends SettingsBundle {
  /** Set the default persona — applies to the active chat lens immediately. */
  setDefaultAgentId: (agentId: string | null) => void;
  setRegion: (region: Region) => void;
  setDeepResearchBackend: (backend: DeepResearchBackend) => void;
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
    persist();
  },

  setRegion: (region) => {
    set({ region });
    persist();
  },

  setDeepResearchBackend: (backend) => {
    set({ deepResearchBackend: backend });
    persist();
  },

  setAll: (bundle) => {
    // Merge over the seed so a partial blob (older export, hand-edited import)
    // can't strip a field — every key keeps a sane value. Unknown/killed keys
    // (themeKnobs, palette*, starterCockpitPanelIds, panelDefaults,
    // providerPreferenceOrder) are silently dropped by construction.
    const base = seed();
    const defaultAgentId = parseDefaultAgentId(bundle.defaultAgentId);
    set({
      defaultAgentId,
      region: isRegion(bundle.region) ? bundle.region : base.region,
      deepResearchBackend:
        bundle.deepResearchBackend === "native" || bundle.deepResearchBackend === "perplexity"
          ? bundle.deepResearchBackend
          : base.deepResearchBackend, // legacy "tongyi" blobs coerce to native
    });
    if (!defaultAgentApplied) {
      // Boot restore: seed the chat lens with the persisted default persona.
      useActiveAgentStore.getState().setActiveAgent(defaultAgentId);
      defaultAgentApplied = true;
    }
    persist();
  },

  toBundle: () => {
    const s = get();
    return {
      // Explicit raw chat rides the sentinel (see RAW_CHAT_SENTINEL).
      defaultAgentId: s.defaultAgentId === null ? RAW_CHAT_SENTINEL : s.defaultAgentId,
      region: s.region,
      deepResearchBackend: s.deepResearchBackend,
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
