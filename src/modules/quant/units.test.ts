import { describe, expect, it } from "vitest";

import { formatOptionPrice, greekForDisplay, toMarketUnits } from "./units";

describe("toMarketUnits (R15-UI-028, R15-UI-051)", () => {
  it("reads vega per 1 vol point and theta per calendar day", () => {
    const { vega, theta } = toMarketUnits({ vega: 30, theta: -5, rho: 12 });
    expect(vega).toEqual({ value: 0.3, unit: "per 1 vol pt" });
    expect(theta.value).toBeCloseTo(-5 / 365, 12);
    expect(theta.unit).toBe("per day");
  });

  it("reads rho per 1% rate move (R15-UI-028 residual: rho was still unlabelled)", () => {
    const { rho } = toMarketUnits({ vega: 30, theta: -5, rho: 13.5565 });
    expect(rho.value).toBeCloseTo(0.1356, 4);
    expect(rho.unit).toBe("per 1%");
  });

  it("leaves delta and gamma as served", () => {
    const greeks = { delta: 0.55, gamma: 0.02, vega: 30, theta: -5, rho: 12 };
    expect(greekForDisplay(greeks, "delta")).toEqual({ value: 0.55, unit: null });
    expect(greekForDisplay(greeks, "gamma")).toEqual({ value: 0.02, unit: null });
    expect(greekForDisplay(greeks, "vega").value).toBeCloseTo(0.3, 12);
  });

  it("converts rho through greekForDisplay the same as vega/theta", () => {
    const greeks = { delta: 0.55, gamma: 0.02, vega: 30, theta: -5, rho: 13.5565 };
    const shown = greekForDisplay(greeks, "rho");
    expect(shown.value).toBeCloseTo(0.1356, 4);
    expect(shown.unit).toBe("per 1%");
  });

  it("formats a price at 4 dp with the display currency's symbol", () => {
    expect(formatOptionPrice(8.42, "USD")).toBe("$8.4200");
    expect(formatOptionPrice(8.42, "INR")).toBe("₹8.4200");
  });
});
