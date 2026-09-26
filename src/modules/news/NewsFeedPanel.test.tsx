import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SidecarError } from "@/lib/sidecar-client";
import { useSettingsStore } from "@/store/settings";
import { defaultSymbolsForRegion, useSymbolsStore } from "@/store/symbols";

import type { NewsItem } from "../../../types/data";

// Mock the module's sidecar API — no live calls. The factory references no
// outer-scope bindings, so it is hoist-safe.
vi.mock("./api", () => ({
  fetchNews: vi.fn(),
  fetchNewsSourcesStatus: vi.fn(),
}));

import { fetchNews, fetchNewsSourcesStatus } from "./api";
import { NewsFeedPanel } from "./NewsFeedPanel";

// The fixtures below are written against the US watchlist; the app default is
// IN (R15-UI-076), so seed the US list explicitly.
const US_SYMBOLS = defaultSymbolsForRegion("US");

const mockFetchNews = vi.mocked(fetchNews);
const mockFetchNewsSourcesStatus = vi.mocked(fetchNewsSourcesStatus);

function newsItem(overrides: Partial<NewsItem> = {}): NewsItem {
  return {
    id: "n1",
    title: "NVDA shares climb on strong demand",
    summary: "Chipmaker beats expectations.",
    url: "https://example.com/n1",
    source: "Test Feed",
    published_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    symbols: ["NVDA"],
    sentiment: 0.62,
    sentiment_label: "positive",
    provider: "rss",
    ...overrides,
  };
}

