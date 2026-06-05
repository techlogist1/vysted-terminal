/**
 * Screener formula runner (FR-122 / SC-033) — the async seam the store calls to
 * post-filter the server-returned rows by the user's custom formula.
 *
 * Prefers a Web Worker (`screener-formula.worker.ts`) so a pathological
 * expression evaluates OFF the main thread. When `Worker` is unavailable
 * (jsdom tests, SSR / static-export build, an environment that can't construct
 * a module worker) it falls back to running the SAME sandboxed evaluator inline
 * — correctness is identical; only the thread isolation differs. The worker is
 * created lazily and reused across runs.
 */

import { filterRowsByFormula, type FormulaFilterResult } from "./screener-formula";

import type { ScreenerResultRow } from "../../types/screener";
import type { FormulaWorkerRequest, FormulaWorkerResponse } from "./screener-formula.worker";

let _worker: Worker | null = null;
let _workerUnavailable = false;
let _seq = 0;
/** Outstanding worker requests keyed by request id. */
const _pending = new Map<
  number,
  { resolve: (r: FormulaFilterResult) => void; rows: ScreenerResultRow[] }
>();

/** Lazily build (or reuse) the module worker. Returns null when unsupported. */
function getWorker(): Worker | null {
  if (_workerUnavailable) {
    return null;
  }
  if (_worker) {
    return _worker;
  }
  if (typeof Worker === "undefined") {
    _workerUnavailable = true;
    return null;
  }
  try {
    const worker = new Worker(new URL("./screener-formula.worker.ts", import.meta.url), {
      type: "module",
    });
    worker.onmessage = (event: MessageEvent<FormulaWorkerResponse>) => {
      const { id, passedIndices, error } = event.data;
      const entry = _pending.get(id);
      if (entry) {
        _pending.delete(id);
        entry.resolve({ passedIndices, error });
      }
    };
    worker.onerror = () => {
      // The worker died (e.g. bundling that couldn't resolve the module URL):
      // disable it and resolve every outstanding request via the inline path so
      // the formula still applies — never leave the table hanging.
      _workerUnavailable = true;
      _worker = null;
      for (const [, entry] of _pending) {
        // Re-run inline so the formula still filters (no rows silently lost).
        entry.resolve(filterRowsByFormula(_lastExpression, entry.rows));
      }
      _pending.clear();
    };
    _worker = worker;
    return worker;
  } catch {
    _workerUnavailable = true;
    return null;
  }
}

let _lastExpression = "";

/**
 * Post-filter `rows` by the custom `expression`, returning the matching subset
 * plus an optional inline error. A blank expression returns the rows unchanged.
 * Runs in the Worker when available, else inline (same sandboxed evaluator).
 */
export async function runScreenerFormula(
  expression: string,
  rows: ScreenerResultRow[],
): Promise<{ rows: ScreenerResultRow[]; error?: string }> {
  if (!expression.trim()) {
    return { rows };
  }
  _lastExpression = expression;
  const result = await evaluate(expression, rows);
  return {
    rows: result.passedIndices.map((i) => rows[i]!),
    error: result.error,
  };
}

function evaluate(expression: string, rows: ScreenerResultRow[]): Promise<FormulaFilterResult> {
  const worker = getWorker();
  if (!worker) {
    // Inline fallback — synchronous evaluator wrapped in a resolved promise.
    return Promise.resolve(filterRowsByFormula(expression, rows));
  }
  const id = ++_seq;
  const request: FormulaWorkerRequest = { id, expression, rows };
  return new Promise<FormulaFilterResult>((resolve) => {
    _pending.set(id, { resolve, rows });
    worker.postMessage(request);
  });
}

/** Test helper: tear down the worker + pending queue between tests. */
export function __resetFormulaRunnerForTests(): void {
  if (_worker) {
    _worker.terminate();
  }
  _worker = null;
  _workerUnavailable = false;
  _pending.clear();
  _seq = 0;
  _lastExpression = "";
}
