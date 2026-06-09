/**
 * Screener formula grammar — the TypeScript twin (R7 hackability Pillar 3).
 *
 * Hand-mirrors `sidecar/services/screener_formula.py`, the ONE authoritative
 * grammar the sidecar evaluates server-side. This twin exists so the editor
 * can validate INSTANTLY (caret-position errors while typing, no round-trip)
 * and drive field-name autocomplete — it never evaluates anything; the server
 * is the only evaluator. Change BOTH files in the same commit; the parity
 * vectors live in `screener-expr.test.ts` and `test_screener_formula.py`.
 *
 * Grammar (EBNF):
 *
 *     formula    = or_expr ;                       (top level MUST be boolean)
 *     or_expr    = and_expr { "or" and_expr } ;
 *     and_expr   = not_expr { "and" not_expr } ;
 *     not_expr   = "not" not_expr | comparison ;
 *     comparison = sum [ (">" | ">=" | "<" | "<=" | "==" | "!=") sum ] ;
 *     sum        = term { ("+" | "-") term } ;
 *     term       = factor { ("*" | "/") factor } ;
 *     factor     = "-" factor | primary ;
 *     primary    = NUMBER | FIELD | FUNC "(" or_expr { "," or_expr } ")"
 *                | "(" or_expr ")" ;
 *
 *     FIELD  = any ScreenerNumericField (snake_case) or a documented alias
 *              (pe, marketCap, pb, …) — matched case-insensitively ;
 *     FUNC   = "abs" (exactly 1 arg) | "min" | "max" (2..8 args) ;
 *     NUMBER = float literal incl. scientific notation (1e9) ; must be finite ;
 *
 * Hostile-input caps (MAX_TOKENS / MAX_NESTING_DEPTH) match the sidecar so the
 * client never green-lights a formula the server would reject.
 */

import type { ScreenerNumericField } from "../../types/screener";

// ---------------------------------------------------------------------------
// Grammar surface — keep in lockstep with screener_formula.py
// ---------------------------------------------------------------------------

/** Canonical numeric fields (mirrors `ScreenerNumericField` member order). */
export const NUMERIC_FIELDS: readonly ScreenerNumericField[] = [
  "market_cap",
  "pe_ratio",
  "forward_pe",
  "peg_ratio",
  "price_to_book",
  "price_to_sales",
  "ev_to_ebitda",
  "book_value",
  "dividend_yield",
  "eps",
  "beta",
  "roe",
  "roa",
  "gross_margin",
  "operating_margin",
  "profit_margin",
  "debt_to_equity",
  "current_ratio",
  "quick_ratio",
  "revenue_growth",
  "earnings_growth",
  "fifty_two_week_high",
  "fifty_two_week_low",
  "fifty_two_week_change",
  "held_percent_insiders",
  "held_percent_institutions",
  "price",
  "change_percent_1d",
  "volume",
] as const;

/** Friendly aliases (lowercased) → canonical field. Identical to the sidecar. */
export const FIELD_ALIASES: Readonly<Record<string, ScreenerNumericField>> = {
  pe: "pe_ratio",
  marketcap: "market_cap",
  forwardpe: "forward_pe",
  pegratio: "peg_ratio",
  pricetobook: "price_to_book",
  pb: "price_to_book",
  pricetosales: "price_to_sales",
  ps: "price_to_sales",
  dividendyield: "dividend_yield",
  debttoequity: "debt_to_equity",
  de: "debt_to_equity",
  changepercent1d: "change_percent_1d",
};

const FIELD_LOOKUP: ReadonlyMap<string, ScreenerNumericField> = new Map([
  ...NUMERIC_FIELDS.map((f) => [f, f] as const),
  ...Object.entries(FIELD_ALIASES).map(([alias, field]) => [alias, field] as const),
]);

export const FUNCTIONS = ["abs", "min", "max"] as const;
const FUNCTION_SET: ReadonlySet<string> = new Set(FUNCTIONS);
const KEYWORDS: ReadonlySet<string> = new Set(["and", "or", "not"]);

const MIN_VARIADIC_ARGS = 2;
const MAX_VARIADIC_ARGS = 8;
export const MAX_TOKENS = 256;
export const MAX_NESTING_DEPTH = 32;

const CMP_OPS: ReadonlySet<string> = new Set([">", ">=", "<", "<=", "==", "!="]);

