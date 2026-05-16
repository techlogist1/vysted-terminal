/**
 * Earnings store — upcoming-calendar window + per-symbol history /
 * surprises / estimate-detail caches.
 *
 * Phase 6 (Teammate E). The EarningsCalendarPanel reads ``upcoming``
 * and triggers ``loadUpcoming`` on date-window / watchlist changes.
 * The drill-down (`EarningsSurpriseChart` / `EpsEstimateGrid`) reads
 * the per-symbol caches via the `getHistory` / `getSurprises` /
 * `getEstimates` selectors. The store keys the per-symbol caches by
 * upper-cased symbol so a re-render against the same selection is a
 * no-op.
 *
 * Network paths are deliberately thin — every call goes through
 * `sidecarGet` and the store stores the typed response. Errors land on
 * `error` so the panel can render an inline banner; the caches survive
 * the error so a partial drill-down (e.g. surprises loaded but history
 * pending) keeps rendering.
 */

import { create } from "zustand";

import { sidecarGet } from "@/lib/sidecar-client";

import type {
  EarningsEstimateDetail,
  EarningsHistoryResponse,
  EarningsSurprisesResponse,
  EarningsUpcomingResponse,
} from "../../types/earnings";

export type EarningsLoadStatus = "idle" | "loading" | "ready" | "error";

interface EarningsState {
  // ---- upcoming-window slice ---------------------------------------
  upcoming: EarningsUpcomingResponse | null;
  upcomingStatus: EarningsLoadStatus;
  upcomingError: string | null;
  /** Echo of the query the active window was fetched with — drives the picker form. */
  lastDays: number;
  lastWatchlist: string[] | null;

  // ---- per-symbol caches -------------------------------------------
  histories: Record<string, EarningsHistoryResponse>;
  historyErrors: Record<string, string>;
  surprises: Record<string, EarningsSurprisesResponse>;
  surpriseErrors: Record<string, string>;
  estimates: Record<string, EarningsEstimateDetail>;
  estimateErrors: Record<string, string>;

  // ---- public API --------------------------------------------------
  loadUpcoming: (days?: number, watchlist?: string[] | null) => Promise<void>;
  getHistory: (symbol: string) => Promise<EarningsHistoryResponse | null>;
  getSurprises: (symbol: string) => Promise<EarningsSurprisesResponse | null>;
  getEstimates: (symbol: string) => Promise<EarningsEstimateDetail | null>;

  __resetForTests: () => void;
}

const DEFAULT_DAYS = 7;

function watchlistToParam(watchlist: string[] | null | undefined): string | undefined {
  if (!watchlist || watchlist.length === 0) {
    return undefined;
  }
  return watchlist.join(",");
}

export const useEarningsStore = create<EarningsState>((set, get) => ({
  upcoming: null,
  upcomingStatus: "idle",
  upcomingError: null,
  lastDays: DEFAULT_DAYS,
  lastWatchlist: null,
  histories: {},
  historyErrors: {},
  surprises: {},
  surpriseErrors: {},
  estimates: {},
  estimateErrors: {},

  loadUpcoming: async (days = DEFAULT_DAYS, watchlist = null) => {
    set({
      upcomingStatus: "loading",
      upcomingError: null,
      lastDays: days,
      lastWatchlist: watchlist,
    });
    try {
      const payload = await sidecarGet<EarningsUpcomingResponse>("/earnings/upcoming", {
        days,
        watchlist: watchlistToParam(watchlist),
      });
      set({ upcoming: payload, upcomingStatus: "ready", upcomingError: null });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load upcoming earnings";
      set({ upcomingStatus: "error", upcomingError: message, upcoming: null });
    }
  },

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
      const payload = await sidecarGet<EarningsHistoryResponse>(
        `/earnings/${encodeURIComponent(normalized)}/history`,
      );
      set((state) => ({
        histories: { ...state.histories, [normalized]: payload },
        historyErrors: { ...state.historyErrors, [normalized]: "" },
      }));
      return payload;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : `Failed to load history for ${normalized}`;
      set((state) => ({
        historyErrors: { ...state.historyErrors, [normalized]: message },
      }));
      return null;
    }
  },

  getSurprises: async (symbol) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return null;
    }
    const cached = get().surprises[normalized];
    if (cached) {
      return cached;
    }
    try {
      const payload = await sidecarGet<EarningsSurprisesResponse>(
        `/earnings/${encodeURIComponent(normalized)}/surprises`,
      );
      set((state) => ({
        surprises: { ...state.surprises, [normalized]: payload },
        surpriseErrors: { ...state.surpriseErrors, [normalized]: "" },
      }));
      return payload;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : `Failed to load surprises for ${normalized}`;
      set((state) => ({
        surpriseErrors: { ...state.surpriseErrors, [normalized]: message },
      }));
      return null;
    }
  },

  getEstimates: async (symbol) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return null;
    }
    const cached = get().estimates[normalized];
    if (cached) {
      return cached;
    }
    try {
      const payload = await sidecarGet<EarningsEstimateDetail>(
        `/earnings/${encodeURIComponent(normalized)}/estimates`,
      );
      set((state) => ({
        estimates: { ...state.estimates, [normalized]: payload },
        estimateErrors: { ...state.estimateErrors, [normalized]: "" },
      }));
      return payload;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : `Failed to load estimates for ${normalized}`;
      set((state) => ({
        estimateErrors: { ...state.estimateErrors, [normalized]: message },
      }));
      return null;
    }
  },

  __resetForTests: () =>
    set({
      upcoming: null,
      upcomingStatus: "idle",
      upcomingError: null,
      lastDays: DEFAULT_DAYS,
      lastWatchlist: null,
      histories: {},
      historyErrors: {},
      surprises: {},
      surpriseErrors: {},
      estimates: {},
      estimateErrors: {},
    }),
}));
