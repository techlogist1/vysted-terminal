/**
 * ScreenerResultsTable tests — Phase 6 (lead-completed v0.6.1).
 *
 * Exercises sorting + empty/loading states + the rendered cell formatters.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import type { ScreenerResult } from "../../../types/screener";
import { useScreenerStore } from "@/store/screener";
import { useSettingsStore } from "@/store/settings";

import { ScreenerResultsTable } from "./ScreenerResultsTable";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

const RESULT: ScreenerResult = {
  universe: "sp500",
  evaluated_count: 100,
  skipped_count: 0,
  result_count: 3,
  rows: [
    {
      symbol: "AAPL",
      name: "Apple Inc.",
      sector: "Technology",
      industry: "Consumer Electronics",
      market_cap: 3_000_000_000_000,
      pe_ratio: 18.5,
      price: 192.5,
      change_percent_1d: 1.5,
      volume: 51_000_000,
      matched_criteria: [0, 1, 2],
      currency: "USD",
    },
    {
      symbol: "MSFT",
      name: "Microsoft Corp.",
      sector: "Technology",
      industry: "Software",
      market_cap: 3_200_000_000_000,
      pe_ratio: 19.0,
      price: 420.0,
      change_percent_1d: -0.5,
      volume: 22_000_000,
      matched_criteria: [0, 1, 2],
      currency: "USD",
    },
    {
      symbol: "GOOGL",
      name: "Alphabet Inc.",
      sector: "Technology",
      industry: "Internet Content",
      market_cap: 2_100_000_000_000,
      pe_ratio: 19.5,
      price: 175.0,
      change_percent_1d: 0.3,
      volume: 18_000_000,
      matched_criteria: [0, 1, 2],
      currency: "USD",
    },
  ],
  duration_ms: 320.0,
};

/** An INR row (R11 / D57) — rendered under region US it must still read ₹.
 *  data_basis "snapshot" pins the D52 staleness marker (as of Jun 16, 2026). */
const INR_SNAPSHOT_ROW = {
  symbol: "RELIANCE.NS",
  name: "Reliance Industries",
  sector: "Energy",
  industry: "Oil & Gas",
  market_cap: 17_500_000_000_000,
  pe_ratio: 28.1,
  price: 1293.0,
  change_percent_1d: 0.6,
  volume: 5_400_000,
  matched_criteria: [0],
  currency: "INR",
  data_basis: "snapshot",
  data_as_of: 1_781_611_200, // 2026-06-16T12:00Z (mid-day: "Jun 16" in any test TZ)
};

beforeEach(() => {
  useScreenerStore.getState().__resetForTests();
  // R11 (D57): money cells format in the ROW's currency; the region is only
  // the locale (grouping) + the legacy fallback for rows without a currency.
  // Region is pinned US so grouping is deterministic (en-US) AND so the INR
  // assertions below prove the instrument's currency wins over the region.
  useSettingsStore.setState({ region: "US" });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ScreenerResultsTable", () => {
  it("shows an empty placeholder when there is no result", () => {
    render(<ScreenerResultsTable />);
    expect(screen.getByText(/run the screener/i)).toBeInTheDocument();
  });

  it("renders the rows when a result is present", () => {
    useScreenerStore.setState({ lastResult: RESULT, status: "ready" });
    render(<ScreenerResultsTable />);

    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("MSFT")).toBeInTheDocument();
    expect(screen.getByText("GOOGL")).toBeInTheDocument();
    // Formatted market cap — currency-prefixed + unit-suffixed (single formatter).
    expect(screen.getByText("$3.20T")).toBeInTheDocument();
    expect(screen.getByText("$3.00T")).toBeInTheDocument();
  });

  it("clicking a column header toggles sort direction", () => {
    useScreenerStore.setState({ lastResult: RESULT, status: "ready" });
    render(<ScreenerResultsTable />);

    // Default sort is market_cap desc — MSFT (3.20T) first.
    let firstRow = screen.getAllByRole("row")[1];
    expect(within(firstRow!).getByText("MSFT")).toBeInTheDocument();

    // Click pe_ratio header → desc by P/E → GOOGL (19.5) first.
    fireEvent.click(screen.getByTestId("column-pe_ratio"));
    firstRow = screen.getAllByRole("row")[1];
    expect(within(firstRow!).getByText("GOOGL")).toBeInTheDocument();

    // Click again → asc by P/E → AAPL (18.5) first.
    fireEvent.click(screen.getByTestId("column-pe_ratio"));
    firstRow = screen.getAllByRole("row")[1];
    expect(within(firstRow!).getByText("AAPL")).toBeInTheDocument();
  });

  it("money cells render in the ROW's currency, never the region's (D57 — V6)", () => {
    useScreenerStore.setState({
      lastResult: { ...RESULT, rows: [...RESULT.rows, INR_SNAPSHOT_ROW], result_count: 4 },
      status: "ready",
    });
    render(<ScreenerResultsTable />);

    // USD rows: the price cell is a REAL money format now (was a bare number).
    expect(screen.getByText("$192.50")).toBeInTheDocument();
    // The INR row renders ₹ even under region US — V6 live-confirmed exactly
    // this figure rendering as $1,293.
    expect(screen.getByText("₹1,293.00")).toBeInTheDocument();
    expect(screen.getByText("₹17.5T")).toBeInTheDocument();
  });

  it("a snapshot-basis row carries the quiet staleness marker + as-of (D52)", () => {
    useScreenerStore.setState({
      lastResult: { ...RESULT, rows: [...RESULT.rows, INR_SNAPSHOT_ROW], result_count: 4 },
      status: "ready",
    });
    render(<ScreenerResultsTable />);

    const marker = screen.getByTestId("basis-marker-RELIANCE.NS");
    expect(marker).toHaveTextContent("snap");
    expect(marker.title).toContain("Snapshot basis");
    expect(marker.title).toContain("as of Jun 16");
    // Live rows carry no marker — a snapshot row must never look identical,
    // but a live row must stay unadorned.
    expect(screen.queryByTestId("basis-marker-AAPL")).not.toBeInTheDocument();
  });

  it("a mixed-basis row is marked 'mixed'; live/absent basis renders nothing (D52)", () => {
    const rows = [
      { ...RESULT.rows[0], data_basis: "live" },
      { ...RESULT.rows[1], data_basis: "mixed", data_as_of: 1_781_611_200 },
      RESULT.rows[2], // no basis fields at all — an older payload
    ];
    useScreenerStore.setState({ lastResult: { ...RESULT, rows }, status: "ready" });
    render(<ScreenerResultsTable />);

    expect(screen.queryByTestId("basis-marker-AAPL")).not.toBeInTheDocument();
    const marker = screen.getByTestId("basis-marker-MSFT");
    expect(marker).toHaveTextContent("mixed");
    expect(marker.title).toContain("Mixed basis");
    expect(screen.queryByTestId("basis-marker-GOOGL")).not.toBeInTheDocument();
  });

  it("shows a loading placeholder while status === 'loading'", () => {
    useScreenerStore.setState({ lastResult: null, status: "loading" });
    render(<ScreenerResultsTable />);
    expect(screen.getByText(/running screener/i)).toBeInTheDocument();
  });

  it("renders a friendly message when the result has zero rows", () => {
    useScreenerStore.setState({
      lastResult: { ...RESULT, rows: [], result_count: 0 },
      status: "ready",
    });
    render(<ScreenerResultsTable />);
    expect(screen.getByText(/no rows matched/i)).toBeInTheDocument();
  });
});