// ---------------------------------------------------------------------------
// Tokenizer
// ---------------------------------------------------------------------------

type TokenKind = "num" | "ident" | "op";

interface Token {
  kind: TokenKind;
  text: string;
  position: number;
}

const TOKEN_RE =
  /(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|([A-Za-z_][A-Za-z_0-9]*)|(>=|<=|==|!=|>|<|\+|-|\*|\/|\(|\)|,)/y;

/** A parse failure with the 0-based character position for the caret. */
export class ScreenerExprError extends Error {
  readonly position: number;

  constructor(message: string, position: number) {
    super(message);
    this.name = "ScreenerExprError";
    this.position = position;
  }
}

function tokenize(text: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < text.length) {
    const ch = text[i]!;
    if (/\s/.test(ch)) {
      i += 1;
      continue;
    }
    TOKEN_RE.lastIndex = i;
    const match = TOKEN_RE.exec(text);
    if (!match) {
      throw new ScreenerExprError(`unexpected character '${ch}'`, i);
    }
    const kind: TokenKind =
      match[1] !== undefined ? "num" : match[2] !== undefined ? "ident" : "op";
    tokens.push({ kind, text: match[0], position: i });
    i = TOKEN_RE.lastIndex;
  }
  return tokens;
}

// ---------------------------------------------------------------------------
// Recursive-descent parser (validation + field collection only — no eval)
// ---------------------------------------------------------------------------

class Parser {
  private readonly text: string;
  private readonly tokens: Token[];
  private index = 0;
  private depth = 0;
  /** Canonical fields referenced (filled during the parse). */
  readonly fields = new Set<ScreenerNumericField>();
  /** Did the top level resolve to a boolean production? */
  private boolTop = false;

  constructor(text: string) {
    this.text = text;
    this.tokens = tokenize(text);
    if (this.tokens.length > MAX_TOKENS) {
      throw new ScreenerExprError(
        `formula too long — max ${MAX_TOKENS} tokens, got ${this.tokens.length}`,
        this.tokens[MAX_TOKENS]!.position,
      );
    }
  }

  private peek(): Token | null {
    return this.index < this.tokens.length ? this.tokens[this.index]! : null;
  }

  private next(): Token {
    const token = this.peek();
    if (token === null) {
      throw new ScreenerExprError("unexpected end of formula", this.text.length);
    }
    this.index += 1;
    return token;
  }

  private acceptOp(...ops: string[]): Token | null {
    const token = this.peek();
    if (token !== null && token.kind === "op" && ops.includes(token.text)) {
      this.index += 1;
      return token;
    }
    return null;
  }

  private acceptKeyword(word: string): Token | null {
    const token = this.peek();
    if (token !== null && token.kind === "ident" && token.text.toLowerCase() === word) {
      this.index += 1;
      return token;
    }
    return null;
  }

  private expectOp(op: string, context: string): void {
    const token = this.peek();
    if (token === null) {
      throw new ScreenerExprError(`expected '${op}' ${context}`, this.text.length);
    }
    if (token.kind !== "op" || token.text !== op) {
      throw new ScreenerExprError(
        `expected '${op}' ${context}, found '${token.text}'`,
        token.position,
      );
    }
    this.index += 1;
  }

  private enterNesting(position: number): void {
    this.depth += 1;
    if (this.depth > MAX_NESTING_DEPTH) {
      throw new ScreenerExprError(
        `formula too deeply nested — max depth ${MAX_NESTING_DEPTH}`,
        position,
      );
    }
  }

  parse(): void {
    if (this.tokens.length === 0) {
      throw new ScreenerExprError("empty formula", 0);
    }
    this.boolTop = this.orExpr();
    const trailing = this.peek();
    if (trailing !== null) {
      throw new ScreenerExprError(`unexpected '${trailing.text}'`, trailing.position);
    }
    if (!this.boolTop) {
      throw new ScreenerExprError(
        "formula must be a comparison or boolean expression, e.g. pe_ratio < 15",
        0,
      );
    }
  }

  /** Each production returns whether it produced a BOOLEAN value. */
  private orExpr(): boolean {
    let isBool = this.andExpr();
    while (this.acceptKeyword("or") !== null) {
      this.andExpr();
      isBool = true;
    }
    return isBool;
  }

  private andExpr(): boolean {
    let isBool = this.notExpr();
    while (this.acceptKeyword("and") !== null) {
      this.notExpr();
      isBool = true;
    }
    return isBool;
  }

