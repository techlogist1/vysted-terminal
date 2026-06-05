/**
 * Screener custom-formula engine tests (FR-122 / SC-033).
 *
 * Covers: boolean evaluation over rows, the camelCase + snake_case scope
 * aliases, blank = no-op, parse errors (no-op + inline error), per-row eval
 * errors (drop the row), and the mathjs SANDBOX (import/createUnit/evaluate
 * injection blocked).
 */

import { describe, expect, it } from "vitest";

import { compileFormula, filterRowsByFormula, rowScope } from "./screener-formula";

import type { ScreenerResultRow } from "../../types/screener";

function row(over: Partial<ScreenerResultRow>): ScreenerResultRow {
  return {
    symbol: "X",
    name: "X Co",
    sector: "Technology",
    industry: "Software",
    market_cap: 1_000_000_000,
    pe_ratio: 10,
    price: 100,
    change_percent_1d: 0,
    volume: 1_000_000,
    matched_criteria: [],
    ...over,
  };
}

describe("rowScope", () => {
  it("exposes both snake_case and camelCase aliases for numeric fields", () => {
    const scope = rowScope(row({ pe_ratio: 12, market_cap: 5e9, roe: 0.2 }));
    expect(scope.pe_ratio).toBe(12);
    expect(scope.pe).toBe(12);
    expect(scope.market_cap).toBe(5e9);
    expect(scope.marketCap).toBe(5e9);
    expect(scope.roe).toBe(0.2);
  });

  it("omits null / missing fields (so a reference becomes an eval error, not 0)", () => {
    const scope = rowScope(row({ pe_ratio: null, roe: undefined }));
    expect("pe_ratio" in scope).toBe(false);
    expect("roe" in scope).toBe(false);
  });
});

describe("compileFormula", () => {
  it("a blank expression is valid (no-op)", () => {
    expect(compileFormula("").ok).toBe(true);
    expect(compileFormula("   ").ok).toBe(true);
  });

  it("a well-formed expression parses", () => {
    expect(compileFormula("pe < 15 and roe > 0.2").ok).toBe(true);
  });

  it("a malformed expression surfaces an inline error (no stack)", () => {
    const r = compileFormula("pe < ");
    expect(r.ok).toBe(false);
    expect(typeof r.error).toBe("string");
    expect(r.error).not.toContain("\n");
  });
});

describe("filterRowsByFormula", () => {
  const rows = [
    row({ symbol: "A", pe_ratio: 8, roe: 0.3 }),
    row({ symbol: "B", pe_ratio: 25, roe: 0.05 }),
    row({ symbol: "C", pe_ratio: 12, roe: 0.25 }),
  ];

  it("blank expression keeps every row", () => {
    const r = filterRowsByFormula("", rows);
    expect(r.passedIndices).toEqual([0, 1, 2]);
    expect(r.error).toBeUndefined();
  });

  it("evaluates a compound boolean over each row", () => {
    const r = filterRowsByFormula("pe < 15 and roe > 0.2", rows);
    // A (8, 0.3) and C (12, 0.25) pass; B fails both.
    expect(r.passedIndices).toEqual([0, 2]);
  });

  it("supports arithmetic on fields (market_cap / volume)", () => {
    const r = filterRowsByFormula("market_cap / volume > 500", [
      row({ symbol: "A", market_cap: 1e9, volume: 1e6 }), // 1000 > 500 -> pass
      row({ symbol: "B", market_cap: 1e8, volume: 1e6 }), // 100 -> fail
    ]);
    expect(r.passedIndices).toEqual([0]);
  });

  it("an OR expression passes either branch", () => {
    const r = filterRowsByFormula("pe < 10 or roe > 0.24", rows);
    // A (pe 8) passes; C (roe 0.25) passes; B fails.
    expect(r.passedIndices).toEqual([0, 2]);
  });

  it("a parse error is a no-op (all rows pass) + reports the error", () => {
    const r = filterRowsByFormula("pe <", rows);
    expect(r.passedIndices).toEqual([0, 1, 2]);
    expect(typeof r.error).toBe("string");
  });

  it("a per-row eval error drops just that row and records the first error", () => {
    const mixed = [
      row({ symbol: "A", pe_ratio: 8, roe: 0.3 }),
      row({ symbol: "B", pe_ratio: 8, roe: null }), // roe missing -> eval error
    ];
    const r = filterRowsByFormula("roe > 0.2", mixed);
    expect(r.passedIndices).toEqual([0]);
    expect(typeof r.error).toBe("string");
  });
});

describe("mathjs sandbox (security — CVE-class hardening)", () => {
  const rows = [row({ pe_ratio: 10 })];

  it("blocks import() injection", () => {
    const r = filterRowsByFormula('import("evaluate")', rows);
    // The expression errors out; no row passes via the injection.
    expect(r.error).toBeTruthy();
  });

  it("blocks createUnit() injection", () => {
    const r = filterRowsByFormula('createUnit("evil")', rows);
    expect(r.error).toBeTruthy();
  });

  it("blocks a nested evaluate() re-entry", () => {
    const r = filterRowsByFormula('evaluate("1+1")', rows);
    expect(r.error).toBeTruthy();
  });

  it("cannot reach host globals (no process / window in scope)", () => {
    // `process` is not a mathjs symbol nor in our scope -> undefined-symbol error.
    const r = filterRowsByFormula("process", rows);
    expect(r.passedIndices).toEqual([]); // dropped (eval error per row)
    expect(r.error).toBeTruthy();
  });
});
