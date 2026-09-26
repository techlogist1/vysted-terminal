/**
 * EpsEstimateGrid tests — R15-DATA-113.
 *
 * `revenue_currency` distinguishes `undefined` (a pre-fix cached envelope —
 * fall back to `currency`) from `null` (the provider could not determine the
 * currency at all — render the revenue figure with no currency code).
 */

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { currencyAffix, formatPrice, formatUnit } from "@/lib/format";

import type { EarningsEstimateDetail } from "../../../types/earnings";
import { EpsEstimateGrid } from "./EpsEstimateGrid";

const BASE_ESTIMATE: EarningsEstimateDetail = {
  symbol: "WIT",
  fiscal_period: { quarter: "Q2", year: 2026 },
  eps_estimate_mean: 1.5,
  eps_estimate_median: null,
  eps_estimate_high: 1.6,
  eps_estimate_low: 1.4,
  eps_estimate_stddev: null,
  estimate_analyst_count: 20,
  revenue_estimate_mean: 100_000_000,
  revenue_estimate_median: null,
  revenue_estimate_high: null,
  revenue_estimate_low: null,
  revenue_analyst_count: 0,
  currency: "USD",
  provider: "yfinance",
  as_of: "2026-05-16T00:00:00Z",
};

afterEach(() => {
  cleanup();
});

describe("EpsEstimateGrid", () => {
  it("renders the empty state when no estimate is given", () => {
    render(<EpsEstimateGrid estimate={null} />);
    expect(screen.getByTestId("eps-estimate-grid-empty")).toBeTruthy();
  });

  it("null revenue_currency renders the revenue figure with no currency code", () => {
    render(<EpsEstimateGrid estimate={{ ...BASE_ESTIMATE, revenue_currency: null }} />);
    // The bare unit string, byte-identical to formatUnit's own output — no
    // currency prefix/suffix attached.
    expect(screen.getByText(formatUnit(100_000_000))).toBeTruthy();
  });

  it("undefined revenue_currency (a pre-fix cached envelope) falls back to currency", () => {
    const { revenue_currency: _omit, ...withoutField } = BASE_ESTIMATE;
    render(<EpsEstimateGrid estimate={{ ...withoutField, currency: "EUR" }} />);
    const { prefix, suffix } = currencyAffix("EUR");
    expect(screen.getByText(`${prefix}${formatUnit(100_000_000)}${suffix}`)).toBeTruthy();
  });

  it("a determined revenue_currency renders with its own currency, distinct from EPS currency", () => {
    render(
      <EpsEstimateGrid estimate={{ ...BASE_ESTIMATE, currency: "USD", revenue_currency: "INR" }} />,
    );
    const { prefix, suffix } = currencyAffix("INR");
    expect(screen.getByText(`${prefix}${formatUnit(100_000_000)}${suffix}`)).toBeTruthy();
    // The EPS mean stays in the trading currency (USD), never revenue_currency.
    const { prefix: epsPrefix, suffix: epsSuffix } = currencyAffix("USD");
    expect(screen.getByText(`${epsPrefix}${formatPrice(1.5)}${epsSuffix}`)).toBeTruthy();
  });
});
