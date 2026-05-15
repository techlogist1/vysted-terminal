import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SidecarError } from "@/lib/sidecar-client";
import type { IndicatorResponse, OHLCVSeries } from "../../../types/data";

// --- lightweight-charts mock ------------------------------------------------
// The real library renders to a <canvas>, which jsdom does not implement. The
// mock records calls so the test can assert on the panel's data wiring without
// a real chart. `chartApi` and `candleSeries` are module-scoped so assertions
// can reach them.
const candleSeries = {
  setData: vi.fn(),
  attachPrimitive: vi.fn(),
  detachPrimitive: vi.fn(),
};
const chartApi = {
  // First addSeries call is the candlestick series; subsequent calls are
  // indicator line series. The candle ref needs `attachPrimitive` so the
  // panel can wire the Volume Profile histogram into it.
  addSeries: vi.fn((type: unknown) =>
    type === "Candlestick" ? candleSeries : { setData: vi.fn() },
  ),
  removeSeries: vi.fn(),
  timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
  remove: vi.fn(),
};

// Markers plugin handle returned by `createSeriesMarkers`. Module-scoped so
// the Parabolic SAR test can assert on `setMarkers` / `detach` calls.
const sarMarkersHandle = {
  setMarkers: vi.fn(),
  detach: vi.fn(),
};
const createSeriesMarkersMock = vi.fn(() => sarMarkersHandle);

vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => chartApi),
  CandlestickSeries: "Candlestick",
  LineSeries: "Line",
  createSeriesMarkers: (...args: unknown[]) =>
    (createSeriesMarkersMock as (...inner: unknown[]) => unknown)(...args),
}));

// --- volume profile primitive mock -----------------------------------------
// vitest's `vi.fn()` does not satisfy `new` correctly when bound to a class
// name; use a real ES class whose ctor and method delegate to module-scoped
// spies the assertions can reach.
const volumeProfileSetBuckets = vi.fn();
const volumeProfileCtor = vi.fn();

vi.mock("./volume-profile-primitive", () => {
  class MockVolumeProfilePrimitive {
    constructor() {
      volumeProfileCtor();
    }
    setBuckets(buckets: unknown) {
      volumeProfileSetBuckets(buckets);
    }
  }
  return { VolumeProfilePrimitive: MockVolumeProfilePrimitive };
});

// --- ichimoku cloud primitive mock -----------------------------------------
const ichimokuCloudSetBands = vi.fn();
const ichimokuCloudCtor = vi.fn();

vi.mock("./ichimoku-cloud-primitive", () => {
  class MockIchimokuCloudPrimitive {
    constructor() {
      ichimokuCloudCtor();
    }
    setBands(senkouA: unknown, senkouB: unknown) {
      ichimokuCloudSetBands(senkouA, senkouB);
    }
  }
  return { IchimokuCloudPrimitive: MockIchimokuCloudPrimitive };
});

// --- sidecar-client / api mocks --------------------------------------------
const historyMock = vi.fn();
const fetchIndicatorsMock = vi.fn();

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    sidecarApi: { history: (...args: unknown[]) => historyMock(...args) },
  };
});

vi.mock("./api", () => ({
  fetchIndicators: (...args: unknown[]) => fetchIndicatorsMock(...args),
}));

import ChartPanel from "./ChartPanel";

// --- fixtures ---------------------------------------------------------------
function makeSeries(symbol: string): OHLCVSeries {
  return {
    symbol,
    timeframe: "1d",
    provider: "yfinance",
    bars: [
      { timestamp: "2026-01-01T00:00:00Z", open: 1, high: 2, low: 0.5, close: 1.5, volume: 100 },
      { timestamp: "2026-01-02T00:00:00Z", open: 1.5, high: 3, low: 1, close: 2.5, volume: 120 },
    ],
  };
}

