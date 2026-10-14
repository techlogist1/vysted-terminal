/**
 * Watchlist sidecar access.
 *
 * Built on the shared `sidecarApi` accessors — equities resolve through the
 * batch `/quotes` endpoint (one call per region), crypto through
 * `/crypto/ticker` (one call per symbol, since the batch endpoint is equity-only). The panel polls
 * `fetchWatchlistQuotes` on an interval for near-real-time updates.
 */

import { sidecarApi } from "@/lib/sidecar-client";
import { entryKey, type SymbolEntry } from "@/store/symbols";
import type { Quote } from "../../../types/data";

/** The crypto exchange the watchlist resolves crypto symbols against. */
export const WATCHLIST_CRYPTO_EXCHANGE = "binance";

/** A watchlist row: the tracked entry joined with its latest quote (if resolved). */
export interface WatchlistRow {
  entry: SymbolEntry;
  /** `null` is still loading, or `unavailable` once a refresh completed without it. */
  quote: Quote | null;
  unavailable?: boolean;
}

/**
 * Fetch the latest quote for every tracked entry.
 *
 * Equity symbols go through one batched `/quotes` call per region — a picked
 * listing sends its own region, a region-less entry the session's
 * (R15-DATA-002) — and each quote is stamped with the requested spelling (C14);
 * crypto symbols are fetched individually. Rows join on {@link entryKey}. A
 * symbol absent from its completed batch (or a failed crypto fetch) comes back
 * with a `null` quote, which the panel shows as unavailable, rather than failing
 * the whole refresh.
 */
export async function fetchWatchlistQuotes(entries: SymbolEntry[]): Promise<WatchlistRow[]> {
  const equityByRegion = new Map<string | undefined, string[]>();
  for (const entry of entries) {
    if (entry.assetClass === "equity") {
      equityByRegion.set(entry.region, [...(equityByRegion.get(entry.region) ?? []), entry.symbol]);
    }
  }
  const cryptoEntries = entries.filter((entry) => entry.assetClass === "crypto");

  const equityQuotes = new Map<string, Quote>();
  const batches = await Promise.all(
    [...equityByRegion].map(async ([region, symbols]) => ({
      region,
      quotes: await sidecarApi.quotes(symbols, "equity", region),
    })),
  );
  for (const { region, quotes } of batches) {
    for (const quote of quotes) {
      equityQuotes.set(entryKey({ symbol: quote.symbol, assetClass: "equity", region }), quote);
    }
  }

  const cryptoResults = await Promise.all(
    cryptoEntries.map(async (entry): Promise<[string, Quote | null]> => {
      try {
        const quote = await sidecarApi.cryptoTicker(WATCHLIST_CRYPTO_EXCHANGE, entry.symbol);
        return [entryKey(entry), quote];
      } catch {
        return [entryKey(entry), null];
      }
    }),
  );
  const cryptoQuotes = new Map<string, Quote | null>(cryptoResults);

  return entries.map((entry) => {
    const key = entryKey(entry);
    const quote =
      entry.assetClass === "crypto"
        ? (cryptoQuotes.get(key) ?? null)
        : (equityQuotes.get(key) ?? null);
    return { entry, quote };
  });
}
