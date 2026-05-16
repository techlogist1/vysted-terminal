"use client";

import type { EarningsEstimateDetail } from "../../../types/earnings";

function fmt(value: number | null, digits = 2): string {
  if (value === null) {
    return "—";
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtLargeMoney(value: number | null): string {
  if (value === null) {
    return "—";
  }
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  return value.toLocaleString("en-US");
}

interface Props {
  estimate: EarningsEstimateDetail | null;
}

/**
 * Six-cell mean / median / high / low / stddev / analyst-count grid for
 * the next upcoming earnings event. Renders an em-dash placeholder when
 * the upstream did not surface a value.
 */
export function EpsEstimateGrid({ estimate }: Props) {
  if (!estimate) {
    return (
      <p className="text-charcoal-400 font-mono text-xs" data-testid="eps-estimate-grid-empty">
        Estimate detail unavailable.
      </p>
    );
  }
  return (
    <div
      className="grid grid-cols-3 gap-x-6 gap-y-2 font-mono text-xs"
      data-testid="eps-estimate-grid"
    >
      <Cell label="EPS mean" value={fmt(estimate.eps_estimate_mean)} />
      <Cell label="EPS median" value={fmt(estimate.eps_estimate_median)} />
      <Cell label="EPS high" value={fmt(estimate.eps_estimate_high)} />
      <Cell label="EPS low" value={fmt(estimate.eps_estimate_low)} />
      <Cell label="EPS stddev" value={fmt(estimate.eps_estimate_stddev, 3)} />
      <Cell label="# analysts" value={String(estimate.estimate_analyst_count)} />
      <Cell label="Rev mean" value={fmtLargeMoney(estimate.revenue_estimate_mean)} />
      <Cell label="Rev high" value={fmtLargeMoney(estimate.revenue_estimate_high)} />
      <Cell label="Rev low" value={fmtLargeMoney(estimate.revenue_estimate_low)} />
    </div>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-charcoal-400">{label}</dt>
      <dd className="text-charcoal-100">{value}</dd>
    </div>
  );
}
