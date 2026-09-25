import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Profiler } from "react";
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
// R15-UI-091: the untouched-chart indicator-seeding effect hits this — default
// to an empty suggested set so a freshly rendered `<ChartPanel />` in an
// existing test keeps its prior (empty) starting selection unless a test
// overrides the resolved value itself.
const suggestedIndicatorsMock = vi.fn().mockResolvedValue({ indicators: [] });

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    sidecarApi: { history: (...args: unknown[]) => historyMock(...args) },
    sidecarGet: (...args: unknown[]) => suggestedIndicatorsMock(...args),
  };
});

vi.mock("./api", () => ({
  fetchIndicators: (...args: unknown[]) => fetchIndicatorsMock(...args),
}));

import { resetChartCommandStoreForTests, useChartCommandStore } from "@/store/chart-command";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useChartSyncBus } from "@/store/chart-sync";
import { resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";

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
  // Untouched by default — most existing tests exercise a manual toggle and
  // must not have the R15-UI-091 seed silently pre-populate `selected`.
  suggestedIndicatorsMock.mockResolvedValue({ indicators: [] });
  useChartDrawingsStore.setState({ byPanel: {}, views: {} });
  resetSettingsStoreForTests();
  useChartSyncBus.setState({
    crosshair: null,
    visibleRange: null,
    symbol: null,
    subscriptions: {},
  });
});

afterEach(() => {
  cleanup();
  resetChartCommandStoreForTests();
});

