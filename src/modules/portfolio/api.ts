/**
 * Portfolio live quotes.
 *
 * Holdings are tracked client-side (`src/store/portfolios.ts`, persisted in the
 * workspace blob) — nothing in the app writes the sidecar positions ledger. Only
 * the LIVE QUOTES for P&L come from the sidecar; the panel joins holdings to
 * quotes and computes P&L, weight, and risk metrics client-side. The ledger is
 * read once, to import holdings saved before they moved into the blob.
 */

import { getSidecarBaseUrl, sidecarApi } from "@/lib/sidecar-client";
import type { HoldingInput } from "@/store/portfolios";
import type { OHLCVSeries, Position, Quote } from "../../../types/data";

/** The minimal shape needed to resolve a live quote for a holding. */
export interface QuoteTarget {
  symbol: string;
  assetClass: string;
}

/** The outcome of resolving one holding's live quote — a real failure (network
 *  down, sidecar 502, etc.) is distinct from a plain success, so a caller can
 *  tell "the fetch failed" apart from "the row has no quote". */
export type QuoteFetchResult = { quote: Quote } | { error: string };

/**
 * Fetch a live quote for one symbol, mapping the asset class onto the sidecar's
 * quote endpoint. A failed fetch comes back as `{error}`, never a swallowed
 * `null` — the caller decides how to surface it (R15-UI-004: collapsing every
 * failure into `null` made the panel's failure banner unreachable).
 */
export async function fetchPositionQuote(
  symbol: string,
  assetClass: string,
): Promise<QuoteFetchResult> {
  try {
    return { quote: await sidecarApi.quote(symbol, assetClass) };
  } catch (err) {
    return { error: err instanceof Error ? err.message : String(err) };
  }
}

/** Fetch live quotes for a set of holdings, keyed by upper-cased symbol, plus
 *  a count of the ones that failed to fetch (as opposed to a quote map with no
 *  signal either way). */
export async function fetchPositionQuotes(
  targets: QuoteTarget[],
): Promise<{ quotes: Map<string, Quote>; failed: number }> {
  const quotes = new Map<string, Quote>();
  const results = await Promise.all(targets.map((t) => fetchPositionQuote(t.symbol, t.assetClass)));
  let failed = 0;
  targets.forEach((t, index) => {
    const result = results[index];
    if ("quote" in result) {
      quotes.set(t.symbol.toUpperCase(), result.quote);
    } else {
      failed += 1;
    }
  });
  return { quotes, failed };
}

/**
 * The holdings in the sidecar's SQLite positions ledger (`GET
 * /portfolio/positions`), where tracked holdings lived before they moved into
 * the workspace blob. Empty when the ledger is empty or unreadable.
 */
export async function fetchLegacyPositions(): Promise<HoldingInput[]> {
  const base = await getSidecarBaseUrl();
  const response = await fetch(new URL("/portfolio/positions", base).toString());
  if (!response.ok) {
    return [];
  }
  const rows: unknown = await response.json();
  if (!Array.isArray(rows)) {
    return [];
  }
  return (rows as Position[]).map((row) => ({
    symbol: row.symbol,
    quantity: row.quantity,
    costBasis: row.cost_basis,
    assetClass: row.asset_class === "crypto" ? "crypto" : "equity",
    note: row.note ?? undefined,
  }));
}

// --- Risk analytics price history (R15-CODE-PLATFORM-023) ------------------

/** The benchmark `/history` symbol for a resolved-quote currency bucket, or
 *  `null` when there's no named benchmark for it (beta stays null for that
 *  bucket — an honest gap, never a wrong index substituted in). */
export function benchmarkSymbolForCurrency(currency: string): string | null {
  switch (currency.trim().toUpperCase()) {
    case "INR":
      return "^NSEI";
    case "USD":
      return "SPY";
    default:
      return null;
  }
}

/**
 * One year of daily closes for `symbol`, keyed by ISO date (`YYYY-MM-DD`).
 * `null` on any fetch failure or an empty series — the caller treats it as
 * "this symbol/benchmark has no usable history", never a zero-filled series.
 */
export async function fetchDailyCloses(
  symbol: string,
  assetClass: string,
): Promise<Map<string, number> | null> {
  try {
    const series: OHLCVSeries = await sidecarApi.history(symbol, "1d", "1y", assetClass);
    if (series.bars.length === 0) return null;
    const closes = new Map<string, number>();
    for (const bar of series.bars) {
      closes.set(bar.timestamp.slice(0, 10), bar.close);
    }
    return closes;
  } catch {
    return null;
  }
}
