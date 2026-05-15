/**
 * Per-panel context publishers — integration tests.
 *
 * Each Phase-1 panel publishes its current state to `usePanelContextBus` on
 * mount and on actual state change; the chat sidebar reads the bus via
 * `selectSnapshot`. This test suite covers the four non-chart panels
 * (Watchlist, News, Equity Overview, Portfolio) — the chart panel's publish
 * path is covered in `ChartPanel.test.tsx` because the chart's full mock
 * suite is heavy and lives there.
 *
 * The "publish doesn't trigger infinite re-render" assertion is per-panel
 * and uses the same trick: render the panel, wait one microtask flush, and
 * count the publish calls. A render-loop bug would leave the count at >100
 * within a few ticks; a healthy publisher caps it at the small number of
 * deliberate state transitions (mount + any deferred state setters).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { usePanelContextBus } from "@/store/panel-context";
import { DEFAULT_SYMBOLS, useSymbolsStore } from "@/store/symbols";

// --- shared mocks ---------------------------------------------------------

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:9999"),
  };
});

// Per-panel API mocks. Each panel's mount-time fetch must resolve so the
// publisher's deps stabilise and we can assert on the published payload.

vi.mock("@/modules/watchlist/api", () => ({
  WATCHLIST_CRYPTO_EXCHANGE: "binance",
  fetchWatchlistQuotes: vi.fn(async () =>
    DEFAULT_SYMBOLS.map((entry) => ({
      entry,
      quote: {
        symbol: entry.symbol,
        price: 100,
        change: 0,
        change_percent: 0,
        volume: null,
        currency: "USD",
        market_state: null,
        timestamp: "2026-05-15T00:00:00Z",
        provider: "yfinance",
      },
    })),
  ),
}));

vi.mock("@/modules/news/api", () => ({
  fetchNews: vi.fn(async () => []),
}));

vi.mock("@/modules/equity-overview/api", () => ({
  loadEquityOverview: vi.fn(async (symbol: string) => ({
    symbol,
    quote: {
      symbol,
      price: 200,
      change: 1,
      change_percent: 0.5,
      volume: null,
      currency: "USD",
      market_state: null,
      timestamp: "2026-05-15T00:00:00Z",
      provider: "yfinance",
    },
    fundamentals: null,
    ratings: null,
    income: null,
    balance: null,
    cashFlow: null,
    allFailed: false,
  })),
}));

vi.mock("@/modules/portfolio/api", () => ({
  fetchPositions: vi.fn(async () => []),
  fetchPositionQuotes: vi.fn(async () => new Map()),
  createPosition: vi.fn(),
  updatePosition: vi.fn(),
  deletePosition: vi.fn(),
}));

// --- harness --------------------------------------------------------------

type PublishFn = ReturnType<typeof usePanelContextBus.getState>["publish"];
let publishSpy: ReturnType<typeof vi.fn> & PublishFn;
let realPublish: PublishFn;

beforeEach(() => {
  usePanelContextBus.setState({
    lastEventBySource: {},
    focusedSource: null,
    updatedAt: 0,
  });
  realPublish = usePanelContextBus.getState().publish;
  publishSpy = vi.fn(realPublish) as ReturnType<typeof vi.fn> & PublishFn;
  // Replace publish with a spy so we can count calls.
  usePanelContextBus.setState({ publish: publishSpy });
  useSymbolsStore.setState({ entries: [...DEFAULT_SYMBOLS] });
});

afterEach(() => {
  cleanup();
  usePanelContextBus.setState({ publish: realPublish });
});

/**
 * Assert no infinite-loop pattern: after letting the panel mount and stabilise,
 * the publisher should have been called a bounded number of times (1 mount
 * publish + a small number of dependent updates). We assert <= 10 — anything
 * unbounded blows past that within a tick.
 */
function expectBoundedPublishCount(source: string) {
  const calls = publishSpy.mock.calls.filter(
    (call) => (call[0] as { source: string }).source === source,
  );
  expect(calls.length).toBeGreaterThan(0);
  expect(calls.length).toBeLessThan(10);
}

// --- Watchlist publisher --------------------------------------------------

describe("WatchlistPanel publisher", () => {
  it("publishes the symbols + selectedSymbol selection on mount", async () => {
    const { WatchlistPanel } = await import("@/modules/watchlist/WatchlistPanel");
    render(<WatchlistPanel />);
    await screen.findByText("SPY");
    const calls = publishSpy.mock.calls.filter(
      (c) => (c[0] as { source: string }).source === "watchlist",
    );
    expect(calls.length).toBeGreaterThan(0);
    const latest = calls[calls.length - 1]?.[0] as {
      source: string;
      kind: string;
      payload: { symbols: string[]; selectedSymbol: string | null };
    };
    expect(latest.source).toBe("watchlist");
    expect(latest.kind).toBe("selection");
    expect(latest.payload.symbols).toEqual(DEFAULT_SYMBOLS.map((e) => e.symbol));
    expect(latest.payload.selectedSymbol).toBeNull();
  });

  it("publishes again when the user clicks a row to select a symbol", async () => {
    const { WatchlistPanel } = await import("@/modules/watchlist/WatchlistPanel");
    render(<WatchlistPanel />);
    await screen.findByText("AAPL");
    const before = publishSpy.mock.calls.length;
    fireEvent.click(screen.getByText("AAPL"));
    expect(publishSpy.mock.calls.length).toBeGreaterThan(before);
    const latest = publishSpy.mock.calls[publishSpy.mock.calls.length - 1]?.[0] as {
      payload: { selectedSymbol: string | null };
    };
    expect(latest.payload.selectedSymbol).toBe("AAPL");
  });

  it("does not trigger an infinite re-render loop", async () => {
    const { WatchlistPanel } = await import("@/modules/watchlist/WatchlistPanel");
    render(<WatchlistPanel />);
    await screen.findByText("SPY");
    // Let any microtask-deferred state writes flush.
    await act(async () => {
      await Promise.resolve();
    });
    expectBoundedPublishCount("watchlist");
  });
});

