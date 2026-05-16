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

interface AnalystRatingsState {
  histories: Record<string, RatingsHistoryResponse>;
  historyErrors: Record<string, string>;
  priceTargets: Record<string, PriceTargetHistoryResponse>;
  priceTargetErrors: Record<string, string>;
  individuals: Record<string, IndividualAnalystResponse>;
  individualErrors: Record<string, string>;

  getHistory: (symbol: string) => Promise<RatingsHistoryResponse | null>;
  getPriceTargets: (symbol: string) => Promise<PriceTargetHistoryResponse | null>;
  getIndividual: (symbol: string) => Promise<IndividualAnalystResponse | null>;

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
    if (cached) {
      return cached;
    }
    try {
      const payload = await sidecarGet<RatingsHistoryResponse>(
        `/fundamentals/${encodeURIComponent(normalized)}/ratings/history`,
      );
      set((state) => ({
        histories: { ...state.histories, [normalized]: payload },
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
    if (cached) {
      return cached;
    }
    try {
      const payload = await sidecarGet<PriceTargetHistoryResponse>(
        `/fundamentals/${encodeURIComponent(normalized)}/ratings/price-target-history`,
      );
      set((state) => ({
        priceTargets: { ...state.priceTargets, [normalized]: payload },
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
    if (cached) {
      return cached;
    }
    try {
      const payload = await sidecarGet<IndividualAnalystResponse>(
        `/fundamentals/${encodeURIComponent(normalized)}/ratings/individual`,
      );
      set((state) => ({
        individuals: { ...state.individuals, [normalized]: payload },
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
