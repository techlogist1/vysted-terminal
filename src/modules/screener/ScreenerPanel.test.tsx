/**
 * ScreenerPanel tests — Phase 6 (Teammate Sc backend; v0.6.1 lead-completed frontend).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import type { ScreenerResult, ScreenerUniverse } from "../../../types/screener";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

import { useScreenerStore } from "@/store/screener";

import { ScreenerPanel } from "./ScreenerPanel";

const UNIVERSE_SAMPLE: ScreenerUniverse = {
  id: "sp500",
  label: "S&P 500",
  symbols: ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
  asset_class: "equity",
};

const RESULT_SAMPLE: ScreenerResult = {
  universe: "sp500",
  evaluated_count: 100,
  skipped_count: 0,
  result_count: 2,
  rows: [
    {
      symbol: "AAPL",
      name: "Apple Inc.",
      sector: "Technology",
      industry: "Consumer Electronics",
      market_cap: 3_000_000_000_000,
      pe_ratio: 18.5,
      price: 192.5,
      change_percent_1d: 1.5,
      volume: 51_000_000,
      matched_criteria: [0, 1, 2],
    },
    {
      symbol: "GOOGL",
      name: "Alphabet Inc.",
      sector: "Technology",
      industry: "Internet Content",
      market_cap: 2_100_000_000_000,
      pe_ratio: 19.0,
      price: 175.0,
      change_percent_1d: -0.3,
      volume: 18_000_000,
      matched_criteria: [0, 1, 2],
    },
  ],
  duration_ms: 320.0,
};

/** SSE streaming result — carries partial + freshness to verify header rendering. */
const RESULT_WITH_PARTIAL: ScreenerResult = {
  ...RESULT_SAMPLE,
  partial: true,
  coverage: "screened 100 of 500 — 400 unavailable",
  freshness: {
    quotes_as_of: 1_700_000_000,
    valuation_as_of: 1_699_980_000,
    deep_as_of: 1_699_400_000,
  },
};

/** Real SSE wire format: `data: {json}\n\n` (backtest.py:195 precedent). */
function makeStreamResponse(result: ScreenerResult): Response {
  const progressFrame = `data: ${JSON.stringify({ event: "progress", phase: "sweep", done: 50, total: 100, detail: "sweeping quotes 50/100" })}\n\n`;
  const resultFrame = `data: ${JSON.stringify({ event: "result", ...result })}\n\n`;
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(progressFrame));
      controller.enqueue(encoder.encode(resultFrame));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

/** Fallback mock: /stream returns 404 (older sidecar), /screener/run returns the result.
 *  Matches the streaming-first architecture added in R10. */
function mockFetchFallback(result: ScreenerResult) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    if (String(url).includes("/stream")) {
      return new Response(null, { status: 404 });
    }
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
}

