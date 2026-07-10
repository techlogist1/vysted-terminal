import { describe, expect, it } from "vitest";

import { extractBriefClaims } from "@/lib/brief-claims";

import type { ResearchBriefData } from "../../types/brief";

function brief(
  structured: Record<string, unknown> | undefined,
  symbol = "NVDA",
): ResearchBriefData {
  return {
    query: "q",
    symbol,
    mode: "FAST",
    markdown: "x",
    sources: [],
    sourceCount: 0,
    webAvailable: true,
    createdAt: 1234,
    structured: structured as unknown as ResearchBriefData["structured"],
  };
}

describe("extractBriefClaims — deterministic stated-value ledger (R13 JARVIS 3a)", () => {
  it("pulls headline price, key scalars, and labeled derived metrics", () => {
    const claims = extractBriefClaims(
      brief({
        price: { ok: true, provider: "yfinance", data: { price: 900 } },
        fundamentals: {
          ok: true,
          provider: "yfinance",
          data: { pe_ratio: 55, market_cap: 2.2e12, eps: 16 },
        },
        derived: {
          ok: true,
          provider: "derived",
          data: {
            dividend_yield: { value: 0.0003, label: "Dividend yield", unit: "percent" },
            revenue_growth: { value: 1.2, label: "Revenue growth", unit: "percent" },
            conflicts: [],
          },
        },
      }),
    );
    const byMetric = Object.fromEntries(claims.map((c) => [c.metric, c.value]));
    expect(byMetric["Price"]).toBe(900);
    expect(byMetric["P/E"]).toBe(55);
    expect(byMetric["Market cap"]).toBe(2.2e12);
    expect(byMetric["EPS"]).toBe(16);
    expect(byMetric["Dividend yield"]).toBe(0.0003);
    expect(byMetric["Revenue growth"]).toBe(1.2);
    // Every claim is scoped to the symbol + stamped with the brief's time.
    expect(claims.every((c) => c.symbol === "NVDA" && c.statedAt === 1234)).toBe(true);
  });

  it("skips a null derived value — never fabricates a claim", () => {
    const claims = extractBriefClaims(
      brief({
        derived: {
          ok: true,
          provider: "derived",
          data: {
            dividend_yield: { value: null, label: "Dividend yield", reason: "withheld" },
          },
        },
      }),
    );
    expect(claims.find((c) => c.metric === "Dividend yield")).toBeUndefined();
  });

  it("ignores a failed leg (ok:false)", () => {
    const claims = extractBriefClaims(
      brief({
        fundamentals: {
          ok: false,
          provider: "yfinance",
          error: "provider error",
          reason: "provider_error",
        },
      }),
    );
    expect(claims).toEqual([]);
  });

  it("returns [] when the brief names no symbol", () => {
    expect(extractBriefClaims(brief({ price: { ok: true, data: { price: 1 } } }, ""))).toEqual([]);
  });

  it("returns [] when there is no structured bundle", () => {
    expect(extractBriefClaims(brief(undefined))).toEqual([]);
  });
});
