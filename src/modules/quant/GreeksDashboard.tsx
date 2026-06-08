"use client";

/**
 * Greeks Dashboard — Teammate Q Phase 6.
 *
 * Standalone analytic-Greeks surface — same Black-Scholes inputs as the
 * option pricer panel but without the engine selector, so the user can
 * sweep inputs without picking "black-scholes" each time. Hits
 * ``POST /quant/option/greeks`` which always uses the analytic engine
 * (delta/gamma/vega/theta/rho are closed-form for a European vanilla).
 */

import { useCallback, useState } from "react";
import { Gauge } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useQuantStore } from "@/store/quant";

import type { GreeksRequest, OptionPayoff } from "../../../types/quant";

interface FieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  step?: string;
  disabled?: boolean;
  testId?: string;
}

function Field({ label, value, onChange, type = "number", step, disabled, testId }: FieldProps) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-charcoal-300 text-micro font-mono">{label}</span>
      <input
        type={type}
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        data-testid={testId}
        className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-caption focus-visible:border-charcoal-500 h-8 border px-2 font-mono outline-none disabled:opacity-50"
      />
    </label>
  );
}

export function GreeksDashboard() {
  const lastResult = useQuantStore((s) => s.lastGreeks);
  const status = useQuantStore((s) => s.greeksStatus);
  const error = useQuantStore((s) => s.greeksError);
  const computeGreeks = useQuantStore((s) => s.computeGreeks);

  const [payoff, setPayoff] = useState<OptionPayoff>("call");
  const [spot, setSpot] = useState("220");
  const [strike, setStrike] = useState("220");
  const [r, setR] = useState("0.05");
  const [q, setQ] = useState("0.005");
  const [vol, setVol] = useState("0.28");
  const [valuationDate, setValuationDate] = useState("2026-05-16");
  const [expiryDate, setExpiryDate] = useState("2026-06-30");

  const isRunning = status === "loading";

  const handleCompute = useCallback(async () => {
    const req: GreeksRequest = {
      payoff,
      spot: Number(spot),
      strike: Number(strike),
      risk_free_rate: Number(r),
      dividend_yield: Number(q),
      volatility: Number(vol),
      valuation_date: valuationDate,
      expiry_date: expiryDate,
    };
    try {
      await computeGreeks(req);
    } catch {
      // surfaced via store
    }
  }, [payoff, spot, strike, r, q, vol, valuationDate, expiryDate, computeGreeks]);

  return (
    <div className="bg-charcoal-900 flex h-full min-h-0 w-full">
      <aside
        className="border-charcoal-700 flex w-72 flex-col gap-3 overflow-y-auto border-r p-3"
        data-testid="greeks-form"
      >
        <div className="flex flex-col gap-1.5">
          <span className="text-charcoal-500 text-micro font-mono tracking-widest uppercase">
            Payoff
          </span>
          <div role="radiogroup" aria-label="Payoff" className="grid grid-cols-2 gap-1">
            {(["call", "put"] as const).map((p) => (
              <button
                type="button"
                key={p}
                role="radio"
                aria-checked={payoff === p}
                onClick={() => setPayoff(p)}
                disabled={isRunning}
                className={
                  payoff === p
                    ? "rounded-control text-micro border-charcoal-600 bg-charcoal-875 text-charcoal-100 h-8 border font-mono"
                    : "rounded-control border-charcoal-700 bg-charcoal-850 text-charcoal-300 hover:bg-charcoal-800 text-micro h-8 border font-mono"
                }
                data-testid={`greeks-payoff-${p}`}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Field
            label="Spot"
            value={spot}
            onChange={setSpot}
            step="0.01"
            disabled={isRunning}
            testId="greeks-spot"
          />
          <Field
            label="Strike"
            value={strike}
            onChange={setStrike}
            step="0.01"
            disabled={isRunning}
            testId="greeks-strike"
          />
          <Field label="Risk-free r" value={r} onChange={setR} step="0.001" disabled={isRunning} />
          <Field label="Div. yield q" value={q} onChange={setQ} step="0.001" disabled={isRunning} />
          <Field
            label="Volatility σ"
            value={vol}
            onChange={setVol}
            step="0.01"
            disabled={isRunning}
            testId="greeks-vol"
          />
          <Field
            label="Valuation"
            value={valuationDate}
            onChange={setValuationDate}
            type="date"
            disabled={isRunning}
          />
        </div>
        <Field
          label="Expiry"
          value={expiryDate}
          onChange={setExpiryDate}
          type="date"
          disabled={isRunning}
        />

        <Button
          type="button"
          onClick={handleCompute}
          disabled={isRunning}
          size="sm"
          variant="default"
          className="mt-auto"
          data-testid="compute-greeks"
        >
          <Gauge />
          {isRunning ? "Computing…" : "Compute Greeks"}
        </Button>
      </aside>

      <section className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
        {error && (
          <p
            className="text-negative bg-negative/10 border-negative/30 text-caption mb-3 rounded-none border p-2 font-mono"
            role="alert"
            data-testid="greeks-error"
          >
            {error}
          </p>
        )}

        {!lastResult && !isRunning && (
          <div className="text-charcoal-500 text-caption flex h-full items-center justify-center font-mono">
            Fill in the BSM inputs and click Compute Greeks.
          </div>
        )}

        {lastResult && (
          <div className="grid gap-4" data-testid="greeks-result">
            <div className="border-charcoal-700 bg-charcoal-850 rounded-none border p-4">
              <div className="text-charcoal-500 text-micro mb-2 font-mono tracking-widest uppercase">
                Black-Scholes price
              </div>
              <span
                className="text-overview text-charcoal-300 font-mono"
                data-testid="greeks-price"
              >
                ${lastResult.price.toFixed(4)}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">
              <BigGreek label="Δ Delta" value={lastResult.greeks.delta} testId="greek-delta" />
              <BigGreek label="Γ Gamma" value={lastResult.greeks.gamma} testId="greek-gamma" />
              <BigGreek label="ν Vega" value={lastResult.greeks.vega} testId="greek-vega" />
              <BigGreek label="Θ Theta" value={lastResult.greeks.theta} testId="greek-theta" />
              <BigGreek label="ρ Rho" value={lastResult.greeks.rho} testId="greek-rho" />
            </div>
            <div className="text-charcoal-500 text-micro font-mono">
              computed in {lastResult.duration_ms.toFixed(1)} ms · analytic engine
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function BigGreek({ label, value, testId }: { label: string; value: number; testId: string }) {
  return (
    <div
      className="border-charcoal-700 bg-charcoal-850 flex flex-col gap-1 rounded-none border p-3"
      data-testid={testId}
    >
      <span className="text-charcoal-400 text-micro font-mono">{label}</span>
      <span className="text-charcoal-100 text-body font-mono">{value.toFixed(4)}</span>
    </div>
  );
}
