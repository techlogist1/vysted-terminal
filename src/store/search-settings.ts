/**
 * Search-settings store — the ONE web-search preference surface (R8).
 *
 * The R7 research tier (`researchTier`) is the single authoritative selection:
 *  - `t1_local`   — keyless multi-engine scraping (the zero-setup floor);
 *  - `t2_searxng` — the one-click managed SearXNG instance (an optional
 *                   `searxngUrl` points at a custom instance instead);
 *  - `t3_hosted`  — BYOK: hosted via OpenRouter (`hostedEngine` picks
 *                   firecrawl/exa) or, with `exaDirect`, a direct Exa API key.
 *
 * The LEGACY pre-R8 `tier` field (native / byok-exa / local-searxng) is kept in
 * the bundle for blob round-trip + migration only — no UI writes it. A pre-R8
 * blob (legacy `tier`, no `researchTier`) migrates on restore via
 * {@link migrateSearchSettings}: native→t1_local, local-searxng→t2_searxng,
 * byok-exa→t3_hosted+exaDirect.
 *
 * No secrets here: the Exa and OpenRouter BYOK keys live ONLY in the OS
 * keychain (read at request time and sent as headers), never in this bundle
 * (FR-036/SC-010).
 *
 * Persistence mirrors the region/model-selection pattern: the bundle rides the
 * workspace blob (`SerializedWorkspace.searchSettings`), and because a tier
 * change does not move the dockview layout, the store self-persists by calling
 * `void autosaveLayout()` from each setter — exactly like `store/settings`.
 *
 * SSR-safe: no `window`/`navigator` at module load; `autosaveLayout` no-ops
 * before the dockview layout mounts (so a setter in a unit test is a silent
 * no-op).
 */

import { create } from "zustand";

import { autosaveLayout } from "@/lib/workspace";
import { DEFAULT_SEARCH_TIER, isSearchTier, type SearchTier } from "../../types/search";

/**
 * The R7 research search tiers (Track R Component 3). Mirrors
 * `sidecar/config.py KNOWN_RESEARCH_SEARCH_TIERS` by hand (the
 * `types/data.ts ⇄ sidecar/models/` discipline). Rides requests as the
 * `X-Vysted-Research-Tier` header.
 */
export type ResearchTier = "t1_local" | "t2_searxng" | "t3_hosted";

/** The complete, ordered tier set — for the Settings picker and validation. */
export const RESEARCH_TIERS: readonly ResearchTier[] = ["t1_local", "t2_searxng", "t3_hosted"];

/** A fresh install starts on the keyless t1 floor — never a surprise paid route. */
export const DEFAULT_RESEARCH_TIER: ResearchTier = "t1_local";

/** Type guard for restoring a persisted research tier (garbled blobs → default). */
export function isResearchTier(value: unknown): value is ResearchTier {
  return typeof value === "string" && (RESEARCH_TIERS as readonly string[]).includes(value);
}

/**
 * The t3 hosted-search engine choice (OpenRouter `web_search` backend).
 * Mirrors the engine ids `sidecar/services/search/hosted` accepts. Rides t3
 * requests as the `X-Vysted-Search-Engine` header.
 */
export type HostedSearchEngine = "firecrawl" | "exa";

/** The complete engine set — for the t3 segmented control and validation. */
export const HOSTED_SEARCH_ENGINES: readonly HostedSearchEngine[] = ["firecrawl", "exa"];

/** Firecrawl is the default hosted engine (the one with a free-credit tier). */
export const DEFAULT_HOSTED_SEARCH_ENGINE: HostedSearchEngine = "firecrawl";

/** Type guard for restoring a persisted hosted engine (garbled blobs → default). */
export function isHostedSearchEngine(value: unknown): value is HostedSearchEngine {
  return typeof value === "string" && (HOSTED_SEARCH_ENGINES as readonly string[]).includes(value);
}

/**
 * The serialisable search-preference bundle — exactly what rides the workspace
 * blob's `searchSettings` field. NO secrets (both BYOK keys are keychain-only).
 */
export interface SearchSettingsBundle {
  /**
   * LEGACY (pre-R8) tier. Kept for blob round-trip and migration only — the
   * UI no longer writes it and no routing reads it. See
   * {@link migrateSearchSettings}.
   */
  tier: SearchTier;
  /**
   * The t2 custom SearXNG instance URL ("Advanced"). Empty string = use the
   * one-click managed instance / autodetect. Sent as the
   * `X-Vysted-Searxng-Url` header on t2 requests (omitted when empty).
   */
  searxngUrl: string;
  /** The authoritative research search tier (`X-Vysted-Research-Tier`). */
  researchTier: ResearchTier;
  /**
   * The t3 hosted-search engine (`X-Vysted-Search-Engine`, sent only on t3
   * hosted). The BYOK OpenRouter key is NOT here — keychain-only, read at
   * request time.
   */
  hostedEngine: HostedSearchEngine;
  /**
   * The t3 sub-mode: `true` = "Exa direct" (searches call Exa's API on the
   * user's own Exa key, riding the legacy `byok-exa` wire lane); `false` =
   * hosted via OpenRouter. The Exa key is keychain-only
   * (`vysted-search-exa:exa_api_key`).
   */
  exaDirect: boolean;
}

