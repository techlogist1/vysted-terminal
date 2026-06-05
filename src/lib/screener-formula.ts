/**
 * Screener custom-formula engine (FR-122 / SC-033) — the sandboxed mathjs
 * evaluator shared by the Web Worker (`screener-formula.worker.ts`) and the
 * jsdom/SSR fallback path in the store.
 *
 * A "formula" leaf is a free-text boolean expression (e.g. `pe < 15 and roe >
 * 0.2`, `marketCap / revenue < 5`) that POST-FILTERS the server-returned matched
 * set CLIENT-SIDE — the server evaluates the AND/OR `group` tree; the formula
 * runs over each returned row's numeric fields here.
 *
 * SECURITY — mathjs is sandboxed per its own guidance
 * (https://mathjs.org/docs/expressions/security.html):
 *   - a dedicated `create(all)` instance with `import` / `createUnit` /
 *     `evaluate` / `parse` / `simplify` / `derivative` REMOVED via `math.import`
 *     `{override:true}` so an expression can't redefine functions, mint units,
 *     or re-enter the parser to reach the prototype chain;
 *   - evaluation runs against a RESTRICTED scope object (only the row's numeric
 *     fields, plain numbers) — no host globals, no functions;
 *   - in production it executes inside a Web Worker (see the store), so even a
 *     pathological expression can't touch the main thread / DOM.
 * `expr-eval` is BANNED (CVE-2025-12735, CVSS 9.8 RCE) — never reintroduce it.
 */

import { create, all, type MathJsInstance, type MathNode } from "mathjs";

import type { ScreenerResultRow } from "../../types/screener";

/** A blocked sandbox entry point — throws if an expression tries to reach it. */
function blocked(name: string): (...args: unknown[]) => never {
  return () => {
    throw new Error(`"${name}" is disabled in screener formulas`);
  };
}

interface Sandbox {
  /** A working parser captured BEFORE the dangerous names were disabled. */
  parse: MathJsInstance["parse"];
}

/** Build the locked-down mathjs instance once (module singleton).
 *
 * Per mathjs security guidance we DISABLE the function names an expression
 * could call to escape the sandbox (`import`/`createUnit`/`evaluate`/`parse`/
 * `simplify`/`derivative`/`resolve`) by shadowing them with throwing stubs via
 * `math.import({...}, {override:true})`. We capture `math.parse` FIRST so WE can
 * still compile expressions — disabling the instance's `parse` would otherwise
 * also break our own parsing. The captured parser inherits the disabled
 * function table, so an expression that calls `import(...)` / `evaluate(...)`
 * still hits the stub and throws. */
function buildSandbox(): Sandbox {
  const math = create(all, {});
  // Capture a working parser bound to this instance BEFORE we disable names.
  const parse = math.parse.bind(math) as MathJsInstance["parse"];
  math.import(
    {
      import: blocked("import"),
      createUnit: blocked("createUnit"),
      evaluate: blocked("evaluate"),
      parse: blocked("parse"),
      simplify: blocked("simplify"),
      derivative: blocked("derivative"),
      resolve: blocked("resolve"),
    },
    { override: true },
  );
  return { parse };
}

let _math: Sandbox | null = null;
function sandbox(): Sandbox {
  if (_math === null) {
    _math = buildSandbox();
  }
  return _math;
}

/**
 * Map a result row to a flat numeric scope for the formula. Both the snake_case
 * wire field names (`pe_ratio`, `market_cap`) and friendly camelCase aliases
 * (`pe`, `marketCap`) are exposed so a user can write either. Null / missing
 * fields are omitted — referencing one in the expression surfaces as an
 * "Undefined symbol" eval error (recovery-first), never a silent `0`.
 */
