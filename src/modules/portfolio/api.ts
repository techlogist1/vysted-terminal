/**
 * Portfolio live quotes.
 *
 * Holdings are tracked client-side (`src/store/portfolios.ts`, persisted in the
 * workspace blob) — nothing in the app writes the sidecar positions ledger. Only
 * the LIVE QUOTES for P&L come from the sidecar; the panel joins holdings to
 * quotes and computes P&L, weight, and risk metrics client-side. The ledger is
 * read once, to import holdings saved before they moved into the blob.
 */

import { getSidecarBaseUrl, sidecarApi, sidecarRequest } from "@/lib/sidecar-client";
import type { HoldingInput } from "@/store/portfolios";
import type { OHLCVSeries, Position, Quote } from "../../../types/data";

/** The minimal shape needed to resolve a live quote for a holding. */
export interface QuoteTarget {
  symbol: string;
  assetClass: string;
  /** The holding's own listing region (R15-FINAL-001), never the session's. */
  region?: string;
}

/** A cold batch at the route's bounded concurrency outlasts the 30 s list/CRUD
 *  default by far; aborting it early only re-sends the same work while the
 *  sidecar is still finishing the last one (R15-FINAL-006). */
export const QUOTES_BATCH_TIMEOUT_MS = 120_000;

/**
 * Fetch live quotes for a set of holdings through the batch `/quotes` route:
 * one request per (region, asset class), each sent with that listing region
 * (R15-FINAL-001). Quotes are keyed by upper-cased symbol; `failed` counts the
 * batch REQUESTS that failed (sidecar down, timeout), while `missing` lists the
 * symbols a completed batch answered without — a row-level "no quote", never
 * the transport banner (R15-FINAL-017; R15-UI-004 is the converse).
 */
export async function fetchPositionQuotes(
  targets: QuoteTarget[],
): Promise<{ quotes: Map<string, Quote>; failed: number; missing: string[] }> {
  const groups = new Map<string, { region?: string; assetClass: string; symbols: Set<string> }>();
  for (const t of targets) {
    const key = `${t.region ?? ""}|${t.assetClass}`;
    const group = groups.get(key) ?? {
      region: t.region,
      assetClass: t.assetClass,
      symbols: new Set<string>(),
    };
    group.symbols.add(t.symbol.toUpperCase());
    groups.set(key, group);
  }
  const quotes = new Map<string, Quote>();
  const missing: string[] = [];
  let failed = 0;
  await Promise.all(
    [...groups.values()].map(async ({ region, assetClass, symbols }) => {
      try {
        const rows = await sidecarRequest<Quote[]>("GET", "/quotes", {
          params: { symbols: [...symbols].join(","), asset_class: assetClass },
          headers: { "X-Vysted-Region": region },
          timeoutMs: QUOTES_BATCH_TIMEOUT_MS,
        });
        const answered = new Set<string>();
        for (const quote of rows) {
          quotes.set(quote.symbol.toUpperCase(), quote);
          answered.add(quote.symbol.toUpperCase());
        }
        missing.push(...[...symbols].filter((symbol) => !answered.has(symbol)));
      } catch {
        failed += 1;
      }
    }),
  );
  return { quotes, failed, missing };
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
