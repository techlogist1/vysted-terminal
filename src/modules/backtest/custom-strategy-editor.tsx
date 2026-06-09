"use client";

import { useEffect, useRef, useState } from "react";

import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";

/**
 * Custom-strategy definition editor — the frontend face of the sidecar's
 * restricted signal DSL (`services/backtest_dsl.py`). Two monospaced rule
 * editors (entry/exit) + position size, validated inline against
 * `POST /backtest/strategies/custom/validate` on a short debounce. Errors
 * render with the rule source and a caret at the parser's character
 * position; a valid definition surfaces the referenced indicators and the
 * warm-up bar count so the user knows how much history the rules need.
 *
 * The values ride the same `params` record the panel submits in
 * `BacktestRequest.params` — this component is a specialised ParamsForm for
 * the `custom` strategy id, nothing more.
 */

// ---------------------------------------------------------------------------
// Wire contract — mirrors routers/backtest.py CustomValidateResponse
// ---------------------------------------------------------------------------

export interface CustomRuleError {
  rule: string;
  message: string;
  position: number | null;
}

export interface CustomValidateResult {
  ok: boolean;
  errors: CustomRuleError[];
  indicators: string[];
  requiredBars: number;
}

export async function validateCustomDefinition(definition: {
  entry: string;
  exit: string;
  positionSize?: number;
}): Promise<CustomValidateResult> {
  const base = await getSidecarBaseUrl();
  const url = new URL("/backtest/strategies/custom/validate", base);
  const response = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(definition),
  });
  if (!response.ok) {
    throw new Error(`Validation request failed (${response.status})`);
  }
  return (await response.json()) as CustomValidateResult;
}

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------

const GRAMMAR_HINT = "sma · ema · rsi · highest · lowest · stdev · change(n) · and/or/not";

type ValidationStatus = "idle" | "validating" | "valid" | "invalid" | "unavailable";

export interface CustomStrategyEditorProps {
  /** The panel's `params` record — entry/exit/position_size live here. */
  values: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
  disabled?: boolean;
  /** `false` while the definition fails validation — gates the Run button. */
  onValidityChange?: (valid: boolean) => void;
  /** Debounce for the validate round-trip; tests pass 0. */
  debounceMs?: number;
}

function RuleErrorCaret({ source, error }: { source: string; error: CustomRuleError }) {
  const col = error.position !== null ? ` (col ${error.position + 1})` : "";
  return (
    <div data-testid={`rule-error-${error.rule}`} className="flex flex-col gap-0.5">
      <p className="text-negative text-micro font-mono">
        {error.rule}: {error.message}
        {col}
      </p>
      {error.position !== null && source && (
        <pre className="text-charcoal-400 text-micro overflow-x-auto font-mono leading-tight">
          {source}
          {"\n"}
          {" ".repeat(Math.min(error.position, source.length))}
          <span className="text-negative">^</span>
        </pre>
      )}
    </div>
  );
}

export function CustomStrategyEditor({
  values,
  onChange,
  disabled,
  onValidityChange,
  debounceMs = 350,
}: CustomStrategyEditorProps) {
  const entry = typeof values.entry === "string" ? values.entry : "";
  const exit = typeof values.exit === "string" ? values.exit : "";
  const positionSize = typeof values.position_size === "number" ? values.position_size : 100;

  const [status, setStatus] = useState<ValidationStatus>("idle");
  const [errors, setErrors] = useState<CustomRuleError[]>([]);
  const [indicators, setIndicators] = useState<string[]>([]);
  const [requiredBars, setRequiredBars] = useState(0);

  // Monotonic sequence guards out-of-order validate responses.
  const requestSeq = useRef(0);
  // Latest-callback ref (synced in an effect — React 19 forbids ref writes
  // during render) so the validate effect doesn't re-fire on a new closure.
  const onValidityChangeRef = useRef(onValidityChange);
  useEffect(() => {
    onValidityChangeRef.current = onValidityChange;
  }, [onValidityChange]);

  useEffect(() => {
    const seq = ++requestSeq.current;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- debounce status precedes the async round-trip
    setStatus("validating");
    const timer = setTimeout(() => {
      void validateCustomDefinition({ entry, exit, positionSize })
        .then((result) => {
          if (requestSeq.current !== seq) {
            return;
          }
          setStatus(result.ok ? "valid" : "invalid");
          setErrors(result.errors);
          setIndicators(result.indicators);
          setRequiredBars(result.requiredBars);
          onValidityChangeRef.current?.(result.ok);
        })
        .catch(() => {
          if (requestSeq.current !== seq) {
            return;
          }
          // Sidecar unreachable — don't block Run on a dead validator; the
          // run route re-validates server-side and streams a run-error.
          setStatus("unavailable");
          setErrors([]);
          onValidityChangeRef.current?.(true);
        });
    }, debounceMs);
    return () => clearTimeout(timer);
  }, [entry, exit, positionSize, debounceMs]);

  const errorByRule = new Map(errors.map((error) => [error.rule, error]));

  const ruleField = (rule: "entry" | "exit", source: string) => (
    <label className="flex flex-col gap-1">
      <span className="text-charcoal-300 text-micro font-mono">{rule}</span>
      <textarea
        value={source}
        onChange={(event) => onChange({ ...values, [rule]: event.target.value })}
        disabled={disabled}
        rows={2}
        spellCheck={false}
        aria-label={`${rule} rule`}
        data-testid={`custom-rule-${rule}`}
        className={cn(
          "bg-charcoal-850 text-charcoal-100 rounded-control text-caption focus-visible:border-charcoal-500 resize-y border px-2 py-1.5 font-mono outline-none disabled:opacity-50",
          errorByRule.has(rule) ? "border-negative/60" : "border-charcoal-700",
        )}
      />
      {errorByRule.has(rule) && (
        <RuleErrorCaret source={source} error={errorByRule.get(rule) as CustomRuleError} />
      )}
    </label>
  );

  return (
    <div className="flex flex-col gap-1.5" data-testid="custom-strategy-editor">
      <span className="text-charcoal-500 text-micro font-mono tracking-widest uppercase">
        Definition
      </span>
      {ruleField("entry", entry)}
      {ruleField("exit", exit)}
      <label className="flex flex-col gap-1">
        <span className="text-charcoal-300 text-micro font-mono">position_size</span>
        <input
          type="number"
          min={1}
          value={positionSize}
          onChange={(event) => {
            const parsed = parseFloat(event.target.value);
            onChange({
              ...values,
              position_size: Number.isFinite(parsed) ? parsed : positionSize,
            });
          }}
          disabled={disabled}
          aria-label="position_size"
          className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-caption focus-visible:border-charcoal-500 h-8 border px-2 font-mono outline-none disabled:opacity-50"
        />
        {errorByRule.has("position_size") && (
          <p data-testid="rule-error-position_size" className="text-negative text-micro font-mono">
            {(errorByRule.get("position_size") as CustomRuleError).message}
          </p>
        )}
      </label>
      <p className="text-charcoal-500 text-micro font-mono">{GRAMMAR_HINT}</p>
      {status === "valid" && (
        <p data-testid="custom-valid-summary" className="text-charcoal-400 text-micro font-mono">
          uses {indicators.length > 0 ? indicators.join(", ") : "price fields only"} · needs{" "}
          {requiredBars} bars
        </p>
      )}
      {status === "unavailable" && (
        <p data-testid="custom-validate-offline" className="text-charcoal-500 text-micro font-mono">
          validator offline — rules are checked when the run starts
        </p>
      )}
    </div>
  );
}
