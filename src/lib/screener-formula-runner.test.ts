/**
 * Screener formula runner tests (FR-122 / SC-033).
 *
 * jsdom has no module-Worker that can load our `.worker.ts` URL, so the runner
 * exercises the INLINE fallback here (same sandboxed evaluator). The contract is
 * identical to a worker run: blank = unchanged, formula filters, errors surface.
 */

import { afterEach, describe, expect, it } from "vitest";

import { __resetFormulaRunnerForTests, runScreenerFormula } from "./screener-formula-runner";

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

afterEach(() => __resetFormulaRunnerForTests());

describe("runScreenerFormula", () => {
  const rows = [
    row({ symbol: "A", pe_ratio: 8, roe: 0.3 }),
    row({ symbol: "B", pe_ratio: 25, roe: 0.05 }),
    row({ symbol: "C", pe_ratio: 12, roe: 0.25 }),
  ];

  it("a blank formula returns the rows unchanged", async () => {
    const out = await runScreenerFormula("", rows);
    expect(out.rows).toBe(rows);
    expect(out.error).toBeUndefined();
  });

  it("post-filters the rows by the formula", async () => {
    const out = await runScreenerFormula("pe < 15 and roe > 0.2", rows);
    expect(out.rows.map((r) => r.symbol)).toEqual(["A", "C"]);
  });

  it("surfaces a parse error without dropping rows", async () => {
    const out = await runScreenerFormula("pe <", rows);
    expect(out.rows).toHaveLength(rows.length);
    expect(typeof out.error).toBe("string");
  });
});
