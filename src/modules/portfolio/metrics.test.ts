import { describe, expect, it } from "vitest";

import type { Position, Quote } from "../../../types/data";
import { buildPortfolioSummary } from "./metrics";

function pos(symbol: string, quantity: number, cost: number): Position {
  return { symbol, quantity, cost_basis: cost, asset_class: "equity" } as Position;
}
function quote(symbol: string, price: number, currency = "USD"): Quote {
  return { symbol, price, currency } as Quote;
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
    expect(s.byCurrency).toEqual([]);
    expect(s.mixedCurrencies).toBe(false);
  });

  it("single-currency portfolio: one bucket, mixedCurrencies false (D57)", () => {
    const positions = [pos("AAPL", 10, 100), pos("MSFT", 2, 300)];
    const quotes = new Map([
      ["AAPL", quote("AAPL", 150)],
      ["MSFT", quote("MSFT", 400)],
    ]);
    const s = buildPortfolioSummary(positions, quotes);
    expect(s.mixedCurrencies).toBe(false);
    expect(s.byCurrency).toHaveLength(1);
    expect(s.byCurrency[0]).toMatchObject({
      currency: "USD",
      marketValue: 1500 + 800,
      pnl: 500 + 200,
      resolvedCost: 1000 + 600,
    });
    // The single bucket IS the aggregate — the legacy totals stay honest.
    expect(s.byCurrency[0].marketValue).toBe(s.totalMarketValue);
    expect(s.byCurrency[0].pnl).toBe(s.totalPnl);
  });

  it("mixed-currency portfolio: per-currency subtotals, never a cross-currency sum (D57)", () => {
    // RELIANCE quoted in INR, AAPL in USD — 50×1,293 = ₹64,650 and 10×120 = $1,200.
    const positions = [pos("RELIANCE.NS", 50, 1200), pos("AAPL", 10, 100)];
    const quotes = new Map([
      ["RELIANCE.NS", quote("RELIANCE.NS", 1293, "INR")],
      ["AAPL", quote("AAPL", 120, "USD")],
    ]);
    const s = buildPortfolioSummary(positions, quotes);
    expect(s.mixedCurrencies).toBe(true);
    expect(s.byCurrency).toHaveLength(2);
    const inr = s.byCurrency.find((b) => b.currency === "INR");
    const usd = s.byCurrency.find((b) => b.currency === "USD");
    expect(inr).toMatchObject({ marketValue: 64_650, pnl: 64_650 - 60_000, resolvedCost: 60_000 });
    expect(inr?.pnlPercent).toBeCloseTo(((64_650 - 60_000) / 60_000) * 100);
    expect(usd).toMatchObject({ marketValue: 1_200, pnl: 200, resolvedCost: 1_000 });
    expect(usd?.pnlPercent).toBeCloseTo(20);
  });

  it("unresolved positions join no currency bucket; a blank quote currency buckets as ''", () => {
    const positions = [pos("AAPL", 1, 100), pos("ZZZZ", 1, 100), pos("MYST", 1, 10)];
    const quotes = new Map([
      ["AAPL", quote("AAPL", 150)],
      // A quote whose provider sent no usable currency code.
      ["MYST", quote("MYST", 20, "")],
    ]);
    const s = buildPortfolioSummary(positions, quotes);
    // ZZZZ never resolved — it must not appear in any bucket.
    expect(s.byCurrency.reduce((n, b) => n + b.resolvedCost, 0)).toBe(110);
    expect(s.byCurrency.map((b) => b.currency).sort()).toEqual(["", "USD"]);
    // Two DISTINCT buckets → mixed (the "" bucket formats via region fallback).
    expect(s.mixedCurrencies).toBe(true);
  });
});
