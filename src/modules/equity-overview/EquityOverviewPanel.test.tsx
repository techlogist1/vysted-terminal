import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { SidecarError } from "@/lib/sidecar-client";
import type { AnalystRating, FinancialStatement, Fundamentals, Quote } from "../../../types/data";
import { EquityOverviewPanel } from "./EquityOverviewPanel";
import type { EquityOverview } from "./api";

vi.mock("./api", () => ({
  loadEquityOverview: vi.fn(),
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
    market_cap: 3_000_000_000_000,
    pe_ratio: 31.2,
    forward_pe: 28.4,
    peg_ratio: 2.1,
    price_to_book: 47,
    dividend_yield: 0.0044,
    eps: 6.17,
    beta: 1.25,
    fifty_two_week_high: 220,
    fifty_two_week_low: 160,
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
  it("shows the empty prompt before a symbol is loaded", () => {
    render(<EquityOverviewPanel />);
    expect(screen.getByText(/Enter a symbol to load fundamentals/)).toBeInTheDocument();
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

  it("degrades gracefully when a section is missing", async () => {
    mockLoad.mockResolvedValue(overview({ ratings: null }));
    render(<EquityOverviewPanel />);
    await loadSymbol();

    expect(screen.getByText("Analyst ratings")).toBeInTheDocument();
    expect(screen.getAllByText("Unavailable.").length).toBeGreaterThan(0);
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