export function rowScope(row: ScreenerResultRow): Record<string, number> {
  const scope: Record<string, number> = {};
  const put = (key: string, value: number | null | undefined): void => {
    if (typeof value === "number" && Number.isFinite(value)) {
      scope[key] = value;
    }
  };
  // Canonical (snake_case, matches the wire / criterion field names).
  put("market_cap", row.market_cap);
  put("pe_ratio", row.pe_ratio);
  put("forward_pe", row.forward_pe);
  put("peg_ratio", row.peg_ratio);
  put("price_to_book", row.price_to_book);
  put("dividend_yield", row.dividend_yield);
  put("roe", row.roe);
  put("debt_to_equity", row.debt_to_equity);
  put("price", row.price);
  put("change_percent_1d", row.change_percent_1d);
  put("volume", row.volume);
  // Friendly camelCase / shorthand aliases.
  put("marketCap", row.market_cap);
  put("pe", row.pe_ratio);
  put("forwardPe", row.forward_pe);
  put("pegRatio", row.peg_ratio);
  put("priceToBook", row.price_to_book);
  put("pb", row.price_to_book);
  put("dividendYield", row.dividend_yield);
  put("debtToEquity", row.debt_to_equity);
  put("changePercent1d", row.change_percent_1d);
  return scope;
}

export interface FormulaCompileResult {
  ok: boolean;
  /** Inline, recovery-first error (no raw stack) when `ok === false`. */
  error?: string;
}

/**
 * Validate that an expression PARSES under the sandbox without evaluating it
 * against a row — drives the inline editor error before a run. A blank
 * expression is valid (no-op filter).
 */
export function compileFormula(expression: string): FormulaCompileResult {
  const expr = expression.trim();
  if (!expr) {
    return { ok: true };
  }
  try {
    sandbox().parse(expr);
    return { ok: true };
  } catch (err: unknown) {
    return { ok: false, error: friendlyError(err) };
  }
}

export interface FormulaFilterResult {
  /** Indices into the input rows that PASSED the formula (truthy result). */
  passedIndices: number[];
  /** Inline error if the expression failed to evaluate (no rows are dropped). */
  error?: string;
}

/**
 * Evaluate a boolean formula over each row, returning the indices that pass.
 * A blank expression passes every row (no filter). On a parse error the filter
 * is a NO-OP (all rows pass) and the error is surfaced for inline display — a
 * broken formula never silently empties the table. A per-row eval error drops
 * just that row and records the first such error.
 *
 * The per-row `evaluate` uses a SCOPE-ONLY call so the expression can only read
 * the numeric fields we put in.
 */
export function filterRowsByFormula(
  expression: string,
  rows: ScreenerResultRow[],
): FormulaFilterResult {
  const expr = expression.trim();
  if (!expr) {
    return { passedIndices: rows.map((_, i) => i) };
  }
  const sb = sandbox();
  let compiled: MathNode;
  try {
    // `parse(string)` returns a single MathNode (the array overload is for
    // string[]); the cast pins the scalar overload for the type-checker.
    compiled = sb.parse(expr) as MathNode;
  } catch (err: unknown) {
    return { passedIndices: rows.map((_, i) => i), error: friendlyError(err) };
  }
  const code = compiled.compile();
  const passedIndices: number[] = [];
  let firstError: string | undefined;
  rows.forEach((row, i) => {
    try {
      // Pass a FRESH scope object per row; mathjs may write derived symbols into
      // it, but we discard it after the row so there's no cross-row leakage.
      const value = code.evaluate(rowScope(row)) as unknown;
      if (truthy(value)) {
        passedIndices.push(i);
      }
    } catch (err: unknown) {
      // An eval error for THIS row (e.g. referencing a field the row lacks):
      // the row is dropped and we record the first error for inline display.
      if (firstError === undefined) {
        firstError = friendlyError(err);
      }
    }
  });
  return { passedIndices, error: firstError };
}

/** Coerce a mathjs result to a boolean filter verdict. */
function truthy(value: unknown): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    return value !== 0 && Number.isFinite(value);
  }
  // mathjs may return a BigNumber/Fraction-like object with a numeric coercion.
  if (value && typeof value === "object" && "valueOf" in value) {
    const n = Number((value as { valueOf: () => unknown }).valueOf());
    return Number.isFinite(n) && n !== 0;
  }
  return false;
}

/** Strip a mathjs error down to its message (no raw stack), recovery-first. */
function friendlyError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  // mathjs messages are already concise ("Undefined symbol pe", "Unexpected
  // end of expression") — surface the first line, capped, never the stack.
  return raw.split("\n")[0]!.slice(0, 160);
}
