import { describe, expect, it } from "vitest";

import type { Position, Quote } from "../../../types/data";
import { buildPortfolioSummary } from "./metrics";

function pos(symbol: string, quantity: number, cost: number): Position {
  return { symbol, quantity, cost_basis: cost, asset_class: "equity" } as Position;
}
function quote(symbol: string, price: number): Quote {
  return { symbol, price } as Quote;
}

describe("buildPortfolioSummary", () => {
  it("computes coherent totals when all quotes resolve", () => {
    const positions = [pos("AAPL", 10, 100)]; // cost 1000
    const quotes = new Map([["AAPL", quote("AAPL", 150)]]); // mv 1500, pnl +500
    const s = buildPortfolioSummary(positions, quotes);
    expect(s.totalCost).toBe(1000);
    expect(s.resolvedCost).toBe(1000);
    expect(s.totalMarketValue).toBe(1500);
    expect(s.totalPnl).toBe(500);
    expect(s.totalPnlPercent).toBeCloseTo(50);
    expect(s.unresolvedCount).toBe(0);
  });

  it("excludes unresolved positions from the P&L% denominator (F-GUI-1)", () => {
    // One resolved (+500 on 1000 cost = +50%), one with NO quote and a large cost.
    const positions = [pos("AAPL", 10, 100), pos("ZZZZ", 100, 1000)];
    const quotes = new Map([["AAPL", quote("AAPL", 150)]]);
    const s = buildPortfolioSummary(positions, quotes);
    // totalCost includes the unresolved position; resolvedCost does not.
    expect(s.totalCost).toBe(1000 + 100_000);
    expect(s.resolvedCost).toBe(1000);
    expect(s.totalMarketValue).toBe(1500);
    expect(s.totalPnl).toBe(500);
    // The fix: P&L% is 500/1000 = +50%, NOT 500/101000 = +0.495% (misleading).
    expect(s.totalPnlPercent).toBeCloseTo(50);
    expect(s.unresolvedCount).toBe(1);
  });

  it("returns 0% (not NaN) when no positions resolve", () => {
    const positions = [pos("ZZZZ", 1, 100)];
    const s = buildPortfolioSummary(positions, new Map());
    expect(s.resolvedCost).toBe(0);
    expect(s.totalPnl).toBe(0);
    expect(s.totalPnlPercent).toBe(0);
    expect(Number.isFinite(s.totalPnlPercent)).toBe(true);
  });
});
