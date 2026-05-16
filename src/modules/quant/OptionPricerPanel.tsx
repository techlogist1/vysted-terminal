"use client";

/**
 * Option Pricer Panel — Teammate Q Phase 6.
 *
 * Three engines in one panel: Black-Scholes analytic, Cox-Ross-Rubinstein
 * binomial, Monte Carlo. The user fills in the standard BSM inputs
 * (spot/strike/r/q/σ/T/payoff/exercise), picks a method, and clicks Price.
 *
 * Engine-specific knobs surface only when their method is selected
 * (binomial: steps; Monte Carlo: paths + seed) — keeps the form focused
 * on the active calculation.
 */

import { useCallback, useState } from "react";
import { Calculator } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useQuantStore } from "@/store/quant";

import type {
  OptionExercise,
  OptionPayoff,
  OptionPricingMethod,
  OptionPricingRequest,
} from "../../../types/quant";

const METHODS: ReadonlyArray<{ id: OptionPricingMethod; label: string }> = [
  { id: "black-scholes", label: "Black-Scholes" },
  { id: "binomial", label: "Binomial (CRR)" },
  { id: "monte-carlo", label: "Monte Carlo" },
];

const PAYOFFS: ReadonlyArray<{ id: OptionPayoff; label: string }> = [
  { id: "call", label: "Call" },
  { id: "put", label: "Put" },
];

const EXERCISES: ReadonlyArray<{ id: OptionExercise; label: string }> = [
  { id: "european", label: "European" },
  { id: "american", label: "American" },
];

interface FieldProps {
  label: string;
  value: string | number;
  onChange: (v: string) => void;
  type?: string;
  step?: string;
  disabled?: boolean;
  testId?: string;
}

function Field({ label, value, onChange, type = "number", step, disabled, testId }: FieldProps) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-charcoal-300 font-mono text-[10px]">{label}</span>
      <input
        type={type}
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        data-testid={testId}
        className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs outline-none focus-visible:border-amber-500 disabled:opacity-50"
      />
    </label>
  );
}

