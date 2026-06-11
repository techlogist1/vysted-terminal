"use client";

/**
 * Greeks Dashboard — analytic Black-Scholes Greeks surface.
 *
 * R7 layout (VYSTED_DESIGN.md):
 *
 *   ┌──────────────┬──────────────────────────────────────────────────┐
 *   │ INPUT RAIL   │ BLACK-SCHOLES PRICE  ····  request echo (meta)   │
 *   │  payoff      ├──────────────────────────────────────────────────┤
 *   │  segmented   │ [Δ DELTA] [Γ GAMMA] [ν VEGA] [Θ THETA] [ρ RHO]   │
 *   │  2-col grid  │   metric cards — section-size tabular values     │
 *   │  of 32px     ├──────────────────────────────────────────────────┤
 *   │  inputs      │ SENSITIVITY READ — full-width DataTable          │
 *   │  inline      │   greek · value · what the partial measures      │
 *   │  validation  ├──────────────────────────────────────────────────┤
 *   │ [Compute]    │ computed in N ms · analytic engine               │
 *   └──────────────┴──────────────────────────────────────────────────┘
 *
 * The results column fills the panel width (metric grid + sensitivity table),
 * never a small table stranded in dead space. Empty state is the composed
 * shared EmptyState whose CTA runs the compute with the prefilled inputs.
 * Hits ``POST /quant/option/greeks`` (always the analytic engine — the five
 * Greeks are closed-form for a European vanilla).
 */

import { useCallback, useMemo, useState } from "react";
import { Gauge } from "lucide-react";

import { DataTable, type DataColumn } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useQuantStore } from "@/store/quant";

import type { GreeksRequest, GreeksResult, OptionPayoff } from "../../../types/quant";

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

/** The static, honest sensitivity read per greek — the partial each value IS,
 *  never a fabricated per-unit P&L scaling. */
const GREEK_ROWS: {
  key: keyof GreeksResult["greeks"];
  glyph: string;
  name: string;
  read: string;
}[] = [
  { key: "delta", glyph: "Δ", name: "Delta", read: "∂V/∂S — sensitivity to the underlying spot" },
  { key: "gamma", glyph: "Γ", name: "Gamma", read: "∂²V/∂S² — convexity of delta in spot" },
  { key: "vega", glyph: "ν", name: "Vega", read: "∂V/∂σ — sensitivity to implied volatility" },
  { key: "theta", glyph: "Θ", name: "Theta", read: "∂V/∂t — sensitivity to time decay" },
  { key: "rho", glyph: "ρ", name: "Rho", read: "∂V/∂r — sensitivity to the risk-free rate" },
];

interface SensitivityRow {
  glyph: string;
  name: string;
  value: number;
  read: string;
}

const SENSITIVITY_COLUMNS: DataColumn<SensitivityRow>[] = [
  {
    key: "name",
    header: "Greek",
    width: "18%",
    format: (r) => `${r.glyph} ${r.name}`,
  },
  {
    key: "value",
    header: "Value",
    numeric: true,
    width: "22%",
    format: (r) => r.value.toFixed(4),
  },
  {
    key: "read",
    header: "Sensitivity",
    tier: "secondary",
    truncate: true,
    width: "60%",
    format: (r) => r.read,
    title: (r) => r.read,
  },
];

/** One per-greek metric card — micro label over a section-size tabular value. */
function GreekCard({
  glyph,
  name,
  value,
  testId,
}: {
  glyph: string;
  name: string;
  value: number;
  testId: string;
}) {
  return (
    <div
      className="border-charcoal-700 bg-charcoal-900 flex flex-col gap-2 rounded-none border p-6"
      data-testid={testId}
    >
      <span className="text-charcoal-500 text-micro">
        {glyph} {name}
      </span>
      <span className="text-charcoal-100 text-section tabular-nums">{value.toFixed(4)}</span>
    </div>
  );
}

/** Pulse skeleton mirroring the result layout — shown only for the first
 *  compute (a re-compute keeps the previous result on screen). */
function ResultSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-8" data-testid="greeks-skeleton">
      <div className="border-charcoal-700 rounded-none border p-6">
        <div className="bg-charcoal-800 h-3 w-32 rounded-none" />
        <div className="bg-charcoal-800 mt-3 h-6 w-24 rounded-none" />
      </div>
      <div className="grid grid-cols-2 gap-6 md:grid-cols-3 xl:grid-cols-5">
        {GREEK_ROWS.map((g) => (
          <div key={g.key} className="border-charcoal-700 rounded-none border p-6">
            <div className="bg-charcoal-800 h-3 w-16 rounded-none" />
            <div className="bg-charcoal-800 mt-3 h-5 w-20 rounded-none" />
          </div>
        ))}
      </div>
    </div>
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

  // The request a displayed result was computed FROM — echoed next to the price
  // so the readout never silently pairs with edited-but-uncomputed inputs.
  const [computedReq, setComputedReq] = useState<GreeksRequest | null>(null);

  const isRunning = status === "loading";

  // Honest inline validation — surfaced in the rail, never a silent NaN POST.
  const validationError = useMemo(() => {
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
    return null;
  }, [spot, strike, r, q, vol, valuationDate, expiryDate]);

  const handleCompute = useCallback(async () => {
    if (validationError !== null) {
      return;
    }
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
      setComputedReq(req);
    } catch {
      // surfaced via store
    }
  }, [validationError, payoff, spot, strike, r, q, vol, valuationDate, expiryDate, computeGreeks]);

  const sensitivityRows: SensitivityRow[] = lastResult
    ? GREEK_ROWS.map((g) => ({
        glyph: g.glyph,
        name: g.name,
        value: lastResult.greeks[g.key],
        read: g.read,
      }))
    : [];

  return (
    <div className="bg-charcoal-900 flex h-full min-h-0 w-full">
      {/* --- Input rail ----------------------------------------------------- */}
      <aside
        className="border-charcoal-700 flex w-72 shrink-0 flex-col gap-6 overflow-y-auto border-r p-6"
        data-testid="greeks-form"
      >
        <div className="flex flex-col gap-1">
          <span className="text-charcoal-500 text-micro">Payoff</span>
          <div
            role="radiogroup"
            aria-label="Payoff"
            className="border-charcoal-700 divide-charcoal-700 rounded-control flex h-8 divide-x overflow-hidden border"
          >
            {(["call", "put"] as const).map((p) => (
              <button
                type="button"
                key={p}
                role="radio"
                aria-checked={payoff === p}
                onClick={() => setPayoff(p)}
                disabled={isRunning}
                className={cn(
                  "text-micro flex-1",
                  payoff === p
                    ? "bg-charcoal-875 text-lume"
                    : "text-charcoal-400 hover:text-charcoal-200 bg-transparent",
                )}
                data-testid={`greeks-payoff-${p}`}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
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
        </div>
        <Field
          label="Volatility σ"
          value={vol}
          onChange={setVol}
          step="0.01"
          disabled={isRunning}
          testId="greeks-vol"
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

        {validationError !== null && (
          <p className="text-negative text-caption" role="alert" data-testid="greeks-validation">
            {validationError}
          </p>
        )}

        <Button
          type="button"
          onClick={handleCompute}
          disabled={isRunning || validationError !== null}
          variant="default"
          className="mt-auto"
          data-testid="compute-greeks"
        >
          <Gauge />
          {isRunning ? "Computing…" : "Compute Greeks"}
        </Button>
      </aside>

      {/* --- Results -------------------------------------------------------- */}
      <section className="flex min-h-0 min-w-0 flex-1 flex-col gap-8 overflow-y-auto p-6">
        {error && (
          <p
            className="text-negative bg-negative/10 border-negative/30 text-caption rounded-none border px-3 py-2"
            role="alert"
            data-testid="greeks-error"
          >
            {error}
          </p>
        )}

        {!lastResult && !isRunning && (
          <EmptyState
            icon={Gauge}
            headline="No Greeks computed"
            hint="Set the Black-Scholes inputs on the left and compute — the price, all five Greeks, and a sensitivity read land here."
            cta={{ label: "Compute Greeks", onClick: () => void handleCompute(), primary: true }}
          />
        )}

        {!lastResult && isRunning && <ResultSkeleton />}

        {lastResult && (
          <div className="flex flex-col gap-8" data-testid="greeks-result">
            {/* Price header — the hero number plus the request it was computed from. */}
            <div className="border-charcoal-700 bg-charcoal-900 flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 rounded-none border p-6">
              <div className="flex flex-col gap-2">
                <span className="text-charcoal-500 text-micro">Black-Scholes price</span>
                <span
                  className="text-overview text-charcoal-100 tabular-nums"
                  data-testid="greeks-price"
                >
                  ${lastResult.price.toFixed(4)}
                </span>
              </div>
              {computedReq && (
                <div
                  className="text-charcoal-400 text-caption flex flex-col items-end gap-1 tabular-nums"
                  data-testid="greeks-request-echo"
                >
                  <span>
                    {computedReq.payoff.toUpperCase()} · S {computedReq.spot} · K{" "}
                    {computedReq.strike} · σ {computedReq.volatility}
                  </span>
                  <span className="text-charcoal-500">
                    r {computedReq.risk_free_rate} · q {computedReq.dividend_yield} ·{" "}
                    {computedReq.valuation_date} → {computedReq.expiry_date}
                  </span>
                </div>
              )}
            </div>

            {/* Per-greek metric grid — fills the panel width. */}
            <div className="grid grid-cols-2 gap-6 md:grid-cols-3 xl:grid-cols-5">
              {GREEK_ROWS.map((g) => (
                <GreekCard
                  key={g.key}
                  glyph={g.glyph}
                  name={g.name}
                  value={lastResult.greeks[g.key]}
                  testId={`greek-${g.key}`}
                />
              ))}
            </div>

            {/* Sensitivity read — the full-width table pairing each value with
                the partial derivative it measures. */}
            <div className="border-charcoal-700 rounded-none border">
              <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
                Sensitivity read
              </h3>
              <DataTable
                columns={SENSITIVITY_COLUMNS}
                rows={sensitivityRows}
                rowKey={(row) => row.name}
                data-testid="greeks-sensitivity"
              />
            </div>

            <div className="text-charcoal-500 text-micro">
              computed in {lastResult.duration_ms.toFixed(1)} ms · analytic engine
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
