import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { PriceTargetEntry } from "../../../types/analyst";

const lineSeries = { setData: vi.fn(), applyOptions: vi.fn() };
const timeScale = { fitContent: vi.fn() };
const chartApi = {
  addSeries: vi.fn((_type: unknown, _opts: { title: string }) => lineSeries),
  timeScale: vi.fn(() => timeScale),
  remove: vi.fn(),
  subscribeCrosshairMove: vi.fn(),
  unsubscribeCrosshairMove: vi.fn(),
};
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => chartApi),
  LineSeries: "Line",
}));

import { PriceTargetTimeline } from "./PriceTargetTimeline";

// R15-DATA-069: two firms revise on the same day — the chart collapses them
// into one meaned point, and a third firm's revision lands on a distinct day.
const HISTORY: PriceTargetEntry[] = [
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
  {
    symbol: "AAPL",
    date: "2026-05-01",
    firm: "Goldman Sachs",
    analyst_name: null,
    target_from: 210,
    target_to: 225,
    currency: "USD",
    provider: "yfinance",
  },
  {
    symbol: "AAPL",
    date: "2026-04-01",
    firm: "JP Morgan",
    analyst_name: null,
    target_from: 210,
    target_to: 180,
    currency: "USD",
    provider: "yfinance",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("PriceTargetTimeline", () => {
  it("renders the empty state when there is no history", () => {
    render(<PriceTargetTimeline history={[]} />);
    expect(screen.getByText("No price-target history")).toBeInTheDocument();
  });

  it("labels the series as the mean of targets revised that day (R15-DATA-069)", () => {
    render(<PriceTargetTimeline history={HISTORY} />);
    const opts = chartApi.addSeries.mock.calls[0][1];
    expect(opts.title).toContain("Mean of targets revised that day");
  });

  it("collapses same-day entries into a single averaged point", () => {
    render(<PriceTargetTimeline history={HISTORY} />);
    const pushed = lineSeries.setData.mock.calls[0][0] as { time: number; value: number }[];
    // 3 entries, 2 distinct dates → 2 points, oldest first.
    expect(pushed).toHaveLength(2);
    expect(pushed[0].value).toBeCloseTo(180); // 2026-04-01, JP Morgan alone
    expect(pushed[1].value).toBeCloseTo(227.5); // 2026-05-01, (230 + 225) / 2
  });

  it("subscribes a crosshair handler so the tooltip can report the point's n", () => {
    render(<PriceTargetTimeline history={HISTORY} />);
    expect(chartApi.subscribeCrosshairMove).toHaveBeenCalledTimes(1);
  });
});
