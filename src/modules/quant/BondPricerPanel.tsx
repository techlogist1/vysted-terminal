"use client";

/**
 * Bond Pricer Panel — Teammate Q Phase 6.
 *
 * Fixed-rate bond pricing at a user-supplied yield-to-maturity.
 * Inputs: face / coupon / coupons-per-year / issue / maturity / settle
 * / YTM. Outputs: clean / dirty / accrued / duration (Macaulay,
 * modified) / convexity.
 */

import { useCallback, useState } from "react";
import { Calculator } from "lucide-react";

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

  const handlePrice = useCallback(async () => {
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
    } catch {
      // surfaced via store
    }
  }, [
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
      <aside
        className="border-charcoal-700 flex w-80 flex-col gap-3 overflow-y-auto border-r p-3"
        data-testid="bond-pricer-form"
      >
        <div className="grid grid-cols-2 gap-2">
          <Field
            label="Face value"
            value={faceValue}
            onChange={setFaceValue}
            step="100"
            disabled={isRunning}
            testId="field-face"
          />
          <Field
            label="Coupon (annual)"
            value={couponRate}
            onChange={setCouponRate}
            step="0.001"
            disabled={isRunning}
            testId="field-coupon"
          />
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-charcoal-300 font-mono text-[10px]">Coupons per year</span>
          <select
            value={couponsPerYear}
            onChange={(e) => setCouponsPerYear(e.target.value as "1" | "2" | "4")}
            disabled={isRunning}
            data-testid="field-coupons-per-year"
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs outline-none focus-visible:border-amber-500 disabled:opacity-50"
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

        <Button
          type="button"
          onClick={handlePrice}
          disabled={isRunning}
          size="sm"
          variant="default"
          className="mt-auto"
          data-testid="price-bond"
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
            data-testid="bond-pricing-error"
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
          <div className="grid gap-3" data-testid="bond-pricing-result">
            <div className="border-charcoal-700 bg-charcoal-850 rounded-control border p-4">
              <div className="text-charcoal-500 mb-2 font-mono text-[10px] tracking-widest uppercase">
                Prices
              </div>
              <div className="grid grid-cols-3 gap-2">
                <BondCell
                  label="Clean"
                  value={`$${lastResult.clean_price.toFixed(2)}`}
                  testId="bond-clean"
                />
                <BondCell label="Dirty" value={`$${lastResult.dirty_price.toFixed(2)}`} />
                <BondCell label="Accrued" value={`$${lastResult.accrued_interest.toFixed(2)}`} />
              </div>
            </div>
            <div className="border-charcoal-700 bg-charcoal-850 rounded-control border p-4">
              <div className="text-charcoal-500 mb-2 font-mono text-[10px] tracking-widest uppercase">
                Risk metrics
              </div>
              <div className="grid grid-cols-3 gap-2">
                <BondCell
                  label="Macaulay Dur"
                  value={lastResult.duration.toFixed(4)}
                  testId="bond-duration"
                />
                <BondCell label="Modified Dur" value={lastResult.modified_duration.toFixed(4)} />
                <BondCell label="Convexity" value={lastResult.convexity.toFixed(4)} />
              </div>
            </div>
            <div className="text-charcoal-500 font-mono text-[10px]">
              computed in {lastResult.duration_ms.toFixed(1)} ms
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function BondCell({ label, value, testId }: { label: string; value: string; testId?: string }) {
  return (
    <div
      className="border-charcoal-700 bg-charcoal-900 rounded-control flex flex-col gap-1 border p-2"
      data-testid={testId}
    >
      <span className="text-charcoal-400 font-mono text-[10px]">{label}</span>
      <span className="text-charcoal-100 font-mono text-sm">{value}</span>
    </div>
  );
}
