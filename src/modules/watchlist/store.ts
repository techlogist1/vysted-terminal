import { create } from "zustand";

/**
 * Module-local watchlist store.
 *
 * Holds only the tracked symbol list and its asset class — quote data is
 * fetched live by the panel and never persisted here. The default symbols
 * match the first-launch watchlist from BLUEPRINT §5.1.
 */

/** A tracked symbol plus the asset class the sidecar should resolve it under. */
export interface WatchlistEntry {
  symbol: string;
  assetClass: "equity" | "crypto";
}

/** The pre-loaded first-launch watchlist (BLUEPRINT §5.1). */
export const DEFAULT_WATCHLIST: WatchlistEntry[] = [
  { symbol: "SPY", assetClass: "equity" },
  { symbol: "QQQ", assetClass: "equity" },
  { symbol: "BTC/USDT", assetClass: "crypto" },
  { symbol: "ETH/USDT", assetClass: "crypto" },
  { symbol: "NVDA", assetClass: "equity" },
  { symbol: "AAPL", assetClass: "equity" },
];

interface WatchlistState {
  /** Tracked entries, in display order. */
  entries: WatchlistEntry[];
  /** Add a symbol if not already tracked (case-insensitive de-dup). */
  addSymbol: (symbol: string, assetClass: "equity" | "crypto") => void;
  /** Remove a tracked symbol. */
  removeSymbol: (symbol: string) => void;
}

/** The watchlist symbol-list store, seeded with the default watchlist. */
export const useWatchlistStore = create<WatchlistState>((set) => ({
  entries: [...DEFAULT_WATCHLIST],
  addSymbol: (symbol, assetClass) =>
    set((state) => {
      const normalized = symbol.trim().toUpperCase();
      if (normalized === "") {
        return state;
      }
      if (state.entries.some((entry) => entry.symbol.toUpperCase() === normalized)) {
        return state;
      }
      return { entries: [...state.entries, { symbol: normalized, assetClass }] };
    }),
  removeSymbol: (symbol) =>
    set((state) => ({
      entries: state.entries.filter((entry) => entry.symbol.toUpperCase() !== symbol.toUpperCase()),
    })),
}));
