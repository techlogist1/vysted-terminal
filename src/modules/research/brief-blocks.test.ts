import { describe, expect, it } from "vitest";

import { deriveMetrics } from "@/modules/research/brief-blocks";
import type { BriefStructured } from "../../../types/brief";
import type { Fundamentals, Quote } from "../../../types/data";

function quote(overrides: Partial<Quote> = {}): Quote {
  return {
    symbol: "X",
    price: 100,
    change: 1,
    change_percent: 1,
    volume: 1_000_000,
    currency: "USD",
    market_state: "REGULAR",
    timestamp: "2024-01-01T00:00:00Z",
    provider: "yfinance",
    freshness: "live",
    ...overrides,
  };
}

function fundamentals(overrides: Partial<Fundamentals> = {}): Fundamentals {
  return {
    symbol: "X",
    name: "X Corp",
    sector: null,
    industry: null,
    currency: "USD",
    market_cap: 2_000_000_000,
    pe_ratio: 25,
    forward_pe: 22,
    peg_ratio: 1.5,
    price_to_book: 8,
    price_to_sales: null,
    ev_to_ebitda: null,
    book_value: null,
    dividend_yield: 0.005,
    dividend_per_share: null,
    eps: 4,
    beta: 1.1,
    fifty_two_week_high: 120,
    fifty_two_week_low: 80,
    fifty_two_week_change: null,
    roe: 0.3,
    roa: null,
    gross_margin: null,
    operating_margin: null,
    profit_margin: 0.25,
    debt_to_equity: 0.4,
    current_ratio: null,
    quick_ratio: null,
    revenue_ttm: 500_000_000,
    net_income_ttm: null,
    free_cash_flow: null,
    shares_outstanding: null,
    revenue_growth: 0.2,
    earnings_growth: null,
    held_percent_insiders: null,
    held_percent_institutions: null,
    provider: "yfinance",
    ...overrides,
  };
}

function structured(
  assetClass: string | undefined,
  extra: Partial<BriefStructured> = {},
): BriefStructured {
  return {
    resolved:
      assetClass === undefined
        ? undefined
        : { ok: true, resolved: { symbol: "X", asset_class: assetClass } },
    price: { ok: true, provider: "yfinance", data: quote() },
    fundamentals: { ok: true, provider: "yfinance", data: fundamentals() },
    ...extra,
  };
}

const labels = (s: BriefStructured) => deriveMetrics(s)?.items.map((i) => i.label) ?? [];

describe("deriveMetrics — asset-class branching", () => {
  it("returns null when there is no usable price or fundamentals leg", () => {
    expect(deriveMetrics(undefined)).toBeNull();
    expect(deriveMetrics({})).toBeNull();
    expect(deriveMetrics({ price: { ok: false }, fundamentals: { ok: false } })).toBeNull();
  });

  it("equity: the full valuation + quality + growth grid", () => {
    const model = deriveMetrics(structured("equity"));
    expect(model?.assetClass).toBe("equity");
    const l = labels(structured("equity"));
    expect(l).toContain("P/E");
    expect(l).toContain("ROE");
    expect(l).toContain("Rev growth");
    expect(l).toContain("Market cap");
  });

  it("crypto: market cap + 24h volume + range, NO equity valuation ratios", () => {
    const model = deriveMetrics(structured("crypto"));
    expect(model?.assetClass).toBe("crypto");
    const l = labels(structured("crypto"));
    expect(l).toContain("Market cap");
    expect(l).toContain("24h volume");
    expect(l).toContain("52w range");
    // A coin must never show a meaningless P/E / PEG / ROE.
    expect(l).not.toContain("P/E");
    expect(l).not.toContain("PEG");
    expect(l).not.toContain("ROE");
  });

  it("etf: net assets + yield + beta, no single-company quality ratios", () => {
    const model = deriveMetrics(structured("etf"));
    expect(model?.assetClass).toBe("etf");
    const l = labels(structured("etf"));
    expect(l).toContain("Net assets");
    expect(l).toContain("Beta");
    expect(l).not.toContain("ROE");
    expect(l).not.toContain("Rev growth");
  });

  it("fx: price action + range only, no fundamentals cards", () => {
    const model = deriveMetrics(structured("fx"));
    expect(model?.assetClass).toBe("fx");
    const l = labels(structured("fx"));
    expect(l).not.toContain("Market cap");
    expect(l).not.toContain("P/E");
    expect(l).toContain("52w range");
  });

  it("defaults to the equity set when the resolved instrument is absent", () => {
    const model = deriveMetrics(structured(undefined));
    expect(model?.assetClass).toBe("equity");
    expect(labels(structured(undefined))).toContain("P/E");
  });

  it("never fabricates a card — an absent field renders no card", () => {
    const s = structured("equity", {
      fundamentals: { ok: true, provider: "yfinance", data: fundamentals({ pe_ratio: null }) },
    });
    expect(labels(s)).not.toContain("P/E");
  });
});
