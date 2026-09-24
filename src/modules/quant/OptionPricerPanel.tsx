"use client";

/**
 * Option Pricer — three engines (Black-Scholes / CRR binomial / Monte Carlo).
 *
 * R7 layout (VYSTED_DESIGN.md):
 *
 *   ┌──────────────┬──────────────────────────────────────────────────┐
 *   │ INPUT RAIL   │ RESULT · METHOD  ····  request echo (meta)       │
 *   │  method list ├──────────────────────────────────────────────────┤
 *   │  payoff /    │ [Δ DELTA] [Γ GAMMA] [ν VEGA] [Θ THETA] [ρ RHO]   │
 *   │  exercise    │   metric cards — section-size tabular values     │
 *   │  segmented   ├──────────────────────────────────────────────────┤
 *   │  2-col grid  │ computed in N ms                                 │
 *   │  of 32px     │                                                  │
 *   │  inputs      │                                                  │
 *   │  inline      │                                                  │
 *   │  validation  │                                                  │
 *   │ [Price]      │                                                  │
 *   └──────────────┴──────────────────────────────────────────────────┘
 *
 * Every control sits on the 32px ladder at text-body; validation (including
 * the American×Black-Scholes / American×Monte-Carlo incompatibilities) is an
 * honest inline line, never a silent NaN POST. The empty state is the shared
 * composed EmptyState whose CTA runs the price with the prefilled inputs.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Calculator } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { regionConfig } from "@/lib/region";
import { cn } from "@/lib/utils";
import { usePanelContextBus } from "@/store/panel-context";
import { useQuantStore } from "@/store/quant";
import { useSettingsStore } from "@/store/settings";

import type {
  Greeks,
  OptionExercise,
  OptionPayoff,
  OptionPricingMethod,
  OptionPricingRequest,
} from "../../../types/quant";
import { DISPLAY_CURRENCIES, formatOptionPrice, greekForDisplay } from "./units";

const GREEK_CARDS: ReadonlyArray<{ key: keyof Greeks; label: string }> = [
  { key: "delta", label: "Δ Delta" },
  { key: "gamma", label: "Γ Gamma" },
  { key: "vega", label: "ν Vega" },
  { key: "theta", label: "Θ Theta" },
  { key: "rho", label: "ρ Rho" },
];

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
  value: string;
  onChange: (v: string) => void;
  type?: string;
  step?: string;
  disabled?: boolean;
  testId?: string;
}

/** One labelled rail input — micro label over a 32px inset field (text-body,
 *  tabular figures so swept values stay column-stable). */
function Field({ label, value, onChange, type = "number", step, disabled, testId }: FieldProps) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-charcoal-500 text-micro">{label}</span>
      <input
        type={type}
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        data-testid={testId}
        // Date inputs ride full-width rows (never the 2-col grid) so dd/mm/yyyy
        // plus the native calendar indicator always fit at the fixed rail width.
        className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 w-full border px-3 tabular-nums outline-none disabled:opacity-50"
      />
    </label>
  );
}

