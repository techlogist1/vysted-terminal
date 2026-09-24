import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { SidecarError } from "@/lib/sidecar-client";
import type { Quote } from "../../../types/data";
import { DEFAULT_SYMBOLS, useSymbolsStore } from "@/store/symbols";
import { WatchlistPanel } from "./WatchlistPanel";
import type { WatchlistRow } from "./api";

vi.mock("./api", () => ({
  WATCHLIST_CRYPTO_EXCHANGE: "binance",
  fetchWatchlistQuotes: vi.fn(),
}));

const autocompleteMock = vi.fn();
vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return { ...actual, sidecarGet: (...args: unknown[]) => autocompleteMock(...args) };
});

vi.mock("@/lib/host-actions", async () => ({
  ...(await vi.importActual<typeof import("@/lib/host-actions")>("@/lib/host-actions")),
  loadSymbolIntoChart: vi.fn(),
  openCompanyOverview: vi.fn(),
}));

const { fetchWatchlistQuotes } = await import("./api");
const mockFetch = vi.mocked(fetchWatchlistQuotes);
const hostActions = await import("@/lib/host-actions");

function quote(
  symbol: string,
  price: number,
  changePercent: number,
  freshness: Quote["freshness"] = "eod",
  marketState: string | null = null,
): Quote {
  return {
    symbol,
    price,
    change: 0,
    change_percent: changePercent,
    volume: null,
    currency: "USD",
    market_state: marketState,
    timestamp: "2026-05-15T00:00:00Z",
    provider: "yfinance",
    freshness,
  };
}

function rowsFor(
  entries = DEFAULT_SYMBOLS,
  freshness: Quote["freshness"] = "eod",
  marketState: string | null = null,
): WatchlistRow[] {
  return entries.map((entry) => ({
    entry,
    quote: quote(entry.symbol, 100, entry.symbol === "AAPL" ? -1.5 : 2.5, freshness, marketState),
  }));
}

