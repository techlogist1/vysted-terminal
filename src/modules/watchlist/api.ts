/**
 * Watchlist sidecar access.
 *
 * Built on the shared `sidecarApi` accessors — equities resolve through the
 * batch `/quotes` endpoint, crypto through `/crypto/ticker` (one call per
 * symbol, since the batch endpoint is equity-only). The panel polls
 * `fetchWatchlistQuotes` on an interval for near-real-time updates.
 */

import { sidecarApi } from "@/lib/sidecar-client";
import type { Quote } from "../../../types/data";
import type { WatchlistEntry } from "./store";

/** The crypto exchange the watchlist resolves crypto symbols against. */
export const WATCHLIST_CRYPTO_EXCHANGE = "binance";

/** A watchlist row: the tracked entry joined with its latest quote (if resolved). */
export interface WatchlistRow {
  entry: WatchlistEntry;
  quote: Quote | null;
}

/**
 * Fetch the latest quote for every tracked entry.
 *
 * Equity symbols go through one batched `/quotes` call; crypto symbols are
 * fetched individually. A symbol that fails to resolve comes back with a
 * `null` quote rather than failing the whole refresh.
 */
export async function fetchWatchlistQuotes(entries: WatchlistEntry[]): Promise<WatchlistRow[]> {
  const equitySymbols = entries
    .filter((entry) => entry.assetClass === "equity")
    .map((entry) => entry.symbol);
  const cryptoEntries = entries.filter((entry) => entry.assetClass === "crypto");

  const equityQuotes = new Map<string, Quote>();
  if (equitySymbols.length > 0) {
    const quotes = await sidecarApi.quotes(equitySymbols);
    for (const quote of quotes) {
      equityQuotes.set(quote.symbol.toUpperCase(), quote);
    }
  }

  const cryptoResults = await Promise.all(
    cryptoEntries.map(async (entry): Promise<[string, Quote | null]> => {
      try {
        const quote = await sidecarApi.cryptoTicker(WATCHLIST_CRYPTO_EXCHANGE, entry.symbol);
        return [entry.symbol.toUpperCase(), quote];
      } catch {
        return [entry.symbol.toUpperCase(), null];
      }
    }),
  );
  const cryptoQuotes = new Map<string, Quote | null>(cryptoResults);

  return entries.map((entry) => {
    const key = entry.symbol.toUpperCase();
    const quote =
      entry.assetClass === "crypto"
        ? (cryptoQuotes.get(key) ?? null)
        : (equityQuotes.get(key) ?? null);
    return { entry, quote };
  });
}
