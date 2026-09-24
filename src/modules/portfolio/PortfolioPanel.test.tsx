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

// Keep the real CSV builder; capture the download instead of touching the DOM.
vi.mock("@/lib/csv", async (importActual) => ({
  ...(await importActual<typeof import("@/lib/csv")>()),
  downloadCsv: vi.fn(),
}));

const api = await import("./api");
const mockFetchQuotes = vi.mocked(api.fetchPositionQuotes);
const csvModule = await import("@/lib/csv");
const mockDownloadCsv = vi.mocked(csvModule.downloadCsv);

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
  mockFetchQuotes.mockResolvedValue({ quotes: new Map(), failed: 0 });
  mockDownloadCsv.mockResolvedValue({ path: "/tmp/exports/csv/out.csv", fellBack: false });
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

  it("R15-UI-004: a failed live-quote fetch shows the banner and Retry re-fetches", async () => {
    // Persistent rejection: the initial (empty-holdings) mount fetch and the
    // post-add refetch both reject — the banner is gated on holdings.length,
    // not on which call rejected.
    mockFetchQuotes.mockRejectedValue(new Error("network down"));
    render(<PortfolioPanel />);
    await addHolding("aapl", "10", "150");

    expect(await screen.findByText(/Couldn.t refresh live quotes/)).toBeInTheDocument();
    const retry = screen.getByRole("button", { name: "Retry" });

    mockFetchQuotes.mockResolvedValueOnce({
      quotes: new Map([["AAPL", quote("AAPL", 200)]]),
      failed: 0,
    });
    await act(async () => {
      fireEvent.click(retry);
    });

    expect(screen.queryByText(/Couldn.t refresh live quotes/)).not.toBeInTheDocument();
    // Mount (0 holdings) + post-add refetch + the Retry click.
    expect(mockFetchQuotes).toHaveBeenCalledTimes(3);
  });

  it("R15-UI-005: no live quote resolves -> null total with a note, never a fabricated 0", async () => {
    // Case the fix was not written against (per PLAN.md): one holding priced,
    // one holding whose quote fails — a PARTIAL total, not the all-unresolved
    // case above; the note must name the excluded holding.
    mockFetchQuotes.mockResolvedValue({
      quotes: new Map([["AAPL", quote("AAPL", 200)]]),
      failed: 1,
    });
    render(<PortfolioPanel />);
    await addHolding("aapl", "10", "150");
    await addHolding("zzznotreal", "10", "100");

    expect((await screen.findAllByText("$2,000.00")).length).toBeGreaterThanOrEqual(1);
    const payload = usePanelContextBus.getState().lastEventBySource["portfolio"]?.payload as {
      totalValue: number | null;
      totalValueNote?: string | null;
    };
    expect(payload.totalValue).toBe(2000);
    expect(payload.totalValueNote).toMatch(/ZZZNOTREAL/i);
  });

  it("publishes each holding's id so the agent can name one of two same-symbol lots (R15-AGENT-042)", async () => {
    render(<PortfolioPanel />);
    await addHolding("tcs", "5", "2500");
    await addHolding("tcs", "20", "3900");
    const payload = usePanelContextBus.getState().lastEventBySource["portfolio"]?.payload as {
      holdings: { id?: string; symbol: string; quantity: number }[];
    };
    expect(payload.holdings.map((h) => [h.id, h.quantity])).toEqual(
      activeHoldings().map((h) => [h.id, h.quantity]),
    );
    expect(new Set(payload.holdings.map((h) => h.id)).size).toBe(2);
  });

  it("R15-UI-005: an all-unresolved portfolio publishes totalValue null, never 0, and never fakes concentration/P&L", async () => {
    mockFetchQuotes.mockResolvedValue({ quotes: new Map(), failed: 1 });
    render(<PortfolioPanel />);
    await addHolding("zzznotreal", "10", "100");

    expect(await screen.findByText("— (no live quotes)")).toBeInTheDocument();
    expect(screen.getByText("—", { selector: ".text-charcoal-400" })).toBeInTheDocument();
    expect(screen.queryByText(/Concentration:/)).toBeInTheDocument();
    expect(screen.queryByText("0.0%")).not.toBeInTheDocument();

    const payload = usePanelContextBus.getState().lastEventBySource["portfolio"]?.payload as {
      totalValue: number | null;
      totalValueNote?: string | null;
    };
    expect(payload.totalValue).toBeNull();
    expect(payload.totalValueNote).toBe("no live quotes resolved");
  });

  it("computes P&L and weight from a live quote", async () => {
    mockFetchQuotes.mockResolvedValue({
      quotes: new Map([["AAPL", quote("AAPL", 200)]]),
      failed: 0,
    });
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

  it("R15-UI-090: an eod quote renders a staleness cue on its holding row", async () => {
    mockFetchQuotes.mockResolvedValue({
      quotes: new Map([["AAPL", { ...quote("AAPL", 200), freshness: "eod" as const }]]),
      failed: 0,
    });
    render(<PortfolioPanel />);
    await addHolding("aapl", "10", "150");

    const badge = await screen.findByTestId("staleness-badge");
    expect(badge).toHaveTextContent("EOD");
  });

  it("renders the instrument's currency, not the region's (D57 — the V6 defect)", async () => {
    // Region is pinned US (beforeEach) — an INR-quoted NSE holding must still
    // render ₹ everywhere. V6 live-confirmed ₹1,293 rendered as $1,293.
    mockFetchQuotes.mockResolvedValue({
      quotes: new Map([["RELIANCE.NS", quote("RELIANCE.NS", 1293, "INR")]]),
      failed: 0,
    });
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
    mockFetchQuotes.mockResolvedValue({
      quotes: new Map([
        ["RELIANCE.NS", quote("RELIANCE.NS", 1293, "INR")],
        ["AAPL", quote("AAPL", 120, "USD")],
      ]),
      failed: 0,
    });
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

  it("an edit ends when the portfolio switches; Save then writes nothing silently (R15-UI-034)", async () => {
    usePortfoliosStore.setState({
      portfolios: [
        {
          id: "A",
          name: "A",
          holdings: [
            { id: "h-a", symbol: "RELIANCE", quantity: 10, costBasis: 2500, assetClass: "equity" },
          ],
        },
        {
          id: "B",
          name: "B",
          holdings: [
            { id: "h-b", symbol: "TCS", quantity: 3, costBasis: 3900, assetClass: "equity" },
          ],
        },
      ],
      activeId: "A",
    });
    const before = usePortfoliosStore.getState().portfolios;
    render(<PortfolioPanel />);
    fireEvent.click(screen.getByLabelText("Edit RELIANCE"));
    await act(async () => {
      fireEvent.change(screen.getByLabelText("Active portfolio"), { target: { value: "B" } });
    });
    expect((screen.getByLabelText("Symbol") as HTMLInputElement).value).toBe("");
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "20" } });
    await act(async () => {
      fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
    });
    expect(screen.getByRole("button", { name: /Add/ })).toBeInTheDocument();
    expect(screen.getByText(/are required/)).toBeInTheDocument();
    expect(usePortfoliosStore.getState().portfolios).toEqual(before);
  });

  it("Save on a holding removed mid-edit says nothing was saved (R15-UI-034)", async () => {
    render(<PortfolioPanel />);
    await addHolding("aapl", "10", "150");
    await screen.findByText("AAPL");
    fireEvent.click(screen.getByLabelText("Edit AAPL"));
    // The agent removes the lot while the form is open.
    await act(async () => {
      usePortfoliosStore.getState().removeHolding("default", activeHoldings()[0].id);
    });
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "20" } });
    await act(async () => {
      fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
    });
    expect(
      screen.getByText("That holding is no longer in this portfolio — nothing was saved"),
    ).toBeInTheDocument();
    expect((screen.getByLabelText("Quantity") as HTMLInputElement).value).toBe("20");
    expect(activeHoldings()).toEqual([]);
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

  it("exports the active portfolio to CSV with live-quote P&L", async () => {
    mockFetchQuotes.mockResolvedValue({
      quotes: new Map([["AAPL", quote("AAPL", 200)]]),
      failed: 0,
    });
    render(<PortfolioPanel />);
    await addHolding("aapl", "10", "150");
    await screen.findAllByText("+$500.00 (+33.33%)");

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Export portfolio to CSV"));
    });

    expect(mockDownloadCsv).toHaveBeenCalledTimes(1);
    const [filename, csv] = mockDownloadCsv.mock.calls[0];
    expect(filename).toBe("vysted-portfolio-portfolio.csv");
    const [header, row] = csv.split("\n");
    expect(header).toBe(
      "Symbol,Quantity,Cost basis,Asset class,Currency,Price,Market value,P&L,P&L %,Weight %,Note",
    );
    expect(row.split(",").slice(0, 8)).toEqual([
      "AAPL",
      "10",
      "150",
      "equity",
      "USD",
      "200",
      "2000",
      "500",
    ]);
    expect(row.split(",")[9]).toBe("100.00");
  });

  it("R15-DATA-042: CSV export gets a Currency column and a blank Weight % when mixed", async () => {
    mockFetchQuotes.mockResolvedValue({
      quotes: new Map([
        ["RELIANCE.NS", quote("RELIANCE.NS", 1293, "INR")],
        ["AAPL", quote("AAPL", 120, "USD")],
      ]),
      failed: 0,
    });
    render(<PortfolioPanel />);
    await addHolding("reliance.ns", "50", "1200");
    await addHolding("aapl", "10", "100");
    await screen.findByText(/₹64,650\.00 \+ \$1,200\.00/);

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Export portfolio to CSV"));
    });

    expect(mockDownloadCsv).toHaveBeenCalledTimes(1);
    const [, csv] = mockDownloadCsv.mock.calls[0];
    const lines = csv.split("\n");
    expect(lines[0]).toBe(
      "Symbol,Quantity,Cost basis,Asset class,Currency,Price,Market value,P&L,P&L %,Weight %,Note",
    );
    const relianceRow = lines[1].split(",");
    const aaplRow = lines[2].split(",");
    expect(relianceRow[0]).toBe("RELIANCE.NS");
    expect(relianceRow[4]).toBe("INR");
    expect(aaplRow[0]).toBe("AAPL");
    expect(aaplRow[4]).toBe("USD");
    // Weight % (index 9) is blank — never a cross-currency ratio.
    expect(relianceRow[9]).toBe("");
    expect(aaplRow[9]).toBe("");
  });
});
