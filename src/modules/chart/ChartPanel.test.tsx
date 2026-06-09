import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SidecarError } from "@/lib/sidecar-client";
import type { IndicatorResponse, OHLCVSeries } from "../../../types/data";

// --- lightweight-charts mock ------------------------------------------------
// The real library renders to a <canvas>, which jsdom does not implement. The
// mock records calls so the test can assert on the panel's data wiring without
// a real chart. `chartApi` and `candleSeries` are module-scoped so assertions
// can reach them.
const candleSeries = {
  setData: vi.fn(),
  attachPrimitive: vi.fn(),
  detachPrimitive: vi.fn(),
  coordinateToPrice: vi.fn(() => 100),
  priceToCoordinate: vi.fn(() => 100),
};
const timeScale = {
  fitContent: vi.fn(),
  setVisibleRange: vi.fn(),
  getVisibleRange: vi.fn(() => null),
  subscribeVisibleLogicalRangeChange: vi.fn(),
  unsubscribeVisibleLogicalRangeChange: vi.fn(),
  timeToCoordinate: vi.fn(() => 0),
};
const chartApi = {
  // First addSeries call is the candlestick series; subsequent calls are
  // indicator line series. The candle ref needs `attachPrimitive` so the
  // panel can wire the Volume Profile histogram into it.
  addSeries: vi.fn((type: unknown) =>
    type === "Candlestick" ? candleSeries : { setData: vi.fn(), priceScaleId: vi.fn() },
  ),
  removeSeries: vi.fn(),
  timeScale: vi.fn(() => timeScale),
  remove: vi.fn(),
  subscribeClick: vi.fn(),
  unsubscribeClick: vi.fn(),
  subscribeCrosshairMove: vi.fn(),
  unsubscribeCrosshairMove: vi.fn(),
  setCrosshairPosition: vi.fn(),
};

// Markers plugin handle returned by `createSeriesMarkers`. Module-scoped so
// the Parabolic SAR test can assert on `setMarkers` / `detach` calls.
const sarMarkersHandle = {
  setMarkers: vi.fn(),
  detach: vi.fn(),
};
const createSeriesMarkersMock = vi.fn(() => sarMarkersHandle);

vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => chartApi),
  CandlestickSeries: "Candlestick",
  LineSeries: "Line",
  createSeriesMarkers: (...args: unknown[]) =>
    (createSeriesMarkersMock as (...inner: unknown[]) => unknown)(...args),
}));

// --- volume profile primitive mock -----------------------------------------
// vitest's `vi.fn()` does not satisfy `new` correctly when bound to a class
// name; use a real ES class whose ctor and method delegate to module-scoped
// spies the assertions can reach.
const volumeProfileSetBuckets = vi.fn();
const volumeProfileCtor = vi.fn();

vi.mock("./volume-profile-primitive", () => {
  class MockVolumeProfilePrimitive {
    constructor() {
      volumeProfileCtor();
    }
    setBuckets(buckets: unknown) {
      volumeProfileSetBuckets(buckets);
    }
  }
  return { VolumeProfilePrimitive: MockVolumeProfilePrimitive };
});

// --- ichimoku cloud primitive mock -----------------------------------------
const ichimokuCloudSetBands = vi.fn();
const ichimokuCloudCtor = vi.fn();

vi.mock("./ichimoku-cloud-primitive", () => {
  class MockIchimokuCloudPrimitive {
    constructor() {
      ichimokuCloudCtor();
    }
    setBands(senkouA: unknown, senkouB: unknown) {
      ichimokuCloudSetBands(senkouA, senkouB);
    }
  }
  return { IchimokuCloudPrimitive: MockIchimokuCloudPrimitive };
});

// --- sidecar-client / api mocks --------------------------------------------
const historyMock = vi.fn();
const fetchIndicatorsMock = vi.fn();

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    sidecarApi: { history: (...args: unknown[]) => historyMock(...args) },
  };
});

vi.mock("./api", () => ({
  fetchIndicators: (...args: unknown[]) => fetchIndicatorsMock(...args),
}));

import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useChartSyncBus } from "@/store/chart-sync";

import ChartPanel from "./ChartPanel";
import { CATEGORY_LABELS, INDICATOR_CATALOG } from "./indicators";
import { DRAW_TOOLS } from "./toolbar";

