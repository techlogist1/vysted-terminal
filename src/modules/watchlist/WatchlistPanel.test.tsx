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

const { fetchWatchlistQuotes } = await import("./api");
const mockFetch = vi.mocked(fetchWatchlistQuotes);

function quote(symbol: string, price: number, changePercent: number): Quote {
  return {
    symbol,
    price,
    change: 0,
    change_percent: changePercent,
    volume: null,
    currency: "USD",
    market_state: null,
    timestamp: "2026-05-15T00:00:00Z",
    provider: "yfinance",
  };
}

function rowsFor(entries = DEFAULT_SYMBOLS): WatchlistRow[] {
  return entries.map((entry) => ({
    entry,
    quote: quote(entry.symbol, 100, entry.symbol === "AAPL" ? -1.5 : 2.5),
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
  it("shows a loading state before quotes resolve", () => {
    render(<WatchlistPanel />);
    expect(screen.getByText("Loading quotes…")).toBeInTheDocument();
  });

  it("renders the pre-loaded symbols with prices and change%", async () => {
    render(<WatchlistPanel />);
    expect(await screen.findByText("SPY")).toBeInTheDocument();
    expect(screen.getByText("NVDA")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getAllByText("+2.50%").length).toBeGreaterThan(0);
    expect(screen.getByText("-1.50%")).toBeInTheDocument();
  });

  it("colours gains positive and losses negative", async () => {
    render(<WatchlistPanel />);
    expect(await screen.findByText("-1.50%")).toBeInTheDocument();
    expect(screen.getByText("-1.50%").className).toContain("text-negative");
    expect(screen.getAllByText("+2.50%")[0].className).toContain("text-positive");
  });

  it("surfaces a SidecarError message", async () => {
    mockFetch.mockRejectedValueOnce(new SidecarError(502, "upstream down"));
    render(<WatchlistPanel />);
    expect(await screen.findByText("upstream down")).toBeInTheDocument();
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

  it("polls for quote refreshes on an interval", async () => {
    vi.useFakeTimers();
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
});
