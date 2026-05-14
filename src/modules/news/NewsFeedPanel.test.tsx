import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SidecarError } from "@/lib/sidecar-client";

import type { NewsItem } from "../../../types/data";

// Mock the module's sidecar API — no live calls. The factory references no
// outer-scope bindings, so it is hoist-safe.
vi.mock("./api", () => ({
  fetchNews: vi.fn(),
}));

import { fetchNews } from "./api";
import { NewsFeedPanel } from "./NewsFeedPanel";

const mockFetchNews = vi.mocked(fetchNews);

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
    mockFetchNews.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading state before news resolves", () => {
    mockFetchNews.mockReturnValue(new Promise(() => {}));
    render(<NewsFeedPanel />);
    expect(screen.getByText("Loading news…")).toBeInTheDocument();
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

  it("requests news for the Phase 1 default watchlist", async () => {
    mockFetchNews.mockResolvedValue([]);
    render(<NewsFeedPanel />);
    await waitFor(() => expect(mockFetchNews).toHaveBeenCalledTimes(1));
    const [symbols] = mockFetchNews.mock.calls[0];
    expect(symbols).toEqual(["SPY", "QQQ", "BTC", "ETH", "NVDA", "AAPL"]);
  });

  it("renders an empty state when there is no news", async () => {
    mockFetchNews.mockResolvedValue([]);
    render(<NewsFeedPanel />);
    await waitFor(() => {
      expect(screen.getByText("No news for the current watchlist.")).toBeInTheDocument();
    });
  });

  it("surfaces a SidecarError with its status", async () => {
    mockFetchNews.mockRejectedValue(new SidecarError(502, "all news sources failed"));
    render(<NewsFeedPanel />);
    await waitFor(() => {
      expect(screen.getByText("Sidecar error 502: all news sources failed")).toBeInTheDocument();
    });
  });

  it("falls back to a generic message for non-SidecarError failures", async () => {
    mockFetchNews.mockRejectedValue(new Error("network down"));
    render(<NewsFeedPanel />);
    await waitFor(() => {
      expect(screen.getByText("Could not reach the news service.")).toBeInTheDocument();
    });
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