beforeEach(() => {
  useSymbolsStore.setState({ entries: [...DEFAULT_SYMBOLS] });
  mockFetch.mockReset();
  mockFetch.mockResolvedValue(rowsFor());
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("WatchlistPanel", () => {
  it("a crypto row opens its chart, an equity row the company overview (R15-DATA-081)", async () => {
    vi.mocked(hostActions.loadSymbolIntoChart).mockClear();
    vi.mocked(hostActions.openCompanyOverview).mockClear();
    render(<WatchlistPanel />);
    fireEvent.click(await screen.findByText("BTC/USDT"));
    expect(hostActions.loadSymbolIntoChart).toHaveBeenCalledWith("BTC/USDT");
    expect(hostActions.openCompanyOverview).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("NVDA"));
    expect(hostActions.openCompanyOverview).toHaveBeenCalledWith("NVDA");
    expect(hostActions.loadSymbolIntoChart).toHaveBeenCalledTimes(1);
  });

  it("shows a loading state before quotes resolve", () => {
    // Never resolve so we stay in the loading/skeleton state.
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<WatchlistPanel />);
    // Loading is now a skeleton table — symbol/price/change cells are not rendered.
    expect(screen.queryByText("SPY")).not.toBeInTheDocument();
    expect(screen.queryByText("NVDA")).not.toBeInTheDocument();
  });

  it("renders the pre-loaded symbols with prices and change%", async () => {
    render(<WatchlistPanel />);
    expect(await screen.findByText("SPY")).toBeInTheDocument();
    expect(screen.getByText("NVDA")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getAllByText("+2.50%").length).toBeGreaterThan(0);
    expect(screen.getByText("-1.50%")).toBeInTheDocument();
  });

  it("colours gains positive and losses negative for a LIVE quote", async () => {
    // FR-118: green/red sign colour is reserved for a live tick.
    mockFetch.mockResolvedValue(rowsFor(DEFAULT_SYMBOLS, "live", "REGULAR"));
    render(<WatchlistPanel />);
    expect(await screen.findByText("-1.50%")).toBeInTheDocument();
    expect(screen.getByText("-1.50%").className).toContain("text-negative");
    expect(screen.getAllByText("+2.50%")[0].className).toContain("text-positive");
  });

  it("greys the change% for a NON-live (EOD) quote so it never reads as a live move", async () => {
    // The default fixture is EOD — the stale guard must mute the sign colour.
    render(<WatchlistPanel />);
    expect(await screen.findByText("-1.50%")).toBeInTheDocument();
    expect(screen.getByText("-1.50%").className).toContain("text-charcoal-400");
    expect(screen.getByText("-1.50%").className).not.toContain("text-negative");
  });

  it("shows a humanized session label for a closed-session quote (FR-118)", async () => {
    mockFetch.mockResolvedValue(rowsFor(DEFAULT_SYMBOLS, "eod", "CLOSED"));
    render(<WatchlistPanel />);
    await screen.findByText("AAPL");
    // The raw provider token (CLOSED) is never echoed; a friendly label is shown
    // ("Market closed" on a weekday, "Weekend" on Sat/Sun — both acceptable).
    const labels = screen.getAllByText(/^(Market closed|Weekend)$/);
    expect(labels.length).toBeGreaterThan(0);
    expect(screen.queryByText("CLOSED")).toBeNull();
  });

  it("badges each quoted row with provenance + freshness (SC-019)", async () => {
    render(<WatchlistPanel />);
    await screen.findByText("SPY");
    // One provenance + one staleness badge per quoted row — a stale value is
    // never shown as a live tick.
    const provenance = screen.getAllByTestId("provenance-badge");
    const staleness = screen.getAllByTestId("staleness-badge");
    expect(provenance.length).toBe(DEFAULT_SYMBOLS.length);
    expect(staleness.length).toBe(DEFAULT_SYMBOLS.length);
    // The chip renders the designed short form (R8 §3.1 — "yfinance" used to
    // mid-word clip to "YFINAN"); the full provider id stays in the tooltip.
    expect(provenance[0]).toHaveTextContent("YF");
    expect(provenance[0]).toHaveAttribute("title", "Source: yfinance");
    expect(staleness[0]).toHaveTextContent(/EOD/i);
  });

  it("surfaces a SidecarError message", async () => {
    mockFetch.mockRejectedValueOnce(new SidecarError(502, "upstream down"));
    render(<WatchlistPanel />);
    // Error banner now shows a human message and a Retry button.
    expect(await screen.findByText("Could not refresh quotes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("adds a symbol through the form", async () => {
    render(<WatchlistPanel />);
    await screen.findByText("SPY");
    fireEvent.change(screen.getByLabelText("Add symbol"), { target: { value: "tsla" } });
    act(() => {
      fireEvent.click(screen.getByLabelText("Add to watchlist"));
    });
    expect(useSymbolsStore.getState().entries.some((entry) => entry.symbol === "TSLA")).toBe(true);
  });

  it("removes a symbol through the row control", async () => {
    render(<WatchlistPanel />);
    await screen.findByText("NVDA");
    act(() => {
      fireEvent.click(screen.getByLabelText("Remove NVDA"));
    });
    expect(useSymbolsStore.getState().entries.some((entry) => entry.symbol === "NVDA")).toBe(false);
  });

  describe("rows follow the live list, not a poll snapshot (R15-UI-026)", () => {
    const pollInFlight = async () => {
      vi.useFakeTimers();
      // Live rows poll every 5 s; an all-EOD list waits 60 s (R15-DATA-066).
      mockFetch.mockResolvedValue(rowsFor(DEFAULT_SYMBOLS, "live", "REGULAR"));
      render(<WatchlistPanel />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      let resolvePoll: (rows: WatchlistRow[]) => void = () => {};
      mockFetch.mockReturnValueOnce(new Promise((resolve) => (resolvePoll = resolve)));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5_000);
      });
      expect(mockFetch).toHaveBeenCalledTimes(2);
      return (rows: WatchlistRow[]) => act(async () => resolvePoll(rows));
    };

    it("an added symbol shows at once while a poll is in flight", async () => {
      await pollInFlight();
      act(() => useSymbolsStore.getState().addSymbol("TSLA", "equity"));
      expect(screen.getByText("TSLA")).toBeInTheDocument();
    });

    it("a removed symbol does not come back when the in-flight poll lands", async () => {
      const land = await pollInFlight();
      act(() => {
        fireEvent.click(screen.getByLabelText("Remove NVDA"));
      });
      await land(rowsFor());
      expect(screen.queryByText("NVDA")).toBeNull();
    });
  });

  it("Enter adds the typed ticker when the candidates are still the previous query's (R15-UI-026)", async () => {
    autocompleteMock.mockImplementation(async (_path: string, params: { q: string }) =>
      params.q === "TC"
        ? {
            query: "TC",
            region: "IN",
            candidates: [
              {
                symbol: "TC",
                name: "Token Cat",
                exchange: "NASDAQ",
                region: "US",
                asset_class: "equity",
                yahoo_symbol: "TC",
                confidence: 0.9,
              },
            ],
          }
        : new Promise(() => {}),
    );
    render(<WatchlistPanel />);
    const input = screen.getByLabelText("Add symbol");
    fireEvent.change(input, { target: { value: "TC" } });
    expect(await screen.findByRole("option", { name: /Token Cat/ })).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "TCS" } });
    fireEvent.submit(input.closest("form")!);
    const symbols = useSymbolsStore.getState().entries.map((e) => e.symbol);
    expect(symbols).toContain("TCS");
    expect(symbols).not.toContain("TC");
  });

  it("backs off after a failed poll and pauses while the document is hidden", async () => {
    vi.useFakeTimers();
    mockFetch.mockRejectedValueOnce(new SidecarError(502, "down"));
    render(<WatchlistPanel />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1); // backed off to 10 s
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);

    const hidden = vi.spyOn(document, "hidden", "get").mockReturnValue(true);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);
    hidden.mockReturnValue(false);
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(mockFetch).toHaveBeenCalledTimes(3);
    hidden.mockRestore();
  });

  it("polls for quote refreshes on an interval", async () => {
    vi.useFakeTimers();
    mockFetch.mockResolvedValue(rowsFor(DEFAULT_SYMBOLS, "live", "REGULAR"));
    render(<WatchlistPanel />);
    // Flush the initial refresh.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
    // One interval tick triggers a second refresh.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });
    expect(mockFetch.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("an all-EOD list polls on the 60 s EOD cadence, not every 5 s (R15-DATA-066)", async () => {
    vi.useFakeTimers();
    render(<WatchlistPanel />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("a symbol missing from a completed batch reads unavailable, not loading (R15-DATA-062)", async () => {
    const entries = [
      { symbol: "RELIANCE.NS", assetClass: "equity" as const },
      { symbol: "ZZZZNOPE", assetClass: "equity" as const },
    ];
    useSymbolsStore.setState({ entries });
    mockFetch.mockResolvedValue([
      { entry: entries[0], quote: quote("RELIANCE.NS", 2950, 0.4) },
      { entry: entries[1], quote: null },
    ]);
    render(<WatchlistPanel />);
    expect(await screen.findByText("unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("unavailable")).toHaveLength(1);
    expect(screen.getByText("RELIANCE.NS")).toBeInTheDocument();
  });
});