/** The immutable seed — what a fresh install (or a reset) starts from. */
export const DEFAULT_SEARCH_SETTINGS: Readonly<SearchSettingsBundle> =
  Object.freeze<SearchSettingsBundle>({
    tier: DEFAULT_SEARCH_TIER,
    searxngUrl: "",
    researchTier: DEFAULT_RESEARCH_TIER,
    hostedEngine: DEFAULT_HOSTED_SEARCH_ENGINE,
    exaDirect: false,
  });

/** How each legacy tier folds into the authoritative R7 vocabulary. */
const LEGACY_TIER_MIGRATION: Record<SearchTier, ResearchTier> = {
  native: "t1_local",
  "local-searxng": "t2_searxng",
  "byok-exa": "t3_hosted",
};

/**
 * Migrate a pre-R8 bundle: a blob carrying a valid legacy `tier` but NO valid
 * `researchTier` folds the legacy choice into the R7 vocabulary
 * (native→t1_local, local-searxng→t2_searxng, byok-exa→t3_hosted+exaDirect).
 * A blob that already carries a `researchTier` is returned untouched — the R7
 * selection is authoritative and migration never overwrites it. Pure (returns
 * a new object; never mutates the input).
 */
export function migrateSearchSettings(
  bundle: Partial<SearchSettingsBundle>,
): Partial<SearchSettingsBundle> {
  if (isResearchTier(bundle.researchTier) || !isSearchTier(bundle.tier)) {
    return bundle;
  }
  return {
    ...bundle,
    researchTier: LEGACY_TIER_MIGRATION[bundle.tier],
    exaDirect: bundle.tier === "byok-exa",
  };
}

interface SearchSettingsState extends SearchSettingsBundle {
  setSearxngUrl: (url: string) => void;
  setResearchTier: (tier: ResearchTier) => void;
  setHostedEngine: (engine: HostedSearchEngine) => void;
  setExaDirect: (exaDirect: boolean) => void;
  /** Replace the entire bundle (workspace restore + import); migrates pre-R8 blobs. */
  setAll: (bundle: Partial<SearchSettingsBundle>) => void;
  /** Snapshot the current preferences as a plain bundle (for serialize/export). */
  toBundle: () => SearchSettingsBundle;
}

/** Clone the seed so no caller can mutate the frozen default in place. */
function seed(): SearchSettingsBundle {
  return {
    tier: DEFAULT_SEARCH_SETTINGS.tier,
    searxngUrl: DEFAULT_SEARCH_SETTINGS.searxngUrl,
    researchTier: DEFAULT_SEARCH_SETTINGS.researchTier,
    hostedEngine: DEFAULT_SEARCH_SETTINGS.hostedEngine,
    exaDirect: DEFAULT_SEARCH_SETTINGS.exaDirect,
  };
}

/**
 * Self-persist a preference change into the autosave slot. Fire-and-forget —
 * `autosaveLayout` is best-effort and no-ops before the layout mounts.
 */
function persist(): void {
  void autosaveLayout();
}

export const useSearchSettingsStore = create<SearchSettingsState>((set, get) => ({
  ...seed(),

  setSearxngUrl: (url) => {
    set({ searxngUrl: url });
    persist();
  },

  setResearchTier: (researchTier) => {
    set({ researchTier });
    persist();
  },

  setHostedEngine: (hostedEngine) => {
    set({ hostedEngine });
    persist();
  },

  setExaDirect: (exaDirect) => {
    set({ exaDirect });
    persist();
  },

  setAll: (bundle) => {
    // Fold a pre-R8 blob into the R7 vocabulary FIRST, then merge over the
    // seed so a partial blob (older export, hand-edited import) can't strip a
    // field — every key keeps a sane value, and a garbled value falls back to
    // the default.
    const migrated = migrateSearchSettings(bundle);
    const base = seed();
    set({
      tier: isSearchTier(migrated.tier) ? migrated.tier : base.tier,
      searxngUrl: typeof migrated.searxngUrl === "string" ? migrated.searxngUrl : base.searxngUrl,
      researchTier: isResearchTier(migrated.researchTier)
        ? migrated.researchTier
        : base.researchTier,
      hostedEngine: isHostedSearchEngine(migrated.hostedEngine)
        ? migrated.hostedEngine
        : base.hostedEngine,
      exaDirect: typeof migrated.exaDirect === "boolean" ? migrated.exaDirect : base.exaDirect,
    });
    persist();
  },

  toBundle: () => {
    const s = get();
    return {
      tier: s.tier,
      searxngUrl: s.searxngUrl,
      researchTier: s.researchTier,
      hostedEngine: s.hostedEngine,
      exaDirect: s.exaDirect,
    };
  },
}));

/** Non-reactive snapshot of the search-preference bundle (for serialize/export). */
export function searchSettingsBundle(): SearchSettingsBundle {
  return useSearchSettingsStore.getState().toBundle();
}

/** Test helper: reset the search-settings store to its seed (defaults). */
export function resetSearchSettingsStoreForTests(): void {
  useSearchSettingsStore.setState(seed());
}
