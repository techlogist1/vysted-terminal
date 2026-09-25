import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { resetQuantStoreForTests } from "@/store/quant";
import { useSettingsStore } from "@/store/settings";
import { BondPricerPanel } from "./BondPricerPanel";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
}));

beforeEach(() => {
  resetQuantStoreForTests();
  // R15-DATA-100: the display currency defaults to the SESSION region's —
  // pin the region explicitly so the assertions below don't ride whatever
  // the store's own default happens to be.
  useSettingsStore.setState({ region: "US" });
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        clean_price: 1060.58,
        dirty_price: 1060.58,
        accrued_interest: 0.0,
        duration: 8.05,
        modified_duration: 7.89,
        convexity: 75.0,
        duration_ms: 1.5,
      }),
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("BondPricerPanel date defaults (R15-UI-063)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 25)); // 2026-09-25, local time
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("defaults issue/settlement to today and maturity to today + 10y, not a frozen literal", () => {
    render(<BondPricerPanel />);
    expect(screen.getByTestId("field-issue")).toHaveValue("2026-09-25");
    expect(screen.getByTestId("field-settle")).toHaveValue("2026-09-25");
    expect(screen.getByTestId("field-maturity")).toHaveValue("2036-09-25");
  });
});

describe("BondPricerPanel", () => {
  it("renders the input form", () => {
    render(<BondPricerPanel />);
    expect(screen.getByTestId("bond-pricer-form")).toBeTruthy();
    expect(screen.getByTestId("field-coupon")).toBeTruthy();
    expect(screen.getByTestId("field-ytm")).toBeTruthy();
  });

  it("prices a bond and renders clean / duration / convexity", async () => {
    render(<BondPricerPanel />);
    fireEvent.click(screen.getByTestId("price-bond"));
    await screen.findByTestId("bond-pricing-result");
    expect(screen.getByTestId("bond-clean").textContent).toContain("$1,060.58");
    expect(screen.getByTestId("bond-duration").textContent).toContain("8.0500");
  });

  it("R15-DATA-100: in region IN, prices render with ₹, not a hard-coded $", async () => {
    useSettingsStore.setState({ region: "IN" });
    render(<BondPricerPanel />);
    fireEvent.click(screen.getByTestId("price-bond"));
    await screen.findByTestId("bond-pricing-result");
    expect(screen.getByTestId("bond-clean").textContent).toContain("₹1,060.58");
    expect(screen.getByTestId("bond-clean").textContent).not.toContain("$");
  });

  it("R15-DATA-100: the display-currency select overrides the region default", async () => {
    render(<BondPricerPanel />);
    fireEvent.click(screen.getByTestId("price-bond"));
    await screen.findByTestId("bond-pricing-result");
    expect(screen.getByTestId("bond-clean").textContent).toContain("$1,060.58");

    fireEvent.change(screen.getByTestId("field-display-currency"), {
      target: { value: "INR" },
    });
    expect(screen.getByTestId("bond-clean").textContent).toContain("₹1,060.58");
  });

  it("supports semi-annual / annual / quarterly via the dropdown", () => {
    render(<BondPricerPanel />);
    const select = screen.getByTestId("field-coupons-per-year") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "4" } });
    expect(select.value).toBe("4");
    fireEvent.change(select, { target: { value: "1" } });
    expect(select.value).toBe("1");
  });

  it("renders the composed empty state before the first price", () => {
    render(<BondPricerPanel />);
    expect(screen.getByTestId("empty-state")).toBeTruthy();
    expect(screen.getByTestId("empty-state-headline").textContent).toBe("No bond priced");
    expect(screen.getByTestId("empty-state-cta")).toBeTruthy();
  });

  it("surfaces inline validation and blocks the POST on a bad input", () => {
    render(<BondPricerPanel />);
    fireEvent.change(screen.getByTestId("field-face"), { target: { value: "0" } });
    expect(screen.getByTestId("bond-validation").textContent).toMatch(/positive/);
    const priceBtn = screen.getByTestId("price-bond") as HTMLButtonElement;
    expect(priceBtn.disabled).toBe(true);
    fireEvent.click(priceBtn);
    expect(vi.mocked(fetch)).not.toHaveBeenCalled();
  });

  it("rejects an out-of-window settlement date inline", () => {
    render(<BondPricerPanel />);
    fireEvent.change(screen.getByTestId("field-settle"), { target: { value: "2040-01-01" } });
    expect(screen.getByTestId("bond-validation").textContent).toMatch(/between issue and maturity/);
  });
});