  private notExpr(): boolean {
    const token = this.acceptKeyword("not");
    if (token !== null) {
      this.enterNesting(token.position);
      this.notExpr();
      this.depth -= 1;
      return true;
    }
    return this.comparison();
  }

  private comparison(): boolean {
    const operandIsBool = this.sum();
    const token = this.acceptOp(...CMP_OPS);
    if (token === null) {
      // No comparison — boolean-ness flows up from a parenthesized boolean
      // (`(pe < 15)` parses to the inner Compare in the Python AST).
      return operandIsBool;
    }
    this.sum();
    const chained = this.peek();
    if (chained !== null && chained.kind === "op" && CMP_OPS.has(chained.text)) {
      throw new ScreenerExprError(
        "chained comparisons are not supported — combine with 'and'",
        chained.position,
      );
    }
    return true;
  }

  private sum(): boolean {
    let isBool = this.term();
    while (this.acceptOp("+", "-") !== null) {
      this.term();
      isBool = false; // arithmetic over anything is numeric (mirrors BinOp)
    }
    return isBool;
  }

  private term(): boolean {
    let isBool = this.factor();
    while (this.acceptOp("*", "/") !== null) {
      this.factor();
      isBool = false;
    }
    return isBool;
  }

  private factor(): boolean {
    const token = this.acceptOp("-");
    if (token !== null) {
      this.enterNesting(token.position);
      this.factor();
      this.depth -= 1;
      return false; // unary minus is numeric (mirrors Neg)
    }
    return this.primary();
  }

  /** Returns whether the primary is boolean (a parenthesized boolean expr). */
  private primary(): boolean {
    const token = this.next();
    if (token.kind === "num") {
      const value = Number(token.text);
      if (!Number.isFinite(value)) {
        throw new ScreenerExprError("number literal too large", token.position);
      }
      return false;
    }
    if (token.kind === "op" && token.text === "(") {
      this.enterNesting(token.position);
      const isBool = this.orExpr();
      this.depth -= 1;
      this.expectOp(")", "to close the parenthesis");
      return isBool;
    }
    if (token.kind === "ident") {
      const name = token.text.toLowerCase();
      if (KEYWORDS.has(name)) {
        throw new ScreenerExprError(`unexpected keyword '${name}'`, token.position);
      }
      if (FUNCTION_SET.has(name)) {
        this.call(name, token);
        return false;
      }
      const field = FIELD_LOOKUP.get(name);
      if (field !== undefined) {
        this.fields.add(field);
        return false;
      }
      throw new ScreenerExprError(
        `unknown field '${token.text}' — fields: ${NUMERIC_FIELDS.join(", ")}; ` +
          `functions: ${[...FUNCTIONS].sort().join(", ")}`,
        token.position,
      );
    }
    throw new ScreenerExprError(`unexpected '${token.text}'`, token.position);
  }