describe("ChartPanel", () => {
  it("loads SPY at the 1d timeframe by default", async () => {
    render(<ChartPanel />);
    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("SPY", "1d", undefined, "equity", undefined);
    });
    expect(await screen.findByText(/via yfinance/)).toBeInTheDocument();
  });

  it("an untouched fresh panel seeds the suggested indicator set for its (asset class, timeframe) (R15-UI-091)", async () => {
    suggestedIndicatorsMock.mockResolvedValue({ indicators: ["ema:9", "ema:21", "vwap", "rsi"] });
    render(<ChartPanel />);
    await waitFor(() => {
      expect(suggestedIndicatorsMock).toHaveBeenCalledWith("/indicators/suggested", {
        timeframe: "1d",
        asset_class: "equity",
      });
    });
    await waitFor(() => {
      expect(fetchIndicatorsMock).toHaveBeenCalledWith(
        "SPY",
        expect.arrayContaining(["ema:9", "ema:21", "vwap", "rsi"]),
        "1d",
        "equity",
        undefined,
      );
    });
  });

  it("re-seeds the suggested set on a timeframe change while untouched, but stops once the user edits", async () => {
    suggestedIndicatorsMock.mockResolvedValueOnce({ indicators: ["ma", "volume", "rsi", "macd"] });
    render(<ChartPanel />);
    await waitFor(() => expect(suggestedIndicatorsMock).toHaveBeenCalledTimes(1));

    // A user edit (toggle) turns off further auto-seeding.
    toggleIndicatorByName("Relative Strength Index");
    suggestedIndicatorsMock.mockClear();

    fireEvent.click(screen.getByRole("button", { name: "1h", pressed: false }));
    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("SPY", "1h", undefined, "equity", undefined);
    });
    // The touched chart's timeframe change never re-fetches the suggested set.
    expect(suggestedIndicatorsMock).not.toHaveBeenCalled();
  });

  it("a saved chart default (already touched) never fetches the suggested set", async () => {
    useSettingsStore
      .getState()
      .setChartDefaults({ symbol: "SPY", timeframe: "1d", indicators: ["ma"] });
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    expect(suggestedIndicatorsMock).not.toHaveBeenCalled();
  });

  it("a fresh panel (no persisted view) opens on the settings chart default (R15-UI-048)", async () => {
    useSettingsStore
      .getState()
      .setChartDefaults({ symbol: "TCS.NS", timeframe: "1h", indicators: ["ema"] });
    historyMock.mockResolvedValue(makeSeries("TCS.NS"));
    render(<ChartPanel />);
    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("TCS.NS", "1h", undefined, "equity", undefined);
    });
  });

  it("a persisted per-panel view still wins over the settings default (R15-UI-020)", async () => {
    useSettingsStore
      .getState()
      .setChartDefaults({ symbol: "TCS.NS", timeframe: "1h", indicators: [] });
    useChartDrawingsStore.getState().setView("chart-A", {
      symbol: "RELIANCE.NS",
      timeframe: "1wk",
      indicators: [],
      compare: null,
    });
    render(<ChartPanel api={{ id: "chart-A" }} />);
    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith(
        "RELIANCE.NS",
        "1wk",
        undefined,
        "equity",
        undefined,
      );
    });
  });

  it('"Make default" persists the current symbol/timeframe/indicators to settings', async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Make default" }));
    expect(useSettingsStore.getState().chartDefaults).toEqual({
      symbol: "SPY",
      timeframe: "1d",
      indicators: [],
    });
  });

  it("does not request indicators until one is selected", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    expect(fetchIndicatorsMock).not.toHaveBeenCalled();
  });

  it("a host command's picked region rides the chart's history and indicator calls (R15-DATA-002)", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    openIndicators();
    fireEvent.click(
      screen.getByRole("button", { name: "Relative Strength Index", pressed: false }),
    );

    historyMock.mockResolvedValue(makeSeries("AMAL"));
    act(() => useChartCommandStore.getState().loadSymbol("AMAL", undefined, "US"));

    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("AMAL", "1d", undefined, "equity", "US");
    });
    await waitFor(() => {
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("AMAL", ["rsi"], "1d", "equity", "US");
    });
  });

  it("fetches an indicator server-side when toggled on in the popover", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());

    openIndicators();
    fireEvent.click(
      screen.getByRole("button", { name: "Relative Strength Index", pressed: false }),
    );

    await waitFor(() => {
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("SPY", ["rsi"], "1d", "equity", undefined);
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
      expect(historyMock).toHaveBeenCalledWith("SPY", "1h", undefined, "equity", undefined);
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("SPY", ["rsi"], "1h", "equity", undefined);
    });
  });

  it("loads a new symbol when the symbol form is submitted", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalledTimes(1));

    const input = screen.getByLabelText("Symbol");
    fireEvent.change(input, { target: { value: "nvda" } });
    fireEvent.click(screen.getByRole("button", { name: "Load" }));

    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("NVDA", "1d", undefined, "equity", undefined);
    });
  });

  it("charts a crypto pair under the crypto asset class (R15-DATA-081)", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "btc/usdt" } });
    fireEvent.click(screen.getByRole("button", { name: "Load" }));

    await waitFor(() => {
      expect(historyMock).toHaveBeenCalledWith("BTC/USDT", "1d", undefined, "crypto", undefined);
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

  it("a failed /indicators after a symbol change leaves no overlay of the old symbol (R15-UI-023)", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    toggleIndicatorByName("Relative Strength Index");
    await waitFor(() =>
      expect(chartApi.addSeries.mock.calls.filter(([type]) => type === "Line")).toHaveLength(2),
    );
    const drawn = chartApi.addSeries.mock.results
      .filter((_, i) => chartApi.addSeries.mock.calls[i]?.[0] === "Line")
      .map((r) => r.value as unknown);

    fetchIndicatorsMock.mockRejectedValueOnce(new SidecarError(502, "indicators down"));
    historyMock.mockResolvedValueOnce(makeSeries("RELIANCE.NS"));
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "RELIANCE.NS" } });
    fireEvent.click(screen.getByRole("button", { name: "Load" }));

    expect(await screen.findByText(/indicators down \(502\)/)).toBeInTheDocument();
    const removed = chartApi.removeSeries.mock.calls.map(([s]) => s as unknown);
    for (const series of drawn) expect(removed).toContain(series);
  });

  it("does not draw indicators before their own symbol's candles land (R15-UI-023)", async () => {
    render(<ChartPanel />);
    await waitFor(() => expect(historyMock).toHaveBeenCalledTimes(1));
    let resolveHistory: (series: OHLCVSeries) => void = () => {};
    historyMock.mockReturnValueOnce(new Promise((resolve) => (resolveHistory = resolve)));
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "TCS.NS" } });
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    await waitFor(() =>
      expect(historyMock).toHaveBeenCalledWith("TCS.NS", "1d", undefined, "equity", undefined),
    );

    toggleIndicatorByName("Relative Strength Index");
    await waitFor(() =>
      expect(fetchIndicatorsMock).toHaveBeenCalledWith(
        "TCS.NS",
        ["rsi"],
        "1d",
        "equity",
        undefined,
      ),
    );
    await Promise.resolve();
    expect(chartApi.addSeries.mock.calls.filter(([type]) => type === "Line")).toHaveLength(0);

    resolveHistory(makeSeries("TCS.NS"));
    await waitFor(() =>
      expect(chartApi.addSeries.mock.calls.filter(([type]) => type === "Line")).toHaveLength(2),
    );
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
      expect(fetchIndicatorsMock).toHaveBeenCalledWith(
        "SPY",
        ["macd", "rsi"],
        "1d",
        "equity",
        undefined,
      );
    });
    const chipRow = screen.getByTestId("indicator-chip-row");
    expect(chipRow).toHaveTextContent("RSI");
    expect(chipRow).toHaveTextContent("MACD");

    fireEvent.click(screen.getByRole("button", { name: "Remove RSI" }));

    await waitFor(() => {
      expect(fetchIndicatorsMock).toHaveBeenCalledWith("SPY", ["macd"], "1d", "equity", undefined);
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

  describe("drawing input (R15-UI-022)", () => {
    type ClickHandler = (param: Record<string, unknown>) => void;
    const click = (param: Record<string, unknown>) => {
      const handler = chartApi.subscribeClick.mock.calls.at(-1)?.[0] as ClickHandler;
      act(() => handler(param));
    };
    const arm = async (toolName: string) => {
      render(<ChartPanel api={{ id: "chart-A" }} />);
      await waitFor(() => expect(historyMock).toHaveBeenCalled());
      openDraw();
      fireEvent.click(screen.getByRole("button", { name: toolName }));
    };
    const stored = () => useChartDrawingsStore.getState().getDrawings("chart-A");

    it("anchors at the clicked price, not the bar's close", async () => {
      await arm("Horizontal line");
      candleSeries.coordinateToPrice.mockReturnValueOnce(2.9);
      click({
        time: 1767225600,
        logical: 0,
        point: { x: 10, y: 40 },
        seriesData: new Map([[candleSeries, { close: 1.5 }]]),
      });
      expect(candleSeries.coordinateToPrice).toHaveBeenCalledWith(40);
      expect(stored()[0]?.points).toEqual([{ time: 1767225600, price: 2.9 }]);
    });

    it("keeps a click past the last bar placeable by its logical index", async () => {
      await arm("Trendline");
      click({ time: undefined, logical: 5, point: { x: 500, y: 40 } });
      click({ time: undefined, logical: 8, point: { x: 560, y: 60 } });
      expect(stored()[0]?.points).toEqual([
        { time: null, price: 100, logical: 5 },
        { time: null, price: 100, logical: 8 },
      ]);
    });

    it("takes the Text label from the inline prompt", async () => {
      await arm("Text label");
      click({ time: 1767225600, logical: 0, point: { x: 10, y: 40 } });
      expect(stored()).toHaveLength(0);
      fireEvent.change(screen.getByLabelText("Drawing text"), { target: { value: "support" } });
      fireEvent.click(screen.getByRole("button", { name: "Add" }));
      expect(stored()[0]?.kindOptions).toEqual({ text: "support", fontSize: 12 });
      expect(screen.queryByLabelText("Drawing text")).toBeNull();
    });

    it("disables a locked drawing's delete control", async () => {
      await arm("Horizontal line");
      click({ time: 1767225600, logical: 0, point: { x: 10, y: 40 } });
      fireEvent.click(screen.getByRole("button", { name: "Lock drawing" }));
      expect(screen.getByRole("button", { name: "Delete drawing" })).toBeDisabled();
      fireEvent.click(screen.getByRole("button", { name: /Clear drawings/ }));
      expect(stored()).toHaveLength(1);
    });
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
      symbol: "SPY",
      timeframe: "1d",
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

  it("opens on its persisted view and shows only that chart's drawings (R15-UI-020)", async () => {
    useChartDrawingsStore.getState().setView("chart-A", {
      symbol: "TCS.NS",
      timeframe: "1wk",
      indicators: [],
      compare: null,
    });
    useChartDrawingsStore.getState().addDrawing("chart-A", {
      id: "rel-level",
      panelId: "chart-A",
      symbol: "RELIANCE.NS",
      timeframe: "1wk",
      kind: "horizontal-line",
      points: [{ time: null, price: 2450 }],
      style: { color: "#e9a94d", lineWidth: 1 },
      createdAt: 0,
    });
    render(<ChartPanel api={{ id: "chart-A" }} />);

    await waitFor(() =>
      expect(historyMock).toHaveBeenCalledWith("TCS.NS", "1wk", undefined, "equity", undefined),
    );
    expect(screen.queryByRole("button", { name: "Select horizontal-line" })).toBeNull();

    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "RELIANCE.NS" } });
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    expect(
      await screen.findByRole("button", { name: "Select horizontal-line" }),
    ).toBeInTheDocument();
    expect(useChartDrawingsStore.getState().views["chart-A"]?.symbol).toBe("RELIANCE.NS");
  });

  it("Backspace typed into a field outside the chart keeps the selected drawing (R15-UI-021)", async () => {
    useChartDrawingsStore.getState().addDrawing("chart-A", {
      id: "draw-1",
      panelId: "chart-A",
      symbol: "SPY",
      timeframe: "1d",
      kind: "trendline",
      points: [
        { time: 1, price: 100 },
        { time: 2, price: 110 },
      ],
      style: { color: "#e9a94d", lineWidth: 1 },
      createdAt: 0,
    });
    render(
      <>
        <textarea aria-label="Composer" />
        <ChartPanel api={{ id: "chart-A" }} />
      </>,
    );
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Select trendline" }));

    fireEvent.keyDown(screen.getByLabelText("Composer"), { key: "Backspace" });
    fireEvent.keyDown(screen.getByLabelText("Symbol"), { key: "Backspace" });
    expect(useChartDrawingsStore.getState().getDrawings("chart-A")).toHaveLength(1);

    // The same key on the chart's own (non-text) control does delete.
    fireEvent.keyDown(screen.getByRole("button", { name: "Select trendline" }), {
      key: "Backspace",
    });
    expect(useChartDrawingsStore.getState().getDrawings("chart-A")).toHaveLength(0);
  });

  it("a locked drawing survives Delete (R15-UI-021)", async () => {
    useChartDrawingsStore.getState().addDrawing("chart-A", {
      id: "draw-1",
      panelId: "chart-A",
      symbol: "SPY",
      timeframe: "1d",
      kind: "trendline",
      points: [
        { time: 1, price: 100 },
        { time: 2, price: 110 },
      ],
      style: { color: "#e9a94d", lineWidth: 1 },
      createdAt: 0,
      locked: true,
    });
    render(<ChartPanel api={{ id: "chart-A" }} />);
    await waitFor(() => expect(historyMock).toHaveBeenCalled());
    const chip = screen.getByRole("button", { name: "Select trendline" });
    fireEvent.click(chip);

    fireEvent.keyDown(chip, { key: "Delete" });
    expect(useChartDrawingsStore.getState().getDrawings("chart-A")).toHaveLength(1);
  });

  it("Delete with nothing focused still deletes (WebKit leaves a clicked chip unfocused; R15-UI-021)", async () => {
    useChartDrawingsStore.getState().addDrawing("chart-A", {
      id: "draw-1",
      panelId: "chart-A",
      symbol: "SPY",
      timeframe: "1d",
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
    fireEvent.click(screen.getByRole("button", { name: "Select trendline" }));

    fireEvent.keyDown(document.body, { key: "Delete" });
    expect(useChartDrawingsStore.getState().getDrawings("chart-A")).toHaveLength(0);
  });

  it("clears every drawing through the inspector's Clear drawings control", async () => {
    useChartDrawingsStore.getState().addDrawing("chart-A", {
      id: "draw-1",
      panelId: "chart-A",
      symbol: "SPY",
      timeframe: "1d",
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

  it("N crosshair moves on a lone chart cause 0 ChartPanel re-renders (R15-CODE-FRONTEND-023)", async () => {
    let commits = 0;
    render(
      <Profiler id="chart" onRender={() => void commits++}>
        <ChartPanel api={{ id: "chart-A" }} />
      </Profiler>,
    );
    expect(await screen.findByText(/via yfinance/)).toBeInTheDocument();
    const calls = chartApi.subscribeCrosshairMove.mock.calls as unknown as [
      (param: { time?: number }) => void,
    ][];
    const onCrosshair = calls[calls.length - 1][0];
    const before = commits;
    const seqBefore = useChartSyncBus.getState().crosshair?.seq ?? 0;

    act(() => {
      for (let i = 0; i < 25; i++) {
        onCrosshair({ time: 1_700_000_000 + i });
      }
    });

    // The moves were broadcast on the bus…
    expect(useChartSyncBus.getState().crosshair?.seq).toBe(seqBefore + 25);
    // …but the panel itself never re-rendered.
    expect(commits).toBe(before);
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
      expect(historyMock).toHaveBeenCalledWith("QQQ", "1d", undefined, "equity");
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
    const event = usePanelContextBus.getState().lastEventBySource["chart-pub-1"];
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
      const e = usePanelContextBus.getState().lastEventBySource["chart-pub-2"];
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
    expect(usePanelContextBus.getState().lastEventBySource["chart-pub-3"]).toBeDefined();
    unmount();
    expect(usePanelContextBus.getState().lastEventBySource["chart-pub-3"]).toBeUndefined();
  });

  it("with two charts, the focused second chart is the snapshot's focus (R15-AGENT-052)", async () => {
    const { usePanelContextBus } = await import("@/store/panel-context");
    const { captureTerminalState } = await import("@/modules/chat/context-provider");
    usePanelContextBus.setState({ lastEventBySource: {}, focusedSource: null, updatedAt: 0 });
    render(
      <>
        <ChartPanel api={{ id: "chart" }} />
        <ChartPanel api={{ id: "chart-2" }} />
      </>,
    );
    await waitFor(() => expect(historyMock).toHaveBeenCalledTimes(2));
    fireEvent.change(screen.getAllByLabelText("Symbol")[1]!, { target: { value: "INFY" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Load" })[1]!);
    await waitFor(() =>
      expect(historyMock).toHaveBeenCalledWith("INFY", "1d", undefined, "equity", undefined),
    );
    // PanelHost focuses the dockview id.
    usePanelContextBus.getState().setFocusedSource("chart-2");

    const state = captureTerminalState();
    expect(state.focusedSymbol).toBe("INFY");
    // The chart the runtime's preamble picks: the one whose panelId is focused.
    expect(state.charts.find((c) => c.panelId === state.focusedPanel)?.symbol).toBe("INFY");
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
        (c) => (c[0] as { source: string }).source === "chart-pub-4",
      );
      expect(calls.length).toBeGreaterThan(0);
      expect(calls.length).toBeLessThan(10);
    } finally {
      usePanelContextBus.setState({ publish: realPublish });
    }
  });
});
