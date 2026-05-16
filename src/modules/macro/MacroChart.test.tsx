import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { MacroSeriesExtended } from "../../../types/macro";

const lineSeries = { setData: vi.fn(), applyOptions: vi.fn() };
const timeScale = { fitContent: vi.fn() };
const priceScale = { applyOptions: vi.fn() };
const chartApi = {
  addSeries: vi.fn(() => lineSeries),
  timeScale: vi.fn(() => timeScale),
  priceScale: vi.fn(() => priceScale),
  remove: vi.fn(),
};
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => chartApi),
  LineSeries: "Line",
}));

import { MacroChart } from "./MacroChart";

const SAMPLE_SERIES: MacroSeriesExtended = {
  series_id: "DGS10",
  title: "10-Year Treasury",
  units: "Percent",
  observations: [
    { date: "2026-05-12T00:00:00Z", value: 4.21 },
    { date: "2026-05-13T00:00:00Z", value: 4.25 },
    { date: "2026-05-14T00:00:00Z", value: null },
  ],
  provider: "fred",
  frequency: "daily",
  last_updated: "2026-05-14T00:00:00Z",
  seasonal_adjustment: "not-adjusted",
  source_url: "https://fred.stlouisfed.org/series/DGS10",
  notes: null,
};

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("MacroChart", () => {
  it("renders the series title and metadata", () => {
    render(<MacroChart series={SAMPLE_SERIES} />);
    expect(screen.getByText("10-Year Treasury")).toBeInTheDocument();
    expect(screen.getByText(/DGS10/)).toBeInTheDocument();
    expect(screen.getByText(/fred/)).toBeInTheDocument();
    expect(screen.getByText(/Percent/)).toBeInTheDocument();
  });

  it("skips null-valued observations when pushing data to the chart", () => {
    render(<MacroChart series={SAMPLE_SERIES} />);
    // 3 observations input, 1 is null → 2 chart points.
    expect(lineSeries.setData).toHaveBeenCalled();
    const pushed = lineSeries.setData.mock.calls[0][0];
    expect(pushed).toHaveLength(2);
    expect(pushed[0].value).toBeCloseTo(4.21);
    expect(pushed[1].value).toBeCloseTo(4.25);
  });

  it("renders the source link when source_url is set", () => {
    render(<MacroChart series={SAMPLE_SERIES} />);
    const link = screen.getByRole("link", { name: "source" });
    expect(link).toHaveAttribute("href", "https://fred.stlouisfed.org/series/DGS10");
  });

  it("toggles the price-scale log mode when the checkbox is clicked", () => {
    render(<MacroChart series={SAMPLE_SERIES} />);
    const toggle = screen.getByTestId("macro-log-toggle") as HTMLInputElement;
    expect(toggle.checked).toBe(false);
    fireEvent.click(toggle);
    expect(toggle.checked).toBe(true);
    // applyOptions called with mode=1 (log).
    const lastCall = priceScale.applyOptions.mock.calls.at(-1);
    expect(lastCall?.[0]).toEqual({ mode: 1 });
  });

  it("reports the observation count", () => {
    render(<MacroChart series={SAMPLE_SERIES} />);
    expect(screen.getByText(/2 observations/)).toBeInTheDocument();
  });
});
