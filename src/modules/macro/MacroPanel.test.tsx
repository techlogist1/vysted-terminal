import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { MacroCatalog, MacroSeriesExtended } from "../../../types/macro";

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

vi.mock("@/lib/sidecar-client", () => ({
  SidecarError: class extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

import { useMacroStore } from "@/store/macro";

import { MacroPanel } from "./MacroPanel";

const SAMPLE_SERIES: MacroSeriesExtended = {
  series_id: "DGS10",
  title: "10-Year Treasury",
  units: "Percent",
  observations: [{ date: "2026-05-14T00:00:00Z", value: 4.25 }],
  provider: "fred",
  frequency: "daily",
  last_updated: null,
  seasonal_adjustment: null,
  source_url: null,
  notes: null,
};

const SAMPLE_CATALOG: MacroCatalog = {
  provider: "fred",
  entries: [
    {
      provider: "fred",
      series_id: "DGS10",
      title: "10-Year Treasury",
      category: "Interest Rates",
      frequency: "daily",
      units: "Percent",
    },
  ],
};

beforeEach(() => {
  useMacroStore.getState().reset();
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("MacroPanel", () => {
  it("mounts and triggers a series load + catalog load", async () => {
    // Two calls on mount: /macro/DGS10?provider=fred (loadSeries), and the
    // picker's /macro/catalog?provider=fred. Order isn't strictly defined.
    vi.mocked(sidecarGet).mockImplementation(async (path: string) => {
      if (path === "/macro/DGS10") return SAMPLE_SERIES;
      if (path === "/macro/catalog") return SAMPLE_CATALOG;
      return null;
    });
    render(<MacroPanel />);
    await waitFor(() =>
      expect(sidecarGet).toHaveBeenCalledWith("/macro/DGS10", { provider: "fred" }),
    );
    await waitFor(() =>
      expect(sidecarGet).toHaveBeenCalledWith("/macro/catalog", { provider: "fred" }),
    );
  });

  it("renders the loaded series in the chart once data arrives", async () => {
    vi.mocked(sidecarGet).mockImplementation(async (path: string) => {
      if (path === "/macro/DGS10") return SAMPLE_SERIES;
      if (path === "/macro/catalog") return SAMPLE_CATALOG;
      return null;
    });
    render(<MacroPanel />);
    await waitFor(() => expect(screen.getAllByText("10-Year Treasury").length).toBeGreaterThan(0));
    expect(screen.getByTestId("macro-chart-canvas")).toBeInTheDocument();
  });

  it("shows an error state when the series load fails", async () => {
    vi.mocked(sidecarGet).mockImplementation(async (path: string) => {
      if (path === "/macro/DGS10") throw new Error("FRED is down");
      if (path === "/macro/catalog") return SAMPLE_CATALOG;
      return null;
    });
    render(<MacroPanel />);
    await waitFor(() => expect(screen.getByTestId("macro-error")).toBeInTheDocument());
    expect(screen.getByText(/FRED is down/)).toBeInTheDocument();
  });
});
