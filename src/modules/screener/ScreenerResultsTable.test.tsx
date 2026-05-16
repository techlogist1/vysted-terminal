/**
 * ScreenerResultsTable tests — Phase 6 (lead-completed v0.6.1).
 *
 * Exercises sorting + empty/loading states + the rendered cell formatters.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import type { ScreenerResult } from "../../../types/screener";
import { useScreenerStore } from "@/store/screener";

import { ScreenerResultsTable } from "./ScreenerResultsTable";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

const RESULT: ScreenerResult = {
  universe: "sp500",
  evaluated_count: 100,
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
    },
  ],
  duration_ms: 320.0,
};

beforeEach(() => {
  useScreenerStore.getState().__resetForTests();
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
    // Formatted market cap
    expect(screen.getByText("3.20T")).toBeInTheDocument();
    expect(screen.getByText("3.00T")).toBeInTheDocument();
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
