/**
 * Search-settings store — the three-tier web-search preference (FR-080/083/084).
 *
 * Holds the non-secret half of the web-search config: which tier is active and
 * the local SearXNG URL for the local tier. The BYOK Exa API key is NOT here —
 * like every credential it lives ONLY in the OS keychain (read at request time
 * and sent as a header), never in this bundle (FR-036/SC-010).
 *
 * Persistence mirrors the region/model-selection pattern: the tier + URL ride
 * the workspace blob (`SerializedWorkspace.searchSettings`), and because a tier
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
 * The R7 research search tiers (Track R Component 3), orthogonal to the legacy
 * {@link SearchTier}. Mirrors `sidecar/config.py KNOWN_RESEARCH_SEARCH_TIERS`
 * by hand (the `types/data.ts ⇄ sidecar/models/` discipline). Rides every
 * request as the `X-Vysted-Research-Tier` header.
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
 * blob's `searchSettings` field. NO secrets (the Exa key is keychain-only).
 */
export interface SearchSettingsBundle {
  /** The active web-search tier (FR-080). */
  tier: SearchTier;
  /**
   * The local SearXNG base URL for the local tier (FR-084). Empty string when
   * unset — the sidecar autodetects `localhost:8080` in that case. Sent as the
   * `X-Vysted-Searxng-Url` header (omitted when empty).
   */
  searxngUrl: string;
  /** The R7 research search tier (`X-Vysted-Research-Tier`). */
  researchTier: ResearchTier;
  /**
   * The t3 hosted-search engine (`X-Vysted-Search-Engine`, sent only on t3).
   * The BYOK OpenRouter key is NOT here — keychain-only, read at request time.
   */
  hostedEngine: HostedSearchEngine;
}

/** The immutable seed — what a fresh install (or a reset) starts from. */
export const DEFAULT_SEARCH_SETTINGS: Readonly<SearchSettingsBundle> =
  Object.freeze<SearchSettingsBundle>({
    tier: DEFAULT_SEARCH_TIER,
    searxngUrl: "",
    researchTier: DEFAULT_RESEARCH_TIER,
    hostedEngine: DEFAULT_HOSTED_SEARCH_ENGINE,
  });

interface SearchSettingsState extends SearchSettingsBundle {
  setTier: (tier: SearchTier) => void;
  setSearxngUrl: (url: string) => void;
  setResearchTier: (tier: ResearchTier) => void;
  setHostedEngine: (engine: HostedSearchEngine) => void;
  /** Replace the entire bundle (workspace restore + import). */
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

  setTier: (tier) => {
    set({ tier });
    persist();
  },

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

  setAll: (bundle) => {
    // Merge over the seed so a partial blob (older export, hand-edited import)
    // can't strip a field — every key keeps a sane value, and a garbled tier
    // falls back to the default.
    const base = seed();
    set({
      tier: isSearchTier(bundle.tier) ? bundle.tier : base.tier,
      searxngUrl: typeof bundle.searxngUrl === "string" ? bundle.searxngUrl : base.searxngUrl,
      researchTier: isResearchTier(bundle.researchTier) ? bundle.researchTier : base.researchTier,
      hostedEngine: isHostedSearchEngine(bundle.hostedEngine)
        ? bundle.hostedEngine
        : base.hostedEngine,
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
