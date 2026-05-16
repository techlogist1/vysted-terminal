/**
 * Earnings store tests — upcoming-window load + per-symbol caches.
 *
 * The store's network paths run through `sidecarGet`, which is mocked
 * at the module boundary. Tests exercise the cache-hit-second-call
 * behaviour, error capture, and the watchlist param serialisation.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  EarningsEstimateDetail,
  EarningsHistoryResponse,
  EarningsSurprisesResponse,
  EarningsUpcomingResponse,
} from "../../types/earnings";

import { useEarningsStore } from "./earnings";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

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
  ],
};

const HISTORY_SAMPLE: EarningsHistoryResponse = {
  symbol: "AAPL",
  history: [
    {
      fiscal_period: { quarter: "Q1", year: 2026 },
      reported_date: "2026-02-01",
      eps_actual: 1.32,
      eps_estimate_mean: 1.3,
      revenue_actual: null,
      revenue_estimate_mean: null,
      currency: "USD",
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
  vi.unstubAllGlobals();
});

describe("useEarningsStore — loadUpcoming", () => {
  it("starts idle with no events", () => {
    const state = useEarningsStore.getState();
    expect(state.upcoming).toBeNull();
    expect(state.upcomingStatus).toBe("idle");
  });

  it("loads upcoming events with default days when called without args", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(UPCOMING_SAMPLE);
    await useEarningsStore.getState().loadUpcoming();
    const state = useEarningsStore.getState();
    expect(state.upcoming).toEqual(UPCOMING_SAMPLE);
    expect(state.upcomingStatus).toBe("ready");
    expect(state.lastDays).toBe(7);
  });

  it("serialises the watchlist into a comma-separated param", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(UPCOMING_SAMPLE);
    await useEarningsStore.getState().loadUpcoming(14, ["AAPL", "MSFT"]);
    expect(sidecarGet).toHaveBeenCalledWith("/earnings/upcoming", {
      days: 14,
      watchlist: "AAPL,MSFT",
    });
    expect(useEarningsStore.getState().lastDays).toBe(14);
    expect(useEarningsStore.getState().lastWatchlist).toEqual(["AAPL", "MSFT"]);
  });

  it("captures upcoming load errors", async () => {
    vi.mocked(sidecarGet).mockRejectedValueOnce(new Error("provider error"));
    await useEarningsStore.getState().loadUpcoming();
    const state = useEarningsStore.getState();
    expect(state.upcomingStatus).toBe("error");
    expect(state.upcomingError).toContain("provider error");
  });
});

describe("useEarningsStore — per-symbol caches", () => {
  it("caches history responses by symbol", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(HISTORY_SAMPLE);
    const first = await useEarningsStore.getState().getHistory("AAPL");
    const second = await useEarningsStore.getState().getHistory("AAPL");
    expect(first).toEqual(HISTORY_SAMPLE);
    expect(second).toEqual(HISTORY_SAMPLE);
    expect(sidecarGet).toHaveBeenCalledTimes(1);
  });

  it("normalises symbol case for the cache key", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(HISTORY_SAMPLE);
    await useEarningsStore.getState().getHistory("aapl");
    expect(useEarningsStore.getState().histories.AAPL).toEqual(HISTORY_SAMPLE);
  });

  it("returns null and records an error when history fails", async () => {
    vi.mocked(sidecarGet).mockRejectedValueOnce(new Error("offline"));
    const out = await useEarningsStore.getState().getHistory("AAPL");
    expect(out).toBeNull();
    expect(useEarningsStore.getState().historyErrors.AAPL).toContain("offline");
  });

  it("caches surprises", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(SURPRISES_SAMPLE);
    const out = await useEarningsStore.getState().getSurprises("AAPL");
    expect(out).toEqual(SURPRISES_SAMPLE);
    expect(useEarningsStore.getState().surprises.AAPL).toEqual(SURPRISES_SAMPLE);
  });

  it("caches estimates", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(ESTIMATE_SAMPLE);
    const out = await useEarningsStore.getState().getEstimates("AAPL");
    expect(out).toEqual(ESTIMATE_SAMPLE);
    expect(useEarningsStore.getState().estimates.AAPL).toEqual(ESTIMATE_SAMPLE);
  });

  it("returns null on empty symbol without making a request", async () => {
    const out = await useEarningsStore.getState().getHistory("   ");
    expect(out).toBeNull();
    expect(sidecarGet).not.toHaveBeenCalled();
  });
});
