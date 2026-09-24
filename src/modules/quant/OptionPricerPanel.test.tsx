import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { resetQuantStoreForTests } from "@/store/quant";
import { useSettingsStore } from "@/store/settings";
import { OptionPricerPanel } from "./OptionPricerPanel";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
}));

beforeEach(() => {
  resetQuantStoreForTests();
  // The display currency defaults to the session region's; pin it.
  useSettingsStore.setState({ region: "US" });
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        price: 8.42,
        greeks: { delta: 0.55, gamma: 0.02, vega: 30, theta: -5, rho: 12 },
        method: "black-scholes",
        monte_carlo_std_error: null,
        duration_ms: 1.2,
      }),
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("OptionPricerPanel", () => {
  it("renders the input form and method selector", () => {
    render(<OptionPricerPanel />);
    expect(screen.getByTestId("option-pricer-form")).toBeTruthy();
    expect(screen.getByTestId("method-black-scholes")).toBeTruthy();
    expect(screen.getByTestId("method-binomial")).toBeTruthy();
    expect(screen.getByTestId("method-monte-carlo")).toBeTruthy();
  });

  it("prices an option and renders price + Greeks", async () => {
    render(<OptionPricerPanel />);
    fireEvent.click(screen.getByTestId("price-option"));
    await screen.findByTestId("option-pricing-result");
    expect(screen.getByTestId("option-price").textContent).toContain("$8.42");
  });

  it("R15-UI-028: in region IN, ₹ price and vega/theta in market units", async () => {
    useSettingsStore.setState({ region: "IN" });
    render(<OptionPricerPanel />);
    fireEvent.click(screen.getByTestId("price-option"));
    await screen.findByTestId("option-pricing-result");
    expect(screen.getByTestId("option-price").textContent).toBe("₹8.4200");
    expect(screen.getByTestId("option-pricing-result").textContent).not.toContain("$");
    expect(screen.getByTestId("option-greek-vega").textContent).toContain("0.3000");
    expect(screen.getByTestId("option-greek-vega").textContent).toContain("per 1 vol pt");
    expect(screen.getByTestId("option-greek-theta").textContent).toContain("-0.0137");
    expect(screen.getByTestId("option-greek-theta").textContent).toContain("per day");

    fireEvent.change(screen.getByTestId("field-display-currency"), { target: { value: "USD" } });
    expect(screen.getByTestId("option-price").textContent).toBe("$8.4200");
  });

  it("shows binomial-specific steps field when binomial selected", () => {
    render(<OptionPricerPanel />);
    fireEvent.click(screen.getByTestId("method-binomial"));
    expect(screen.getByTestId("field-binomial-steps")).toBeTruthy();
  });

  it("shows MC-specific paths + seed fields when MC selected", () => {
    render(<OptionPricerPanel />);
    fireEvent.click(screen.getByTestId("method-monte-carlo"));
    expect(screen.getByTestId("field-mc-paths")).toBeTruthy();
    expect(screen.getByTestId("field-mc-seed")).toBeTruthy();
  });

  it("disables Price when American + Black-Scholes selected", () => {
    render(<OptionPricerPanel />);
    const exerciseAmericanBtn = screen.getByText("American");
    fireEvent.click(exerciseAmericanBtn);
    const priceBtn = screen.getByTestId("price-option") as HTMLButtonElement;
    expect(priceBtn.disabled).toBe(true);
    // The incompatibility is honest inline validation, not a silent disable.
    expect(screen.getByTestId("option-validation").textContent).toMatch(/European exercise/);
  });

  it("renders the composed empty state before the first price", () => {
    render(<OptionPricerPanel />);
    expect(screen.getByTestId("empty-state")).toBeTruthy();
    expect(screen.getByTestId("empty-state-headline").textContent).toBe("No option priced");
    expect(screen.getByTestId("empty-state-cta")).toBeTruthy();
  });

  it("surfaces inline validation and blocks the POST on a bad input", () => {
    render(<OptionPricerPanel />);
    fireEvent.change(screen.getByTestId("field-spot"), { target: { value: "-3" } });
    expect(screen.getByTestId("option-validation").textContent).toMatch(/positive/);
    const priceBtn = screen.getByTestId("price-option") as HTMLButtonElement;
    expect(priceBtn.disabled).toBe(true);
    fireEvent.click(priceBtn);
    expect(vi.mocked(fetch)).not.toHaveBeenCalled();
  });

  it("surfaces errors from the store via the error card", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        statusText: "Bad Request",
        json: async () => ({ detail: "invalid spot" }),
      }),
    );
    render(<OptionPricerPanel />);
    fireEvent.click(screen.getByTestId("price-option"));
    await screen.findByTestId("option-pricing-error");
  });
});
