import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { SidecarError } from "@/lib/sidecar-client";
import type { AnalystRating, FinancialStatement, Fundamentals, Quote } from "../../../types/data";
import { EquityOverviewPanel } from "./EquityOverviewPanel";
import type { EquityOverview } from "./api";

vi.mock("./api", () => ({
  loadEquityOverview: vi.fn(),
  autocompleteSymbols: vi.fn(() => Promise.resolve([])),
}));

const { loadEquityOverview } = await import("./api");
const mockLoad = vi.mocked(loadEquityOverview);

function quote(): Quote {
  return {
    symbol: "AAPL",
    price: 192.5,
    change: 2.5,
    change_percent: 1.31,
    volume: 51_000_000,
    currency: "USD",
    market_state: null,
    timestamp: "2026-05-15T00:00:00Z",
    provider: "yfinance",
  };
}

function fundamentals(): Fundamentals {
  return {
    symbol: "AAPL",
    name: "Apple Inc.",
    sector: "Technology",
    industry: "Consumer Electronics",
    currency: "USD",
    market_cap: 3_000_000_000_000,
    pe_ratio: 31.2,
    forward_pe: 28.4,
    peg_ratio: 2.1,
    price_to_book: 47,
    price_to_sales: 8.1,
    ev_to_ebitda: 24,
    book_value: 4.4,
    dividend_yield: 0.0044,
    dividend_per_share: 1.0,
    eps: 6.17,
    beta: 1.25,
    fifty_two_week_high: 220,
    fifty_two_week_low: 160,
    fifty_two_week_change: 0.18,
    roe: 1.5,
    roa: 0.28,
    gross_margin: 0.46,
    operating_margin: 0.3,
    profit_margin: 0.25,
    debt_to_equity: 1.5,
    current_ratio: 0.95,
    quick_ratio: 0.85,
    revenue_ttm: 400_000_000_000,
    net_income_ttm: 100_000_000_000,
    free_cash_flow: 95_000_000_000,
    shares_outstanding: 15_500_000_000,
    revenue_growth: 0.05,
    earnings_growth: 0.11,
    held_percent_insiders: 0.0007,
    held_percent_institutions: 0.61,
    provider: "yfinance",
  };
}

function statement(): FinancialStatement {
  return {
    symbol: "AAPL",
    periods: ["2025", "2024"],
    lines: [
      { label: "Total Revenue", values: { "2025": 400_000, "2024": 380_000 } },
      { label: "Net Income", values: { "2025": 100_000, "2024": 95_000 } },
    ],
    provider: "yfinance",
  };
}

function ratings(): AnalystRating {
  return {
    symbol: "AAPL",
    consensus: "buy",
    target_mean: 225,
    target_high: 260,
    target_low: 170,
    strong_buy: 12,
    buy: 20,
    hold: 8,
    sell: 1,
    strong_sell: 0,
    provider: "yfinance",
  };
}

function overview(overrides: Partial<EquityOverview> = {}): EquityOverview {
  return {
    symbol: "AAPL",
    quote: quote(),
    fundamentals: fundamentals(),
    income: statement(),
    balance: statement(),
    cashFlow: statement(),
    ratings: ratings(),
    allFailed: false,
    ...overrides,
  };
}

async function loadSymbol(value = "aapl"): Promise<void> {
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value } });
  await act(async () => {
    fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("EquityOverviewPanel", () => {
  it("shows a composed empty state with quick-load chips before a symbol is loaded", () => {
    render(<EquityOverviewPanel />);
    // The shared composed EmptyState — never instructional copy as content.
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state-headline").textContent).toBe("Equity overview");
    expect(
      screen.getByText(/Screener-grade fundamentals, statements, and ratings/),
    ).toBeInTheDocument();
    const chips = screen.getByTestId("quick-load-chips");
    for (const t of ["AAPL", "RELIANCE", "NVDA"]) {
      expect(chips.textContent).toContain(t);
    }
  });

  it("a quick-load chip loads its symbol", async () => {
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "AAPL" }));
    });
    expect(mockLoad).toHaveBeenCalledWith("AAPL");
    expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument();
  });

  it("loads and displays fundamentals, ratios, statements, and ratings", async () => {
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);
    await loadSymbol();

    expect(mockLoad).toHaveBeenCalledWith("AAPL");
    expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument();
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
    // Valuation ratio.
    expect(screen.getByText("31.20")).toBeInTheDocument();
    // Analyst consensus.
    expect(screen.getByText("buy")).toBeInTheDocument();
    // Statement sections + line items.
    expect(screen.getByText("Income statement")).toBeInTheDocument();
    expect(screen.getByText("Balance sheet")).toBeInTheDocument();
    expect(screen.getByText("Cash flow")).toBeInTheDocument();
    expect(screen.getAllByText("Total Revenue").length).toBeGreaterThan(0);
  });

  it("formats every magnitude with a unit (checklist #1: the missing-B fix)", async () => {
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);
    await loadSymbol();

    // Currency magnitudes carry a unit suffix — never a bare overflow.
    expect(screen.getByText("$3.00T")).toBeInTheDocument(); // market cap
    expect(screen.getByText("$400B")).toBeInTheDocument(); // revenue (TTM)
    expect(screen.getByText("$95.0B")).toBeInTheDocument(); // free cash flow
    // Bare share count is B-suffixed (the "14.698" bug), not a raw integer.
    expect(screen.getByText("15.50B")).toBeInTheDocument();
    // Curated labels — no snake_case ever renders.
    expect(screen.queryByText(/free_cash_flow|shares_outstanding/)).toBeNull();
  });

  it("degrades gracefully when a section is missing", async () => {
    mockLoad.mockResolvedValue(overview({ ratings: null }));
    render(<EquityOverviewPanel />);
    await loadSymbol();

    expect(screen.getByText("Analyst ratings")).toBeInTheDocument();
    // The failed section renders a composed dense empty state, never bare prose.
    expect(screen.getByText("Ratings unavailable")).toBeInTheDocument();
  });

  it("renders analyst ratings as a labelled metric strip", async () => {
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);
    await loadSymbol();

    const strip = screen.getByTestId("ratings-strip");
    expect(strip.textContent).toContain("Consensus");
    expect(strip.textContent).toContain("buy");
    expect(strip.textContent).toContain("Target mean");
    expect(strip.textContent).toContain("SB · B · H · S · SS");
    expect(strip.textContent).toContain("12 · 20 · 8 · 1 · 0");
  });

  it("shows an error when every section fails", async () => {
    mockLoad.mockResolvedValue(
      overview({
        quote: null,
        fundamentals: null,
        income: null,
        balance: null,
        cashFlow: null,
        ratings: null,
        allFailed: true,
      }),
    );
    render(<EquityOverviewPanel />);
    await loadSymbol("zzzz");

    expect(screen.getByText("No data available for ZZZZ")).toBeInTheDocument();
  });

  it("surfaces a SidecarError thrown by the loader", async () => {
    mockLoad.mockRejectedValueOnce(new SidecarError(502, "upstream down"));
    render(<EquityOverviewPanel />);
    await loadSymbol();

    expect(screen.getByText("upstream down")).toBeInTheDocument();
  });
});