// --- fixtures ---------------------------------------------------------------
function makeSeries(symbol: string): OHLCVSeries {
  return {
    symbol,
    timeframe: "1d",
    provider: "yfinance",
    bars: [
      { timestamp: "2026-01-01T00:00:00Z", open: 1, high: 2, low: 0.5, close: 1.5, volume: 100 },
      { timestamp: "2026-01-02T00:00:00Z", open: 1.5, high: 3, low: 1, close: 2.5, volume: 120 },
    ],
  };
}

function makeIndicatorResponse(): IndicatorResponse {
  return {
    symbol: "SPY",
    timeframe: "1d",
    provider: "yfinance",
    indicators: [
      {
        name: "sma",
        panel: "price",
        lines: [
          {
            label: "SMA(20)",
            points: [
              { time: "2026-01-01T00:00:00Z", value: null },
              { time: "2026-01-02T00:00:00Z", value: 2.0 },
            ],
          },
        ],
      },
      {
        name: "rsi",
        panel: "separate",
        lines: [
          {
            label: "RSI(14)",
            points: [
              { time: "2026-01-01T00:00:00Z", value: 55 },
              { time: "2026-01-02T00:00:00Z", value: 60 },
            ],
          },
        ],
      },
    ],
    volume_profile: null,
  };
}

// --- popover helpers ---------------------------------------------------------
// Trigger accessible names start with the visible label; an active count may
// follow ("Indicators 2"), so the lookups are prefix regexes.
function openDraw() {
  fireEvent.click(screen.getByRole("button", { name: /^Draw\b/ }));
}
function openIndicators() {
  fireEvent.click(screen.getByRole("button", { name: /^Indicators\b/ }));
}
function openCompare() {
  fireEvent.click(screen.getByRole("button", { name: /^Compare\b/ }));
}
function openSync() {
  fireEvent.click(screen.getByRole("button", { name: /^Sync\b/ }));
}

/** Open the Indicators popover and toggle one indicator by its full name. */
function toggleIndicatorByName(menuLabel: string) {
  openIndicators();
  fireEvent.click(screen.getByRole("button", { name: menuLabel }));
  // Close the popover so follow-up queries see only the idle surface.
  fireEvent.keyDown(document, { key: "Escape" });
}

beforeEach(() => {
  vi.clearAllMocks();
  historyMock.mockResolvedValue(makeSeries("SPY"));
  fetchIndicatorsMock.mockResolvedValue(makeIndicatorResponse());
  useChartDrawingsStore.setState({ byPanel: {} });
  useChartSyncBus.setState({
    crosshair: null,
    visibleRange: null,
    symbol: null,
    subscriptions: {},
  });
});

afterEach(() => {
  cleanup();
});

