import { describe, expect, it } from "vitest";

import {
  CODE_NODE_ID,
  CODE_NODE_OUTPUT_PORT,
  codeNodeBindings,
  codeNodeExpression,
  compileCodeExpression,
  evaluateCodeExpression,
  isValidBindingName,
  nextBindingName,
} from "./code-node";

describe("code-node: bindings", () => {
  it("validates identifier-shaped binding names", () => {
    expect(isValidBindingName("a")).toBe(true);
    expect(isValidBindingName("price_close")).toBe(true);
    expect(isValidBindingName("_x1")).toBe(true);
    expect(isValidBindingName("1a")).toBe(false);
    expect(isValidBindingName("a-b")).toBe(false);
    expect(isValidBindingName("")).toBe(false);
    expect(isValidBindingName("a b")).toBe(false);
  });

  it("reads bindings from config, dropping malformed and duplicate entries", () => {
    expect(codeNodeBindings({ inputs: ["a", "b"] })).toEqual(["a", "b"]);
    expect(codeNodeBindings({ inputs: ["a", "a", 3, "9x", "", "ok_1"] })).toEqual(["a", "ok_1"]);
    expect(codeNodeBindings({ inputs: "not-an-array" })).toEqual([]);
    expect(codeNodeBindings({})).toEqual([]);
  });

  it("reads the expression string defensively", () => {
    expect(codeNodeExpression({ expression: "a + 1" })).toBe("a + 1");
    expect(codeNodeExpression({ expression: 42 })).toBe("");
    expect(codeNodeExpression({})).toBe("");
  });

  it("proposes the next free binding name", () => {
    expect(nextBindingName([])).toBe("a");
    expect(nextBindingName(["a", "b"])).toBe("c");
    const alphabet = Array.from({ length: 26 }, (_, i) => String.fromCharCode(97 + i));
    expect(nextBindingName(alphabet)).toBe("in1");
    expect(nextBindingName([...alphabet, "in1"])).toBe("in2");
  });
});

describe("code-node: compile", () => {
  it("accepts a well-formed expression", () => {
    expect(compileCodeExpression("a + b * 2")).toEqual({ ok: true });
    expect(compileCodeExpression("max(a, b) > 10 and a < 5")).toEqual({ ok: true });
  });

  it("rejects a blank expression (a code node must emit something)", () => {
    const result = compileCodeExpression("   ");
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/empty/);
  });

  it("surfaces a single-line parse error, never a stack", () => {
    const result = compileCodeExpression("a +");
    expect(result.ok).toBe(false);
    expect(result.error).toBeDefined();
    expect(result.error).not.toContain("\n");
  });
});

describe("code-node: evaluate", () => {
  it("evaluates arithmetic over the bound scope", () => {
    expect(evaluateCodeExpression("a + b * 2", { a: 1, b: 3 })).toEqual({ ok: true, value: 7 });
  });

  it("evaluates boolean logic and comparisons", () => {
    expect(evaluateCodeExpression("a > b and a > 0", { a: 5, b: 3 })).toEqual({
      ok: true,
      value: true,
    });
  });

  it("supports object property access on JSON inputs (quote.price style)", () => {
    expect(evaluateCodeExpression("quote.price * qty", { quote: { price: 12.5 }, qty: 4 })).toEqual(
      { ok: true, value: 50 },
    );
  });

  it("supports array math and serializes matrix results to plain arrays", () => {
    const result = evaluateCodeExpression("xs * 2", { xs: [1, 2, 3] });
    expect(result).toEqual({ ok: true, value: [2, 4, 6] });
    expect(evaluateCodeExpression("sum(xs)", { xs: [1, 2, 3] })).toEqual({ ok: true, value: 6 });
  });

  it("reports an undefined symbol when a binding is unwired", () => {
    const result = evaluateCodeExpression("a + b", { a: 1 });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toMatch(/Undefined symbol b/);
    }
  });

  it("never coerces a missing input to a silent zero", () => {
    const result = evaluateCodeExpression("a", { a: undefined });
    expect(result.ok).toBe(false);
  });
});

describe("code-node: sandbox", () => {
  it.each(["import", "createUnit", "evaluate", "parse", "simplify", "derivative", "resolve"])(
    "blocks the %s escape hatch",
    (name) => {
      const result = evaluateCodeExpression(`${name}("1+1")`, {});
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error).toContain("disabled in code nodes");
      }
    },
  );

  it("does not leak host globals into the scope", () => {
    const result = evaluateCodeExpression("globalThis", {});
    expect(result.ok).toBe(false);
  });
});

describe("code-node: constants", () => {
  it("pins the node-type id and output port the run path depends on", () => {
    expect(CODE_NODE_ID).toBe("transform.code");
    expect(CODE_NODE_OUTPUT_PORT).toBe("value");
  });
});
