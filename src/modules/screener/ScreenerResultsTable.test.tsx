/**
 * ScreenerResultsTable tests — Phase 6 (lead-completed v0.6.1).
 *
 * Exercises sorting + empty/loading states + the rendered cell formatters.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import type { ScreenerResult, ScreenerResultRow } from "../../../types/screener";
import { useScreenerStore } from "@/store/screener";
import { saveTextArtifact } from "@/lib/export-artifact";
import { useSettingsStore } from "@/store/settings";

import { ScreenerResultsTable } from "./ScreenerResultsTable";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));
vi.mock("@/lib/export-artifact", () => ({
  saveTextArtifact: vi.fn(async () => ({ path: "/data/exports/csv/out.csv", fellBack: false })),
}));

/**
 * R15-UI-006: a numeric-column header click now re-runs the sort SERVER-SIDE
 * (`runScreener`) rather than re-sorting the already-served page — the real
 * fix, since a client-only re-sort can't surface rows the `limit` cut before
 * they were ever seen. These tests stub `runScreener` to mimic the server's
 * sort (mirrors `apply_criteria`'s currency-grouped, null-last ordering)
 * instead of exercising a real network round trip.
 */
function serverSortedRows(rows: ScreenerResultRow[]): ScreenerResultRow[] {
  const { sortBy, sortDir } = useScreenerStore.getState();
  const dir = sortDir === "asc" ? 1 : -1;
  const moneyKeys = new Set(["market_cap", "price"]);
  return [...rows].sort((a, b) => {
    if (moneyKeys.has(sortBy) && a.currency !== b.currency) {
      const ac = a.currency ?? "";
      const bc = b.currency ?? "";
      return ac < bc ? -1 : ac > bc ? 1 : 0;
    }
    const av = (a as unknown as Record<string, number | null>)[sortBy];
    const bv = (b as unknown as Record<string, number | null>)[sortBy];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    return (av - bv) * dir;
  });
}

/** Wires `runScreener` so a header-click-triggered call resolves with `rows`
 *  re-sorted by whatever `sortBy`/`sortDir` the click just set. */
function stubServerSort(rows: ScreenerResultRow[]): void {
  useScreenerStore.setState({
    runScreener: vi.fn(async () => {
      const next = { ...RESULT, rows: serverSortedRows(rows) };
      useScreenerStore.setState({ lastResult: next, status: "ready" });
      return next;
    }),
  });
}

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
  currency: "INR",
  data_basis: "snapshot",
  data_as_of: 1_781_611_200, // 2026-06-16T12:00Z (mid-day: "Jun 16" in any test TZ)
};

// `__resetForTests` only resets DATA fields — `runScreener` is an action the
// store never rebuilds, so a test that stubs it (`stubServerSort`) must be
// restored, or the stub leaks into every later test in this file.
const ORIGINAL_RUN_SCREENER = useScreenerStore.getState().runScreener;

