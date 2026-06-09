import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { resetQuantStoreForTests } from "@/store/quant";
import { GreeksDashboard } from "./GreeksDashboard";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
}));

beforeEach(() => {
  resetQuantStoreForTests();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        greeks: { delta: 0.55, gamma: 0.02, vega: 30, theta: -5, rho: 12 },
        price: 8.42,
        duration_ms: 1.2,
      }),
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("GreeksDashboard", () => {
  it("renders payoff selector + BSM inputs", () => {
    render(<GreeksDashboard />);
    expect(screen.getByTestId("greeks-form")).toBeTruthy();
    expect(screen.getByTestId("greeks-payoff-call")).toBeTruthy();
    expect(screen.getByTestId("greeks-payoff-put")).toBeTruthy();
    expect(screen.getByTestId("greeks-spot")).toBeTruthy();
  });

  it("shows the composed empty state (never bare prose) before a compute", () => {
    render(<GreeksDashboard />);
    expect(screen.getByTestId("empty-state")).toBeTruthy();
    expect(screen.getByTestId("empty-state-headline").textContent).toBe("No Greeks computed");
    // The CTA runs the compute with the prefilled inputs.
    expect(screen.getByTestId("empty-state-cta")).toBeTruthy();
  });

  it("computes greeks on click and renders five cards", async () => {
    render(<GreeksDashboard />);
    fireEvent.click(screen.getByTestId("compute-greeks"));
    await screen.findByTestId("greeks-result");
    expect(screen.getByTestId("greek-delta").textContent).toContain("0.5500");
    expect(screen.getByTestId("greek-gamma").textContent).toContain("0.0200");
    expect(screen.getByTestId("greek-vega").textContent).toContain("30.0000");
    expect(screen.getByTestId("greek-theta").textContent).toContain("-5.0000");
    expect(screen.getByTestId("greek-rho").textContent).toContain("12.0000");
    expect(screen.getByTestId("greeks-price").textContent).toContain("$8.4200");
  });

  it("renders the sensitivity read table + the request echo with the result", async () => {
    render(<GreeksDashboard />);
    fireEvent.click(screen.getByTestId("compute-greeks"));
    await screen.findByTestId("greeks-result");
    const table = screen.getByTestId("greeks-sensitivity");
    expect(table.textContent).toContain("Δ Delta");
    expect(table.textContent).toContain("∂V/∂σ — sensitivity to implied volatility");
    expect(table.textContent).toContain("0.5500");
    // The price pairs with the request it was computed from.
    expect(screen.getByTestId("greeks-request-echo").textContent).toContain("CALL · S 220");
  });

  it("surfaces honest inline validation and blocks the compute", () => {
    render(<GreeksDashboard />);
    fireEvent.change(screen.getByTestId("greeks-spot"), { target: { value: "" } });
    expect(screen.getByTestId("greeks-validation").textContent).toMatch(/numeric spot/i);
    expect(screen.getByTestId("compute-greeks")).toHaveProperty("disabled", true);

    fireEvent.change(screen.getByTestId("greeks-spot"), { target: { value: "-5" } });
    expect(screen.getByTestId("greeks-validation").textContent).toMatch(/must be positive/i);

    fireEvent.change(screen.getByTestId("greeks-spot"), { target: { value: "220" } });
    expect(screen.queryByTestId("greeks-validation")).toBeNull();
    expect(screen.getByTestId("compute-greeks")).toHaveProperty("disabled", false);
  });
});
