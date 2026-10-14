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
// miss and refetched rather than served forever. TTL expiry is always
// client-side (`fetchedAt`); `asOf` below additionally surfaces the
// SERVER's freshness stamp for display, once the sidecar sends one.
export const ANALYST_RATINGS_CACHE_TTL_MS = 15 * 60 * 1000;

/**
 * Read an optional `as_of` off an envelope without depending on it being
 * declared on the response type yet (C16 adds `as_of?: string | null` to
 * `types/analyst.ts` — this store's TTL/chip work is coded against it ahead
 * of that landing, so it stays green whether or not the field exists on the
 * wire yet).
 */
function extractAsOf(payload: unknown): string | null {
  const asOf = (payload as { as_of?: unknown } | null)?.as_of;
  return typeof asOf === "string" ? asOf : null;
}

function isFresh(fetchedAt: number): boolean {
  return Date.now() - fetchedAt < ANALYST_RATINGS_CACHE_TTL_MS;
}

/** A cached slice entry — `asOf` is the server-stated freshness (C16),
 *  `null` until the sidecar sends one; `fetchedAt` (client clock) always
 *  drives the TTL and is the chip's fallback when `asOf` is absent. */
interface CachedSlice<T> {
  payload: T;
  fetchedAt: number;
  asOf: string | null;
}

interface AnalystRatingsState {
  histories: Record<string, CachedSlice<RatingsHistoryResponse>>;
  historyErrors: Record<string, string>;
  priceTargets: Record<string, CachedSlice<PriceTargetHistoryResponse>>;
  priceTargetErrors: Record<string, string>;
  individuals: Record<string, CachedSlice<IndividualAnalystResponse>>;
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
        histories: {
          ...state.histories,
          [normalized]: { payload, fetchedAt: Date.now(), asOf: extractAsOf(payload) },
        },
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
        priceTargets: {
          ...state.priceTargets,
          [normalized]: { payload, fetchedAt: Date.now(), asOf: extractAsOf(payload) },
        },
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
        individuals: {
          ...state.individuals,
          [normalized]: { payload, fetchedAt: Date.now(), asOf: extractAsOf(payload) },
        },
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
