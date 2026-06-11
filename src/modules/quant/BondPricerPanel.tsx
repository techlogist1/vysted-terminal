"use client";

/**
 * Bond Pricer — fixed-rate bond priced at a user-supplied yield-to-maturity.
 *
 * R7 layout (VYSTED_DESIGN.md):
 *
 *   ┌──────────────┬──────────────────────────────────────────────────┐
 *   │ INPUT RAIL   │ CLEAN PRICE  ····  request echo (meta)           │
 *   │  2-col grid  ├──────────────────────────────────────────────────┤
 *   │  of 32px     │ [DIRTY] [ACCRUED]                                │
 *   │  inputs +    │ [MACAULAY DUR] [MODIFIED DUR] [CONVEXITY]        │
 *   │  date trio   │   metric cards — section-size tabular values     │
 *   │  inline      ├──────────────────────────────────────────────────┤
 *   │  validation  │ computed in N ms                                 │
 *   │ [Price bond] │                                                  │
 *   └──────────────┴──────────────────────────────────────────────────┘
 *
 * Every control sits on the 32px ladder at text-body; validation is an honest
 * inline line (positive face, ordered dates, numeric YTM), never a silent NaN
 * POST. The empty state is the shared composed EmptyState whose CTA runs the
 * price with the prefilled US-Treasury-flavoured defaults.
 */

import { useCallback, useMemo, useState } from "react";
import { Landmark } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { useQuantStore } from "@/store/quant";

import type { BondPricingRequest } from "../../../types/quant";

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
        className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 w-full border px-3 tabular-nums outline-none disabled:opacity-50"
      />
    </label>
  );
}

/** One result metric card — micro label over a section-size tabular value. */
function MetricCard({ label, value, testId }: { label: string; value: string; testId?: string }) {
  return (
    <div
      className="border-charcoal-700 bg-charcoal-900 flex flex-col gap-2 rounded-none border p-6"
      data-testid={testId}
    >
      <span className="text-charcoal-500 text-micro">{label}</span>
      <span className="text-charcoal-100 text-section tabular-nums">{value}</span>
    </div>
  );
}

/** Pulse skeleton mirroring the result layout — first price only. */
function ResultSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-8" data-testid="bond-skeleton">
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

