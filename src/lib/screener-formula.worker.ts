/**
 * Screener formula Web Worker (FR-122 / SC-033).
 *
 * Runs the sandboxed mathjs evaluator OFF the main thread so a hostile or
 * pathological custom formula can't touch the DOM / main-thread globals — the
 * worker scope has no `window`, no `document`, and the sandboxed mathjs instance
 * has `import`/`createUnit`/`evaluate`/`parse`-injection disabled (see
 * `screener-formula.ts`). The worker only ever receives plain JSON rows + an
 * expression string and posts back the passing indices.
 */

import { filterRowsByFormula } from "./screener-formula";

import type { ScreenerResultRow } from "../../types/screener";

export interface FormulaWorkerRequest {
  id: number;
  expression: string;
  rows: ScreenerResultRow[];
}

export interface FormulaWorkerResponse {
  id: number;
  passedIndices: number[];
  error?: string;
}

self.onmessage = (event: MessageEvent<FormulaWorkerRequest>) => {
  const { id, expression, rows } = event.data;
  const { passedIndices, error } = filterRowsByFormula(expression, rows);
  const response: FormulaWorkerResponse = { id, passedIndices, error };
  (self as unknown as Worker).postMessage(response);
};
