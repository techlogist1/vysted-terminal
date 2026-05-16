import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { resetQuantStoreForTests } from "@/store/quant";
import { YieldCurvePanel } from "./YieldCurvePanel";

// lightweight-charts is the heavyweight that the panel renders into. Its
// jsdom shim doesn't reliably draw, so we stub the surface we touch so the
// panel exercise stays focused on the form / store wiring.
vi.mock("lightweight-charts", () => {
  const fakeSeries = { setData: vi.fn() };
  const fakeChart = {
    addSeries: vi.fn().mockReturnValue(fakeSeries),
    timeScale: vi.fn().mockReturnValue({ fitContent: vi.fn() }),
    remove: vi.fn(),
  };
  return {
    createChart: vi.fn().mockReturnValue(fakeChart),
    LineSeries: "line-series-token",
  };
});

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
        valuation_date: "2026-05-16",
        curve: [
          {
            date: "2026-06-16",
            tenor_years: 0.083,
            zero_rate: 0.041,
            discount_factor: 0.997,
          },
          { date: "2031-05-16", tenor_years: 5.0, zero_rate: 0.047, discount_factor: 0.79 },
        ],
        duration_ms: 1.5,
      }),
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("YieldCurvePanel", () => {
  it("renders the default 7-instrument grid + sample count", () => {
    render(<YieldCurvePanel />);
    expect(screen.getByTestId("yield-curve-form")).toBeTruthy();
    expect(screen.getByTestId("inst-0")).toBeTruthy();
    expect(screen.getByTestId("inst-6")).toBeTruthy(); // 30y swap
    expect(screen.getByTestId("field-sample-count")).toBeTruthy();
  });

  it("bootstraps and renders the sample table", async () => {
    render(<YieldCurvePanel />);
    fireEvent.click(screen.getByTestId("bootstrap-curve"));
    await screen.findByTestId("yield-curve-table");
  });
});
