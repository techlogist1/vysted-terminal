/**
 * AnalystRatingsPanel tests.
 */

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  IndividualAnalystResponse,
  PriceTargetHistoryResponse,
  RatingsHistoryResponse,
} from "../../../types/analyst";

const lineSeries = { setData: vi.fn() };
const timeScale = { fitContent: vi.fn() };
const chartApi = {
  addSeries: vi.fn(() => lineSeries),
  removeSeries: vi.fn(),
  timeScale: vi.fn(() => timeScale),
  remove: vi.fn(),
};
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => chartApi),
  LineSeries: "Line",
  HistogramSeries: "Histogram",
  AreaSeries: "Area",
}));

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";
import { useAnalystRatingsStore } from "@/store/analyst-ratings";

import { AnalystRatingsPanel } from "./AnalystRatingsPanel";

const HISTORY: RatingsHistoryResponse = {
  symbol: "AAPL",
  history: [
    {
      symbol: "AAPL",
      date: "2026-05-01",
      firm: "Morgan Stanley",
      analyst_name: null,
      rating_from: "hold",
      rating_to: "buy",
      raw_rating: "Overweight",
      note: "up",
      provider: "yfinance",
    },
    {
      symbol: "AAPL",
      date: "2026-04-15",
      firm: "Goldman Sachs",
      analyst_name: null,
      rating_from: null,
      rating_to: "buy",
      raw_rating: "Buy",
      note: "initiated",
      provider: "yfinance",
    },
  ],
};

const TARGETS: PriceTargetHistoryResponse = {
  symbol: "AAPL",
  history: [
    {
      symbol: "AAPL",
      date: "2026-05-01",
      firm: "Morgan Stanley",
      analyst_name: null,
      target_from: 200,
      target_to: 230,
      currency: "USD",
      provider: "yfinance",
    },
  ],
};

const INDIVIDUAL: IndividualAnalystResponse = {
  symbol: "AAPL",
  analysts: [
    {
      symbol: "AAPL",
      firm: "Goldman Sachs",
      analyst_name: "Goldman Sachs",
      current_rating: "buy",
      current_price_target: 225,
      currency: "USD",
      rating_issued_date: "2026-04-15",
      one_year_accuracy: 0.72,
      star_rating: 4,
      provider: "yfinance",
    },
    {
      symbol: "AAPL",
      firm: "JP Morgan",
      analyst_name: "JP Morgan",
      current_rating: "sell",
      current_price_target: 180,
      currency: "USD",
      rating_issued_date: "2026-04-01",
      one_year_accuracy: null,
      star_rating: null,
      provider: "yfinance",
    },
  ],
};

beforeEach(() => {
  useAnalystRatingsStore.getState().__resetForTests();
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("AnalystRatingsPanel", () => {
  it("requires a symbol before loading", () => {
    render(<AnalystRatingsPanel />);
    expect(screen.getByText(/Enter a symbol/i)).toBeInTheDocument();
  });

  it("loads history / price targets / individual on symbol submit", async () => {
    vi.mocked(sidecarGet)
      .mockResolvedValueOnce(HISTORY)
      .mockResolvedValueOnce(TARGETS)
      .mockResolvedValueOnce(INDIVIDUAL);
    render(<AnalystRatingsPanel />);
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByRole("button", { name: /load/i }));
    await waitFor(() => {
      expect(screen.getByText(/Morgan Stanley/i)).toBeInTheDocument();
    });
    expect(sidecarGet).toHaveBeenCalledWith("/fundamentals/AAPL/ratings/history");
    expect(sidecarGet).toHaveBeenCalledWith("/fundamentals/AAPL/ratings/price-target-history");
    expect(sidecarGet).toHaveBeenCalledWith("/fundamentals/AAPL/ratings/individual");
  });

  it("switches to the price-targets tab and renders the chart container", async () => {
    vi.mocked(sidecarGet)
      .mockResolvedValueOnce(HISTORY)
      .mockResolvedValueOnce(TARGETS)
      .mockResolvedValueOnce(INDIVIDUAL);
    render(<AnalystRatingsPanel />);
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByRole("button", { name: /load/i }));
    await waitFor(() => expect(screen.getByText(/Morgan Stanley/i)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /price targets/i }));
    await waitFor(() => {
      expect(screen.getByTestId("price-target-timeline-chart")).toBeInTheDocument();
    });
  });

  it("renders the individual analyst table on the Individual tab", async () => {
    vi.mocked(sidecarGet)
      .mockResolvedValueOnce(HISTORY)
      .mockResolvedValueOnce(TARGETS)
      .mockResolvedValueOnce(INDIVIDUAL);
    render(<AnalystRatingsPanel />);
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByRole("button", { name: /load/i }));
    await waitFor(() => expect(screen.getByText(/Morgan Stanley/i)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /individual/i }));
    await waitFor(() => {
      expect(screen.getByTestId("individual-analyst-table")).toBeInTheDocument();
      expect(screen.getByText("Goldman Sachs")).toBeInTheDocument();
      expect(screen.getByText("JP Morgan")).toBeInTheDocument();
    });
  });

  it("surfaces an error banner when a slice fails", async () => {
    vi.mocked(sidecarGet)
      .mockRejectedValueOnce(new Error("history offline"))
      .mockResolvedValueOnce(TARGETS)
      .mockResolvedValueOnce(INDIVIDUAL);
    render(<AnalystRatingsPanel />);
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByRole("button", { name: /load/i }));
    await waitFor(() => {
      expect(screen.getByText(/history offline/i)).toBeInTheDocument();
    });
  });
});