beforeEach(() => {
  useScreenerStore.getState().__resetForTests();
  vi.mocked(sidecarGet).mockResolvedValue(UNIVERSE_SAMPLE);
  mockFetchFallback(RESULT_SAMPLE);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ScreenerPanel", () => {
  it("renders the universe picker + default criteria + run button", () => {
    render(<ScreenerPanel />);
    expect(screen.getByLabelText(/universe/i)).toBeInTheDocument();
    expect(screen.getByTestId("run-screener-button")).toBeInTheDocument();
    // default seeded criteria
    expect(screen.getByTestId("criterion-row-0")).toBeInTheDocument();
    expect(screen.getByTestId("criterion-row-1")).toBeInTheDocument();
    expect(screen.getByTestId("criterion-row-2")).toBeInTheDocument();
  });

  it("shows the ticker count after universe load", async () => {
    render(<ScreenerPanel />);
    await waitFor(() => {
      expect(screen.getByText(/5 tickers/i)).toBeInTheDocument();
    });
  });

  it("clicking Run posts to /screener/run and renders the results table", async () => {
    render(<ScreenerPanel />);
    fireEvent.click(screen.getByTestId("run-screener-button"));
    await waitFor(() => {
      expect(screen.getByText(/Apple Inc\./)).toBeInTheDocument();
      expect(screen.getByText(/Alphabet Inc\./)).toBeInTheDocument();
    });
    // the universe id is rendered as a status label on the results header
    expect(screen.getByText(/sp500/i)).toBeInTheDocument();
  });

  it("switching to the custom universe reveals the symbols input", () => {
    render(<ScreenerPanel />);
    fireEvent.change(screen.getByLabelText(/universe/i), { target: { value: "custom" } });
    expect(screen.getByLabelText(/symbols/i)).toBeInTheDocument();
  });

  it("an error response surfaces as an inline banner", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "universe unreachable" }), { status: 502 }),
    );
    render(<ScreenerPanel />);
    fireEvent.click(screen.getByTestId("run-screener-button"));
    await waitFor(() => {
      expect(screen.getByText(/universe unreachable/)).toBeInTheDocument();
    });
  });

  it("Run button morphs to Cancel while the screener is running", async () => {
    // Never-resolving stream: keeps the panel in loading state.
    const neverStream = new ReadableStream({ start() {} });
    vi.spyOn(globalThis, "fetch").mockReturnValue(
      Promise.resolve(
        new Response(neverStream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      ),
    );

    render(<ScreenerPanel />);
    expect(screen.getByTestId("run-screener-button")).toBeInTheDocument();
    expect(screen.queryByTestId("cancel-screener-button")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("run-screener-button"));

    await waitFor(() => {
      expect(screen.queryByTestId("run-screener-button")).not.toBeInTheDocument();
      expect(screen.getByTestId("cancel-screener-button")).toBeInTheDocument();
    });
  });

  it("progress detail and bar render while the screener is loading", async () => {
    // Stream that emits a progress frame then hangs (so we can assert the bar).
    const encoder = new TextEncoder();
    const progressFrame = `data: ${JSON.stringify({ event: "progress", phase: "sweep", done: 50, total: 100, detail: "sweeping quotes 50/100" })}\n\n`;
    let streamController: ReadableStreamDefaultController<Uint8Array>;
    const stream = new ReadableStream<Uint8Array>({
      start(ctrl) {
        streamController = ctrl;
        ctrl.enqueue(encoder.encode(progressFrame));
        // Do NOT close — hang so we can assert the loading state.
      },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(stream, { status: 200, headers: { "Content-Type": "text/event-stream" } }),
    );

    render(<ScreenerPanel />);
    fireEvent.click(screen.getByTestId("run-screener-button"));

    await waitFor(() => {
      expect(screen.getByTestId("screener-progress")).toBeInTheDocument();
      expect(screen.getByText(/sweeping quotes 50\/100/i)).toBeInTheDocument();
    });

    // Clean up the hanging stream.
    streamController!.close();
  });

  it("result with partial=true renders the PARTIAL badge and coverage line", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(makeStreamResponse(RESULT_WITH_PARTIAL));
    render(<ScreenerPanel />);
    fireEvent.click(screen.getByTestId("run-screener-button"));

    await waitFor(() => {
      expect(screen.getByTestId("partial-badge")).toBeInTheDocument();
      expect(screen.getByText(/screened 100 of 500/)).toBeInTheDocument();
    });
  });

  it("partial=true without coverage still shows the PARTIAL badge", async () => {
    const resultPartialNoCoverage: ScreenerResult = {
      ...RESULT_SAMPLE,
      partial: true,
      coverage: null,
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(makeStreamResponse(resultPartialNoCoverage));
    render(<ScreenerPanel />);
    fireEvent.click(screen.getByTestId("run-screener-button"));

    await waitFor(() => {
      expect(screen.getByTestId("partial-badge")).toBeInTheDocument();
    });
  });

  it("result with freshness renders all three tiers with correct labels", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(makeStreamResponse(RESULT_WITH_PARTIAL));
    render(<ScreenerPanel />);
    fireEvent.click(screen.getByTestId("run-screener-button"));

    await waitFor(() => {
      // All three freshness labels must appear.
      expect(screen.getByText(/quotes .* ago/)).toBeInTheDocument();
      expect(screen.getByText(/valuation .* ago/)).toBeInTheDocument();
      expect(screen.getByText(/deep fields .* ago/)).toBeInTheDocument();
    });
  });

  it("saved-screens strip: save, load, and delete a screen", async () => {
    render(<ScreenerPanel />);
    // Open the save input.
    fireEvent.click(screen.getByTestId("open-save-screen"));
    const input = screen.getByTestId("save-screen-input");
    fireEvent.change(input, { target: { value: "My Value Screen" } });
    fireEvent.click(screen.getByTestId("save-screen-confirm"));

    // The saved chip appears.
    await waitFor(() => {
      expect(screen.getByTestId("load-screen-My Value Screen")).toBeInTheDocument();
    });

    // Load it back.
    fireEvent.click(screen.getByTestId("load-screen-My Value Screen"));
    // The store reflects the loaded screen name.
    expect(useScreenerStore.getState().savedScreens[0]!.name).toBe("My Value Screen");

    // Delete it.
    fireEvent.click(screen.getByTestId("delete-screen-My Value Screen"));
    await waitFor(() => {
      expect(screen.queryByTestId("load-screen-My Value Screen")).not.toBeInTheDocument();
    });
    expect(useScreenerStore.getState().savedScreens).toHaveLength(0);
  });
});
