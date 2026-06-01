import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { usePortfoliosStore } from "@/store/portfolios";
import type { Quote } from "../../../types/data";
import { PortfolioPanel } from "./PortfolioPanel";

vi.mock("./api", () => ({
  fetchPositionQuotes: vi.fn(),
}));

const api = await import("./api");
const mockFetchQuotes = vi.mocked(api.fetchPositionQuotes);

function quote(symbol: string, price: number): Quote {
  return {
    symbol,
    price,
    change: 0,
    change_percent: 0,
    volume: null,
    currency: "USD",
    market_state: null,
    timestamp: "2026-05-15T00:00:00Z",
    provider: "yfinance",
  };
}

function resetStore() {
  usePortfoliosStore.setState({
    portfolios: [{ id: "default", name: "Portfolio", holdings: [] }],
    activeId: "default",
  });
}

function activeHoldings() {
  const state = usePortfoliosStore.getState();
  return state.portfolios.find((p) => p.id === state.activeId)?.holdings ?? [];
}

async function addHolding(symbol: string, quantity: string, costBasis: string) {
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: symbol } });
  fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: quantity } });
  fireEvent.change(screen.getByLabelText("Cost basis"), { target: { value: costBasis } });
  await act(async () => {
    fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  resetStore();
  mockFetchQuotes.mockResolvedValue(new Map());
});

afterEach(() => {
  cleanup();
});

describe("PortfolioPanel", () => {
  it("shows a real empty state for a fresh empty portfolio (no fake data)", () => {
    render(<PortfolioPanel />);
    expect(screen.getByText("This portfolio is empty")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add your first holding/i })).toBeInTheDocument();
    // No fabricated value anywhere.
    expect(screen.queryByText(/107\.69/)).not.toBeInTheDocument();
  });

  it("adds a manually entered holding to the active portfolio", async () => {
    render(<PortfolioPanel />);
    await addHolding("nvda", "5", "900");

    expect(await screen.findByText("NVDA")).toBeInTheDocument();
    const holdings = activeHoldings();
    expect(holdings).toHaveLength(1);
    expect(holdings[0]).toMatchObject({
      symbol: "NVDA",
      quantity: 5,
      costBasis: 900,
      assetClass: "equity",
    });
  });

  it("computes P&L and weight from a live quote", async () => {
    mockFetchQuotes.mockResolvedValue(new Map([["AAPL", quote("AAPL", 200)]]));
    render(<PortfolioPanel />);
    await addHolding("aapl", "10", "150");

    // 10 shares, cost 150 → cost 1500; price 200 → mkt 2000; P&L +500 (+33.33%).
    expect((await screen.findAllByText("+$500.00 (+33.33%)")).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("100.0%").length).toBeGreaterThanOrEqual(1);
  });

  it("edits a holding through the row control", async () => {
    render(<PortfolioPanel />);
    await addHolding("aapl", "10", "150");
    await screen.findByText("AAPL");

    fireEvent.click(screen.getByLabelText("Edit AAPL"));
    expect((screen.getByLabelText("Symbol") as HTMLInputElement).value).toBe("AAPL");
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "20" } });
    await act(async () => {
      fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
    });

    expect(activeHoldings()[0].quantity).toBe(20);
  });

  it("deletes a holding through the row control", async () => {
    render(<PortfolioPanel />);
    await addHolding("aapl", "10", "150");
    await screen.findByText("AAPL");

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Delete AAPL"));
    });
    expect(activeHoldings()).toHaveLength(0);
    expect(screen.getByText("This portfolio is empty")).toBeInTheDocument();
  });

  it("validates required fields", async () => {
    render(<PortfolioPanel />);
    await act(async () => {
      fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
    });
    expect(screen.getByText("Symbol, quantity, and cost basis are required")).toBeInTheDocument();
    expect(activeHoldings()).toHaveLength(0);
  });

  it("creates and switches to a new named portfolio", async () => {
    render(<PortfolioPanel />);
    fireEvent.click(screen.getByLabelText("New portfolio"));
    fireEvent.change(screen.getByLabelText("New portfolio name"), { target: { value: "Crypto" } });
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Confirm"));
    });

    const state = usePortfoliosStore.getState();
    expect(state.portfolios).toHaveLength(2);
    const active = state.portfolios.find((p) => p.id === state.activeId);
    expect(active?.name).toBe("Crypto");
    expect(active?.holdings).toHaveLength(0);
  });

  it("renames the active portfolio", async () => {
    render(<PortfolioPanel />);
    fireEvent.click(screen.getByLabelText("Rename portfolio"));
    fireEvent.change(screen.getByLabelText("Rename portfolio"), { target: { value: "Long-term" } });
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Confirm"));
    });
    expect(usePortfoliosStore.getState().portfolios[0].name).toBe("Long-term");
  });

  it("never drops below one portfolio when deleting the last", async () => {
    render(<PortfolioPanel />);
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Delete portfolio"));
    });
    expect(usePortfoliosStore.getState().portfolios).toHaveLength(1);
  });
});
