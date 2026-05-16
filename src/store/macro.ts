/**
 * Macro store — Phase 6 (Teammate M).
 *
 * Zustand store for the Macro panel: a per-(provider, series_id) cache of
 * loaded :type:`MacroSeriesExtended` payloads, plus a cached search-result
 * map keyed by ``{provider}:{query}`` and a cached catalog per provider.
 *
 * Selector contract (per the CLAUDE.md ``useSyncExternalStore`` Gotcha):
 * selectors that may legitimately return "nothing" for a given input return
 * a module-level frozen empty reference so an unknown key does not mint a
 * fresh empty object every render. Same pattern as
 * :file:`src/store/workflow.ts`.
 *
 * No ``localStorage`` / ``sessionStorage`` per the CLAUDE.md constraint
 * (sidecar owns persistence; the Macro panel re-fetches on next open).
 */

import { create } from "zustand";

import { SidecarError, sidecarGet } from "@/lib/sidecar-client";

import type {
  MacroCatalog,
  MacroProvider,
  MacroSearchResult,
  MacroSeriesExtended,
} from "../../types/macro";

/** Cache key for one series: ``"<provider>:<series_id>"``. */
function seriesKey(provider: MacroProvider, seriesId: string): string {
  return `${provider}:${seriesId}`;
}

/** Cache key for a search query: ``"<provider>:<query-lower>"``. */
function searchKey(provider: MacroProvider, query: string): string {
  return `${provider}:${query.toLowerCase()}`;
}

interface SeriesLoadStatus {
  status: "loading" | "ready" | "error";
  error?: string;
  series?: MacroSeriesExtended;
}

interface MacroState {
  /** Per-(provider, series) cached load state. */
  seriesStatus: Record<string, SeriesLoadStatus>;
  /** Per-(provider, query) cached search rows. */
  searchResults: Record<string, MacroSearchResult[]>;
  /** Per-provider cached catalog. */
  catalogByProvider: Partial<Record<MacroProvider, MacroCatalog>>;
  /** Currently selected (provider, series) for the panel. */
  selected: { provider: MacroProvider; seriesId: string } | null;

  /** Set the currently-selected series. */
  select: (provider: MacroProvider, seriesId: string) => void;
  /** Load + cache one series. */
  loadSeries: (provider: MacroProvider, seriesId: string) => Promise<void>;
  /** Run a search; results are cached by (provider, query). */
  search: (provider: MacroProvider, query: string, limit?: number) => Promise<void>;
  /** Load + cache one provider's curated catalog. */
  loadCatalog: (provider: MacroProvider) => Promise<void>;
  /** Wipe all caches — useful for tests / "reload everything" UX. */
  reset: () => void;
}

export const useMacroStore = create<MacroState>((set, get) => ({
  seriesStatus: {},
  searchResults: {},
  catalogByProvider: {},
  selected: null,

  select: (provider, seriesId) => set({ selected: { provider, seriesId } }),

  loadSeries: async (provider, seriesId) => {
    if (!seriesId) return;
    const key = seriesKey(provider, seriesId);
    set((state) => ({
      seriesStatus: { ...state.seriesStatus, [key]: { status: "loading" } },
    }));
    try {
      const series = await sidecarGet<MacroSeriesExtended>(
        `/macro/${encodeURIComponent(seriesId)}`,
        { provider },
      );
      set((state) => ({
        seriesStatus: {
          ...state.seriesStatus,
          [key]: { status: "ready", series },
        },
      }));
    } catch (err) {
      const message =
        err instanceof SidecarError
          ? err.message
          : err instanceof Error
            ? err.message
            : String(err);
      set((state) => ({
        seriesStatus: {
          ...state.seriesStatus,
          [key]: { status: "error", error: message },
        },
      }));
    }
  },

  search: async (provider, query, limit = 25) => {
    if (!query) return;
    const key = searchKey(provider, query);
    try {
      const results = await sidecarGet<MacroSearchResult[]>("/macro/search", {
        q: query,
        provider,
        limit,
      });
      set((state) => ({
        searchResults: { ...state.searchResults, [key]: results },
      }));
    } catch {
      set((state) => ({
        searchResults: { ...state.searchResults, [key]: [] },
      }));
    }
  },

  loadCatalog: async (provider) => {
    if (get().catalogByProvider[provider]) return;
    try {
      const catalog = await sidecarGet<MacroCatalog>("/macro/catalog", { provider });
      set((state) => ({
        catalogByProvider: { ...state.catalogByProvider, [provider]: catalog },
      }));
    } catch {
      // Leave the slot empty — UI shows "no catalog" state.
    }
  },

  reset: () =>
    set({ seriesStatus: {}, searchResults: {}, catalogByProvider: {}, selected: null }),
}));

// ---------------------------------------------------------------------------
// Selectors — referentially-stable per the useSyncExternalStore Gotcha
// ---------------------------------------------------------------------------

const EMPTY_RESULTS: readonly MacroSearchResult[] = Object.freeze([]);

/** Select the load status for one (provider, seriesId), or undefined if untouched. */
export function selectSeriesStatus(
  state: MacroState,
  provider: MacroProvider,
  seriesId: string,
): SeriesLoadStatus | undefined {
  return state.seriesStatus[seriesKey(provider, seriesId)];
}

/** Select the cached search results for (provider, query); stable empty fallback. */
export function selectSearchResults(
  state: MacroState,
  provider: MacroProvider,
  query: string,
): readonly MacroSearchResult[] {
  if (!query) return EMPTY_RESULTS;
  const key = searchKey(provider, query);
  return state.searchResults[key] ?? EMPTY_RESULTS;
}

/** Select the cached catalog for one provider; undefined when not loaded. */
export function selectCatalog(
  state: MacroState,
  provider: MacroProvider,
): MacroCatalog | undefined {
  return state.catalogByProvider[provider];
}

/** Select the currently-selected (provider, seriesId), or null. */
export function selectSelected(
  state: MacroState,
): { provider: MacroProvider; seriesId: string } | null {
  return state.selected;
}

export type { SeriesLoadStatus };
