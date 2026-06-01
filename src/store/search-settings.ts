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
}

/** The immutable seed — what a fresh install (or a reset) starts from. */
export const DEFAULT_SEARCH_SETTINGS: Readonly<SearchSettingsBundle> =
  Object.freeze<SearchSettingsBundle>({
    tier: DEFAULT_SEARCH_TIER,
    searxngUrl: "",
  });

interface SearchSettingsState extends SearchSettingsBundle {
  setTier: (tier: SearchTier) => void;
  setSearxngUrl: (url: string) => void;
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

  setAll: (bundle) => {
    // Merge over the seed so a partial blob (older export, hand-edited import)
    // can't strip a field — every key keeps a sane value, and a garbled tier
    // falls back to the default.
    const base = seed();
    set({
      tier: isSearchTier(bundle.tier) ? bundle.tier : base.tier,
      searxngUrl: typeof bundle.searxngUrl === "string" ? bundle.searxngUrl : base.searxngUrl,
    });
    persist();
  },

  toBundle: () => {
    const s = get();
    return {
      tier: s.tier,
      searxngUrl: s.searxngUrl,
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
