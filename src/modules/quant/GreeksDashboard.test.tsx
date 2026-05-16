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
});
