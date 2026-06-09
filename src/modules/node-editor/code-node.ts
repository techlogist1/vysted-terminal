/**
 * Code node (`transform.code`) — sandboxed mathjs expression evaluator.
 *
 * A code node is a user/agent-authored expression that transforms its
 * bound inputs into one output value inside a workflow run. The spec is
 * plain JSON riding `WorkflowNode.config`:
 *
 *   { "expression": "a + b * 2", "inputs": ["a", "b"] }
 *
 * Each binding name in `inputs` is BOTH an input port on the canvas node
 * AND a variable in the expression scope. Evaluation happens CLIENT-side
 * (mathjs is a frontend dependency; the sidecar engine has no JS runtime)
 * — see `code-node-run.ts` for how the run lifecycle weaves code nodes
 * into the sidecar SSE run.
 *
 * SECURITY — same sandbox recipe as `src/lib/screener-formula.ts`, per
 * mathjs guidance (https://mathjs.org/docs/expressions/security.html):
 * a dedicated `create(all)` instance with `import` / `createUnit` /
 * `evaluate` / `parse` / `simplify` / `derivative` / `resolve` shadowed
 * by throwing stubs, evaluated against a caller-built scope object only.
 * `expr-eval` is BANNED (CVE-2025-12735) — never reintroduce it.
 */

import { create, all, type MathJsInstance, type MathNode } from "mathjs";

/** Node-type id of the code node. Mirrored nowhere in the sidecar (yet) —
 * see docs/redesign/INTEGRATION_NOTES_R7_HACK.md for the parity handler. */
export const CODE_NODE_ID = "transform.code";

/** Output port id every code node emits on. */
export const CODE_NODE_OUTPUT_PORT = "value";

/** Default config stamped onto a freshly-dropped code node — valid as-is. */
export const DEFAULT_CODE_NODE_CONFIG: Readonly<{ expression: string; inputs: readonly string[] }> =
  { expression: "a + b", inputs: ["a", "b"] };

/** Valid binding name: a mathjs identifier. */
const BINDING_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;

export function isValidBindingName(name: string): boolean {
  return BINDING_RE.test(name);
}

/**
 * Read the binding names out of a code node's config. Non-arrays, blank
 * and malformed entries are dropped; duplicates keep the first.
 */
export function codeNodeBindings(config: Record<string, unknown>): string[] {
  const raw = config["inputs"];
  if (!Array.isArray(raw)) {
    return [];
  }
  const seen = new Set<string>();
  const out: string[] = [];
  for (const entry of raw) {
    if (typeof entry === "string" && isValidBindingName(entry) && !seen.has(entry)) {
      seen.add(entry);
      out.push(entry);
    }
  }
  return out;
}

/** Read the expression string out of a code node's config. */
export function codeNodeExpression(config: Record<string, unknown>): string {
  const raw = config["expression"];
  return typeof raw === "string" ? raw : "";
}

/** Propose the next free binding name (a, b, …, z, then in1, in2, …). */
export function nextBindingName(existing: readonly string[]): string {
  const taken = new Set(existing);
  for (let i = 0; i < 26; i += 1) {
    const candidate = String.fromCharCode(97 + i);
    if (!taken.has(candidate)) {
      return candidate;
    }
  }
  let n = 1;
  while (taken.has(`in${n}`)) {
    n += 1;
  }
  return `in${n}`;
}

// ---------------------------------------------------------------------------
// Sandbox
// ---------------------------------------------------------------------------

/** A blocked sandbox entry point — throws if an expression reaches it. */
function blocked(name: string): (...args: unknown[]) => never {
  return () => {
    throw new Error(`"${name}" is disabled in code nodes`);
  };
}

interface Sandbox {
  /** A working parser captured BEFORE the dangerous names were disabled. */
  parse: MathJsInstance["parse"];
  /** The instance itself — used to test whether a symbol is a known function/constant. */
  math: MathJsInstance;
}

function buildSandbox(): Sandbox {
  const math = create(all, {});
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
  return { parse, math };
}

let _sandbox: Sandbox | null = null;
function sandbox(): Sandbox {
  if (_sandbox === null) {
    _sandbox = buildSandbox();
  }
  return _sandbox;
}

// ---------------------------------------------------------------------------
// Compile + evaluate
// ---------------------------------------------------------------------------

