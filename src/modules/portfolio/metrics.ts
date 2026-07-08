/**
 * Portfolio metrics — computed client-side by joining stored positions with
 * live quotes. The sidecar persists only the manually entered facts; P&L,
 * weight, and basic risk metrics are derived here so no extra sidecar model is
 * needed (per the Phase 1.B brief).
 */

import type { Position, Quote } from "../../../types/data";

/** A position joined with its live quote and derived per-position metrics. */
export interface PositionRow {
  position: Position;
  quote: Quote | null;
  /** Cost basis × quantity. */
  costValue: number;
  /** Live price × quantity, or `null` when the quote did not resolve. */
  marketValue: number | null;
  /** Market value − cost value, or `null` without a quote. */
  pnl: number | null;
  /** P&L as a percentage of cost value, or `null` without a quote. */
  pnlPercent: number | null;
  /** Share of total portfolio market value (0–1), or `null` without a quote. */
  weight: number | null;
}

/**
 * Per-currency roll-up (R11 / D57). A portfolio can hold instruments quoted in
 * different currencies; summing their raw values is a fabricated number
 * (₹64,650 + $1,200 is not 65,850 of anything). Each resolved position lands
 * in the bucket of its QUOTE's currency; the UI renders one subtotal per
 * bucket and never a cross-currency aggregate.
 */
export interface CurrencySubtotal {
  /** Normalized quote currency code ("" when the quote carried none — such a
   *  bucket formats with the region fallback, exactly as before D57). */
  currency: string;
  /** Sum of resolved market values quoted in this currency. */
  marketValue: number;
  /** Unrealised P&L of the resolved positions in this currency. */
  pnl: number;
  /** Cost of the RESOLVED positions in this currency (denominator-matched). */
  resolvedCost: number;
  /** P&L as a percentage of {@link resolvedCost} (0 when that cost is 0). */
  pnlPercent: number;
}

/** Portfolio-level roll-up across every position. */
export interface PortfolioSummary {
  rows: PositionRow[];
  /** Sum of cost values across ALL positions (resolved or not). */
  totalCost: number;
  /** Sum of cost values across only positions with a resolved quote. */
  resolvedCost: number;
  /**
   * Sum of resolved market values. HONEST ONLY when {@link mixedCurrencies}
   * is false — a cross-currency sum is a fabricated number (D57); when mixed,
   * render {@link byCurrency} instead and never publish this as a total.
   */
  totalMarketValue: number;
  /** Total unrealised P&L across resolved positions — same D57 caveat as
   *  {@link totalMarketValue} when currencies are mixed. */
  totalPnl: number;
  /**
   * Total P&L as a percentage of the cost of the RESOLVED positions only.
   * Denominator-matched to {@link totalPnl} — counting unresolved positions'
   * cost into the denominator (while their P&L is necessarily excluded from the
   * numerator) produced a misleading percentage (Phase 9.5 F-GUI-1).
   */
  totalPnlPercent: number;
  /** Largest single-position weight (0–1) — a basic concentration metric. */
  concentration: number;
  /** Count of positions whose live quote failed to resolve. */
  unresolvedCount: number;
  /** Per-currency subtotals across the RESOLVED positions, in first-seen
   *  order (R11 / D57). Empty when nothing resolved. */
  byCurrency: CurrencySubtotal[];
  /** True when the resolved positions span more than one quote currency —
   *  the aggregate totals above are then fabricated; use {@link byCurrency}. */
  mixedCurrencies: boolean;
}

/** Normalize a quote's currency for bucketing ("usd " → "USD"; absent → ""). */
function currencyKey(quote: Quote | null): string {
  return (quote?.currency ?? "").trim().toUpperCase();
}

/** Join positions to quotes and compute per-position + portfolio-level metrics. */
export function buildPortfolioSummary(
  positions: Position[],
  quotes: Map<string, Quote>,
): PortfolioSummary {
  const partials = positions.map((position) => {
    const quote = quotes.get(position.symbol.toUpperCase()) ?? null;
    const costValue = position.cost_basis * position.quantity;
    const marketValue = quote !== null ? quote.price * position.quantity : null;
    const pnl = marketValue !== null ? marketValue - costValue : null;
    // P&L% is undefined for a zero cost basis (vested shares / RSUs are a valid
    // cost_basis=0 case) — return null so the UI shows "—" rather than a
    // misleading "+0.00%" on a real gain (hunt-state-logic).
    const pnlPercent = pnl !== null && costValue !== 0 ? (pnl / costValue) * 100 : null;
    return { position, quote, costValue, marketValue, pnl, pnlPercent };
  });

  const totalCost = partials.reduce((sum, row) => sum + row.costValue, 0);
  // Resolved cost = cost of the positions whose quote resolved — the only cost
  // that can legitimately back the resolved P&L numerator.
  const resolvedCost = partials.reduce(
    (sum, row) => sum + (row.marketValue !== null ? row.costValue : 0),
    0,
  );
  const totalMarketValue = partials.reduce((sum, row) => sum + (row.marketValue ?? 0), 0);
  const totalPnl = partials.reduce((sum, row) => sum + (row.pnl ?? 0), 0);
  const totalPnlPercent = resolvedCost !== 0 ? (totalPnl / resolvedCost) * 100 : 0;

  // Per-currency buckets (D57) — resolved positions only, keyed by the QUOTE's
  // currency (positions are entered in the listing currency; the quote is the
  // instrument-truth for what unit the numbers are in).
  const buckets = new Map<string, CurrencySubtotal>();
  for (const row of partials) {
    if (row.marketValue === null) {
      continue;
    }
    const key = currencyKey(row.quote);
    const bucket = buckets.get(key) ?? {
      currency: key,
      marketValue: 0,
      pnl: 0,
      resolvedCost: 0,
      pnlPercent: 0,
    };
    bucket.marketValue += row.marketValue;
    bucket.pnl += row.pnl ?? 0;
    bucket.resolvedCost += row.costValue;
    buckets.set(key, bucket);
  }
  const byCurrency = [...buckets.values()].map((b) => ({
    ...b,
    pnlPercent: b.resolvedCost !== 0 ? (b.pnl / b.resolvedCost) * 100 : 0,
  }));
  const mixedCurrencies = byCurrency.length > 1;

  const rows: PositionRow[] = partials.map((row) => ({
    ...row,
    weight:
      row.marketValue !== null && totalMarketValue !== 0
        ? row.marketValue / totalMarketValue
        : null,
  }));

  const concentration = rows.reduce((max, row) => Math.max(max, row.weight ?? 0), 0);
  const unresolvedCount = rows.filter((row) => row.quote === null).length;

  return {
    rows,
    totalCost,
    resolvedCost,
    totalMarketValue,
    totalPnl,
    totalPnlPercent,
    concentration,
    unresolvedCount,
    byCurrency,
    mixedCurrencies,
  };
}
