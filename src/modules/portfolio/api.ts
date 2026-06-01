/**
 * Portfolio live quotes.
 *
 * Holdings are tracked client-side (`src/store/portfolios.ts`, persisted in the
 * workspace blob) — there is NO sidecar positions CRUD. Only the LIVE QUOTES for
 * P&L come from the sidecar; the panel joins holdings to quotes and computes
 * P&L, weight, and risk metrics client-side.
 */

import { sidecarApi } from "@/lib/sidecar-client";
import type { Quote } from "../../../types/data";

/** The minimal shape needed to resolve a live quote for a holding. */
export interface QuoteTarget {
  symbol: string;
  assetClass: string;
}

/**
 * Fetch a live quote for one symbol, mapping the asset class onto the sidecar's
 * quote endpoint. A symbol that fails to resolve comes back `null`.
 */
export async function fetchPositionQuote(
  symbol: string,
  assetClass: string,
): Promise<Quote | null> {
  try {
    return await sidecarApi.quote(symbol, assetClass);
  } catch {
    return null;
  }
}

/** Fetch live quotes for a set of holdings, keyed by upper-cased symbol. */
export async function fetchPositionQuotes(targets: QuoteTarget[]): Promise<Map<string, Quote>> {
  const quotes = new Map<string, Quote>();
  const results = await Promise.all(targets.map((t) => fetchPositionQuote(t.symbol, t.assetClass)));
  targets.forEach((t, index) => {
    const quote = results[index];
    if (quote !== null) {
      quotes.set(t.symbol.toUpperCase(), quote);
    }
  });
  return quotes;
}