  private call(name: string, nameToken: Token): void {
    const open = this.peek();
    this.expectOp("(", `after '${name}'`);
    this.enterNesting(open?.position ?? nameToken.position);
    let argCount = 1;
    this.orExpr();
    while (this.acceptOp(",") !== null) {
      this.orExpr();
      argCount += 1;
      if (argCount > MAX_VARIADIC_ARGS) {
        throw new ScreenerExprError(
          `${name}() takes at most ${MAX_VARIADIC_ARGS} arguments`,
          nameToken.position,
        );
      }
    }
    this.expectOp(")", `to close ${name}()`);
    this.depth -= 1;
    if (name === "abs" && argCount !== 1) {
      throw new ScreenerExprError(
        `abs() takes exactly 1 argument, got ${argCount}`,
        nameToken.position,
      );
    }
    if ((name === "min" || name === "max") && argCount < MIN_VARIADIC_ARGS) {
      throw new ScreenerExprError(
        `${name}() takes at least ${MIN_VARIADIC_ARGS} arguments, e.g. ${name}(roe, roa)`,
        nameToken.position,
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Public compile surface
// ---------------------------------------------------------------------------

export type ScreenerExprResult =
  | { ok: true; fields: ScreenerNumericField[] }
  | { ok: false; error: string; position: number };

/**
 * Validate a formula against the shared grammar. Never throws. A blank
 * formula is `ok` with no fields (it is a no-op filter — the store strips it
 * from the request).
 */
export function compileScreenerExpr(source: string): ScreenerExprResult {
  if (!source.trim()) {
    return { ok: true, fields: [] };
  }
  try {
    const parser = new Parser(source);
    parser.parse();
    return { ok: true, fields: [...parser.fields].sort() };
  } catch (err: unknown) {
    if (err instanceof ScreenerExprError) {
      return { ok: false, error: err.message, position: err.position };
    }
    // Unreachable by construction; surfaced honestly if it ever happens.
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, error: message.slice(0, 160), position: 0 };
  }
}

// ---------------------------------------------------------------------------
// Autocomplete helpers (the editor's prefix dropdown)
// ---------------------------------------------------------------------------

/** Human hints for the dropdown — canonical fields plus the alias rows. */
export interface FieldSuggestion {
  /** The text inserted on accept. */
  name: string;
  /** The canonical field it resolves to (=== name for canonical rows). */
  canonical: ScreenerNumericField;
  /** One-line hint ("P/E ratio", "alias for pe_ratio"). */
  hint: string;
}

const FIELD_HINTS: Record<ScreenerNumericField, string> = {
  market_cap: "Market cap",
  pe_ratio: "P/E ratio",
  forward_pe: "Forward P/E",
  peg_ratio: "PEG ratio",
  price_to_book: "Price / Book",
  price_to_sales: "Price / Sales",
  ev_to_ebitda: "EV / EBITDA",
  book_value: "Book value",
  dividend_yield: "Dividend yield (frac)",
  eps: "EPS",
  beta: "Beta",
  roe: "ROE (frac)",
  roa: "ROA (frac)",
  gross_margin: "Gross margin (frac)",
  operating_margin: "Operating margin (frac)",
  profit_margin: "Net margin (frac)",
  debt_to_equity: "Debt / Equity",
  current_ratio: "Current ratio",
  quick_ratio: "Quick ratio",
  revenue_growth: "Revenue growth (frac)",
  earnings_growth: "Earnings growth (frac)",
  fifty_two_week_high: "52w high",
  fifty_two_week_low: "52w low",
  fifty_two_week_change: "1y change (frac)",
  held_percent_insiders: "Insider holding (frac)",
  held_percent_institutions: "Institutional holding (frac)",
  price: "Price (live quote)",
  change_percent_1d: "1-day % (live quote)",
  volume: "Volume (live quote)",
};

/** Every completable name: canonical fields first, then aliases. */
export const FIELD_SUGGESTIONS: readonly FieldSuggestion[] = [
  ...NUMERIC_FIELDS.map((f) => ({ name: f, canonical: f, hint: FIELD_HINTS[f] })),
  ...Object.entries(FIELD_ALIASES).map(([alias, field]) => ({
    name: alias,
    canonical: field,
    hint: `alias for ${field}`,
  })),
];

/** The identifier span under the caret, if the caret sits in/after one. */
export interface IdentifierSpan {
  start: number;
  end: number;
  prefix: string;
}

/**
 * Find the identifier the caret is touching (for completion). Returns null
 * when the caret is not at the end of / inside an identifier (e.g. after a
 * space or a digit), so the dropdown only opens while a name is being typed.
 */
export function identifierAt(source: string, caret: number): IdentifierSpan | null {
  const clamped = Math.max(0, Math.min(caret, source.length));
  let start = clamped;
  while (start > 0 && /[A-Za-z_0-9]/.test(source[start - 1]!)) {
    start -= 1;
  }
  let end = clamped;
  while (end < source.length && /[A-Za-z_0-9]/.test(source[end]!)) {
    end += 1;
  }
  if (start === end) {
    return null;
  }
  const prefix = source.slice(start, clamped);
  // An identifier must start with a letter/underscore (a bare number is not one).
  if (!/^[A-Za-z_]/.test(source[start]!)) {
    return null;
  }
  return { start, end, prefix };
}

/**
 * Prefix-match suggestions for the dropdown (case-insensitive), capped at
 * `limit`. An exact, already-complete match is excluded — nothing to add.
 * Keywords/functions are not suggested; the dropdown is a FIELD helper.
 */
export function suggestFields(prefix: string, limit = 8): FieldSuggestion[] {
  const needle = prefix.toLowerCase();
  if (!needle) {
    return [];
  }
  return FIELD_SUGGESTIONS.filter(
    (s) => s.name.toLowerCase().startsWith(needle) && s.name.toLowerCase() !== needle,
  ).slice(0, limit);
}