describe("ChartPanel", () => {
  it("loads SPY at the 1d timeframe by default", async () => {
    render(<ChartPanel />);
    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("SPY", "1d");
    });
    expect(await screen.findByText(/via yfinance/)).toBeInTheDocument();
  });

  it("does not request indicators until one is selected", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    expect(fetchIndicatorsMock).not.toHaveBeenCalled();
  });

  it("fetches an indicator server-side when toggled on in the popover", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openIndicators();
    fireEvent.click(
      screen.getByRole("button", { name: "Relative Strength Index", pressed: false }),
    );

    await waitFor(() => {
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("SPY", ["rsi"], "1d");
    });
    // The popover stays open for multi-select; the row reflects the toggle.
    expect(
      screen.getByRole("button", { name: "Relative Strength Index", pressed: true }),
    ).toBeInTheDocument();
  });

  it("re-requests history and indicators when the timeframe changes", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalledTimes(1));

    toggleIndicatorByName("Relative Strength Index");
    await waitFor(() => expect(fetchIndicatorsMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "1h", pressed: false }));

    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("SPY", "1h");
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("SPY", ["rsi"], "1h");
    });
  });

  it("loads a new symbol when the symbol form is submitted", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalledTimes(1));

    const input = screen.getByLabelText("Symbol");
    fireEvent.change(input, { target: { value: "nvda" } });
    fireEvent.click(screen.getByRole("button", { name: "Load" }));

    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("NVDA", "1d");
    });
  });

  it("surfaces a SidecarError from the history call", async () => {
    historyMock.mockRejectedValueOnce(new SidecarError(502, "provider down"));
    render(<ChartPanel />);
    expect(await screen.findByText(/provider down \(502\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("surfaces a SidecarError from the indicator call on the chip row", async () => {
    fetchIndicatorsMock.mockRejectedValueOnce(new SidecarError(400, "bad indicator"));
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    toggleIndicatorByName("Moving Average Convergence Divergence");

    expect(await screen.findByText(/bad indicator \(400\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry indicators" })).toBeInTheDocument();
  });

  it("clears all selected indicators from the chip row's Clear all control", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    toggleIndicatorByName("Relative Strength Index");
    await waitFor(() => expect(fetchIndicatorsMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Clear all \(1\)/ }));

    expect(screen.queryByTestId("indicator-chip-row")).toBeNull();
  });

  // --------------------------------------------------------------------------
  // R7 — disclosure toolbar: the indicator wall is gone, popovers carry the
  // full catalog, active selections are chips.
  // --------------------------------------------------------------------------

  it("renders no always-on indicator wall — the catalog only exists inside the popover", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    // No indicator toggle is rendered while the popover is closed.
    for (const def of INDICATOR_CATALOG) {
      expect(screen.queryByRole("button", { name: def.menuLabel })).toBeNull();
    }
    // No category group headers idle below the chart.
    for (const label of Object.values(CATEGORY_LABELS)) {
      expect(screen.queryByText(label)).toBeNull();
    }
    // No earned chip row without an active indicator.
    expect(screen.queryByTestId("indicator-chip-row")).toBeNull();
  });

  it("lists the entire 50-indicator catalog, grouped and spelled out, in the popover", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openIndicators();

    expect(INDICATOR_CATALOG.length).toBe(50);
    for (const def of INDICATOR_CATALOG) {
      expect(screen.getByRole("button", { name: def.menuLabel })).toBeInTheDocument();
    }
    // getAllByText: "Volume" the group header also exact-matches the "Volume"
    // indicator row's name span, so each label asserts ≥1 match.
    for (const label of Object.values(CATEGORY_LABELS)) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it("filters the indicator popover by search query", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openIndicators();
    fireEvent.change(screen.getByLabelText("Search indicators"), {
      target: { value: "bollinger" },
    });

    expect(screen.getByRole("button", { name: "Bollinger Bands" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bollinger Bandwidth" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Relative Strength Index" })).toBeNull();

    // The search also matches terse codes, so "RSI" finds the spelled-out row.
    fireEvent.change(screen.getByLabelText("Search indicators"), { target: { value: "rsi" } });
    expect(screen.getByRole("button", { name: "Relative Strength Index" })).toBeInTheDocument();
  });

  it("renders active indicators as removable chips and prunes the fetch on remove", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openIndicators();
    fireEvent.click(screen.getByRole("button", { name: "Relative Strength Index" }));
    fireEvent.click(screen.getByRole("button", { name: "Moving Average Convergence Divergence" }));
    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => {
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("SPY", ["macd", "rsi"], "1d");
    });
    const chipRow = screen.getByTestId("indicator-chip-row");
    expect(chipRow).toHaveTextContent("RSI");
    expect(chipRow).toHaveTextContent("MACD");

    fireEvent.click(screen.getByRole("button", { name: "Remove RSI" }));

    await waitFor(() => {
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("SPY", ["macd"], "1d");
    });
    expect(screen.queryByRole("button", { name: "Remove RSI" })).toBeNull();
  });

  it("dismisses a popover on Escape without disturbing the armed drawing tool", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openDraw();
    fireEvent.click(screen.getByRole("button", { name: "Trendline" }));
    expect(screen.getByTestId("active-tool-chip")).toBeInTheDocument();

    openIndicators();
    expect(screen.getByLabelText("Search indicators")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByLabelText("Search indicators")).toBeNull();
    // The popover's Escape must not bubble into the chart's disarm handler.
    expect(screen.getByTestId("active-tool-chip")).toBeInTheDocument();
  });

  it("dismisses a popover on outside click", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openIndicators();
    expect(screen.getByLabelText("Search indicators")).toBeInTheDocument();

    fireEvent.mouseDown(document.body);

    expect(screen.queryByLabelText("Search indicators")).toBeNull();
  });

  it("proves functionality parity: every old toolbar control has a new home", async () => {
    render(<ChartPanel api={{ id: "chart-parity" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    // Old row 1 — symbol + Load + 8 timeframes stay directly on the toolbar.
    expect(screen.getByLabelText("Symbol")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load" })).toBeInTheDocument();
    for (const timeframe of ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"]) {
      expect(screen.getByRole("button", { name: timeframe })).toBeInTheDocument();
    }

    // Old row 2 — the ten DRAW codes live in the Draw popover, spelled out.
    const oldDrawToNew: Record<string, string> = {
      Trend: "Trendline",
      "H-Line": "Horizontal line",
      "V-Line": "Vertical line",
      Ray: "Ray",
      Rect: "Rectangle",
      Ellipse: "Ellipse",
      "Fib Retr": "Fibonacci retracement",
      "Fib Ext": "Fibonacci extension",
      Channel: "Parallel channel",
      Text: "Text label",
    };
    openDraw();
    expect(DRAW_TOOLS.length).toBe(10);
    for (const tool of DRAW_TOOLS) {
      expect(oldDrawToNew[tool.chipLabel]).toBe(tool.name);
      expect(screen.getByRole("button", { name: tool.name })).toBeInTheDocument();
    }
    fireEvent.keyDown(document, { key: "Escape" });

    // Old indicator wall — all 50 toggles live in the Indicators popover.
    openIndicators();
    for (const def of INDICATOR_CATALOG) {
      expect(screen.getByRole("button", { name: def.menuLabel })).toBeInTheDocument();
    }
    fireEvent.keyDown(document, { key: "Escape" });

    // Old row 3 — COMPARE symbol + Add live in the Compare popover.
    openCompare();
    expect(screen.getByLabelText("Compare symbol")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });

    // Old SYNC CX/ZM/SY codes — spelled-out toggles in the Sync popover.
    openSync();
    expect(screen.getByRole("button", { name: "Sync crosshair" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sync visibleRange" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sync symbol" })).toBeInTheDocument();
  });

  // --------------------------------------------------------------------------
  // Indicator data wiring (unchanged contracts, new click path)
  // --------------------------------------------------------------------------

  it("attaches a Volume Profile primitive when the indicator is toggled on", async () => {
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [],
      volume_profile: {
        buckets: [
          { price: 100.0, volume: 1_000 },
          { price: 101.0, volume: 2_000 },
        ],
      },
    } satisfies IndicatorResponse);
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    toggleIndicatorByName("Volume Profile");

    await waitFor(() => {
      expect(volumeProfileCtor).toHaveBeenCalled();
    });
    expect(candleSeries.attachPrimitive).toHaveBeenCalled();
    expect(volumeProfileSetBuckets).toHaveBeenCalledWith([
      { price: 100.0, volume: 1_000 },
      { price: 101.0, volume: 2_000 },
    ]);
  });

  it("draws Parabolic SAR as series markers with trend-aware placement", async () => {
    // SPY default fixture: bar 1 closes at 1.5, bar 2 closes at 2.5.
    // SAR < close → uptrend → belowBar; SAR > close → downtrend → aboveBar.
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [
        {
          name: "parabolic_sar",
          panel: "price",
          lines: [
            {
              label: "Parabolic SAR",
              points: [
                { time: "2026-01-01T00:00:00Z", value: 0.8 }, // < 1.5 → uptrend
                { time: "2026-01-02T00:00:00Z", value: 3.0 }, // > 2.5 → downtrend
              ],
            },
          ],
        },
      ],
      volume_profile: null,
    } satisfies IndicatorResponse);

    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    toggleIndicatorByName("Parabolic SAR");

    await waitFor(() => expect(createSeriesMarkersMock).toHaveBeenCalled());
    // The candle series — not a new LineSeries — is the markers' host.
    expect(createSeriesMarkersMock).toHaveBeenCalledWith(
      candleSeries,
      expect.arrayContaining([
        expect.objectContaining({ position: "belowBar", shape: "circle" }),
        expect.objectContaining({ position: "aboveBar", shape: "circle" }),
      ]),
    );
    // No line series should be added for the SAR indicator.
    const lineCalls = chartApi.addSeries.mock.calls.filter(([type]) => type === "Line");
    expect(lineCalls).toHaveLength(0);
  });

  it("detaches Parabolic SAR markers when the indicator chip is removed", async () => {
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [
        {
          name: "parabolic_sar",
          panel: "price",
          lines: [
            {
              label: "Parabolic SAR",
              points: [{ time: "2026-01-02T00:00:00Z", value: 1.0 }],
            },
          ],
        },
      ],
      volume_profile: null,
    } satisfies IndicatorResponse);

    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    toggleIndicatorByName("Parabolic SAR");
    await waitFor(() => expect(createSeriesMarkersMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Remove Parabolic SAR" }));

    await waitFor(() => expect(sarMarkersHandle.detach).toHaveBeenCalled());
  });

  it("detaches the Volume Profile primitive when the indicator chip is removed", async () => {
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [],
      volume_profile: { buckets: [{ price: 100.0, volume: 500 }] },
    } satisfies IndicatorResponse);
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    toggleIndicatorByName("Volume Profile");
    await waitFor(() => expect(candleSeries.attachPrimitive).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Remove Volume Profile" }));

    await waitFor(() => {
      expect(candleSeries.detachPrimitive).toHaveBeenCalled();
    });
  });

  it("attaches the Ichimoku cloud primitive when the indicator is toggled on", async () => {
    fetchIndicatorsMock.mockResolvedValueOnce({
      symbol: "SPY",
      timeframe: "1d",
      provider: "yfinance",
      indicators: [
        {
          name: "ichimoku",
          panel: "price",
          lines: [
            { label: "Tenkan-sen", points: [{ time: "2026-01-02T00:00:00Z", value: 1.5 }] },
            { label: "Kijun-sen", points: [{ time: "2026-01-02T00:00:00Z", value: 1.6 }] },
            { label: "Senkou Span A", points: [{ time: "2026-01-02T00:00:00Z", value: 1.7 }] },
            { label: "Senkou Span B", points: [{ time: "2026-01-02T00:00:00Z", value: 1.4 }] },
            { label: "Chikou Span", points: [{ time: "2026-01-01T00:00:00Z", value: 1.3 }] },
          ],
        },
      ],
      volume_profile: null,
    } satisfies IndicatorResponse);

    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    toggleIndicatorByName("Ichimoku Cloud");

    await waitFor(() => expect(ichimokuCloudCtor).toHaveBeenCalled());
    expect(candleSeries.attachPrimitive).toHaveBeenCalled();
    expect(ichimokuCloudSetBands).toHaveBeenCalledWith(
      [{ time: "2026-01-02T00:00:00Z", value: 1.7 }],
      [{ time: "2026-01-02T00:00:00Z", value: 1.4 }],
    );
  });

  // ------------------------------------------------------------------------
  // Drawing tools, sync bus, comparison overlay (popover click paths)
  // ------------------------------------------------------------------------

  it("lists the ten drawing tools with full names and points-required meta", async () => {
    render(<ChartPanel api={{ id: "chart-A" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openDraw();
    for (const tool of DRAW_TOOLS) {
      expect(screen.getByRole("button", { name: tool.name })).toBeInTheDocument();
    }
  });

  it("arms a drawing tool from the popover and shows the active-tool chip", async () => {
    render(<ChartPanel api={{ id: "chart-A" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openDraw();
    fireEvent.click(screen.getByRole("button", { name: "Trendline" }));

    // Arming closes the popover (one-shot pick, not a multi-select).
    expect(screen.queryByRole("button", { name: "Horizontal line" })).toBeNull();
    const chip = screen.getByTestId("active-tool-chip");
    expect(chip).toHaveTextContent("Trend");
    expect(chip).toHaveTextContent("2 points left");
  });

  it("disarms the active tool from the chip's [x]", async () => {
    render(<ChartPanel api={{ id: "chart-A" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openDraw();
    fireEvent.click(screen.getByRole("button", { name: "Horizontal line" }));
    expect(screen.getByTestId("active-tool-chip")).toHaveTextContent("1 point left");

    fireEvent.click(screen.getByRole("button", { name: "Disarm drawing tool" }));

    expect(screen.queryByTestId("active-tool-chip")).toBeNull();
  });

  it("renders existing drawings from the store on mount and exposes a delete control", async () => {
    useChartDrawingsStore.getState().addDrawing("chart-A", {
      id: "draw-1",
      panelId: "chart-A",
      kind: "rectangle",
      points: [
        { time: 1, price: 100 },
        { time: 2, price: 110 },
      ],
      style: { color: "#e9a94d", lineWidth: 1 },
      createdAt: 0,
    });
    render(<ChartPanel api={{ id: "chart-A" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    expect(screen.getByRole("button", { name: "Select rectangle" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete drawing" }));

    expect(useChartDrawingsStore.getState().getDrawings("chart-A")).toHaveLength(0);
  });

  it("clears every drawing through the inspector's Clear drawings control", async () => {
    useChartDrawingsStore.getState().addDrawing("chart-A", {
      id: "draw-1",
      panelId: "chart-A",
      kind: "trendline",
      points: [
        { time: 1, price: 100 },
        { time: 2, price: 110 },
      ],
      style: { color: "#e9a94d", lineWidth: 1 },
      createdAt: 0,
    });
    render(<ChartPanel api={{ id: "chart-A" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Clear drawings \(1\)/ }));

    expect(useChartDrawingsStore.getState().getDrawings("chart-A")).toHaveLength(0);
  });

  it("toggles sync subscriptions through the Sync popover", async () => {
    render(<ChartPanel api={{ id: "chart-A" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openSync();
    fireEvent.click(screen.getByRole("button", { name: "Sync crosshair" }));

    const subs = useChartSyncBus.getState().subscriptions["chart-A"];
    expect(subs?.crosshair).toBe(true);
    expect(subs?.symbol).toBe(false);
  });

  it("submits a comparison-overlay symbol from the popover and toggles its normalization chip", async () => {
    render(<ChartPanel api={{ id: "chart-A" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalledTimes(1));

    openCompare();
    fireEvent.change(screen.getByLabelText("Compare symbol"), { target: { value: "qqq" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("QQQ", "1d");
    });
    // Submitting closes the popover; the overlay lives on as a toolbar chip.
    expect(screen.queryByRole("button", { name: "Add" })).toBeNull();
    expect(screen.getByTestId("compare-chip")).toHaveTextContent("QQQ");
    expect(
      screen.getByRole("button", { name: "Normalize comparison", pressed: true }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Normalize comparison" }));
    expect(
      screen.getByRole("button", { name: "Normalize comparison", pressed: false }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Remove comparison overlay" }));
    expect(screen.queryByTestId("compare-chip")).toBeNull();
  });

  it("uses a stable per-instance panelId from dockview's panel api when present", async () => {
    render(<ChartPanel api={{ id: "chart-special-id" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    expect(document.querySelector('[data-panel-id="chart-special-id"]')).not.toBeNull();
  });

  // Phase-3 Teammate C: per-panel context publisher tests.
  it("publishes a chart snapshot to the panel-context bus on mount", async () => {
    const { usePanelContextBus } = await import("@/store/panel-context");
    usePanelContextBus.setState({
      lastEventBySource: {},
      focusedSource: null,
      updatedAt: 0,
    });
    render(<ChartPanel api={{ id: "chart-pub-1" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    const event = usePanelContextBus.getState().lastEventBySource["chart-chart-pub-1"];
    expect(event).toBeDefined();
    expect(event!.kind).toBe("snapshot");
    expect((event!.payload as { symbol: string }).symbol).toBe("SPY");
    expect((event!.payload as { timeframe: string }).timeframe).toBe("1d");
    expect((event!.payload as { drawingCount: number }).drawingCount).toBe(0);
  });

  it("re-publishes when the timeframe changes", async () => {
    const { usePanelContextBus } = await import("@/store/panel-context");
    usePanelContextBus.setState({
      lastEventBySource: {},
      focusedSource: null,
      updatedAt: 0,
    });
    render(<ChartPanel api={{ id: "chart-pub-2" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "1h", pressed: false }));
    await waitFor(() => {
      const e = usePanelContextBus.getState().lastEventBySource["chart-chart-pub-2"];
      expect((e!.payload as { timeframe: string }).timeframe).toBe("1h");
    });
  });

  it("unregisters its panel-context source on unmount", async () => {
    const { usePanelContextBus } = await import("@/store/panel-context");
    usePanelContextBus.setState({
      lastEventBySource: {},
      focusedSource: null,
      updatedAt: 0,
    });
    const { unmount } = render(<ChartPanel api={{ id: "chart-pub-3" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    expect(usePanelContextBus.getState().lastEventBySource["chart-chart-pub-3"]).toBeDefined();
    unmount();
    expect(usePanelContextBus.getState().lastEventBySource["chart-chart-pub-3"]).toBeUndefined();
  });

  it("publish does not trigger an infinite re-render loop", async () => {
    const { usePanelContextBus } = await import("@/store/panel-context");
    usePanelContextBus.setState({
      lastEventBySource: {},
      focusedSource: null,
      updatedAt: 0,
    });
    const realPublish = usePanelContextBus.getState().publish;
    const publishSpy = vi.fn(realPublish);
    usePanelContextBus.setState({ publish: publishSpy });
    try {
      render(<ChartPanel api={{ id: "chart-pub-4" }} />);
      await waitFor(() => expect(historyMock).toHaveBeenCalled());
      const calls = publishSpy.mock.calls.filter(
        (c) => (c[0] as { source: string }).source === "chart-chart-pub-4",
      );
      expect(calls.length).toBeGreaterThan(0);
      expect(calls.length).toBeLessThan(10);
    } finally {
      usePanelContextBus.setState({ publish: realPublish });
    }
  });
});
