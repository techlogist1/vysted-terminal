import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { usePanelContextBus } from "@/store/panel-context";
import { usePortfoliosStore } from "@/store/portfolios";
import { useSettingsStore } from "@/store/settings";
import type { Quote } from "../../../types/data";
import { PortfolioPanel } from "./PortfolioPanel";

vi.mock("./api", () => ({
  fetchPositionQuotes: vi.fn(),
}));

const api = await import("./api");
const mockFetchQuotes = vi.mocked(api.fetchPositionQuotes);

function quote(symbol: string, price: number, currency = "USD"): Quote {
  return {
    symbol,
    price,
    change: 0,
    change_percent: 0,
    volume: null,
    currency,
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
  usePanelContextBus.setState({ lastEventBySource: {}, focusedSource: null, updatedAt: 0 });
  // R11 (D57): money renders in the QUOTE's currency — the region is only the
  // locale (grouping) + the fallback when no quote resolved. Region is pinned
  // US here so number GROUPING is deterministic (en-US); the currency
  // assertions below prove the instrument's symbol wins over the region
  // (an INR quote renders ₹ under region US).
  useSettingsStore.setState({ region: "US" });
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
    // Single-currency portfolio: the panel publishes a REAL numeric total.
    const payload = usePanelContextBus.getState().lastEventBySource["portfolio"]?.payload as {
      totalValue: number | null;
      totalValueNote?: string | null;
    };
    expect(payload.totalValue).toBe(2000);
    expect(payload.totalValueNote ?? null).toBeNull();
  });

  it("renders the instrument's currency, not the region's (D57 — the V6 defect)", async () => {
    // Region is pinned US (beforeEach) — an INR-quoted NSE holding must still
    // render ₹ everywhere. V6 live-confirmed ₹1,293 rendered as $1,293.
    mockFetchQuotes.mockResolvedValue(
      new Map([["RELIANCE.NS", quote("RELIANCE.NS", 1293, "INR")]]),
    );
    render(<PortfolioPanel />);
    await addHolding("reliance.ns", "50", "1200");

    // Price cell: the quote's ₹, never the region's $.
    expect(await screen.findByText("₹1,293.00")).toBeInTheDocument();
    // Cost basis renders in the quote's currency too (positions are entered in
    // the listing currency).
    expect(screen.getByText("₹1,200.00")).toBeInTheDocument();
    // P&L row + summary strip: +₹4,650.00 (+7.75%).
    expect((await screen.findAllByText(/\+₹4,650\.00/)).length).toBeGreaterThanOrEqual(2);
    // No dollar sign anywhere — the region default must not leak onto an INR
    // instrument.
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument();
  });

  it("mixed currencies: per-currency subtotals, null published total (D57)", async () => {
    mockFetchQuotes.mockResolvedValue(
      new Map([
        ["RELIANCE.NS", quote("RELIANCE.NS", 1293, "INR")],
        ["AAPL", quote("AAPL", 120, "USD")],
      ]),
    );
    render(<PortfolioPanel />);
    await addHolding("reliance.ns", "50", "1200");
    await addHolding("aapl", "10", "100");

    // The summary strip renders ONE subtotal PER currency — never a fabricated
    // cross-currency sum (₹64,650 + $1,200 is not 65,850 of anything).
    expect(await screen.findByText(/₹64,650\.00 \+ \$1,200\.00/)).toBeInTheDocument();
    // Per-currency P&L: +₹4,650.00 (+7.75%) and +$200.00 (+20.00%).
    expect(screen.getAllByText(/\+₹4,650\.00 \(\+7\.75%\)/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/\+\$200\.00 \(\+20\.00%\)/).length).toBeGreaterThanOrEqual(1);
    // Concentration (a share of the summed value) yields to the honest note.
    expect(screen.getByText(/mixed currencies — totals per currency/)).toBeInTheDocument();
    expect(screen.queryByText(/Concentration:/)).not.toBeInTheDocument();

    // The published agent context carries totalValue: null + a stated reason —
    // the copilot must never be handed a cross-currency sum.
    const payload = usePanelContextBus.getState().lastEventBySource["portfolio"]?.payload as {
      totalValue: number | null;
      totalValueNote?: string | null;
    };
    expect(payload.totalValue).toBeNull();
    expect(payload.totalValueNote).toMatch(/INR/);
    expect(payload.totalValueNote).toMatch(/USD/);
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
