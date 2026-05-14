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

/** Portfolio-level roll-up across every position. */
export interface PortfolioSummary {
  rows: PositionRow[];
  /** Sum of cost values. */
  totalCost: number;
  /** Sum of resolved market values. */
  totalMarketValue: number;
  /** Total unrealised P&L across resolved positions. */
  totalPnl: number;
  /** Total P&L as a percentage of total cost. */
  totalPnlPercent: number;
  /** Largest single-position weight (0–1) — a basic concentration metric. */
  concentration: number;
  /** Count of positions whose live quote failed to resolve. */
  unresolvedCount: number;
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
    const pnlPercent =
      pnl !== null && costValue !== 0 ? (pnl / costValue) * 100 : pnl !== null ? 0 : null;
    return { position, quote, costValue, marketValue, pnl, pnlPercent };
  });

  const totalCost = partials.reduce((sum, row) => sum + row.costValue, 0);
  const totalMarketValue = partials.reduce((sum, row) => sum + (row.marketValue ?? 0), 0);
  const totalPnl = partials.reduce((sum, row) => sum + (row.pnl ?? 0), 0);
  const totalPnlPercent = totalCost !== 0 ? (totalPnl / totalCost) * 100 : 0;

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
    totalMarketValue,
    totalPnl,
    totalPnlPercent,
    concentration,
    unresolvedCount,
  };
}