export function OptionPricerPanel() {
  const lastResult = useQuantStore((s) => s.lastOptionPricing);
  const status = useQuantStore((s) => s.optionStatus);
  const error = useQuantStore((s) => s.optionError);
  const priceOption = useQuantStore((s) => s.priceOption);

  const [exercise, setExercise] = useState<OptionExercise>("european");
  const [payoff, setPayoff] = useState<OptionPayoff>("call");
  const [method, setMethod] = useState<OptionPricingMethod>("black-scholes");
  const [spot, setSpot] = useState("220");
  const [strike, setStrike] = useState("220");
  const [r, setR] = useState("0.05");
  const [q, setQ] = useState("0.005");
  const [vol, setVol] = useState("0.28");
  const [valuationDate, setValuationDate] = useState("2026-05-16");
  const [expiryDate, setExpiryDate] = useState("2026-06-30");
  const [binomialSteps, setBinomialSteps] = useState("200");
  const [mcPaths, setMcPaths] = useState("50000");
  const [mcSeed, setMcSeed] = useState("42");

  const isRunning = status === "loading";

  const handlePrice = useCallback(async () => {
    const req: OptionPricingRequest = {
      exercise,
      payoff,
      method,
      spot: Number(spot),
      strike: Number(strike),
      risk_free_rate: Number(r),
      dividend_yield: Number(q),
      volatility: Number(vol),
      valuation_date: valuationDate,
      expiry_date: expiryDate,
    };
    if (method === "binomial") {
      req.binomial_steps = Number(binomialSteps);
    }
    if (method === "monte-carlo") {
      req.monte_carlo_paths = Number(mcPaths);
      req.monte_carlo_seed = Number(mcSeed);
    }
    try {
      await priceOption(req);
    } catch {
      // surfaced via store.optionError
    }
  }, [
    exercise,
    payoff,
    method,
    spot,
    strike,
    r,
    q,
    vol,
    valuationDate,
    expiryDate,
    binomialSteps,
    mcPaths,
    mcSeed,
    priceOption,
  ]);

  // American + black-scholes is invalid — disable Price when so.
  const incompatibleAmericanBs = exercise === "american" && method === "black-scholes";
  const incompatibleAmericanMc = exercise === "american" && method === "monte-carlo";
  const incompatible = incompatibleAmericanBs || incompatibleAmericanMc;
  const canPrice = !isRunning && !incompatible;

  return (
    <div className="bg-charcoal-900 flex h-full min-h-0 w-full">
      <aside
        className="border-charcoal-700 flex w-80 flex-col gap-3 overflow-y-auto border-r p-3"
        data-testid="option-pricer-form"
      >
        <div className="flex flex-col gap-1.5">
          <span className="text-charcoal-500 font-mono text-[10px] tracking-widest uppercase">
            Method
          </span>
          <div role="radiogroup" aria-label="Pricing method" className="grid grid-cols-3 gap-1">
            {METHODS.map((m) => (
              <button
                type="button"
                key={m.id}
                role="radio"
                aria-checked={method === m.id}
                onClick={() => setMethod(m.id)}
                disabled={isRunning}
                className={cn(
                  "rounded-control h-7 border font-mono text-[10px]",
                  method === m.id
                    ? "border-amber-500 bg-amber-500/20 text-amber-200"
                    : "border-charcoal-700 bg-charcoal-850 text-charcoal-300 hover:bg-charcoal-800",
                )}
                data-testid={`method-${m.id}`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-charcoal-500 font-mono text-[10px] tracking-widest uppercase">
            Payoff / Exercise
          </span>
          <div className="grid grid-cols-2 gap-2">
            <div role="radiogroup" aria-label="Payoff" className="grid grid-cols-2 gap-1">
              {PAYOFFS.map((p) => (
                <button
                  type="button"
                  key={p.id}
                  role="radio"
                  aria-checked={payoff === p.id}
                  onClick={() => setPayoff(p.id)}
                  disabled={isRunning}
                  className={cn(
                    "rounded-control h-7 border font-mono text-[10px]",
                    payoff === p.id
                      ? "border-amber-500 bg-amber-500/20 text-amber-200"
                      : "border-charcoal-700 bg-charcoal-850 text-charcoal-300 hover:bg-charcoal-800",
                  )}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <div role="radiogroup" aria-label="Exercise" className="grid grid-cols-2 gap-1">
              {EXERCISES.map((e) => (
                <button
                  type="button"
                  key={e.id}
                  role="radio"
                  aria-checked={exercise === e.id}
                  onClick={() => setExercise(e.id)}
                  disabled={isRunning}
                  className={cn(
                    "rounded-control h-7 border font-mono text-[10px]",
                    exercise === e.id
                      ? "border-amber-500 bg-amber-500/20 text-amber-200"
                      : "border-charcoal-700 bg-charcoal-850 text-charcoal-300 hover:bg-charcoal-800",
                  )}
                >
                  {e.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Field
            label="Spot"
            value={spot}
            onChange={setSpot}
            step="0.01"
            disabled={isRunning}
            testId="field-spot"
          />
          <Field
            label="Strike"
            value={strike}
            onChange={setStrike}
            step="0.01"
            disabled={isRunning}
            testId="field-strike"
          />
          <Field
            label="Risk-free r"
            value={r}
            onChange={setR}
            step="0.001"
            disabled={isRunning}
            testId="field-rate"
          />
          <Field
            label="Div. yield q"
            value={q}
            onChange={setQ}
            step="0.001"
            disabled={isRunning}
            testId="field-div"
          />
          <Field
            label="Volatility σ"
            value={vol}
            onChange={setVol}
            step="0.01"
            disabled={isRunning}
            testId="field-vol"
          />
          <Field
            label="Valuation date"
            value={valuationDate}
            onChange={setValuationDate}
            type="date"
            disabled={isRunning}
          />
        </div>
        <Field
          label="Expiry date"
          value={expiryDate}
          onChange={setExpiryDate}
          type="date"
          disabled={isRunning}
        />

        {method === "binomial" && (
          <Field
            label="Tree steps"
            value={binomialSteps}
            onChange={setBinomialSteps}
            disabled={isRunning}
            testId="field-binomial-steps"
          />
        )}
        {method === "monte-carlo" && (
          <div className="grid grid-cols-2 gap-2">
            <Field
              label="MC paths"
              value={mcPaths}
              onChange={setMcPaths}
              disabled={isRunning}
              testId="field-mc-paths"
            />
            <Field
              label="MC seed"
              value={mcSeed}
              onChange={setMcSeed}
              disabled={isRunning}
              testId="field-mc-seed"
            />
          </div>
        )}

        {incompatible && (
          <p className="font-mono text-[10px] text-amber-300" role="alert">
            {incompatibleAmericanBs
              ? "Black-Scholes only supports European exercise. Switch to Binomial for American."
              : "Monte Carlo only supports European exercise in v0.6.0. Use Binomial for American."}
          </p>
        )}

        <Button
          type="button"
          onClick={handlePrice}
          disabled={!canPrice}
          size="sm"
          variant="default"
          aria-label="Price option"
          className="mt-auto"
          data-testid="price-option"
        >
          <Calculator />
          {isRunning ? "Pricing…" : "Price"}
        </Button>
      </aside>

      <section className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
        {error && (
          <p
            className="text-negative bg-negative/10 border-negative/30 rounded-control mb-3 border p-2 font-mono text-xs"
            role="alert"
            data-testid="option-pricing-error"
          >
            {error}
          </p>
        )}

        {!lastResult && status === "idle" && (
          <div className="text-charcoal-500 flex h-full items-center justify-center font-mono text-xs">
            Fill in the inputs on the left and click Price.
          </div>
        )}

        {lastResult && (
          <div className="grid gap-4" data-testid="option-pricing-result">
            <div className="border-charcoal-700 bg-charcoal-850 rounded-control border p-4">
              <div className="text-charcoal-500 mb-2 font-mono text-[10px] tracking-widest uppercase">
                Result · {lastResult.method}
              </div>
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-3xl text-amber-300" data-testid="option-price">
                  ${lastResult.price.toFixed(4)}
                </span>
                {lastResult.monte_carlo_std_error !== null && (
                  <span
                    className="text-charcoal-400 font-mono text-xs"
                    data-testid="option-mc-error"
                  >
                    ± {lastResult.monte_carlo_std_error.toFixed(4)} (1 SE)
                  </span>
                )}
              </div>
              <div className="text-charcoal-500 mt-2 font-mono text-[10px]">
                computed in {lastResult.duration_ms.toFixed(1)} ms
              </div>
            </div>

            {lastResult.greeks && (
              <div className="border-charcoal-700 bg-charcoal-850 rounded-control border p-4">
                <div className="text-charcoal-500 mb-2 font-mono text-[10px] tracking-widest uppercase">
                  Greeks
                </div>
                <div className="grid grid-cols-5 gap-2">
                  <GreekCell label="Δ Delta" value={lastResult.greeks.delta} />
                  <GreekCell label="Γ Gamma" value={lastResult.greeks.gamma} />
                  <GreekCell label="ν Vega" value={lastResult.greeks.vega} />
                  <GreekCell label="Θ Theta" value={lastResult.greeks.theta} />
                  <GreekCell label="ρ Rho" value={lastResult.greeks.rho} />
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

function GreekCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="border-charcoal-700 bg-charcoal-900 rounded-control flex flex-col gap-1 border p-2">
      <span className="text-charcoal-400 font-mono text-[10px]">{label}</span>
      <span className="text-charcoal-100 font-mono text-sm">{value.toFixed(4)}</span>
    </div>
  );
}