function makeIndicatorResponse(): IndicatorResponse {
  return {
    symbol: "SPY",
    timeframe: "1d",
    provider: "yfinance",
    indicators: [
      {
        name: "sma",
        panel: "price",
        lines: [
          {
            label: "SMA(20)",
            points: [
              { time: "2026-01-01T00:00:00Z", value: null },
              { time: "2026-01-02T00:00:00Z", value: 2.0 },
            ],
          },
        ],
      },
      {
        name: "rsi",
        panel: "separate",
        lines: [
          {
            label: "RSI(14)",
            points: [
              { time: "2026-01-01T00:00:00Z", value: 55 },
              { time: "2026-01-02T00:00:00Z", value: 60 },
            ],
          },
        ],
      },
    ],
    volume_profile: null,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  historyMock.mockResolvedValue(makeSeries("SPY"));
  fetchIndicatorsMock.mockResolvedValue(makeIndicatorResponse());
});

afterEach(() => {
  cleanup();
});

describe("ChartPanel", () => {
  it("loads SPY at the 1d timeframe by default", async () => {
    render(<ChartPanel />);
    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("SPY", "1d");
    });
    expect(await screen.findByText(/via yfinance/)).toBeInTheDocument();
  });

  it("does not request indicators until one is selected", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    expect(fetchIndicatorsMock).not.toHaveBeenCalled();
  });

  it("fetches an indicator server-side when toggled on", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "RSI", pressed: false }));

    await waitFor(() => {
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("SPY", ["rsi"], "1d");
    });
    expect(screen.getByRole("button", { name: "RSI", pressed: true })).toBeInTheDocument();
  });

  it("re-requests history and indicators when the timeframe changes", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "RSI", pressed: false }));
    await waitFor(() => expect(fetchIndicatorsMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "1h", pressed: false }));

    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("SPY", "1h");
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("SPY", ["rsi"], "1h");
    });
  });

  it("loads a new symbol when the symbol form is submitted", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalledTimes(1));

    const input = screen.getByLabelText("Symbol");
    fireEvent.change(input, { target: { value: "nvda" } });
    fireEvent.click(screen.getByRole("button", { name: "Load" }));

    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("NVDA", "1d");
    });
  });

  it("surfaces a SidecarError from the history call", async () => {
    historyMock.mockRejectedValueOnce(new SidecarError(502, "provider down"));
    render(<ChartPanel />);
    expect(await screen.findByText(/provider down \(502\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("surfaces a SidecarError from the indicator call", async () => {
    fetchIndicatorsMock.mockRejectedValueOnce(new SidecarError(400, "bad indicator"));
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "MACD", pressed: false }));

    expect(await screen.findByText(/bad indicator \(400\)/)).toBeInTheDocument();
  });

  it("clears all selected indicators with the Clear control", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "RSI", pressed: false }));
    await waitFor(() => expect(fetchIndicatorsMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Clear \(1\)/ }));

    expect(screen.getByRole("button", { name: "RSI", pressed: false })).toBeInTheDocument();
  });

  it("renders all 20 indicators in the selector", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    // 20 indicator toggles + 8 timeframe toggles + Load button = the selector
    // grid itself should expose exactly 20 indicator buttons.
    for (const label of ["RSI", "MACD", "VWAP", "Volume Profile", "Parabolic SAR", "ROC"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  it("attaches a Volume Profile primitive when the indicator is toggled on", async () => {
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [],
      volume_profile: {
        buckets: [
          { price: 100.0, volume: 1_000 },
          { price: 101.0, volume: 2_000 },
        ],
      },
    } satisfies IndicatorResponse);
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Volume Profile", pressed: false }));

    await waitFor(() => {
      expect(volumeProfileCtor).toHaveBeenCalled();
    });
    expect(candleSeries.attachPrimitive).toHaveBeenCalled();
    expect(volumeProfileSetBuckets).toHaveBeenCalledWith([
      { price: 100.0, volume: 1_000 },
      { price: 101.0, volume: 2_000 },
    ]);
  });

  it("draws Parabolic SAR as series markers with trend-aware placement", async () => {
    // SPY default fixture: bar 1 closes at 1.5, bar 2 closes at 2.5.
    // SAR < close → uptrend → belowBar; SAR > close → downtrend → aboveBar.
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [
        {
          name: "parabolic_sar",
          panel: "price",
          lines: [
            {
              label: "Parabolic SAR",
              points: [
                { time: "2026-01-01T00:00:00Z", value: 0.8 }, // < 1.5 → uptrend
                { time: "2026-01-02T00:00:00Z", value: 3.0 }, // > 2.5 → downtrend
              ],
            },
          ],
        },
      ],
      volume_profile: null,
    } satisfies IndicatorResponse);

    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Parabolic SAR", pressed: false }));

    await waitFor(() => expect(createSeriesMarkersMock).toHaveBeenCalled());
    // The candle series — not a new LineSeries — is the markers' host.
    expect(createSeriesMarkersMock).toHaveBeenCalledWith(
      candleSeries,
      expect.arrayContaining([
        expect.objectContaining({ position: "belowBar", shape: "circle" }),
        expect.objectContaining({ position: "aboveBar", shape: "circle" }),
      ]),
    );
    // No line series should be added for the SAR indicator.
    const lineCalls = chartApi.addSeries.mock.calls.filter(([type]) => type === "Line");
    expect(lineCalls).toHaveLength(0);
  });

  it("detaches Parabolic SAR markers when the indicator is cleared", async () => {
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [
        {
          name: "parabolic_sar",
          panel: "price",
          lines: [
            {
              label: "Parabolic SAR",
              points: [{ time: "2026-01-02T00:00:00Z", value: 1.0 }],
            },
          ],
        },
      ],
      volume_profile: null,
    } satisfies IndicatorResponse);

    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Parabolic SAR", pressed: false }));
    await waitFor(() => expect(createSeriesMarkersMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Clear \(1\)/ }));

    await waitFor(() => expect(sarMarkersHandle.detach).toHaveBeenCalled());
  });

  it("detaches the Volume Profile primitive when the indicator is cleared", async () => {
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [],
      volume_profile: { buckets: [{ price: 100.0, volume: 500 }] },
    } satisfies IndicatorResponse);
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Volume Profile", pressed: false }));
    await waitFor(() => expect(candleSeries.attachPrimitive).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Clear \(1\)/ }));

    await waitFor(() => {
      expect(candleSeries.detachPrimitive).toHaveBeenCalled();
    });
  });

  it("attaches the Ichimoku cloud primitive when the indicator is toggled on", async () => {
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [
        {
          name: "ichimoku",
          panel: "price",
          lines: [
            { label: "Tenkan-sen", points: [{ time: "2026-01-02T00:00:00Z", value: 1.5 }] },
            { label: "Kijun-sen", points: [{ time: "2026-01-02T00:00:00Z", value: 1.6 }] },
            { label: "Senkou Span A", points: [{ time: "2026-01-02T00:00:00Z", value: 1.7 }] },
            { label: "Senkou Span B", points: [{ time: "2026-01-02T00:00:00Z", value: 1.4 }] },
            { label: "Chikou Span", points: [{ time: "2026-01-01T00:00:00Z", value: 1.3 }] },
          ],
        },
      ],
      volume_profile: null,
    } satisfies IndicatorResponse);

    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Ichimoku Cloud", pressed: false }));

    await waitFor(() => expect(ichimokuCloudCtor).toHaveBeenCalled());
    expect(candleSeries.attachPrimitive).toHaveBeenCalled();
    expect(ichimokuCloudSetBands).toHaveBeenCalledWith(
      [{ time: "2026-01-02T00:00:00Z", value: 1.7 }],
      [{ time: "2026-01-02T00:00:00Z", value: 1.4 }],
    );
  });
});