export interface CodeCompileResult {
  ok: boolean;
  /** Recovery-first inline error (single line, no stack) when `ok === false`. */
  error?: string;
}

/**
 * Validate that an expression PARSES under the sandbox — drives the inline
 * inspector error before a run. A blank expression is INVALID for a code
 * node (it would emit nothing), unlike the screener formula's no-op blank.
 */
export function compileCodeExpression(expression: string): CodeCompileResult {
  const expr = expression.trim();
  if (expr === "") {
    return { ok: false, error: "expression is empty" };
  }
  try {
    sandbox().parse(expr);
    return { ok: true };
  } catch (err: unknown) {
    return { ok: false, error: friendlyError(err) };
  }
}

export type CodeEvalResult = { ok: true; value: unknown } | { ok: false; error: string };

/**
 * Evaluate an expression against a scope of bound input values. The scope
 * is cloned per call (mathjs may write derived symbols into it). The result
 * is serialized to plain JSON-able data (`Matrix` → array, `BigNumber` /
 * `Fraction` → number) so it can ride `WorkflowRunEvent.outputs`.
 */
export function evaluateCodeExpression(
  expression: string,
  scope: Record<string, unknown>,
): CodeEvalResult {
  const expr = expression.trim();
  if (expr === "") {
    return { ok: false, error: "expression is empty" };
  }
  let compiled: MathNode;
  try {
    compiled = sandbox().parse(expr) as MathNode;
  } catch (err: unknown) {
    return { ok: false, error: friendlyError(err) };
  }
  const cleanScope = buildScope(scope);
  // mathjs resolves unknown symbols to UNITS when the name matches one
  // (`b` → bit, `m` → meter), which would silently turn an unwired input
  // into unit math. Reject undefined symbols explicitly instead.
  const missing = undefinedSymbols(compiled, cleanScope);
  if (missing.length > 0) {
    return { ok: false, error: `Undefined symbol ${missing[0]}` };
  }
  try {
    const value: unknown = compiled.compile().evaluate(cleanScope);
    return { ok: true, value: toPlain(value) };
  } catch (err: unknown) {
    return { ok: false, error: friendlyError(err) };
  }
}

/**
 * Collect symbols that are neither in the scope, nor known sandbox
 * functions/constants, nor assignment targets within the expression
 * (`x = 2; x * 3` defines `x` locally).
 */
function undefinedSymbols(root: MathNode, scope: Record<string, unknown>): string[] {
  const math = sandbox().math as unknown as Record<string, unknown>;
  const defined = new Set<string>(Object.keys(scope));
  root.traverse((node) => {
    if (node.type === "AssignmentNode") {
      const target = (node as unknown as { object?: { name?: string } }).object;
      if (typeof target?.name === "string") {
        defined.add(target.name);
      }
    } else if (node.type === "FunctionAssignmentNode") {
      const fn = node as unknown as { name?: string; params?: string[] };
      if (typeof fn.name === "string") {
        defined.add(fn.name);
      }
      for (const param of fn.params ?? []) {
        defined.add(param);
      }
    }
  });
  const missing: string[] = [];
  root.traverse((node) => {
    if (node.type === "SymbolNode") {
      const name = (node as unknown as { name: string }).name;
      if (!defined.has(name) && !(name in math) && !missing.includes(name)) {
        missing.push(name);
      }
    }
  });
  return missing;
}

/** Drop undefined bindings so a missing input surfaces as "Undefined symbol". */
function buildScope(scope: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(scope)) {
    if (value !== undefined) {
      out[key] = value;
    }
  }
  return out;
}

/** Serialize a mathjs result to plain JSON-able data. */
function toPlain(value: unknown): unknown {
  if (value === null || typeof value !== "object") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(toPlain);
  }
  const candidate = value as {
    toArray?: () => unknown;
    toNumber?: () => number;
    toJSON?: () => unknown;
  };
  if (typeof candidate.toArray === "function") {
    return toPlain(candidate.toArray());
  }
  if (typeof candidate.toNumber === "function") {
    return candidate.toNumber();
  }
  if (typeof candidate.toJSON === "function") {
    return candidate.toJSON();
  }
  return value;
}

/** Strip a mathjs error to its first line, capped — never the raw stack. */
function friendlyError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  return raw.split("\n")[0]!.slice(0, 160);
}
