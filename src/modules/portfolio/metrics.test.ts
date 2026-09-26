import { describe, expect, it } from "vitest";

import type { Holding } from "@/store/portfolios";

import type { Quote } from "../../../types/data";
import {
  annualizedVolatility,
  beta,
  buildPortfolioSummary,
  calmarRatio,
  computeCurrencyRisk,
  correlation,
  dailyReturns,
  historicalVaR95,
  maxDrawdown,
  MIN_RISK_HISTORY_DAYS,
  sharpeRatio,
  sortinoRatio,
  type HoldingPriceHistory,
} from "./metrics";

function pos(symbol: string, quantity: number, cost: number): Holding {
  return { id: `h-${symbol}`, symbol, quantity, costBasis: cost, assetClass: "equity" };
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
    // R15-CODE-PLATFORM-053 (case the fix was not written against): a
    // single-currency portfolio still gets a real numeric concentration.
    expect(s.concentration).not.toBeNull();
    expect(s.concentration).toBeCloseTo(1500 / (1500 + 800));
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
    // R15-DATA-042 / R15-CODE-PLATFORM-053: weight and concentration are a
    // share of a cross-currency sum — the contract nulls them, not just the
    // panel that reads it.
    expect(s.concentration).toBeNull();
    expect(s.rows.every((r) => r.weight === null)).toBe(true);
  });

  it("rows carry the real holding id (R15-CODE-PLATFORM-050: no synthetic array-index id)", () => {
    const positions = [pos("AAPL", 10, 100), pos("MSFT", 2, 300)];
    const s = buildPortfolioSummary(positions, new Map());
    expect(s.rows.map((r) => r.position.id)).toEqual(["h-AAPL", "h-MSFT"]);
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

// R12 Gate 6: the operator's exact scenario — 5 RELIANCE + 5 INFY + 5 TATASTEEL,
// all INR (NSE). One currency bucket, a REAL non-zero totalValue (never the
// totalValue:0 fabrication D50 killed), correct per-symbol cost bases.
describe("Gate 6 — INR portfolio scenario (R12)", () => {
  it("5 RELIANCE + 5 INFY + 5 TATASTEEL yields correct cost bases and a non-zero INR total", () => {
    const positions = [
      pos("RELIANCE", 5, 1279.8),
      pos("INFY", 5, 1620.5),
      pos("TATASTEEL", 5, 165.3),
    ];
    const quotes = new Map([
      ["RELIANCE", quote("RELIANCE", 1279.8, "INR")],
      ["INFY", quote("INFY", 1620.5, "INR")],
      ["TATASTEEL", quote("TATASTEEL", 165.3, "INR")],
    ]);
    const s = buildPortfolioSummary(positions, quotes);
    // cost basis = qty x cost, summed: 5*(1279.8+1620.5+165.3) = 15328.0
    expect(s.totalCost).toBeCloseTo(15328.0, 2);
    expect(s.resolvedCost).toBeCloseTo(15328.0, 2);
    // a real, NON-ZERO market value — the gate's headline requirement
    expect(s.totalMarketValue).toBeCloseTo(15328.0, 2);
    expect(s.totalMarketValue).toBeGreaterThan(0);
    expect(s.unresolvedCount).toBe(0);
    // one INR bucket, no cross-currency fabrication
    expect(s.mixedCurrencies).toBe(false);
    expect(s.byCurrency).toHaveLength(1);
    expect(s.byCurrency[0].currency).toBe("INR");
    expect(s.byCurrency[0].marketValue).toBeCloseTo(15328.0, 2);
  });
});

// --- Risk analytics (R15-CODE-PLATFORM-023) ---------------------------------
// Hand-computed fixture: a 5-close series with deliberately non-constant
// returns (a flat-return series makes stdev = 0, which degenerates
// Sharpe/Sortino to 0 and would hide a wrong formula). Expected values below
// were computed independently in Python (float64, same formulas) and are
// asserted to 1e-9.
const RISK_CLOSES = [100, 110, 99, 108.9, 100.0];
const RISK_RETURNS = dailyReturns(RISK_CLOSES);

const RISK_BENCH_CLOSES = [50, 52, 49.4, 54.34, 51.0];
const RISK_BENCH_RETURNS = dailyReturns(RISK_BENCH_CLOSES);

describe("risk metric primitives (R15-CODE-PLATFORM-023)", () => {
  it("dailyReturns: simple day-over-day pct change", () => {
    expect(RISK_RETURNS).toHaveLength(4);
    expect(RISK_RETURNS[0]).toBeCloseTo(0.1, 9);
    expect(RISK_RETURNS[1]).toBeCloseTo(-0.1, 9);
    expect(RISK_RETURNS[2]).toBeCloseTo(0.1, 9);
    expect(RISK_RETURNS[3]).toBeCloseTo(-0.08172635445362719, 9);
  });

  it("annualizedVolatility: sample stdev x sqrt(252)", () => {
    expect(annualizedVolatility(RISK_RETURNS)).toBeCloseTo(1.7532940713065994, 9);
  });

  it("sharpeRatio: rf = 0, annualized mean / annualized vol", () => {
    expect(sharpeRatio(RISK_RETURNS)).toBeCloseTo(0.6566152753619742, 9);
  });

  it("sortinoRatio: MAR = 0, downside deviation over ALL observations", () => {
    expect(sortinoRatio(RISK_RETURNS)).toBeCloseTo(1.123072781986583, 9);
  });

  it("maxDrawdown: peak-to-trough on the implied equity curve", () => {
    expect(maxDrawdown(RISK_RETURNS)).toBeCloseTo(-0.09999999999999998, 9);
  });

  it("calmarRatio: annualized return / |max drawdown|", () => {
    expect(calmarRatio(RISK_RETURNS)).toBeCloseTo(11.512396694214997, 9);
  });

  it("historicalVaR95: linear-interpolated 5th percentile, loss magnitude", () => {
    expect(historicalVaR95(RISK_RETURNS)).toBeCloseTo(0.09725895316804406, 9);
  });

  it("correlation + beta: date-aligned pairwise stats", () => {
    expect(correlation(RISK_RETURNS, RISK_BENCH_RETURNS)).toBeCloseTo(0.9394691703263957, 9);
    expect(beta(RISK_RETURNS, RISK_BENCH_RETURNS)).toBeCloseTo(1.3518414354132757, 9);
  });

  it("a flat/zero-length series never divides by zero", () => {
    expect(sharpeRatio([])).toBe(0);
    expect(sortinoRatio([0, 0, 0])).toBe(0);
    expect(calmarRatio([0, 0, 0])).toBe(0);
    expect(beta([0.01, -0.01], [0, 0])).toBe(0);
    expect(correlation([0.01, -0.01], [0, 0])).toBe(0);
  });
});

/** Build a date-ascending closesByDate map from a start date + closes. */
function pricesByDate(startISO: string, closes: readonly number[]): Map<string, number> {
  const map = new Map<string, number>();
  const start = new Date(startISO);
  closes.forEach((close, i) => {
    const d = new Date(start);
    d.setUTCDate(d.getUTCDate() + i);
    map.set(d.toISOString().slice(0, 10), close);
  });
  return map;
}

function longSeries(days: number, seed: number): number[] {
  // A deterministic pseudo-random-looking walk — enough variance that
  // stdev/beta/correlation are well-defined, never a flat line.
  const closes = [100];
  let x = seed;
  for (let i = 1; i < days; i++) {
    x = (x * 1103515245 + 12345) % 2147483648;
    const pct = (x / 2147483648 - 0.5) * 0.04; // +/-2%
    closes.push(closes[i - 1] * (1 + pct));
  }
  return closes;
}

describe("computeCurrencyRisk (R15-CODE-PLATFORM-023)", () => {
  it("is null under MIN_RISK_HISTORY_DAYS overlapping days", () => {
    const holdings: HoldingPriceHistory[] = [
      { symbol: "AAPL", closesByDate: pricesByDate("2025-01-01", RISK_CLOSES), weight: 1 },
    ];
    expect(computeCurrencyRisk("USD", holdings, null)).toBeNull();
    expect(RISK_CLOSES.length).toBeLessThan(MIN_RISK_HISTORY_DAYS + 1);
  });

  it("is null for an empty holdings list", () => {
    expect(computeCurrencyRisk("USD", [], null)).toBeNull();
  });

  it("computes per-bucket metrics once >= MIN_RISK_HISTORY_DAYS days overlap, never a fabricated cross-currency blend", () => {
    const usdHoldings: HoldingPriceHistory[] = [
      { symbol: "AAPL", closesByDate: pricesByDate("2025-01-01", longSeries(35, 7)), weight: 0.6 },
      { symbol: "MSFT", closesByDate: pricesByDate("2025-01-01", longSeries(35, 13)), weight: 0.4 },
    ];
    const inrHoldings: HoldingPriceHistory[] = [
      { symbol: "TCS", closesByDate: pricesByDate("2025-01-01", longSeries(35, 21)), weight: 1 },
    ];

    const usd = computeCurrencyRisk(
      "USD",
      usdHoldings,
      pricesByDate("2025-01-01", longSeries(35, 29)),
    );
    const inr = computeCurrencyRisk(
      "INR",
      inrHoldings,
      pricesByDate("2025-01-01", longSeries(35, 31)),
    );

    expect(usd).not.toBeNull();
    expect(inr).not.toBeNull();
    expect(usd!.currency).toBe("USD");
    expect(inr!.currency).toBe("INR");
    expect(usd!.days).toBeGreaterThanOrEqual(MIN_RISK_HISTORY_DAYS);
    expect(usd!.correlation.symbols).toEqual(["AAPL", "MSFT"]);
    // Diagonal of a correlation matrix is always 1 (a series with itself).
    expect(usd!.correlation.matrix[0][0]).toBeCloseTo(1, 9);
    expect(usd!.correlation.matrix[1][1]).toBeCloseTo(1, 9);
    expect(usd!.beta).not.toBeNull();
    expect(Number.isFinite(usd!.sharpeRatio)).toBe(true);
    expect(Number.isFinite(usd!.valueAtRisk95)).toBe(true);
    // The two buckets are independent computations — no shared/blended state.
    expect(usd!.correlation.symbols).not.toEqual(inr!.correlation.symbols);
  });

  it("beta is null when the benchmark's history doesn't cover enough overlapping days", () => {
    const holdings: HoldingPriceHistory[] = [
      { symbol: "AAPL", closesByDate: pricesByDate("2025-01-01", longSeries(35, 7)), weight: 1 },
    ];
    const sparseBenchmark = pricesByDate("2025-01-01", longSeries(10, 29)); // only 10 days
    const result = computeCurrencyRisk("USD", holdings, sparseBenchmark);
    expect(result).not.toBeNull();
    expect(result!.beta).toBeNull();
  });
});