beforeEach(() => {
  useScreenerStore.getState().__resetForTests();
  useScreenerStore.setState({ runScreener: ORIGINAL_RUN_SCREENER });
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

  it("R15-UI-009: Export CSV saves through the Rust text writer, not a Blob download", () => {
    useScreenerStore.setState({ lastResult: RESULT, status: "ready" });
    render(<ScreenerResultsTable />);
    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));
    expect(saveTextArtifact).toHaveBeenCalledWith(
      "csv",
      "vysted-screener-sp500.csv",
      expect.stringContaining("AAPL"),
    );
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

  it("clicking a column header re-runs the sort server-side", () => {
    stubServerSort(RESULT.rows);
    useScreenerStore.setState({
      lastResult: { ...RESULT, rows: serverSortedRows(RESULT.rows) },
      status: "ready",
    });
    render(<ScreenerResultsTable />);

    // Default sort is market_cap desc — MSFT (3.20T) first.
    let firstRow = screen.getAllByRole("row")[1];
    expect(within(firstRow!).getByText("MSFT")).toBeInTheDocument();

    // Click pe_ratio header → desc by P/E → GOOGL (19.5) first. R15-UI-006:
    // this is a real `runScreener()` call (stubbed above), not a client
    // re-sort of the page already served — the stub's async body has no
    // `await`, so its state write lands synchronously within this call.
    fireEvent.click(within(screen.getByTestId("column-pe_ratio")).getByRole("button"));
    expect(useScreenerStore.getState().sortBy).toBe("pe_ratio");
    expect(useScreenerStore.getState().sortDir).toBe("desc");
    firstRow = screen.getAllByRole("row")[1];
    expect(within(firstRow!).getByText("GOOGL")).toBeInTheDocument();

    // Click again → asc by P/E → AAPL (18.5) first.
    fireEvent.click(within(screen.getByTestId("column-pe_ratio")).getByRole("button"));
    expect(useScreenerStore.getState().sortDir).toBe("asc");
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

  it("R15-DATA-043: money-column sort groups by currency, never interleaved", () => {
    // TCS's raw INR market cap (2.5T) sits BETWEEN two USD rows' raw
    // magnitudes (GOOGL 2.1T, AAPL 3.0T) — a naive cross-currency sort would
    // interleave it between them. The grouped sort keeps every INR row
    // contiguous, ahead of every USD row. displaySymbol strips ".NS", so the
    // rendered Symbol cells read "RELIANCE" / "TCS", not the raw ticker.
    const RELIANCE_NS = {
      symbol: "RELIANCE.NS",
      name: "Reliance Industries",
      sector: "Energy",
      industry: "Oil & Gas",
      market_cap: 17_500_000_000_000,
      pe_ratio: 28.1,
      price: 1293.0,
      change_percent_1d: 0.6,
      volume: 5_400_000,
      currency: "INR",
    };
    const TCS_NS = {
      symbol: "TCS.NS",
      name: "Tata Consultancy Services",
      sector: "Technology",
      industry: "IT Services",
      market_cap: 2_500_000_000_000,
      pe_ratio: 27.0,
      price: 3800.0,
      change_percent_1d: 0.2,
      volume: 1_200_000,
      currency: "INR",
    };
    const combined = [...RESULT.rows, RELIANCE_NS, TCS_NS];
    stubServerSort(combined);
    useScreenerStore.setState({
      lastResult: {
        ...RESULT,
        rows: serverSortedRows(combined),
        result_count: 5,
      },
      status: "ready",
    });
    render(<ScreenerResultsTable />);

    // Default sort is market_cap desc.
    let symbolOrder = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[0]!.textContent);
    expect(symbolOrder).toEqual(["RELIANCE", "TCS", "MSFT", "AAPL", "GOOGL"]);

    // Click the Price header — the same currency grouping must hold there.
    // R15-UI-006: a real (stubbed) `runScreener()` call, not a client re-sort.
    fireEvent.click(within(screen.getByTestId("column-price")).getByRole("button"));
    symbolOrder = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[0]!.textContent);
    const inrIndices = symbolOrder
      .map((s, i) => [s, i] as const)
      .filter(([s]) => s === "RELIANCE" || s === "TCS")
      .map(([, i]) => i);
    // The two INR rows stay adjacent — never split by a USD row.
    expect(inrIndices[1]).toBe(inrIndices[0]! + 1);
  });

  it("renders a friendly message when the result has zero rows", () => {
    useScreenerStore.setState({
      lastResult: { ...RESULT, rows: [], result_count: 0 },
      status: "ready",
    });
    render(<ScreenerResultsTable />);
    expect(screen.getByText(/no rows matched/i)).toBeInTheDocument();
  });

  it("R15-UI-055: a run that evaluated nothing says so instead of blaming the filters", () => {
    useScreenerStore.setState({
      lastResult: {
        ...RESULT,
        rows: [],
        result_count: 0,
        evaluated_count: 0,
        skipped_count: 506,
        partial: true,
        throttled: true,
      },
      status: "ready",
    });
    render(<ScreenerResultsTable />);
    expect(screen.getByText("Nothing could be screened")).toBeInTheDocument();
    expect(screen.getByText(/data provider is throttled; retry in a moment/)).toBeInTheDocument();
    expect(screen.queryByText(/loosen a threshold/i)).not.toBeInTheDocument();
  });
});