// --- News publisher -------------------------------------------------------

describe("NewsFeedPanel publisher", () => {
  it("publishes the watched symbols + focused article id on mount", async () => {
    const { NewsFeedPanel } = await import("@/modules/news/NewsFeedPanel");
    render(<NewsFeedPanel />);
    const calls = publishSpy.mock.calls.filter(
      (c) => (c[0] as { source: string }).source === "news",
    );
    expect(calls.length).toBeGreaterThan(0);
    const latest = calls[calls.length - 1]?.[0] as {
      payload: { watchedSymbols: string[]; focusedArticleId: string | null };
    };
    expect(latest.payload.focusedArticleId).toBeNull();
    expect(latest.payload.watchedSymbols.length).toBeGreaterThan(0);
  });

  it("does not trigger an infinite re-render loop", async () => {
    const { NewsFeedPanel } = await import("@/modules/news/NewsFeedPanel");
    render(<NewsFeedPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    expectBoundedPublishCount("news");
  });
});

// --- Equity Overview publisher -------------------------------------------

describe("EquityOverviewPanel publisher", () => {
  it("publishes a null ticker on mount, then the loaded ticker after load", async () => {
    const { EquityOverviewPanel } = await import("@/modules/equity-overview/EquityOverviewPanel");
    render(<EquityOverviewPanel />);
    const calls = publishSpy.mock.calls.filter(
      (c) => (c[0] as { source: string }).source === "equity",
    );
    expect(calls.length).toBeGreaterThan(0);
    const initial = calls[0]?.[0] as {
      payload: { ticker: string | null; loadedSections: string[] };
    };
    expect(initial.payload.ticker).toBeNull();
    expect(initial.payload.loadedSections).toEqual([]);

    // Submit a symbol — the mocked loadEquityOverview returns AAPL with a quote.
    const input = screen.getByLabelText("Symbol");
    fireEvent.change(input, { target: { value: "AAPL" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Load/i }));
      await Promise.resolve();
      await Promise.resolve();
    });
    const after = publishSpy.mock.calls.filter(
      (c) => (c[0] as { source: string }).source === "equity",
    );
    const latest = after[after.length - 1]?.[0] as {
      payload: { ticker: string | null; loadedSections: string[] };
    };
    expect(latest.payload.ticker).toBe("AAPL");
    expect(latest.payload.loadedSections).toContain("quote");
  });

  it("does not trigger an infinite re-render loop", async () => {
    const { EquityOverviewPanel } = await import("@/modules/equity-overview/EquityOverviewPanel");
    render(<EquityOverviewPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    expectBoundedPublishCount("equity");
  });
});

// --- Portfolio publisher --------------------------------------------------

describe("PortfolioPanel publisher", () => {
  it("publishes a positionCount + totalValue snapshot on mount", async () => {
    const { PortfolioPanel } = await import("@/modules/portfolio/PortfolioPanel");
    render(<PortfolioPanel />);
    // Wait for the initial load to settle.
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    const calls = publishSpy.mock.calls.filter(
      (c) => (c[0] as { source: string }).source === "portfolio",
    );
    expect(calls.length).toBeGreaterThan(0);
    const latest = calls[calls.length - 1]?.[0] as {
      payload: { positionCount: number; totalValue: number };
    };
    // No positions in the mock — both fields are zero.
    expect(latest.payload.positionCount).toBe(0);
    expect(latest.payload.totalValue).toBe(0);
  });

  it("does not trigger an infinite re-render loop", async () => {
    const { PortfolioPanel } = await import("@/modules/portfolio/PortfolioPanel");
    render(<PortfolioPanel />);
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expectBoundedPublishCount("portfolio");
  });
});

// --- Unmount cleanup ------------------------------------------------------

describe("publisher cleanup", () => {
  it("watchlist unregisters its source on unmount", async () => {
    const { WatchlistPanel } = await import("@/modules/watchlist/WatchlistPanel");
    const { unmount } = render(<WatchlistPanel />);
    await screen.findByText("SPY");
    expect(usePanelContextBus.getState().lastEventBySource.watchlist).toBeDefined();
    unmount();
    expect(usePanelContextBus.getState().lastEventBySource.watchlist).toBeUndefined();
  });

  it("news unregisters its source on unmount", async () => {
    const { NewsFeedPanel } = await import("@/modules/news/NewsFeedPanel");
    const { unmount } = render(<NewsFeedPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(usePanelContextBus.getState().lastEventBySource.news).toBeDefined();
    unmount();
    expect(usePanelContextBus.getState().lastEventBySource.news).toBeUndefined();
  });

  it("equity unregisters its source on unmount", async () => {
    const { EquityOverviewPanel } = await import("@/modules/equity-overview/EquityOverviewPanel");
    const { unmount } = render(<EquityOverviewPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(usePanelContextBus.getState().lastEventBySource.equity).toBeDefined();
    unmount();
    expect(usePanelContextBus.getState().lastEventBySource.equity).toBeUndefined();
  });

  it("portfolio unregisters its source on unmount", async () => {
    const { PortfolioPanel } = await import("@/modules/portfolio/PortfolioPanel");
    const { unmount } = render(<PortfolioPanel />);
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(usePanelContextBus.getState().lastEventBySource.portfolio).toBeDefined();
    unmount();
    expect(usePanelContextBus.getState().lastEventBySource.portfolio).toBeUndefined();
  });
});
