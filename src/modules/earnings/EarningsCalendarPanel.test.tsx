/**
 * EarningsCalendarPanel tests.
 *
 * Mocks the sidecar-client + lightweight-charts so the panel exercises
 * its rendering + sort + watchlist-apply paths in jsdom.
 */

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  EarningsEstimateDetail,
  EarningsSurprisesResponse,
  EarningsUpcomingResponse,
} from "../../../types/earnings";

// lightweight-charts mock — jsdom has no canvas.
const histogramSeries = { setData: vi.fn() };
const timeScale = { fitContent: vi.fn() };
const chartApi = {
  addSeries: vi.fn(() => histogramSeries),
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
import { useEarningsStore } from "@/store/earnings";

import { EarningsCalendarPanel } from "./EarningsCalendarPanel";

const UPCOMING_SAMPLE: EarningsUpcomingResponse = {
  start_date: "2026-05-16",
  end_date: "2026-05-23",
  events: [
    {
      symbol: "AAPL",
      company_name: "Apple Inc.",
      scheduled_date: "2026-05-20",
      time_of_day: "after-close",
      fiscal_period: { quarter: "Q2", year: 2026 },
      eps_estimate_mean: 1.5,
      eps_estimate_stddev: 0.05,
      estimate_analyst_count: 20,
      currency: "USD",
      provider: "yfinance",
    },
    {
      symbol: "MSFT",
      company_name: "Microsoft Corp.",
      scheduled_date: "2026-05-22",
      time_of_day: "after-close",
      fiscal_period: { quarter: "Q2", year: 2026 },
      eps_estimate_mean: 3.1,
      eps_estimate_stddev: 0.08,
      estimate_analyst_count: 35,
      currency: "USD",
      provider: "yfinance",
    },
  ],
};

const SURPRISES_SAMPLE: EarningsSurprisesResponse = {
  symbol: "AAPL",
  surprises: [
    {
      symbol: "AAPL",
      reported_date: "2026-02-01",
      fiscal_period: { quarter: "Q1", year: 2026 },
      eps_actual: 1.32,
      eps_estimate_mean: 1.3,
      eps_surprise: 0.02,
      eps_surprise_pct: 0.015,
      revenue_actual: null,
      revenue_estimate_mean: null,
      revenue_surprise_pct: null,
      currency: "USD",
      provider: "yfinance",
    },
  ],
};

const ESTIMATE_SAMPLE: EarningsEstimateDetail = {
  symbol: "AAPL",
  fiscal_period: { quarter: "Q2", year: 2026 },
  eps_estimate_mean: 1.5,
  eps_estimate_median: 1.5,
  eps_estimate_high: 1.6,
  eps_estimate_low: 1.4,
  eps_estimate_stddev: 0.05,
  estimate_analyst_count: 20,
  revenue_estimate_mean: null,
  revenue_estimate_median: null,
  revenue_estimate_high: null,
  revenue_estimate_low: null,
  revenue_analyst_count: 0,
  currency: "USD",
  provider: "yfinance",
  as_of: "2026-05-16T00:00:00Z",
};

beforeEach(() => {
  useEarningsStore.getState().__resetForTests();
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("EarningsCalendarPanel", () => {
  it("loads the upcoming window on mount and renders the rows", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(UPCOMING_SAMPLE);
    render(<EarningsCalendarPanel />);
    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument();
      expect(screen.getByText("MSFT")).toBeInTheDocument();
    });
  });

  it("renders the company name + consensus EPS columns", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(UPCOMING_SAMPLE);
    render(<EarningsCalendarPanel />);
    await waitFor(() => {
      expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
      expect(screen.getByText("1.50")).toBeInTheDocument();
    });
  });

  it("expands an inline drill-down on row click and fetches history/surprises/estimates", async () => {
    vi.mocked(sidecarGet)
      .mockResolvedValueOnce(UPCOMING_SAMPLE)
      .mockResolvedValueOnce({ symbol: "AAPL", history: [] })
      .mockResolvedValueOnce(SURPRISES_SAMPLE)
      .mockResolvedValueOnce(ESTIMATE_SAMPLE);

    render(<EarningsCalendarPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("earnings-row-AAPL")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("earnings-row-AAPL"));
    await waitFor(() => {
      expect(screen.getByTestId("eps-estimate-grid")).toBeInTheDocument();
    });
  });

  it("captures upcoming-load errors inline", async () => {
    vi.mocked(sidecarGet).mockRejectedValueOnce(new Error("provider blew up"));
    render(<EarningsCalendarPanel />);
    await waitFor(() => {
      expect(screen.getByText(/provider blew up/i)).toBeInTheDocument();
    });
  });

  it("applies a watchlist + days when the form submits", async () => {
    vi.mocked(sidecarGet)
      .mockResolvedValueOnce(UPCOMING_SAMPLE)
      .mockResolvedValueOnce(UPCOMING_SAMPLE);
    render(<EarningsCalendarPanel />);
    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText("Window in days"), { target: { value: "14" } });
    fireEvent.change(screen.getByLabelText("Watchlist"), { target: { value: "AAPL,MSFT,NVDA" } });
    fireEvent.click(screen.getByRole("button", { name: /apply/i }));
    await waitFor(() => {
      expect(sidecarGet).toHaveBeenCalledWith("/earnings/upcoming", {
        days: 14,
        watchlist: "AAPL,MSFT,NVDA",
      });
    });
  });
});
