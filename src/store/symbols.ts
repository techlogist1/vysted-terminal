import { create } from "zustand";

/**
 * Shared symbol-list store.
 *
 * The single source of truth for the user's tracked symbol list. The watchlist
 * panel reads/writes it directly; downstream panels (news feed, charts, …)
 * subscribe read-only so they react when the watchlist changes. Only the
 * symbol list and its asset class live here — quote data is fetched live by
 * each panel and never persisted. The default symbols match the first-launch
 * watchlist from BLUEPRINT §5.1.
 */

/** A tracked symbol plus the asset class the sidecar should resolve it under. */
export interface SymbolEntry {
  symbol: string;
  assetClass: "equity" | "crypto";
}

/** The pre-loaded first-launch symbol list (BLUEPRINT §5.1). */
export const DEFAULT_SYMBOLS: SymbolEntry[] = [
  { symbol: "SPY", assetClass: "equity" },
  { symbol: "QQQ", assetClass: "equity" },
  { symbol: "BTC/USDT", assetClass: "crypto" },
  { symbol: "ETH/USDT", assetClass: "crypto" },
  { symbol: "NVDA", assetClass: "equity" },
  { symbol: "AAPL", assetClass: "equity" },
];

interface SymbolsState {
  /** Tracked entries, in display order. */
  entries: SymbolEntry[];
  /** Add a symbol if not already tracked (case-insensitive de-dup). */
  addSymbol: (symbol: string, assetClass: "equity" | "crypto") => void;
  /** Remove a tracked symbol. */
  removeSymbol: (symbol: string) => void;
}

/** The shared symbol-list store, seeded with the default watchlist. */
export const useSymbolsStore = create<SymbolsState>((set) => ({
  entries: [...DEFAULT_SYMBOLS],
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

/**
 * Project a stored symbol into the form the news feed expects.
 *
 * The watchlist stores crypto pairs (e.g. `"BTC/USDT"`), but the news feed
 * tags by base asset (e.g. `"BTC"`). For pair-style symbols, return the part
 * before the first `/`; otherwise return the symbol unchanged.
 */
export function toNewsSymbol(entry: SymbolEntry): string {
  const slashAt = entry.symbol.indexOf("/");
  return slashAt === -1 ? entry.symbol : entry.symbol.slice(0, slashAt);
}
