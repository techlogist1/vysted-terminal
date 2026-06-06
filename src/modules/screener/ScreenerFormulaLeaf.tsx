"use client";

import { useMemo } from "react";
import { FunctionSquare, AlertCircle } from "lucide-react";

import { compileFormula } from "@/lib/screener-formula";
import { useScreenerStore } from "@/store/screener";

/**
 * Custom-formula leaf (FR-122 / SC-033).
 *
 * A free-text mathjs boolean expression evaluated CLIENT-SIDE over each
 * server-returned result row in a Web Worker — it POST-FILTERS the matched set
 * (it does not change the server query). The UI says so explicitly. Available
 * symbols are the row's numeric fields (`pe`/`pe_ratio`, `marketCap`/
 * `market_cap`, `roe`, `dividend_yield`, `price`, `volume`, …). Parse errors
 * surface inline (recovery-first, no raw stack); the live filtered/total count
 * after a run is shown by the results table.
 */
export function ScreenerFormulaLeaf() {
  const formula = useScreenerStore((s) => s.formula);
  const setFormula = useScreenerStore((s) => s.setFormula);
  const formulaError = useScreenerStore((s) => s.formulaError);
  const preFormulaCount = useScreenerStore((s) => s.preFormulaCount);
  const lastResult = useScreenerStore((s) => s.lastResult);

  // Eager parse check so a typo lights up before the user runs.
  const compile = useMemo(() => compileFormula(formula), [formula]);
  const parseError = !compile.ok ? compile.error : undefined;
  // After a run, the eval-time error (e.g. a missing field on some rows).
  const runError = formulaError ?? undefined;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <FunctionSquare className="text-muted-foreground size-4" />
        <h3 className="text-muted-foreground text-caption font-semibold tracking-wide uppercase">
          Custom formula
        </h3>
        <span className="text-muted-foreground text-micro">
          Filters the matched results · runs client-side
        </span>
      </div>
      <input
        aria-label="custom formula"
        data-testid="screener-formula-input"
        type="text"
        spellCheck={false}
        value={formula}
        onChange={(e) => setFormula(e.target.value)}
        placeholder="e.g. pe < 15 and roe > 0.2   ·   market_cap / volume > 1e6"
        className={
          "border-border bg-charcoal-850 rounded-control text-body h-8 w-full border px-2 font-mono " +
          (parseError ? "border-destructive/60" : "")
        }
      />
      {parseError ? (
        <div className="text-destructive text-micro flex items-center gap-1.5">
          <AlertCircle className="size-3 shrink-0" />
          <span>{parseError}</span>
        </div>
      ) : runError ? (
        <div className="text-warning text-micro flex items-center gap-1.5">
          <AlertCircle className="size-3 shrink-0" />
          <span>{runError} — rows missing that field were dropped.</span>
        </div>
      ) : formula.trim() && preFormulaCount !== null && lastResult ? (
        <p className="text-muted-foreground text-micro">
          Formula kept {lastResult.result_count} of {preFormulaCount} matched row
          {preFormulaCount === 1 ? "" : "s"}.
        </p>
      ) : formula.trim() ? (
        <p className="text-muted-foreground text-micro">
          Available: pe, pe_ratio, marketCap, market_cap, roe, dividend_yield, price, volume, … —
          run the screener to apply.
        </p>
      ) : null}
    </div>
  );
}