export function BondPricerPanel() {
  const lastResult = useQuantStore((s) => s.lastBondPricing);
  const status = useQuantStore((s) => s.bondStatus);
  const error = useQuantStore((s) => s.bondError);
  const priceBond = useQuantStore((s) => s.priceBond);

  const [faceValue, setFaceValue] = useState("1000");
  const [couponRate, setCouponRate] = useState("0.05");
  const [couponsPerYear, setCouponsPerYear] = useState<"1" | "2" | "4">("2");
  const [issueDate, setIssueDate] = useState("2026-05-16");
  const [maturityDate, setMaturityDate] = useState("2036-05-16");
  const [settlementDate, setSettlementDate] = useState("2026-05-16");
  const [ytm, setYtm] = useState("0.0425");

  const isRunning = status === "loading";

  // Honest inline validation — surfaced in the rail, never a silent NaN POST.
  const validationError = useMemo(() => {
    const nums = { "face value": faceValue, "coupon rate": couponRate, "yield-to-maturity": ytm };
    for (const [name, raw] of Object.entries(nums)) {
      if (raw.trim() === "" || Number.isNaN(Number(raw))) {
        return `Enter a numeric ${name}.`;
      }
    }
    if (Number(faceValue) <= 0) {
      return "Face value must be positive.";
    }
    if (Number(couponRate) < 0) {
      return "Coupon rate cannot be negative.";
    }
    if (issueDate === "" || maturityDate === "" || settlementDate === "") {
      return "All three dates are required.";
    }
    if (maturityDate <= issueDate) {
      return "Maturity must be after the issue date.";
    }
    if (settlementDate < issueDate || settlementDate >= maturityDate) {
      return "Settlement must fall between issue and maturity.";
    }
    return null;
  }, [faceValue, couponRate, ytm, issueDate, maturityDate, settlementDate]);

  // The request a displayed result was computed FROM — echoed next to the
  // price so the readout never silently pairs with edited-but-unpriced inputs.
  const [computedReq, setComputedReq] = useState<BondPricingRequest | null>(null);

  const handlePrice = useCallback(async () => {
    if (validationError !== null) {
      return;
    }
    const req: BondPricingRequest = {
      face_value: Number(faceValue),
      coupon_rate: Number(couponRate),
      coupons_per_year: Number(couponsPerYear) as 1 | 2 | 4,
      issue_date: issueDate,
      maturity_date: maturityDate,
      settlement_date: settlementDate,
      yield_to_maturity: Number(ytm),
    };
    try {
      await priceBond(req);
      setComputedReq(req);
    } catch {
      // surfaced via store
    }
  }, [
    validationError,
    faceValue,
    couponRate,
    couponsPerYear,
    issueDate,
    maturityDate,
    settlementDate,
    ytm,
    priceBond,
  ]);

  return (
    <div className="bg-charcoal-900 flex h-full min-h-0 w-full">
      {/* --- Input rail ----------------------------------------------------- */}
      <aside
        className="border-charcoal-700 flex w-72 shrink-0 flex-col gap-6 overflow-y-auto border-r p-6"
        data-testid="bond-pricer-form"
      >
        <div className="grid grid-cols-2 gap-3">
          <Field
            label="Face value"
            value={faceValue}
            onChange={setFaceValue}
            step="100"
            disabled={isRunning}
            testId="field-face"
          />
          <Field
            label="Coupon (ann.)"
            value={couponRate}
            onChange={setCouponRate}
            step="0.001"
            disabled={isRunning}
            testId="field-coupon"
          />
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-charcoal-500 text-micro">Coupons per year</span>
          <select
            value={couponsPerYear}
            onChange={(e) => setCouponsPerYear(e.target.value as "1" | "2" | "4")}
            disabled={isRunning}
            data-testid="field-coupons-per-year"
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 border px-3 outline-none disabled:opacity-50"
          >
            <option value="1">1 — annual</option>
            <option value="2">2 — semi-annual</option>
            <option value="4">4 — quarterly</option>
          </select>
        </label>

        <Field
          label="Issue date"
          value={issueDate}
          onChange={setIssueDate}
          type="date"
          disabled={isRunning}
          testId="field-issue"
        />
        <Field
          label="Maturity date"
          value={maturityDate}
          onChange={setMaturityDate}
          type="date"
          disabled={isRunning}
          testId="field-maturity"
        />
        <Field
          label="Settlement date"
          value={settlementDate}
          onChange={setSettlementDate}
          type="date"
          disabled={isRunning}
          testId="field-settle"
        />
        <Field
          label="Yield-to-maturity"
          value={ytm}
          onChange={setYtm}
          step="0.001"
          disabled={isRunning}
          testId="field-ytm"
        />

        {validationError !== null && (
          <p className="text-negative text-caption" role="alert" data-testid="bond-validation">
            {validationError}
          </p>
        )}

        <Button
          type="button"
          onClick={handlePrice}
          disabled={isRunning || validationError !== null}
          variant="default"
          className="mt-auto"
          data-testid="price-bond"
        >
          <Landmark />
          {isRunning ? "Pricing…" : "Price bond"}
        </Button>
      </aside>

      {/* --- Results -------------------------------------------------------- */}
      <section className="flex min-h-0 min-w-0 flex-1 flex-col gap-8 overflow-y-auto p-6">
        {error && (
          <p
            className="text-negative bg-negative/10 border-negative/30 text-caption rounded-none border px-3 py-2"
            role="alert"
            data-testid="bond-pricing-error"
          >
            {error}
          </p>
        )}

        {!lastResult && !isRunning && (
          <EmptyState
            icon={Landmark}
            headline="No bond priced"
            hint="Set the coupon, dates, and yield-to-maturity on the left — clean/dirty prices, accrued interest, duration, and convexity land here."
            cta={{ label: "Price bond", onClick: () => void handlePrice(), primary: true }}
          />
        )}

        {!lastResult && isRunning && <ResultSkeleton />}

        {lastResult && (
          <div className="flex flex-col gap-8" data-testid="bond-pricing-result">
            {/* Price header — the hero number plus the request it was priced from. */}
            <div className="border-charcoal-700 bg-charcoal-900 flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 rounded-none border p-6">
              <div className="flex flex-col gap-2">
                <span className="text-charcoal-500 text-micro">Clean price</span>
                <span
                  className="text-overview text-charcoal-100 tabular-nums"
                  data-testid="bond-clean"
                >
                  ${lastResult.clean_price.toFixed(2)}
                </span>
              </div>
              {computedReq && (
                <div
                  className="text-charcoal-400 text-caption flex flex-col items-end gap-1 tabular-nums"
                  data-testid="bond-request-echo"
                >
                  <span>
                    Face {computedReq.face_value} · coupon {computedReq.coupon_rate} ·{" "}
                    {computedReq.coupons_per_year}×/yr · YTM {computedReq.yield_to_maturity}
                  </span>
                  <span className="text-charcoal-500">
                    {computedReq.issue_date} → {computedReq.maturity_date} · settles{" "}
                    {computedReq.settlement_date}
                  </span>
                </div>
              )}
            </div>

            {/* Price + risk metric grid — fills the panel width. */}
            <div className="grid grid-cols-2 gap-6 md:grid-cols-3 xl:grid-cols-5">
              <MetricCard label="Dirty price" value={`$${lastResult.dirty_price.toFixed(2)}`} />
              <MetricCard
                label="Accrued interest"
                value={`$${lastResult.accrued_interest.toFixed(2)}`}
              />
              <MetricCard
                label="Macaulay duration"
                value={lastResult.duration.toFixed(4)}
                testId="bond-duration"
              />
              <MetricCard
                label="Modified duration"
                value={lastResult.modified_duration.toFixed(4)}
              />
              <MetricCard label="Convexity" value={lastResult.convexity.toFixed(4)} />
            </div>

            <div className="text-charcoal-500 text-micro">
              computed in {lastResult.duration_ms.toFixed(1)} ms
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
