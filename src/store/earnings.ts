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

export const EARNINGS_CACHE_TTL_MS = 15 * 60 * 1000;

interface EarningsState {
  // ---- upcoming-window slice ---------------------------------------
  upcoming: EarningsUpcomingResponse | null;
  upcomingStatus: EarningsLoadStatus;
  upcomingError: string | null;
  /** R15-UI-015: the ORIGINAL caught error, kept alongside `upcomingError` so
   *  a caller can tell a transient sidecar-not-ready failure from a
   *  deterministic one (`useRetryOnSidecarReady`) instead of re-throwing a
   *  flattened `new Error(string)` that always reads as transient. */
  upcomingCause: unknown;
  /** Echo of the query the active window was fetched with — drives the picker form. */
  lastDays: number;
  lastWatchlist: string[] | null;

  // ---- per-symbol caches ---------------------------------------------
  // R15-DATA-068: every cache entry pairs the payload with the client
  // timestamp it was fetched at, so a stale entry (older than
  // EARNINGS_CACHE_TTL_MS) is treated as a miss and refetched rather than
  // served forever.
  histories: Record<string, { payload: EarningsHistoryResponse; fetchedAt: number }>;
  historyErrors: Record<string, string>;
  surprises: Record<string, { payload: EarningsSurprisesResponse; fetchedAt: number }>;
  surpriseErrors: Record<string, string>;
  estimates: Record<string, { payload: EarningsEstimateDetail; fetchedAt: number }>;
  estimateErrors: Record<string, string>;

  // ---- public API --------------------------------------------------
  loadUpcoming: (days?: number, watchlist?: string[] | null) => Promise<void>;
  getHistory: (symbol: string) => Promise<EarningsHistoryResponse | null>;
  getSurprises: (symbol: string) => Promise<EarningsSurprisesResponse | null>;
  getEstimates: (symbol: string) => Promise<EarningsEstimateDetail | null>;
  /** Bypasses the TTL and refetches this symbol's three slices unconditionally. */
  refresh: (symbol: string) => Promise<void>;

  __resetForTests: () => void;
}

const DEFAULT_DAYS = 7;

function isFresh(fetchedAt: number): boolean {
  return Date.now() - fetchedAt < EARNINGS_CACHE_TTL_MS;
}

function watchlistToParam(watchlist: string[] | null | undefined): string | undefined {
  if (!watchlist || watchlist.length === 0) {
    return undefined;
  }
  return watchlist.join(",");
}

/** Bumped per `loadUpcoming` call; a response commits only if still the newest. */
let upcomingGeneration = 0;

export const useEarningsStore = create<EarningsState>((set, get) => ({
  upcoming: null,
  upcomingStatus: "idle",
  upcomingError: null,
  upcomingCause: null,
  lastDays: DEFAULT_DAYS,
  lastWatchlist: null,
  histories: {},
  historyErrors: {},
  surprises: {},
  surpriseErrors: {},
  estimates: {},
  estimateErrors: {},

  loadUpcoming: async (days = DEFAULT_DAYS, watchlist = null) => {
    // Only the newest window commits: a slower 7-day response landing after
    // the 30-day one is dropped (R15-CODE-FRONTEND-017).
    const generation = ++upcomingGeneration;
    set({
      upcomingStatus: "loading",
      upcomingError: null,
      upcomingCause: null,
      lastDays: days,
      lastWatchlist: watchlist,
    });
    try {
      const payload = await sidecarGet<EarningsUpcomingResponse>("/earnings/upcoming", {
        days,
        watchlist: watchlistToParam(watchlist),
      });
      if (generation !== upcomingGeneration) return;
      set({ upcoming: payload, upcomingStatus: "ready", upcomingError: null, upcomingCause: null });
    } catch (err: unknown) {
      if (generation !== upcomingGeneration) return;
      const message = err instanceof Error ? err.message : "Failed to load upcoming earnings";
      set({ upcomingStatus: "error", upcomingError: message, upcomingCause: err, upcoming: null });
    }
  },

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
      const payload = await sidecarGet<EarningsHistoryResponse>(
        `/earnings/${encodeURIComponent(normalized)}/history`,
      );
      set((state) => ({
        histories: { ...state.histories, [normalized]: { payload, fetchedAt: Date.now() } },
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
    if (cached && isFresh(cached.fetchedAt)) {
      return cached.payload;
    }
    try {
      const payload = await sidecarGet<EarningsSurprisesResponse>(
        `/earnings/${encodeURIComponent(normalized)}/surprises`,
      );
      set((state) => ({
        surprises: { ...state.surprises, [normalized]: { payload, fetchedAt: Date.now() } },
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
    if (cached && isFresh(cached.fetchedAt)) {
      return cached.payload;
    }
    try {
      const payload = await sidecarGet<EarningsEstimateDetail>(
        `/earnings/${encodeURIComponent(normalized)}/estimates`,
      );
      set((state) => ({
        estimates: { ...state.estimates, [normalized]: { payload, fetchedAt: Date.now() } },
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

  refresh: async (symbol) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return;
    }
    // Evict first so getHistory/getSurprises/getEstimates cannot short-circuit
    // on a still-fresh cache entry (R15-DATA-068's "Refresh button" path).
    set((state) => {
      const { [normalized]: _h, ...histories } = state.histories;
      const { [normalized]: _s, ...surprises } = state.surprises;
      const { [normalized]: _e, ...estimates } = state.estimates;
      return { histories, surprises, estimates };
    });
    await Promise.all([
      get().getHistory(normalized),
      get().getSurprises(normalized),
      get().getEstimates(normalized),
    ]);
  },

  __resetForTests: () =>
    set({
      upcoming: null,
      upcomingStatus: "idle",
      upcomingError: null,
      upcomingCause: null,
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
