import { create } from "zustand";

import { DEFAULT_REGION, type Region } from "@/lib/region";

/**
 * Shared symbol-list store.
 *
 * The single source of truth for the user's tracked symbol list. The watchlist
 * panel reads/writes it directly; downstream panels (news feed, charts, …)
 * subscribe read-only so they react when the watchlist changes. Only the
 * symbol list and its asset class live here — quote data is fetched live by
 * each panel and never persisted. The default symbols match the first-launch
 * watchlist from BLUEPRINT §5.1, region-seeded (R15-UI-076): a clean IN profile
 * (the app default) opens on NSE names, not a US watchlist.
 */

/** A tracked symbol plus the asset class the sidecar should resolve it under. */
export interface SymbolEntry {
  symbol: string;
  assetClass: "equity" | "crypto";
}

/**
 * The asset class a bare symbol names: a slash pair (`BTC/USDT`) is the app's
 * crypto notation, everything else an equity. The one place a symbol that
 * crossed panels without its entry recovers its class (R15-DATA-081).
 */
export function assetClassOf(symbol: string): SymbolEntry["assetClass"] {
  return symbol.includes("/") ? "crypto" : "equity";
}

const US_DEFAULT_SYMBOLS: SymbolEntry[] = [
  { symbol: "SPY", assetClass: "equity" },
  { symbol: "QQQ", assetClass: "equity" },
  { symbol: "BTC/USDT", assetClass: "crypto" },
  { symbol: "ETH/USDT", assetClass: "crypto" },
  { symbol: "NVDA", assetClass: "equity" },
  { symbol: "AAPL", assetClass: "equity" },
];

const IN_DEFAULT_SYMBOLS: SymbolEntry[] = [
  { symbol: "^NSEI", assetClass: "equity" }, // NIFTY 50
  { symbol: "RELIANCE.NS", assetClass: "equity" },
  { symbol: "TCS.NS", assetClass: "equity" },
  { symbol: "HDFCBANK.NS", assetClass: "equity" },
];

/** The first-launch watchlist for a region (BLUEPRINT §5.1, R15-UI-076): `IN`
 *  (the app default) seeds NSE names instead of the US list. */
export function defaultSymbolsForRegion(region: Region): SymbolEntry[] {
  return region === "IN" ? IN_DEFAULT_SYMBOLS : US_DEFAULT_SYMBOLS;
}

/** The pre-loaded first-launch symbol list for the app's default region. */
export const DEFAULT_SYMBOLS: SymbolEntry[] = defaultSymbolsForRegion(DEFAULT_REGION);

interface SymbolsState {
  /** Tracked entries, in display order. */
  entries: SymbolEntry[];
  /** Add a symbol if not already tracked (case-insensitive de-dup). */
  addSymbol: (symbol: string, assetClass: "equity" | "crypto") => void;
  /** Remove a tracked symbol. */
  removeSymbol: (symbol: string) => void;
  /** Replace the whole list — used to restore a persisted watchlist on launch. */
  setEntries: (entries: SymbolEntry[]) => void;
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
  setEntries: (entries) =>
    set(() => ({
      // Normalise + de-dup so a corrupt persisted blob can't seed garbage.
      entries: entries
        .filter((e) => e && typeof e.symbol === "string" && e.symbol.trim() !== "")
        .map((e) => ({
          symbol: e.symbol.trim().toUpperCase(),
          assetClass: e.assetClass === "crypto" ? "crypto" : "equity",
        })),
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
