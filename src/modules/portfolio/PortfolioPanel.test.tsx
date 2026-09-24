import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { usePanelContextBus } from "@/store/panel-context";
import { usePortfoliosStore } from "@/store/portfolios";
import { useSettingsStore } from "@/store/settings";
import type { Quote } from "../../../types/data";
import { PortfolioPanel } from "./PortfolioPanel";

vi.mock("./api", () => ({
  fetchPositionQuotes: vi.fn(),
  fetchDailyCloses: vi.fn(),
  benchmarkSymbolForCurrency: vi.fn(() => null),
}));

// Keep the real CSV builder; capture the download instead of touching the DOM.
vi.mock("@/lib/csv", async (importActual) => ({
  ...(await importActual<typeof import("@/lib/csv")>()),
  downloadCsv: vi.fn(),
}));

const api = await import("./api");
const mockFetchQuotes = vi.mocked(api.fetchPositionQuotes);
const mockFetchDailyCloses = vi.mocked(api.fetchDailyCloses);
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
  fireEvent.change(screen.getByLabelText("Avg cost / share"), { target: { value: costBasis } });
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
  // No history by default — existing tests that don't exercise the Risk
  // section see it settle to "insufficient" rather than hang.
  mockFetchDailyCloses.mockResolvedValue(null);
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

  it("the cost input and column say per share (R15-UI-037)", async () => {
    render(<PortfolioPanel />);
    expect(screen.getByText("Avg cost / share")).toBeInTheDocument();
    expect(screen.getByLabelText("Avg cost / share")).toHaveAttribute("placeholder", "per share");
    expect(screen.queryByText("Cost basis")).not.toBeInTheDocument();
    await addHolding("aapl", "10", "150");
    expect(screen.getByRole("columnheader", { name: "Avg cost" })).toBeInTheDocument();
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

  it("refreshes quotes on the Watchlist interval and dates the totals by the oldest quote (R15-UI-036)", async () => {
    vi.useFakeTimers();
    try {
      mockFetchQuotes.mockResolvedValue({
        quotes: new Map([
          ["AAPL", { ...quote("AAPL", 200), timestamp: "2026-05-15T14:30:00Z" }],
          ["MSFT", { ...quote("MSFT", 400), timestamp: "2026-05-15T14:00:00Z" }],
        ]),
        failed: 0,
      });
      render(<PortfolioPanel />);
      await addHolding("aapl", "10", "150");
      await addHolding("msft", "1", "300");
      await act(async () => {}); // settle the quote fetch
      expect(screen.getByTestId("portfolio-totals-as-of").title).toBe(
        "Oldest quote in these totals: 2026-05-15T14:00:00Z",
      );
      const calls = mockFetchQuotes.mock.calls.length;
      await act(async () => {
        vi.advanceTimersByTime(5_000);
      });
      expect(mockFetchQuotes.mock.calls.length).toBe(calls + 1);
    } finally {
      vi.useRealTimers();
    }
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

  it("prices a BTC/USDT lot as crypto and shows its money in USDT, never ₹ (R15-DATA-081)", async () => {
    useSettingsStore.setState({ region: "IN" });
    usePortfoliosStore.setState({
      portfolios: [
        {
          id: "default",
          name: "Portfolio",
          holdings: [
            { id: "h1", symbol: "BTC/USDT", quantity: 0.5, costBasis: 60000, assetClass: "crypto" },
          ],
        },
      ],
      activeId: "default",
    });
    mockFetchQuotes.mockResolvedValue({
      quotes: new Map([["BTC/USDT", quote("BTC/USDT", 67000, "USDT")]]),
      failed: 0,
    });
    render(<PortfolioPanel />);

    expect(await screen.findByText("67,000.00 USDT")).toBeInTheDocument();
    expect(screen.getByText("60,000.00 USDT")).toBeInTheDocument();
    expect(mockFetchQuotes).toHaveBeenCalledWith([{ symbol: "BTC/USDT", assetClass: "crypto" }]);
    expect(screen.queryByText(/₹/)).not.toBeInTheDocument();
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

  it("Delete works in a portfolio switched to after mount (R15-UI-035)", async () => {
    render(<PortfolioPanel />);
    await addHolding("reliance.ns", "1", "2500");
    await act(async () => {
      usePortfoliosStore.getState().createPortfolio("Second");
    });
    await addHolding("tcs.ns", "2", "3900");
    await screen.findByText("TCS.NS");
    // Two-step confirm (R15-UI-018): same button, second click acts — each
    // click needs its own act() flush so the second click's handler closure
    // sees the just-armed state.
    const deleteButton = screen.getByLabelText("Delete TCS.NS");
    await act(async () => {
      fireEvent.click(deleteButton);
    });
    await act(async () => {
      fireEvent.click(deleteButton);
    });
    expect(activeHoldings()).toEqual([]);
    expect(usePortfoliosStore.getState().portfolios[0].holdings.map((h) => h.symbol)).toEqual([
      "RELIANCE.NS",
    ]);
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

    // Two-step confirm (R15-UI-018): a single click only arms it.
    const deleteButton = screen.getByLabelText("Delete AAPL");
    await act(async () => {
      fireEvent.click(deleteButton);
    });
    expect(activeHoldings()).toHaveLength(1);
    await act(async () => {
      fireEvent.click(deleteButton);
    });
    expect(activeHoldings()).toHaveLength(0);
    expect(screen.getByText("This portfolio is empty")).toBeInTheDocument();
  });

  it("validates required fields", async () => {
    render(<PortfolioPanel />);
    await act(async () => {
      fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
    });
    expect(
      screen.getByText("Symbol, quantity, and avg cost per share are required"),
    ).toBeInTheDocument();
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
    const deleteButton = screen.getByLabelText("Delete portfolio");
    await act(async () => {
      fireEvent.click(deleteButton);
    });
    await act(async () => {
      fireEvent.click(deleteButton);
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

  describe("risk section (R15-CODE-PLATFORM-023)", () => {
    /** `n` daily closes from `start`, ascending, with enough day-to-day
     *  variance for a non-zero stdev (never a flat, degenerate series). */
    function closesFrom(start: string, n: number, base: number): Map<string, number> {
      const closes = new Map<string, number>();
      const date = new Date(`${start}T00:00:00Z`);
      for (let i = 0; i < n; i++) {
        closes.set(date.toISOString().slice(0, 10), base + (i % 2 === 0 ? i * 0.3 : -i * 0.1));
        date.setUTCDate(date.getUTCDate() + 1);
      }
      return closes;
    }

    it("shows a loading state while daily closes are in flight", async () => {
      mockFetchQuotes.mockResolvedValue({
        quotes: new Map([["AAPL", quote("AAPL", 200)]]),
        failed: 0,
      });
      let resolveCloses: (v: Map<string, number> | null) => void = () => {};
      mockFetchDailyCloses.mockReturnValue(
        new Promise((resolve) => {
          resolveCloses = resolve;
        }),
      );
      render(<PortfolioPanel />);
      await addHolding("aapl", "10", "150");

      expect(await screen.findByText("Computing risk metrics…")).toBeInTheDocument();
      await act(async () => {
        resolveCloses(null);
      });
    });

    it("shows an insufficient-history message under MIN_RISK_HISTORY_DAYS", async () => {
      mockFetchQuotes.mockResolvedValue({
        quotes: new Map([["AAPL", quote("AAPL", 200)]]),
        failed: 0,
      });
      mockFetchDailyCloses.mockResolvedValue(closesFrom("2026-01-01", 10, 100));
      render(<PortfolioPanel />);
      await addHolding("aapl", "10", "150");

      expect(
        await screen.findByText(/Not enough price history yet \(needs 30\+ overlapping days\)/),
      ).toBeInTheDocument();
    });

    it("renders Sharpe/Sortino/maxDD/Calmar/VaR for a bucket with enough history", async () => {
      mockFetchQuotes.mockResolvedValue({
        quotes: new Map([["AAPL", quote("AAPL", 200)]]),
        failed: 0,
      });
      mockFetchDailyCloses.mockResolvedValue(closesFrom("2026-01-01", 40, 100));
      render(<PortfolioPanel />);
      await addHolding("aapl", "10", "150");

      expect(await screen.findByText(/Sharpe:/)).toBeInTheDocument();
      expect(screen.getByText(/Sortino:/)).toBeInTheDocument();
      expect(screen.getByText(/Max DD:/)).toBeInTheDocument();
      expect(screen.getByText(/Calmar:/)).toBeInTheDocument();
      expect(screen.getByText(/VaR 95%/)).toBeInTheDocument();
      expect(screen.getByText("39d history")).toBeInTheDocument();
    });

    it("renders one bucket per currency and a per-symbol correlation matrix", async () => {
      mockFetchQuotes.mockResolvedValue({
        quotes: new Map([
          ["AAPL", quote("AAPL", 200, "USD")],
          ["MSFT", quote("MSFT", 300, "USD")],
        ]),
        failed: 0,
      });
      mockFetchDailyCloses.mockImplementation((symbol: string) =>
        Promise.resolve(closesFrom("2026-01-01", 40, symbol === "AAPL" ? 100 : 250)),
      );
      render(<PortfolioPanel />);
      await addHolding("aapl", "10", "150");
      await addHolding("msft", "5", "280");

      expect(await screen.findByText("39d history")).toBeInTheDocument();
      expect(screen.getAllByText("AAPL").length).toBeGreaterThan(0);
      expect(screen.getAllByText("MSFT").length).toBeGreaterThan(0);
    });
  });
});
