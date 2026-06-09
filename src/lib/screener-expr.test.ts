/**
 * Screener formula grammar tests — the TypeScript twin (R7 Pillar 3).
 *
 * PARITY CONTRACT: every vector here mirrors a case asserted in
 * `sidecar/tests/test_screener_formula.py` against the authoritative Python
 * grammar (`sidecar/services/screener_formula.py`). If a vector diverges, the
 * editor would green-light a formula the server rejects (or vice versa) —
 * change both files in the same commit.
 */

import { describe, expect, it } from "vitest";

import {
  compileScreenerExpr,
  FIELD_ALIASES,
  identifierAt,
  MAX_NESTING_DEPTH,
  MAX_TOKENS,
  NUMERIC_FIELDS,
  suggestFields,
} from "./screener-expr";

function expectError(source: string): { error: string; position: number } {
  const result = compileScreenerExpr(source);
  if (result.ok) {
    throw new Error(`expected '${source}' to fail`);
  }
  return result;
}

describe("compileScreenerExpr — happy paths (Python parity)", () => {
  it("parses a simple comparison and collects the field", () => {
    const result = compileScreenerExpr("pe_ratio < 15");
    expect(result).toEqual({ ok: true, fields: ["pe_ratio"] });
  });

  it("resolves aliases to canonical fields", () => {
    const result = compileScreenerExpr("pe < 15 and marketCap > 1e9 and pb < 2");
    expect(result).toEqual({ ok: true, fields: ["market_cap", "pe_ratio", "price_to_book"] });
  });

  it("matches fields case-insensitively", () => {
    expect(compileScreenerExpr("PE_RATIO < 15")).toEqual({ ok: true, fields: ["pe_ratio"] });
  });

  it("parses every canonical numeric field", () => {
    for (const field of NUMERIC_FIELDS) {
      expect(compileScreenerExpr(`${field} > 0`)).toEqual({ ok: true, fields: [field] });
    }
  });

  it("parses every alias", () => {
    for (const [alias, field] of Object.entries(FIELD_ALIASES)) {
      expect(compileScreenerExpr(`${alias} > 0`)).toEqual({ ok: true, fields: [field] });
    }
  });

  it("parses arithmetic, boolean ops, and functions together", () => {
    const result = compileScreenerExpr(
      "(market_cap / volume > 1e6 or not (pe < 10)) " +
        "and max(roe, roa) > 0.15 and abs(change_percent_1d) < 2 " +
        "and min(pe_ratio, forward_pe) > 0",
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.fields).toContain("volume");
      expect(result.fields).toContain("roa");
    }
  });

  it("a parenthesized boolean stays boolean at the top level", () => {
    expect(compileScreenerExpr("(pe < 15)").ok).toBe(true);
  });

  it("a blank formula is ok (no-op filter)", () => {
    expect(compileScreenerExpr("   ")).toEqual({ ok: true, fields: [] });
  });
});

describe("compileScreenerExpr — positioned errors (Python parity)", () => {
  it("unknown field points at the identifier", () => {
    const src = "pe < 15 and bogus > 1";
    const { error, position } = expectError(src);
    expect(position).toBe(src.indexOf("bogus"));
    expect(error).toContain("unknown field 'bogus'");
  });

  it("unexpected character carries its position", () => {
    const { position } = expectError("pe < 15 $ roe > 1");
    expect(position).toBe(8);
  });

  it("unclosed paren positions at end of input", () => {
    const src = "(pe < 15";
    expect(expectError(src).position).toBe(src.length);
  });

  it("incomplete comparison positions at end of input", () => {
    const { position } = expectError("pe <");
    expect(position).toBe(4);
  });

  it("top level must be boolean", () => {
    expect(expectError("pe_ratio + 1").error).toContain("comparison or boolean");
  });

  it("chained comparisons are rejected with the combine hint", () => {
    const src = "1 < pe < 15";
    const { error, position } = expectError(src);
    expect(error).toContain("combine with 'and'");
    expect(position).toBe(src.lastIndexOf("<"));
  });

  it("abs() arity is enforced", () => {
    expect(expectError("abs(pe, roe) > 1").error).toContain("abs() takes exactly 1");
  });

  it("min() needs two args", () => {
    expect(expectError("min(pe) > 1").error).toContain("min() takes at least 2");
  });

  it("max() arg count is capped at 8", () => {
    const args = Array.from({ length: 9 }, () => "1").join(", ");
    expect(expectError(`max(${args}) > 1`).error).toContain("at most 8");
  });

  it("a paren bomb is a positioned error, never a RangeError", () => {
    const bomb = "(".repeat(5000) + "pe < 1" + ")".repeat(5000);
    const { error } = expectError(bomb);
    expect(error).toMatch(/too long|too deeply nested/);
  });

  it("a token flood is capped", () => {
    const flood = "pe > 1" + " and pe > 1".repeat(MAX_TOKENS);
    expect(expectError(flood).error).toContain(`max ${MAX_TOKENS} tokens`);
  });

  it("nesting depth is capped", () => {
    const depth = MAX_NESTING_DEPTH + 1;
    const src = "(".repeat(depth) + "pe < 1" + ")".repeat(depth);
    expect(expectError(src).error).toContain("too deeply nested");
  });

  it("a non-finite literal is rejected", () => {
    expect(expectError("pe < 1e999").error).toContain("number literal too large");
  });
});

describe("identifierAt", () => {
  it("finds the identifier span under the caret", () => {
    const src = "pe < 15 and mar";
    expect(identifierAt(src, src.length)).toEqual({ start: 12, end: 15, prefix: "mar" });
  });

  it("returns the typed prefix when the caret sits mid-identifier", () => {
    const src = "market_cap > 1";
    expect(identifierAt(src, 3)).toEqual({ start: 0, end: 10, prefix: "mar" });
  });

  it("returns null on whitespace and after numbers", () => {
    expect(identifierAt("pe < 15", 4)).toBeNull(); // after "< "
    expect(identifierAt("pe < 15", 7)).toBeNull(); // after the number
  });
});

describe("suggestFields", () => {
  it("prefix-matches canonical fields and aliases", () => {
    const names = suggestFields("mar").map((s) => s.name);
    expect(names).toContain("market_cap");
    expect(names).toContain("marketcap");
  });

  it("excludes an already-complete exact match", () => {
    expect(suggestFields("roe").map((s) => s.name)).not.toContain("roe");
  });

  it("caps the list and returns nothing for an empty prefix", () => {
    expect(suggestFields("p").length).toBeLessThanOrEqual(8);
    expect(suggestFields("")).toEqual([]);
  });

  it("alias rows resolve to their canonical field", () => {
    const pb = suggestFields("pb").find((s) => s.name === "pb");
    // "pb" itself is excluded as exact — check via a shorter prefix.
    expect(pb).toBeUndefined();
    const aliases = suggestFields("debtto");
    expect(aliases[0]).toMatchObject({ name: "debttoequity", canonical: "debt_to_equity" });
  });
});
