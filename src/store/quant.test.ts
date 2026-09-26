/**
 * Quant store tests — round-trips through the mocked sidecar verb.
 *
 * The store POSTs through the shared ``sidecarRequest`` (R15-CODE-FRONTEND-027),
 * mocked at the module boundary; ``SidecarError`` stays real. Each test
 * verifies one of the four pricing slices end-to-end: loading → ready (or →
 * error).
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { SidecarError, sidecarRequest } from "@/lib/sidecar-client";

import { resetQuantStoreForTests, useQuantStore } from "./quant";

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return { ...actual, sidecarRequest: vi.fn() };
});

const baseOptionRequest = {
  exercise: "european" as const,
  payoff: "call" as const,
  spot: 100,
  strike: 100,
  risk_free_rate: 0.05,
  dividend_yield: 0.02,
  volatility: 0.2,
  valuation_date: "2026-05-16",
  expiry_date: "2027-05-16",
  method: "black-scholes" as const,
};

beforeEach(() => {
  resetQuantStoreForTests();
  vi.mocked(sidecarRequest).mockReset();
});

function mockResult(body: object): void {
  vi.mocked(sidecarRequest).mockResolvedValue(body);
}

describe("useQuantStore.priceOption", () => {
  it("loads → ready and stores the result", async () => {
    mockResult({
      price: 5.5,
      greeks: { delta: 0.6, gamma: 0.02, vega: 30, theta: -5, rho: 12 },
      method: "black-scholes",
      monte_carlo_std_error: null,
      duration_ms: 12.3,
    });
    const result = await useQuantStore.getState().priceOption(baseOptionRequest);
    expect(result.price).toBe(5.5);
    expect(useQuantStore.getState().optionStatus).toBe("ready");
    expect(useQuantStore.getState().lastOptionPricing?.price).toBe(5.5);
    expect(useQuantStore.getState().optionError).toBeNull();
  });

  it("POSTs the request through the shared verb", async () => {
    mockResult({ price: 5.5, greeks: {}, method: "black-scholes", duration_ms: 1 });
    await useQuantStore.getState().priceOption(baseOptionRequest);
    expect(sidecarRequest).toHaveBeenCalledWith("POST", "/quant/option/price", {
      body: baseOptionRequest,
    });
  });

  it("captures errors via store.error", async () => {
    // sidecarRequest turns the 400 into SidecarError(400, <detail>): the
    // store shows the server's sentence (it used to prefix "POST <path>
    // failed (400):" — one error policy now, the status rides `.status`).
    vi.mocked(sidecarRequest).mockRejectedValue(new SidecarError(400, "bad request"));
    await expect(useQuantStore.getState().priceOption(baseOptionRequest)).rejects.toThrow();
    expect(useQuantStore.getState().optionStatus).toBe("error");
    expect(useQuantStore.getState().optionError).toBe("bad request");
  });
});

describe("useQuantStore.computeGreeks", () => {
  it("stores the greeks slice", async () => {
    mockResult({
      greeks: { delta: 0.6, gamma: 0.02, vega: 30, theta: -5, rho: 12 },
      price: 5.5,
      duration_ms: 1.0,
    });
    await useQuantStore.getState().computeGreeks({
      payoff: "call",
      spot: 100,
      strike: 100,
      risk_free_rate: 0.05,
      dividend_yield: 0.02,
      volatility: 0.2,
      valuation_date: "2026-05-16",
      expiry_date: "2027-05-16",
    });
    expect(useQuantStore.getState().greeksStatus).toBe("ready");
    expect(useQuantStore.getState().lastGreeks?.price).toBe(5.5);
  });
});

describe("useQuantStore.priceBond", () => {
  it("stores the bond slice", async () => {
    mockResult({
      clean_price: 1000,
      dirty_price: 1000,
      accrued_interest: 0,
      duration: 8.0,
      modified_duration: 7.8,
      convexity: 70,
      duration_ms: 0.5,
    });
    await useQuantStore.getState().priceBond({
      face_value: 1000,
      coupon_rate: 0.05,
      coupons_per_year: 2,
      issue_date: "2026-05-16",
      maturity_date: "2036-05-16",
      settlement_date: "2026-05-16",
      yield_to_maturity: 0.05,
    });
    expect(useQuantStore.getState().bondStatus).toBe("ready");
    expect(useQuantStore.getState().lastBondPricing?.duration).toBe(8.0);
  });
});

describe("useQuantStore.bootstrapYieldCurve", () => {
  it("stores the curve slice", async () => {
    mockResult({
      valuation_date: "2026-05-16",
      curve: [
        { date: "2026-06-16", tenor_years: 0.083, zero_rate: 0.041, discount_factor: 0.997 },
        { date: "2031-05-16", tenor_years: 5.0, zero_rate: 0.047, discount_factor: 0.79 },
      ],
      duration_ms: 1.0,
    });
    await useQuantStore.getState().bootstrapYieldCurve({
      valuation_date: "2026-05-16",
      instruments: [
        { type: "deposit", tenor: 1, tenor_unit: "months", rate: 0.041 },
        { type: "swap", tenor: 5, tenor_unit: "years", rate: 0.047 },
      ],
      sample_count: 2,
    });
    expect(useQuantStore.getState().yieldCurveStatus).toBe("ready");
    expect(useQuantStore.getState().lastYieldCurve?.curve.length).toBe(2);
  });
});

describe("resetQuantStoreForTests", () => {
  it("resets every slice to idle", async () => {
    mockResult({
      price: 5.5,
      greeks: { delta: 0.6, gamma: 0.02, vega: 30, theta: -5, rho: 12 },
      method: "black-scholes",
      monte_carlo_std_error: null,
      duration_ms: 12.3,
    });
    await useQuantStore.getState().priceOption(baseOptionRequest);
    expect(useQuantStore.getState().lastOptionPricing).not.toBeNull();
    resetQuantStoreForTests();
    expect(useQuantStore.getState().lastOptionPricing).toBeNull();
    expect(useQuantStore.getState().optionStatus).toBe("idle");
  });
});
