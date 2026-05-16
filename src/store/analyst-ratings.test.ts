/**
 * Analyst-ratings store tests — three independent per-symbol caches with
 * per-slice error capture.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  IndividualAnalystResponse,
  PriceTargetHistoryResponse,
  RatingsHistoryResponse,
} from "../../types/analyst";

import { useAnalystRatingsStore } from "./analyst-ratings";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

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
  vi.unstubAllGlobals();
});

describe("useAnalystRatingsStore", () => {
  it("caches ratings history by symbol", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(HISTORY);
    const first = await useAnalystRatingsStore.getState().getHistory("AAPL");
    const second = await useAnalystRatingsStore.getState().getHistory("AAPL");
    expect(first).toEqual(HISTORY);
    expect(second).toEqual(HISTORY);
    expect(sidecarGet).toHaveBeenCalledTimes(1);
  });

  it("caches price targets independently of history", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(HISTORY).mockResolvedValueOnce(TARGETS);
    await useAnalystRatingsStore.getState().getHistory("AAPL");
    const out = await useAnalystRatingsStore.getState().getPriceTargets("AAPL");
    expect(out).toEqual(TARGETS);
  });

  it("caches individual analysts independently", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(INDIVIDUAL);
    const out = await useAnalystRatingsStore.getState().getIndividual("AAPL");
    expect(out).toEqual(INDIVIDUAL);
  });

  it("records error per slice without clobbering other slices", async () => {
    vi.mocked(sidecarGet)
      .mockResolvedValueOnce(HISTORY)
      .mockRejectedValueOnce(new Error("offline"));
    await useAnalystRatingsStore.getState().getHistory("AAPL");
    const ptOut = await useAnalystRatingsStore.getState().getPriceTargets("AAPL");
    expect(ptOut).toBeNull();
    const state = useAnalystRatingsStore.getState();
    expect(state.histories.AAPL).toEqual(HISTORY);
    expect(state.priceTargetErrors.AAPL).toContain("offline");
  });

  it("normalises symbol case", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(HISTORY);
    await useAnalystRatingsStore.getState().getHistory("aapl");
    expect(useAnalystRatingsStore.getState().histories.AAPL).toEqual(HISTORY);
  });

  it("returns null on empty symbol without making a request", async () => {
    const out = await useAnalystRatingsStore.getState().getHistory("");
    expect(out).toBeNull();
    expect(sidecarGet).not.toHaveBeenCalled();
  });
});
