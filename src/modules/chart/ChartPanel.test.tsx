import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SidecarError } from "@/lib/sidecar-client";
import type { IndicatorResponse, OHLCVSeries } from "../../../types/data";

// --- lightweight-charts mock ------------------------------------------------
// The real library renders to a <canvas>, which jsdom does not implement. The
// mock records calls so the test can assert on the panel's data wiring without
// a real chart. `chartApi` is module-scoped so assertions can reach it.
const chartApi = {
  addSeries: vi.fn(() => ({ setData: vi.fn() })),
  removeSeries: vi.fn(),
  timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
  remove: vi.fn(),
};

vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => chartApi),
  CandlestickSeries: "Candlestick",
  LineSeries: "Line",
}));

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
});
