/**
 * Analyst-ratings store — per-symbol caches for ratings history,
 * price-target history, and individual-analyst forecasts.
 *
 * Phase 6 (Teammate E). The AnalystRatingsPanel reads the three slices
 * directly via the `getHistory` / `getPriceTargets` / `getIndividual`
 * accessors. The store keys each cache by upper-cased symbol so a
 * re-render against the same selection is a no-op; errors land on the
 * matching `*Errors` map so the panel can surface inline banners
 * without losing the data from the other two tabs.
 */

import { create } from "zustand";

import { sidecarGet } from "@/lib/sidecar-client";

import type {
  IndividualAnalystResponse,
  PriceTargetHistoryResponse,
  RatingsHistoryResponse,
} from "../../types/analyst";

// R15-DATA-068: pair every per-symbol entry with the client timestamp it was
// fetched at, so a stale entry (older than CACHE_TTL_MS) is treated as a
// miss and refetched rather than served forever. The analyst-ratings routes
// (sidecar/routers/fundamentals.py) don't stamp a server as_of the way the
// earnings routes do, so freshness here is tracked client-side only.
export const ANALYST_RATINGS_CACHE_TTL_MS = 15 * 60 * 1000;

function isFresh(fetchedAt: number): boolean {
  return Date.now() - fetchedAt < ANALYST_RATINGS_CACHE_TTL_MS;
}

interface AnalystRatingsState {
  histories: Record<string, { payload: RatingsHistoryResponse; fetchedAt: number }>;
  historyErrors: Record<string, string>;
  priceTargets: Record<string, { payload: PriceTargetHistoryResponse; fetchedAt: number }>;
  priceTargetErrors: Record<string, string>;
  individuals: Record<string, { payload: IndividualAnalystResponse; fetchedAt: number }>;
  individualErrors: Record<string, string>;

  getHistory: (symbol: string) => Promise<RatingsHistoryResponse | null>;
  getPriceTargets: (symbol: string) => Promise<PriceTargetHistoryResponse | null>;
  getIndividual: (symbol: string) => Promise<IndividualAnalystResponse | null>;
  /** Bypasses the TTL and refetches this symbol's three slices unconditionally. */
  refresh: (symbol: string) => Promise<void>;

  __resetForTests: () => void;
}

export const useAnalystRatingsStore = create<AnalystRatingsState>((set, get) => ({
  histories: {},
  historyErrors: {},
  priceTargets: {},
  priceTargetErrors: {},
  individuals: {},
  individualErrors: {},

  getHistory: async (symbol) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return null;
    }
    const cached = get().histories[normalized];
    if (cached && isFresh(cached.fetchedAt)) {
      return cached.payload;
    }
    try {
      const payload = await sidecarGet<RatingsHistoryResponse>(
        `/fundamentals/${encodeURIComponent(normalized)}/ratings/history`,
      );
      set((state) => ({
        histories: { ...state.histories, [normalized]: { payload, fetchedAt: Date.now() } },
        historyErrors: { ...state.historyErrors, [normalized]: "" },
      }));
      return payload;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : `Failed to load ratings history for ${normalized}`;
      set((state) => ({
        historyErrors: { ...state.historyErrors, [normalized]: message },
      }));
      return null;
    }
  },

  getPriceTargets: async (symbol) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return null;
    }
    const cached = get().priceTargets[normalized];
    if (cached && isFresh(cached.fetchedAt)) {
      return cached.payload;
    }
    try {
      const payload = await sidecarGet<PriceTargetHistoryResponse>(
        `/fundamentals/${encodeURIComponent(normalized)}/ratings/price-target-history`,
      );
      set((state) => ({
        priceTargets: { ...state.priceTargets, [normalized]: { payload, fetchedAt: Date.now() } },
        priceTargetErrors: { ...state.priceTargetErrors, [normalized]: "" },
      }));
      return payload;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : `Failed to load price targets for ${normalized}`;
      set((state) => ({
        priceTargetErrors: { ...state.priceTargetErrors, [normalized]: message },
      }));
      return null;
    }
  },

  getIndividual: async (symbol) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return null;
    }
    const cached = get().individuals[normalized];
    if (cached && isFresh(cached.fetchedAt)) {
      return cached.payload;
    }
    try {
      const payload = await sidecarGet<IndividualAnalystResponse>(
        `/fundamentals/${encodeURIComponent(normalized)}/ratings/individual`,
      );
      set((state) => ({
        individuals: { ...state.individuals, [normalized]: { payload, fetchedAt: Date.now() } },
        individualErrors: { ...state.individualErrors, [normalized]: "" },
      }));
      return payload;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : `Failed to load individual analysts for ${normalized}`;
      set((state) => ({
        individualErrors: { ...state.individualErrors, [normalized]: message },
      }));
      return null;
    }
  },

  refresh: async (symbol) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return;
    }
    set((state) => {
      const { [normalized]: _h, ...histories } = state.histories;
      const { [normalized]: _p, ...priceTargets } = state.priceTargets;
      const { [normalized]: _i, ...individuals } = state.individuals;
      return { histories, priceTargets, individuals };
    });
    await Promise.all([
      get().getHistory(normalized),
      get().getPriceTargets(normalized),
      get().getIndividual(normalized),
    ]);
  },

  __resetForTests: () =>
    set({
      histories: {},
      historyErrors: {},
      priceTargets: {},
      priceTargetErrors: {},
      individuals: {},
      individualErrors: {},
    }),
}));
