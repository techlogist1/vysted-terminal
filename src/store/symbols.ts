import { create } from "zustand";

import { REGIONS } from "@/lib/region";

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
  /** The listing's region when the user picked one (AMAL is Amal Ltd in IN and
   *  Amalgamated Financial in US); absent follows the session region (R15-DATA-002). */
  region?: string;
}

/** One key per tracked listing: the same ticker in two regions is two entries. */
export function entryKey(entry: SymbolEntry): string {
  return `${entry.region ?? ""}|${entry.symbol.toUpperCase()}`;
}

/**
 * The asset class a bare symbol names: a slash pair (`BTC/USDT`) is the app's
 * crypto notation, everything else an equity. The one place a symbol that
 * crossed panels without its entry recovers its class (R15-DATA-081).
 */
export function assetClassOf(symbol: string): SymbolEntry["assetClass"] {
  return symbol.includes("/") ? "crypto" : "equity";
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
  /** Add a symbol if that listing is not already tracked (case-insensitive symbol + region). */
  addSymbol: (symbol: string, assetClass: "equity" | "crypto", region?: string) => void;
  /** Remove a tracked symbol: every listing of it, or with `region` only that one
   *  (`null` names the region-less entry). */
  removeSymbol: (symbol: string, region?: string | null) => void;
  /** Replace the whole list — used to restore a persisted watchlist on launch. */
  setEntries: (entries: SymbolEntry[]) => void;
}

/** The shared symbol-list store, seeded with the default watchlist. */
export const useSymbolsStore = create<SymbolsState>((set) => ({
  entries: [...DEFAULT_SYMBOLS],
  addSymbol: (symbol, assetClass, region) =>
    set((state) => {
      const normalized = symbol.trim().toUpperCase();
      if (normalized === "") {
        return state;
      }
      const entry: SymbolEntry = region
        ? { symbol: normalized, assetClass, region }
        : { symbol: normalized, assetClass };
      if (state.entries.some((e) => entryKey(e) === entryKey(entry))) {
        return state;
      }
      return { entries: [...state.entries, entry] };
    }),
  removeSymbol: (symbol, region) =>
    set((state) => ({
      entries: state.entries.filter(
        (entry) =>
          entry.symbol.toUpperCase() !== symbol.toUpperCase() ||
          (region !== undefined && (entry.region ?? null) !== region),
      ),
    })),
  setEntries: (entries) =>
    set(() => ({
      // Normalise + de-dup so a corrupt persisted blob can't seed garbage.
      entries: entries
        .filter((e) => e && typeof e.symbol === "string" && e.symbol.trim() !== "")
        .map((e): SymbolEntry => {
          const entry: SymbolEntry = {
            symbol: e.symbol.trim().toUpperCase(),
            assetClass: e.assetClass === "crypto" ? "crypto" : "equity",
          };
          // The persisted blob is a trust boundary: keep only a known region.
          if (REGIONS.some((r) => r.id === e.region)) entry.region = e.region;
          return entry;
        }),
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