describe("NewsFeedPanel", () => {
  beforeEach(() => {
    // Reset the shared symbols store between tests so per-test mutations do
    // not leak into other cases.
    useSymbolsStore.setState({ entries: [...US_SYMBOLS] });
    // Reset region to the default so a prior region-switch test can't leak.
    useSettingsStore.setState({ region: "US" });
    mockFetchNews.mockReset();
    mockFetchNewsSourcesStatus.mockReset();
    mockFetchNewsSourcesStatus.mockResolvedValue({ newsapi: "absent" });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading state before news resolves", () => {
    mockFetchNews.mockReturnValue(new Promise(() => {}));
    render(<NewsFeedPanel />);
    // Loading is now a skeleton — verify the panel is in loading state via the
    // Refresh button showing "Loading…" (it reads that when status === 'loading').
    expect(screen.getByRole("button", { name: /loading/i })).toBeInTheDocument();
  });

  it("renders 'date unknown' for an item the feed did not date (R15-DATA-070)", async () => {
    mockFetchNews.mockResolvedValue([newsItem({ published_at: null })]);
    render(<NewsFeedPanel />);

    await waitFor(() => {
      expect(screen.getByText("NVDA shares climb on strong demand")).toBeInTheDocument();
    });
    expect(screen.getByText(/date unknown/)).toBeInTheDocument();
    expect(screen.queryByText(/\bnow\b/)).not.toBeInTheDocument();
  });

  it("renders news items with headline, source, and sentiment", async () => {
    mockFetchNews.mockResolvedValue([
      newsItem(),
      newsItem({
        id: "n2",
        title: "AAPL slumps after weak guidance",
        symbols: ["AAPL"],
        sentiment: -0.45,
        sentiment_label: "negative",
      }),
    ]);
    render(<NewsFeedPanel />);

    await waitFor(() => {
      expect(screen.getByText("NVDA shares climb on strong demand")).toBeInTheDocument();
    });
    expect(screen.getByText("AAPL slumps after weak guidance")).toBeInTheDocument();

    const badges = screen.getAllByTestId("sentiment-badge");
    expect(badges).toHaveLength(2);
    expect(badges[0]).toHaveTextContent("positive");
    expect(badges[0]).toHaveTextContent("+0.62");
    expect(badges[0].className).toContain("text-positive");
    expect(badges[1]).toHaveTextContent("negative");
    expect(badges[1].className).toContain("text-negative");
  });

  it("requests news for the default watchlist projected through toNewsSymbol", async () => {
    mockFetchNews.mockResolvedValue([]);
    render(<NewsFeedPanel />);
    await waitFor(() => expect(mockFetchNews).toHaveBeenCalledTimes(1));
    const [symbols] = mockFetchNews.mock.calls[0];
    // `BTC/USDT` / `ETH/USDT` collapse to their base assets for news tagging.
    expect(symbols).toEqual(["SPY", "QQQ", "BTC", "ETH", "NVDA", "AAPL"]);
  });

  it("re-fetches when the shared symbols store changes", async () => {
    mockFetchNews.mockResolvedValue([]);
    render(<NewsFeedPanel />);
    await waitFor(() => expect(mockFetchNews).toHaveBeenCalledTimes(1));

    act(() => {
      useSymbolsStore.setState({ entries: [{ symbol: "TSLA", assetClass: "equity" }] });
    });

    await waitFor(() => expect(mockFetchNews).toHaveBeenCalledTimes(2));
    const [symbols] = mockFetchNews.mock.calls[1];
    expect(symbols).toEqual(["TSLA"]);
  });

  it("re-fetches when the active region changes (region-first feed)", async () => {
    mockFetchNews.mockResolvedValue([]);
    render(<NewsFeedPanel />);
    await waitFor(() => expect(mockFetchNews).toHaveBeenCalledTimes(1));

    act(() => {
      useSettingsStore.setState({ region: "IN" });
    });

    await waitFor(() => expect(mockFetchNews).toHaveBeenCalledTimes(2));
  });

  it("renders an empty state when there is no news", async () => {
    mockFetchNews.mockResolvedValue([]);
    render(<NewsFeedPanel />);
    await waitFor(() => {
      expect(screen.getByText("No headlines for your watchlist.")).toBeInTheDocument();
    });
  });

  it("surfaces a SidecarError with its status after ONE request, never a retry loop (R15-UI-015)", async () => {
    vi.useFakeTimers();
    mockFetchNews.mockRejectedValue(new SidecarError(502, "all news sources failed"));
    render(<NewsFeedPanel />);
    // A 502 is the engine's answer, not a cold boot: the cold-boot backoff
    // window passes without a second request.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(screen.getByText("Sidecar error 502: all news sources failed")).toBeInTheDocument();
    expect(mockFetchNews).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it("falls back to a generic message for non-SidecarError failures", async () => {
    vi.useFakeTimers();
    mockFetchNews.mockRejectedValue(new Error("network down"));
    render(<NewsFeedPanel />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(screen.getByText("Could not reach the news service.")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("badges a rejected NewsAPI key without blocking the feed (R15-DATA-094)", async () => {
    mockFetchNews.mockResolvedValue([newsItem()]);
    mockFetchNewsSourcesStatus.mockResolvedValue({ newsapi: "unauthorized" });
    render(<NewsFeedPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("newsapi-status-badge")).toBeInTheDocument();
    });
    // The RSS-backed feed still renders — a bad NewsAPI key degrades, never blocks.
    expect(screen.getByText("NVDA shares climb on strong demand")).toBeInTheDocument();
  });

  it("shows no badge when NewsAPI is unconfigured or working", async () => {
    mockFetchNews.mockResolvedValue([newsItem()]);
    mockFetchNewsSourcesStatus.mockResolvedValue({ newsapi: "absent" });
    render(<NewsFeedPanel />);
    await waitFor(() => {
      expect(screen.getByText("NVDA shares climb on strong demand")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("newsapi-status-badge")).not.toBeInTheDocument();
  });

  it("renders the symbol tags for each item", async () => {
    mockFetchNews.mockResolvedValue([newsItem({ symbols: ["NVDA", "SPY"] })]);
    render(<NewsFeedPanel />);
    await waitFor(() => {
      expect(screen.getByText("NVDA")).toBeInTheDocument();
    });
    expect(screen.getByText("SPY")).toBeInTheDocument();
  });
});