/** A horizontal segmented radiogroup — one bordered unit, hairline-divided. */
function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
  disabled,
  testIdPrefix,
}: {
  label: string;
  options: ReadonlyArray<{ id: T; label: string }>;
  value: T;
  onChange: (next: T) => void;
  disabled?: boolean;
  testIdPrefix?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-charcoal-500 text-micro">{label}</span>
      <div
        role="radiogroup"
        aria-label={label}
        className="border-charcoal-700 divide-charcoal-700 rounded-control flex h-8 divide-x overflow-hidden border"
      >
        {options.map((opt) => (
          <button
            type="button"
            key={opt.id}
            role="radio"
            aria-checked={value === opt.id}
            onClick={() => onChange(opt.id)}
            disabled={disabled}
            className={cn(
              "text-micro flex-1 uppercase",
              value === opt.id
                ? "bg-charcoal-875 text-lume"
                : "text-charcoal-400 hover:text-charcoal-200 bg-transparent",
            )}
            data-testid={testIdPrefix ? `${testIdPrefix}-${opt.id}` : undefined}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** A vertical segmented radio list — for options whose labels are too wide
 *  for thirds of the rail (the three engine names). One bordered unit. */
function SegmentedList<T extends string>({
  label,
  options,
  value,
  onChange,
  disabled,
  testIdPrefix,
}: {
  label: string;
  options: ReadonlyArray<{ id: T; label: string }>;
  value: T;
  onChange: (next: T) => void;
  disabled?: boolean;
  testIdPrefix: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-charcoal-500 text-micro">{label}</span>
      <div
        role="radiogroup"
        aria-label={label}
        className="border-charcoal-700 divide-charcoal-700 rounded-control flex flex-col divide-y overflow-hidden border"
      >
        {options.map((opt) => (
          <button
            type="button"
            key={opt.id}
            role="radio"
            aria-checked={value === opt.id}
            onClick={() => onChange(opt.id)}
            disabled={disabled}
            className={cn(
              "text-micro h-8 px-3 text-left uppercase",
              value === opt.id
                ? "bg-charcoal-875 text-lume"
                : "text-charcoal-400 hover:text-charcoal-200 bg-transparent",
            )}
            data-testid={`${testIdPrefix}-${opt.id}`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** One result metric card — micro label over a section-size tabular value,
 *  with its unit beneath when it has one. */
function MetricCard({
  label,
  value,
  unit,
  testId,
}: {
  label: string;
  value: string;
  unit?: string | null;
  testId?: string;
}) {
  return (
    <div
      className="border-charcoal-700 bg-charcoal-900 flex flex-col gap-2 rounded-none border p-6"
      data-testid={testId}
    >
      <span className="text-charcoal-500 text-micro">{label}</span>
      <span className="text-charcoal-100 text-section tabular-nums">{value}</span>
      {unit && <span className="text-charcoal-500 text-micro">{unit}</span>}
    </div>
  );
}

/** Pulse skeleton mirroring the result layout — first price only (a re-price
 *  keeps the previous result on screen). */
function ResultSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-8" data-testid="option-skeleton">
      <div className="border-charcoal-700 rounded-none border p-6">
        <div className="bg-charcoal-800 h-3 w-32 rounded-none" />
        <div className="bg-charcoal-800 mt-3 h-6 w-24 rounded-none" />
      </div>
      <div className="grid grid-cols-2 gap-6 md:grid-cols-3 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="border-charcoal-700 rounded-none border p-6">
            <div className="bg-charcoal-800 h-3 w-16 rounded-none" />
            <div className="bg-charcoal-800 mt-3 h-5 w-20 rounded-none" />
          </div>
        ))}
      </div>
    </div>
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

  // Display currency, defaulting to the session region's (the Bond pricer's
  // R15-DATA-100 select). Display only; the pricing request stays currency-free.
  const region = useSettingsStore((s) => s.region);
  const [displayCurrency, setDisplayCurrency] = useState(() => regionConfig(region).currency);

  const isRunning = status === "loading";

  // Honest inline validation — surfaced in the rail, never a silent NaN POST.
  // The exercise×engine incompatibilities are validation too, stated plainly.
  const validationError = useMemo(() => {
    if (exercise === "american" && method === "black-scholes") {
      return "Black-Scholes only supports European exercise — switch to Binomial for American.";
    }
    if (exercise === "american" && method === "monte-carlo") {
      return "Monte Carlo only supports European exercise — switch to Binomial for American.";
    }
    const nums = { spot, strike, "risk-free r": r, "div. yield q": q, "volatility σ": vol };
    for (const [name, raw] of Object.entries(nums)) {
      if (raw.trim() === "" || Number.isNaN(Number(raw))) {
        return `Enter a numeric ${name}.`;
      }
    }
    if (Number(spot) <= 0 || Number(strike) <= 0) {
      return "Spot and strike must be positive.";
    }
    if (Number(vol) <= 0) {
      return "Volatility must be positive.";
    }
    if (valuationDate === "" || expiryDate === "") {
      return "Both dates are required.";
    }
    if (expiryDate <= valuationDate) {
      return "Expiry must be after the valuation date.";
    }
    if (method === "binomial") {
      const steps = Number(binomialSteps);
      if (!Number.isInteger(steps) || steps < 1) {
        return "Tree steps must be a whole number ≥ 1.";
      }
    }
    if (method === "monte-carlo") {
      const paths = Number(mcPaths);
      if (!Number.isInteger(paths) || paths < 1) {
        return "MC paths must be a whole number ≥ 1.";
      }
      if (mcSeed.trim() === "" || !Number.isInteger(Number(mcSeed))) {
        return "MC seed must be a whole number.";
      }
    }
    return null;
  }, [
    exercise,
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
  ]);

  // The request a displayed result was computed FROM — echoed next to the
  // price so the readout never silently pairs with edited-but-unpriced inputs.
  const [computedReq, setComputedReq] = useState<OptionPricingRequest | null>(null);

  const handlePrice = useCallback(async () => {
    if (validationError !== null) {
      return;
    }
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
      setComputedReq(req);
    } catch {
      // surfaced via store.optionError
    }
  }, [
    validationError,
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

  const greeks = lastResult?.greeks ?? null;

  // R15-AGENT-053: publish the active pricing setup + last result so the
  // copilot can see what's on screen.
  const publishPanelContext = usePanelContextBus((s) => s.publish);
  const unregisterPanelContext = usePanelContextBus((s) => s.unregisterSource);

  useEffect(() => {
    publishPanelContext({
      source: "option-pricer",
      kind: "snapshot",
      payload: {
        method,
        payoff,
        exercise,
        strike: Number(strike),
        price: lastResult?.price ?? null,
      },
      emittedAt: Date.now(),
    });
  }, [publishPanelContext, method, payoff, exercise, strike, lastResult]);

  useEffect(() => {
    return () => {
      unregisterPanelContext("option-pricer");
    };
  }, [unregisterPanelContext]);

  return (
    <div className="bg-charcoal-900 flex h-full min-h-0 w-full">
      {/* --- Input rail ----------------------------------------------------- */}
      <aside
        className="border-charcoal-700 flex w-72 shrink-0 flex-col gap-6 overflow-y-auto border-r p-6"
        data-testid="option-pricer-form"
      >
        <SegmentedList
          label="Method"
          options={METHODS}
          value={method}
          onChange={setMethod}
          disabled={isRunning}
          testIdPrefix="method"
        />
        <Segmented
          label="Payoff"
          options={PAYOFFS}
          value={payoff}
          onChange={setPayoff}
          disabled={isRunning}
        />
        <Segmented
          label="Exercise"
          options={EXERCISES}
          value={exercise}
          onChange={setExercise}
          disabled={isRunning}
        />

        <div className="grid grid-cols-2 gap-3">
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
        </div>
        <Field
          label="Volatility σ"
          value={vol}
          onChange={setVol}
          step="0.01"
          disabled={isRunning}
          testId="field-vol"
        />
        {/* Date fields take the rail's full width — at the 2-col grid step the
            native calendar indicator clips the year's last digit. */}
        <Field
          label="Valuation"
          value={valuationDate}
          onChange={setValuationDate}
          type="date"
          disabled={isRunning}
        />
        <Field
          label="Expiry"
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
          <div className="grid grid-cols-2 gap-3">
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

        <label className="flex flex-col gap-1">
          <span className="text-charcoal-500 text-micro">Display currency</span>
          <select
            value={displayCurrency}
            onChange={(e) => setDisplayCurrency(e.target.value)}
            data-testid="field-display-currency"
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 border px-3 outline-none"
          >
            {DISPLAY_CURRENCIES.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </label>

        {validationError !== null && (
          <p className="text-negative text-caption" role="alert" data-testid="option-validation">
            {validationError}
          </p>
        )}

        <Button
          type="button"
          onClick={handlePrice}
          disabled={isRunning || validationError !== null}
          variant="default"
          aria-label="Price option"
          className="mt-auto"
          data-testid="price-option"
        >
          <Calculator />
          {isRunning ? "Pricing…" : "Price option"}
        </Button>
      </aside>

      {/* --- Results -------------------------------------------------------- */}
      <section className="flex min-h-0 min-w-0 flex-1 flex-col gap-8 overflow-y-auto p-6">
        {error && (
          <p
            className="text-negative bg-negative/10 border-negative/30 text-caption rounded-none border px-3 py-2"
            role="alert"
            data-testid="option-pricing-error"
          >
            {error}
          </p>
        )}

        {!lastResult && !isRunning && (
          <EmptyState
            icon={Calculator}
            headline="No option priced"
            hint="Pick an engine and set the inputs on the left — the fair value (and Greeks, where the engine yields them) lands here."
            cta={{ label: "Price option", onClick: () => void handlePrice(), primary: true }}
          />
        )}

        {!lastResult && isRunning && <ResultSkeleton />}

        {lastResult && (
          <div className="flex flex-col gap-8" data-testid="option-pricing-result">
            {/* Price header — the hero number plus the request it was priced from. */}
            <div className="border-charcoal-700 bg-charcoal-900 flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 rounded-none border p-6">
              <div className="flex flex-col gap-2">
                <span className="text-charcoal-500 text-micro">
                  Fair value · {lastResult.method}
                </span>
                <span className="flex items-baseline gap-3">
                  <span
                    className="text-overview text-charcoal-100 tabular-nums"
                    data-testid="option-price"
                  >
                    {formatOptionPrice(lastResult.price, displayCurrency)}
                  </span>
                  {lastResult.monte_carlo_std_error !== null && (
                    <span
                      className="text-charcoal-400 text-caption tabular-nums"
                      data-testid="option-mc-error"
                    >
                      ± {lastResult.monte_carlo_std_error.toFixed(4)} (1 SE)
                    </span>
                  )}
                </span>
              </div>
              {computedReq && (
                <div
                  className="text-charcoal-400 text-caption flex flex-col items-end gap-1 tabular-nums"
                  data-testid="option-request-echo"
                >
                  <span>
                    {computedReq.exercise.toUpperCase()} {computedReq.payoff.toUpperCase()} · S{" "}
                    {computedReq.spot} · K {computedReq.strike} · σ {computedReq.volatility}
                  </span>
                  <span className="text-charcoal-500">
                    r {computedReq.risk_free_rate} · q {computedReq.dividend_yield} ·{" "}
                    {computedReq.valuation_date} → {computedReq.expiry_date}
                  </span>
                </div>
              )}
            </div>

            {/* Per-greek metric grid — fills the panel width. */}
            {greeks && (
              <div className="grid grid-cols-2 gap-6 md:grid-cols-3 xl:grid-cols-5">
                {GREEK_CARDS.map(({ key, label }) => {
                  const shown = greekForDisplay(greeks, key);
                  return (
                    <MetricCard
                      key={key}
                      label={label}
                      value={shown.value.toFixed(4)}
                      unit={shown.unit}
                      testId={`option-greek-${key}`}
                    />
                  );
                })}
              </div>
            )}

            <div className="text-charcoal-500 text-micro">
              computed in {lastResult.duration_ms.toFixed(1)} ms · {lastResult.method} engine
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
