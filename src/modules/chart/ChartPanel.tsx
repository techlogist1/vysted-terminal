"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CandlestickSeries,
  createChart,
  createSeriesMarkers,
  LineSeries,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type LineData,
  type LogicalRange,
  type MouseEventParams,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";

import { Button } from "@/components/ui/button";
import { SidecarError, sidecarApi } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { newDrawingId, useChartDrawingsStore } from "@/store/chart-drawings";
import {
  selectSubscriptions,
  useChartSyncBus,
  type CrosshairBroadcast,
  type SymbolBroadcast,
  type VisibleRangeBroadcast,
} from "@/store/chart-sync";
import type { IndicatorResponse, OHLCVSeries } from "../../../types/data";
import type { DrawingKind, DrawingPoint, DrawingSpec } from "../../../types/drawings";
import { fetchIndicators } from "./api";
import { DrawingPrimitive } from "./drawings/base";
import { createDrawingPrimitive, DEFAULT_DRAWING_STYLE, pointsRequired } from "./drawings/factory";
import { IchimokuCloudPrimitive } from "./ichimoku-cloud-primitive";
import { INDICATOR_COLORS, indicatorsByCategory, type IndicatorDef } from "./indicators";
import { VolumeProfilePrimitive } from "./volume-profile-primitive";

/** Bar intervals the chart panel exposes — mirrors the sidecar's `timeframe`. */
const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

const DEFAULT_SYMBOL = "SPY";
const DEFAULT_TIMEFRAME: Timeframe = "1d";

/** The ten drawing kinds shown in the toolbar, in display order. */
const DRAWING_TOOLS: ReadonlyArray<{ kind: DrawingKind; label: string }> = [
  { kind: "trendline", label: "Trend" },
  { kind: "horizontal-line", label: "H-Line" },
  { kind: "vertical-line", label: "V-Line" },
  { kind: "ray", label: "Ray" },
  { kind: "rectangle", label: "Rect" },
  { kind: "ellipse", label: "Ellipse" },
  { kind: "fib-retracement", label: "Fib Retr" },
  { kind: "fib-extension", label: "Fib Ext" },
  { kind: "parallel-channel", label: "Channel" },
  { kind: "text", label: "Text" },
];

/** Vysted dark palette, applied to the lightweight-charts canvas. */
const CHART_THEME = {
  layout: {
    background: { color: "#1c1916" }, // charcoal-900
    textColor: "#c9c2b2", // charcoal-200
    fontFamily: "var(--font-jetbrains-mono), ui-monospace, 'SF Mono', 'Cascadia Mono', monospace",
  },
  grid: {
    vertLines: { color: "#2a2620" }, // charcoal-800
    horzLines: { color: "#2a2620" },
  },
  rightPriceScale: { borderColor: "#3a352c" }, // charcoal-700
  timeScale: { borderColor: "#3a352c", timeVisible: true, secondsVisible: false },
  crosshair: { vertLine: { color: "#4d4639" }, horzLine: { color: "#4d4639" } },
} as const;

const CANDLE_THEME = {
  upColor: "#7faa6b", // positive
  downColor: "#c8654b", // negative
  borderUpColor: "#7faa6b",
  borderDownColor: "#c8654b",
  wickUpColor: "#7faa6b",
  wickDownColor: "#c8654b",
} as const;

const COMPARISON_LINE_COLOR = "#8fa67c"; // sage-400

/** Stable empty drawings reference so the store selector stays referentially equal. */
const EMPTY_DRAWINGS: readonly DrawingSpec[] = Object.freeze([]);

/** Convert an ISO-8601 timestamp to the lightweight-charts UTCTimestamp (seconds). */
function toChartTime(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

/**
 * Map an OHLCV series to candlestick data. Bars are de-duplicated by timestamp
 * and sorted ascending — lightweight-charts rejects unordered or repeated
 * times, and provider feeds occasionally include both.
 */
function toCandlestickData(series: OHLCVSeries): CandlestickData<Time>[] {
  const byTime = new Map<number, CandlestickData<Time>>();
  for (const bar of series.bars) {
    const time = toChartTime(bar.timestamp);
    if (Number.isNaN(time)) {
      continue;
    }
    byTime.set(time, {
      time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    });
  }
  return [...byTime.values()].sort((a, b) => (a.time as number) - (b.time as number));
}

/** Map an indicator line's points to lightweight-charts line data, dropping gaps. */
function toLineData(points: { time: string; value: number | null }[]): LineData<Time>[] {
  const byTime = new Map<number, LineData<Time>>();
  for (const point of points) {
    if (point.value === null) {
      continue;
    }
    const time = toChartTime(point.time);
    if (Number.isNaN(time)) {
      continue;
    }
    byTime.set(time, { time, value: point.value });
  }
  return [...byTime.values()].sort((a, b) => (a.time as number) - (b.time as number));
}

/**
 * Build a comparison-overlay line from an OHLCV series. When `normalize` is on,
 * each value is `(close[i] / close[0] - 1) * 100` so the overlay shares the
 * percentage scale with any future second-symbol overlay; when off, raw closes
 * are emitted on the second symbol's natural scale.
 */
function toComparisonLineData(series: OHLCVSeries, normalize: boolean): LineData<Time>[] {
  if (series.bars.length === 0) {
    return [];
  }
  const sorted = [...series.bars].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );
  const base = sorted[0]?.close ?? 1;
  const safeBase = base === 0 ? 1 : base;
  const out: LineData<Time>[] = [];
  for (const bar of sorted) {
    const time = toChartTime(bar.timestamp);
    if (Number.isNaN(time)) {
      continue;
    }
    const value = normalize ? (bar.close / safeBase - 1) * 100 : bar.close;
    out.push({ time, value });
  }
  return out;
}

type LoadState = "idle" | "loading" | "ready" | "error";

/** Minimal shape of the dockview panel props the chart panel needs. */
interface ChartPanelProps {
  api?: { id?: string };
}

/** Falls back to a random instance id if dockview's panel api is unavailable. */
function usePanelId(api?: { id?: string }): string {
  // useState lazy initializer guarantees one stable id per mount.
  const [fallback] = useState(() => `chart-${Math.random().toString(36).slice(2, 10)}`);
  return api?.id ?? fallback;
}

/**
 * Chart panel — a lightweight-charts candlestick chart with a symbol input, a
 * timeframe selector, the 50-indicator catalog selector grouped into six
 * categories, ten drawing tools persisted via the workspace, optional
 * comparison overlay, and three opt-in sync flavors (crosshair / visible-range
 * / symbol) so multiple chart instances can stay in lock-step.
 */
function ChartPanel(props: ChartPanelProps = {}) {
  const panelId = usePanelId(props.api);

  // --- chart refs ---------------------------------------------------------
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const indicatorSeriesRef = useRef<ISeriesApi<"Line">[]>([]);
  const volumeProfileRef = useRef<VolumeProfilePrimitive | null>(null);
  const ichimokuCloudRef = useRef<IchimokuCloudPrimitive | null>(null);
  // Cached candle data — Parabolic SAR markers need the per-bar close to
  // decide above- vs below-bar placement and the trend colour.
  const candleDataRef = useRef<CandlestickData<Time>[]>([]);
  const sarMarkersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  // Drawings — primitive registry keyed by spec id, so we can reconcile the
  // store's drawings array with attached primitives without rebuilding all of
  // them on every state change.
  const drawingPrimitivesRef = useRef<Map<string, DrawingPrimitive>>(new Map());
  // Comparison overlay — second-symbol line series, replaced on toggle.
  const comparisonSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  // --- form / data state --------------------------------------------------
  const [symbolInput, setSymbolInput] = useState(DEFAULT_SYMBOL);
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
  const [timeframe, setTimeframe] = useState<Timeframe>(DEFAULT_TIMEFRAME);
  const [selected, setSelected] = useState<Set<string>>(() => new Set());

  const [priceState, setPriceState] = useState<LoadState>("idle");
  const [priceError, setPriceError] = useState<string | null>(null);
  const [indicatorState, setIndicatorState] = useState<LoadState>("idle");
  const [indicatorError, setIndicatorError] = useState<string | null>(null);
  const [provider, setProvider] = useState<string | null>(null);

  // --- drawings state -----------------------------------------------------
  const [activeTool, setActiveTool] = useState<DrawingKind | null>(null);
  const [draftPoints, setDraftPoints] = useState<DrawingPoint[]>([]);
  const [selectedDrawingId, setSelectedDrawingId] = useState<string | null>(null);

  const drawings = useChartDrawingsStore((state) => state.byPanel[panelId] ?? EMPTY_DRAWINGS);
  const addDrawing = useChartDrawingsStore((state) => state.addDrawing);
  const removeDrawing = useChartDrawingsStore((state) => state.removeDrawing);
  const updateDrawing = useChartDrawingsStore((state) => state.updateDrawing);
  const clearPanelDrawings = useChartDrawingsStore((state) => state.clearPanel);

  // --- comparison overlay state ------------------------------------------
  const [compareInput, setCompareInput] = useState("");
  const [compareSymbol, setCompareSymbol] = useState<string | null>(null);
  const [compareNormalize, setCompareNormalize] = useState(true);

  // --- sync bus -----------------------------------------------------------
  const syncSubscriptions = useChartSyncBus((state) => selectSubscriptions(state, panelId));
  const setSubscription = useChartSyncBus((state) => state.setSubscription);
  const unregisterPanel = useChartSyncBus((state) => state.unregisterPanel);
  const broadcastCrosshair = useChartSyncBus((state) => state.setCrosshair);
  const broadcastVisibleRange = useChartSyncBus((state) => state.setVisibleRange);
  const broadcastSymbol = useChartSyncBus((state) => state.setSymbol);

  // The latest broadcasts — keep the function-ref stable so subscriber effects
  // don't churn when only the source/seq changes.
  const crosshairBroadcast = useChartSyncBus((state) => state.crosshair);
  const visibleRangeBroadcast = useChartSyncBus((state) => state.visibleRange);
  const symbolBroadcast = useChartSyncBus((state) => state.symbol);

  const selectedKeys = useMemo(() => [...selected].sort(), [selected]);

  // --- chart lifecycle ----------------------------------------------------
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const chart = createChart(container, {
      ...CHART_THEME,
      autoSize: true,
    });
    const candleSeries = chart.addSeries(CandlestickSeries, CANDLE_THEME);
    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    // Capture the ref-current drawings registry so cleanup uses the same
    // instance the effect saw at mount, not whatever it points to later.
    const drawings = drawingPrimitivesRef.current;
    return () => {
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      indicatorSeriesRef.current = [];
      volumeProfileRef.current = null;
      ichimokuCloudRef.current = null;
      sarMarkersRef.current = null;
      candleDataRef.current = [];
      drawings.clear();
      comparisonSeriesRef.current = null;
      // Drawings persist across mount/unmount via the store; only the local
      // primitive registry resets. Sync subscriptions clear on unmount so a
      // closed panel does not keep echoing through the bus.
      unregisterPanel(panelId);
    };
  }, [panelId, unregisterPanel]);

  // --- price data ---------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    // The fetch is driven from an inner function so the synchronous "loading"
    // transition is a callback, not a direct setState in the effect body.
    const loadHistory = async () => {
      setPriceState("loading");
      setPriceError(null);
      try {
        const series = await sidecarApi.history(symbol, timeframe);
        if (cancelled) {
          return;
        }
        const candleSeries = candleSeriesRef.current;
        if (candleSeries) {
          const candleData = toCandlestickData(series);
          candleSeries.setData(candleData);
          candleDataRef.current = candleData;
          chartRef.current?.timeScale().fitContent();
        }
        setProvider(series.provider);
        setPriceState("ready");
      } catch (error: unknown) {
        if (cancelled) {
          return;
        }
        setPriceError(
          error instanceof SidecarError
            ? `${error.message} (${error.status})`
            : "Failed to load price history.",
        );
        setPriceState("error");
      }
    };
    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe]);

  // --- indicator data -----------------------------------------------------
  const clearIndicatorSeries = useCallback(() => {
    const chart = chartRef.current;
    if (chart) {
      for (const series of indicatorSeriesRef.current) {
        chart.removeSeries(series);
      }
    }
    indicatorSeriesRef.current = [];
    const candleSeries = candleSeriesRef.current;
    const volumeProfile = volumeProfileRef.current;
    if (candleSeries && volumeProfile) {
      candleSeries.detachPrimitive(volumeProfile);
    }
    volumeProfileRef.current = null;
    const ichimokuCloud = ichimokuCloudRef.current;
    if (candleSeries && ichimokuCloud) {
      candleSeries.detachPrimitive(ichimokuCloud);
    }
    ichimokuCloudRef.current = null;
    const sarMarkers = sarMarkersRef.current;
    if (sarMarkers) {
      sarMarkers.detach();
    }
    sarMarkersRef.current = null;
  }, []);

  /**
   * Parabolic SAR is drawn as above- / below-bar dot markers rather than a
   * line — that is the conventional rendering, and lightweight-charts' line
   * series cannot draw discrete dots. Each SAR sample is compared to the bar's
   * close: SAR < close → uptrend dot below; SAR > close → downtrend dot above.
   */
  const renderParabolicSar = useCallback((points: { time: string; value: number | null }[]) => {
    const candleSeries = candleSeriesRef.current;
    if (!candleSeries) {
      return;
    }
    const closeByTime = new Map<number, number>();
    for (const candle of candleDataRef.current) {
      closeByTime.set(candle.time as number, candle.close);
    }
    const markers: SeriesMarker<Time>[] = [];
    for (const point of points) {
      if (point.value === null) {
        continue;
      }
      const time = toChartTime(point.time);
      if (Number.isNaN(time)) {
        continue;
      }
      const close = closeByTime.get(time);
      if (close === undefined) {
        continue;
      }
      const isUptrend = point.value < close;
      markers.push({
        time,
        position: isUptrend ? "belowBar" : "aboveBar",
        shape: "circle",
        color: isUptrend ? "#8fa67c" : "#c8654b",
        size: 1,
      });
    }
    markers.sort((a, b) => (a.time as number) - (b.time as number));
    const existing = sarMarkersRef.current;
    if (existing) {
      existing.setMarkers(markers);
    } else {
      sarMarkersRef.current = createSeriesMarkers(candleSeries, markers);
    }
  }, []);

  const renderIndicators = useCallback(
    (response: IndicatorResponse) => {
      const chart = chartRef.current;
      if (!chart) {
        return;
      }
      clearIndicatorSeries();
      // Price-pane overlays share pane 0; each separate-pane indicator gets the
      // next pane index, so all panes stay time-synced within the one chart.
      let nextPane = 1;
      for (const indicator of response.indicators) {
        if (indicator.name === "parabolic_sar") {
          renderParabolicSar(indicator.lines[0]?.points ?? []);
          continue;
        }
        const isOverlay = indicator.panel === "price";
        const paneIndex = isOverlay ? 0 : nextPane++;
        indicator.lines.forEach((line, lineIndex) => {
          const data = toLineData(line.points);
          if (data.length === 0) {
            return;
          }
          const series = chart.addSeries(
            LineSeries,
            {
              color: INDICATOR_COLORS[lineIndex % INDICATOR_COLORS.length],
              lineWidth: 2,
              priceLineVisible: false,
              lastValueVisible: isOverlay,
              title: line.label,
            },
            paneIndex,
          );
          series.setData(data);
          indicatorSeriesRef.current.push(series);
        });
        // Ichimoku — the five lines are drawn as LineSeries above; the cloud
        // is the filled band between Senkou A and Senkou B, painted by a
        // dedicated primitive attached to the candle series.
        if (indicator.name === "ichimoku") {
          const senkouA = indicator.lines.find((line) => line.label === "Senkou Span A");
          const senkouB = indicator.lines.find((line) => line.label === "Senkou Span B");
          const candleSeriesForCloud = candleSeriesRef.current;
          if (senkouA && senkouB && candleSeriesForCloud) {
            const cloud = new IchimokuCloudPrimitive();
            cloud.setBands(senkouA.points, senkouB.points);
            candleSeriesForCloud.attachPrimitive(cloud);
            ichimokuCloudRef.current = cloud;
          }
        }
      }
      // Volume Profile rides on its own contract (a price-axis histogram) and
      // is drawn through a series primitive attached to the candle series so
      // it shares the price scale.
      const candleSeries = candleSeriesRef.current;
      if (response.volume_profile && candleSeries) {
        const primitive = new VolumeProfilePrimitive();
        primitive.setBuckets(response.volume_profile.buckets);
        candleSeries.attachPrimitive(primitive);
        volumeProfileRef.current = primitive;
      }
    },
    [clearIndicatorSeries, renderParabolicSar],
  );

  useEffect(() => {
    let cancelled = false;
    // Inner function so every setState is a callback, never a synchronous call
    // in the effect body — including the no-selection reset path.
    const loadIndicators = async () => {
      if (selectedKeys.length === 0) {
        clearIndicatorSeries();
        setIndicatorState("idle");
        setIndicatorError(null);
        return;
      }
      setIndicatorState("loading");
      setIndicatorError(null);
      try {
        const response = await fetchIndicators(symbol, selectedKeys, timeframe);
        if (cancelled) {
          return;
        }
        renderIndicators(response);
        setIndicatorState("ready");
      } catch (error: unknown) {
        if (cancelled) {
          return;
        }
        setIndicatorError(
          error instanceof SidecarError
            ? `${error.message} (${error.status})`
            : "Failed to load indicators.",
        );
        setIndicatorState("error");
      }
    };
    void loadIndicators();
    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe, selectedKeys, renderIndicators, clearIndicatorSeries]);

  // --- drawings: reconcile store → primitives -----------------------------
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    if (!candleSeries) {
      return;
    }
    const registry = drawingPrimitivesRef.current;
    const seen = new Set<string>();
    for (const spec of drawings) {
      seen.add(spec.id);
      const existing = registry.get(spec.id);
      if (existing) {
        existing.setSpec(spec);
      } else {
        const primitive = createDrawingPrimitive(spec);
        candleSeries.attachPrimitive(primitive);
        registry.set(spec.id, primitive);
      }
    }
    for (const [id, primitive] of registry) {
      if (!seen.has(id)) {
        candleSeries.detachPrimitive(primitive);
        registry.delete(id);
      }
    }
  }, [drawings]);

  // --- drawings: click-to-create + delete-key handlers --------------------
  const handleChartClick = useCallback(
    (param: MouseEventParams<Time>) => {
      if (!activeTool) {
        return;
      }
      const candleSeries = candleSeriesRef.current;
      if (!candleSeries) {
        return;
      }
      // Resolve the click into a drawing point — `time` is whatever bar the
      // crosshair is over (or null for V/H lines anchored only on price/time).
      const time = typeof param.time === "number" ? (param.time as number) : null;
      const seriesData = param.seriesData?.get(candleSeries);
      let price: number | null = null;
      if (seriesData && "close" in seriesData && typeof seriesData.close === "number") {
        price = seriesData.close;
      } else if (param.point && param.logical !== undefined) {
        const coord = candleSeries.coordinateToPrice(param.point.y);
        if (coord !== null) {
          price = coord;
        }
      }
      const point: DrawingPoint = { time, price };
      const required = pointsRequired(activeTool);
      const next = [...draftPoints, point];
      if (next.length < required) {
        setDraftPoints(next);
        return;
      }
      // Commit the drawing.
      const spec: DrawingSpec = {
        id: newDrawingId(),
        panelId,
        kind: activeTool,
        points: next,
        style: { ...DEFAULT_DRAWING_STYLE },
        createdAt: Date.now(),
        kindOptions: activeTool === "text" ? { text: "label", fontSize: 12 } : undefined,
      };
      addDrawing(panelId, spec);
      setDraftPoints([]);
      setActiveTool(null);
    },
    [activeTool, addDrawing, draftPoints, panelId],
  );

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) {
      return;
    }
    chart.subscribeClick(handleChartClick);
    return () => {
      chart.unsubscribeClick(handleChartClick);
    };
  }, [handleChartClick]);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setActiveTool(null);
        setDraftPoints([]);
        setSelectedDrawingId(null);
      }
      if ((event.key === "Delete" || event.key === "Backspace") && selectedDrawingId) {
        removeDrawing(panelId, selectedDrawingId);
        setSelectedDrawingId(null);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [panelId, removeDrawing, selectedDrawingId]);

  // --- sync bus: subscribe to crosshair / range / symbol broadcasts ------
  useEffect(() => {
    if (!syncSubscriptions.crosshair) {
      return;
    }
    const handleBroadcast = (broadcast: CrosshairBroadcast | null) => {
      if (!broadcast || broadcast.source === panelId || broadcast.time === null) {
        return;
      }
      chartRef.current?.setCrosshairPosition(NaN, broadcast.time as Time, candleSeriesRef.current!);
    };
    handleBroadcast(crosshairBroadcast);
  }, [syncSubscriptions.crosshair, crosshairBroadcast, panelId]);

  useEffect(() => {
    if (!syncSubscriptions.visibleRange) {
      return;
    }
    const handleBroadcast = (broadcast: VisibleRangeBroadcast | null) => {
      if (!broadcast || broadcast.source === panelId) {
        return;
      }
      chartRef.current
        ?.timeScale()
        .setVisibleRange({ from: broadcast.from as Time, to: broadcast.to as Time });
    };
    handleBroadcast(visibleRangeBroadcast);
  }, [syncSubscriptions.visibleRange, visibleRangeBroadcast, panelId]);

  useEffect(() => {
    if (!syncSubscriptions.symbol) {
      return;
    }
    const handleBroadcast = (broadcast: SymbolBroadcast | null) => {
      if (!broadcast || broadcast.source === panelId) {
        return;
      }
      setSymbol(broadcast.symbol);
      setSymbolInput(broadcast.symbol);
    };
    handleBroadcast(symbolBroadcast);
  }, [syncSubscriptions.symbol, symbolBroadcast, panelId]);

  // --- sync bus: broadcast our crosshair / visible-range / symbol --------
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) {
      return;
    }
    const onCrosshair = (param: MouseEventParams<Time>) => {
      const time = typeof param.time === "number" ? (param.time as number) : null;
      broadcastCrosshair(panelId, time);
    };
    chart.subscribeCrosshairMove(onCrosshair);
    const onRange = (range: LogicalRange | null) => {
      if (!range) {
        return;
      }
      const visible = chart.timeScale().getVisibleRange();
      if (!visible) {
        return;
      }
      broadcastVisibleRange(panelId, Number(visible.from), Number(visible.to));
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(onRange);
    return () => {
      chart.unsubscribeCrosshairMove(onCrosshair);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onRange);
    };
  }, [broadcastCrosshair, broadcastVisibleRange, panelId]);

  // --- comparison overlay -------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    const chart = chartRef.current;
    if (!chart) {
      return;
    }
    if (comparisonSeriesRef.current) {
      chart.removeSeries(comparisonSeriesRef.current);
      comparisonSeriesRef.current = null;
    }
    if (!compareSymbol) {
      return;
    }
    const load = async () => {
      try {
        const series = await sidecarApi.history(compareSymbol, timeframe);
        if (cancelled || !chartRef.current) {
          return;
        }
        const data = toComparisonLineData(series, compareNormalize);
        if (data.length === 0) {
          return;
        }
        const overlay = chartRef.current.addSeries(LineSeries, {
          color: COMPARISON_LINE_COLOR,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: `${compareSymbol}${compareNormalize ? " %" : ""}`,
          // Normalised overlay rides its own price scale on the left so it
          // does not warp the candle series' right scale.
          priceScaleId: compareNormalize ? "left" : "right",
        });
        overlay.setData(data);
        comparisonSeriesRef.current = overlay;
      } catch {
        // Comparison-overlay failures are non-fatal — silently drop. The
        // primary chart's error path already surfaces upstream issues.
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [compareSymbol, compareNormalize, timeframe]);

  // --- handlers -----------------------------------------------------------
  const submitSymbol = useCallback(() => {
    const next = symbolInput.trim().toUpperCase();
    if (next.length > 0) {
      setSymbol(next);
      setSymbolInput(next);
      broadcastSymbol(panelId, next);
    }
  }, [broadcastSymbol, panelId, symbolInput]);

  const toggleIndicator = useCallback((key: string) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  const submitComparison = useCallback(() => {
    const next = compareInput.trim().toUpperCase();
    setCompareSymbol(next.length > 0 ? next : null);
  }, [compareInput]);

  const clearComparison = useCallback(() => {
    setCompareInput("");
    setCompareSymbol(null);
  }, []);

  const onToolToggle = useCallback((kind: DrawingKind) => {
    setActiveTool((current) => (current === kind ? null : kind));
    setDraftPoints([]);
    setSelectedDrawingId(null);
  }, []);

  const onSelectDrawing = useCallback((id: string) => {
    setSelectedDrawingId((current) => (current === id ? null : id));
  }, []);

  const onToggleLock = useCallback(
    (id: string, locked: boolean) => {
      updateDrawing(panelId, id, (drawing) => ({ ...drawing, locked }));
    },
    [panelId, updateDrawing],
  );

  const onDeleteDrawing = useCallback(
    (id: string) => {
      removeDrawing(panelId, id);
      if (selectedDrawingId === id) {
        setSelectedDrawingId(null);
      }
    },
    [panelId, removeDrawing, selectedDrawingId],
  );

  const onClearAllDrawings = useCallback(() => {
    clearPanelDrawings(panelId);
    setSelectedDrawingId(null);
  }, [clearPanelDrawings, panelId]);

  const renderIndicatorButton = (indicator: IndicatorDef) => {
    const active = selected.has(indicator.key);
    return (
      <button
        key={indicator.key}
        type="button"
        onClick={() => toggleIndicator(indicator.key)}
        aria-pressed={active}
        className={cn(
          "rounded-control border px-2 py-1 text-left font-mono text-xs transition-colors",
          active
            ? "border-amber-500 bg-amber-500/15 text-amber-300"
            : "border-charcoal-700 text-charcoal-400 hover:border-charcoal-600 hover:text-charcoal-200",
        )}
      >
        {indicator.label}
      </button>
    );
  };

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col" data-panel-id={panelId}>
      {/* Controls */}
      <div className="border-charcoal-700 flex flex-wrap items-center gap-2 border-b px-3 py-2">
        <form
          className="flex items-center gap-1.5"
          onSubmit={(event) => {
            event.preventDefault();
            submitSymbol();
          }}
        >
          <input
            value={symbolInput}
            onChange={(event) => setSymbolInput(event.target.value)}
            aria-label="Symbol"
            placeholder="Symbol"
            spellCheck={false}
            className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 rounded-control w-24 border px-2 py-1 font-mono text-sm uppercase outline-none focus-visible:border-amber-500"
          />
          <Button type="submit" size="sm" variant="outline">
            Load
          </Button>
        </form>

        <div className="flex items-center gap-1" role="group" aria-label="Timeframe">
          {TIMEFRAMES.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setTimeframe(option)}
              aria-pressed={timeframe === option}
              className={cn(
                "rounded-control px-2 py-1 font-mono text-xs transition-colors",
                timeframe === option
                  ? "bg-amber-500/20 text-amber-300"
                  : "text-charcoal-400 hover:text-charcoal-100",
              )}
            >
              {option}
            </button>
          ))}
        </div>

        {/* Sync toggles — three independent flavors */}
        <div className="flex items-center gap-1" role="group" aria-label="Sync">
          <span className="text-charcoal-500 mr-1 font-mono text-[10px] tracking-widest uppercase">
            Sync
          </span>
          {(
            [
              ["crosshair", "Cx"],
              ["visibleRange", "Zm"],
              ["symbol", "Sy"],
            ] as const
          ).map(([flavor, label]) => (
            <button
              key={flavor}
              type="button"
              onClick={() => setSubscription(panelId, flavor, !syncSubscriptions[flavor])}
              aria-pressed={syncSubscriptions[flavor]}
              aria-label={`Sync ${flavor}`}
              className={cn(
                "rounded-control px-2 py-1 font-mono text-[10px] transition-colors",
                syncSubscriptions[flavor]
                  ? "bg-amber-500/20 text-amber-300"
                  : "text-charcoal-400 hover:text-charcoal-100",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="text-charcoal-400 ml-auto font-mono text-xs">
          <span className="text-charcoal-200">{symbol}</span>
          {provider ? <span className="ml-2">via {provider}</span> : null}
        </div>
      </div>

      {/* Drawing toolbar + comparison overlay row */}
      <div className="border-charcoal-700 flex flex-wrap items-center gap-2 border-b px-3 py-1.5">
        <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Drawings">
          <span className="text-charcoal-500 mr-1 font-mono text-[10px] tracking-widest uppercase">
            Draw
          </span>
          {DRAWING_TOOLS.map((tool) => {
            const active = activeTool === tool.kind;
            return (
              <button
                key={tool.kind}
                type="button"
                onClick={() => onToolToggle(tool.kind)}
                aria-pressed={active}
                className={cn(
                  "rounded-control px-2 py-1 font-mono text-[10px] transition-colors",
                  active
                    ? "bg-amber-500/20 text-amber-300"
                    : "text-charcoal-400 hover:text-charcoal-100",
                )}
              >
                {tool.label}
              </button>
            );
          })}
          {drawings.length > 0 ? (
            <button
              type="button"
              onClick={onClearAllDrawings}
              className="text-charcoal-400 hover:text-charcoal-100 ml-1 font-mono text-[10px] underline-offset-2 hover:underline"
            >
              clear ({drawings.length})
            </button>
          ) : null}
          {activeTool ? (
            <span className="text-charcoal-400 ml-1 font-mono text-[10px]">
              click chart {pointsRequired(activeTool) - draftPoints.length} more time(s)
            </span>
          ) : null}
        </div>

        <form
          className="ml-auto flex items-center gap-1"
          onSubmit={(event) => {
            event.preventDefault();
            submitComparison();
          }}
        >
          <span className="text-charcoal-500 mr-1 font-mono text-[10px] tracking-widest uppercase">
            Compare
          </span>
          <input
            value={compareInput}
            onChange={(event) => setCompareInput(event.target.value)}
            aria-label="Compare symbol"
            placeholder="Symbol"
            spellCheck={false}
            className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 rounded-control w-20 border px-2 py-1 font-mono text-xs uppercase outline-none focus-visible:border-amber-500"
          />
          <Button type="submit" size="sm" variant="outline">
            Add
          </Button>
          {compareSymbol ? (
            <>
              <button
                type="button"
                onClick={() => setCompareNormalize((current) => !current)}
                aria-pressed={compareNormalize}
                aria-label="Normalize comparison"
                className={cn(
                  "rounded-control px-2 py-1 font-mono text-[10px] transition-colors",
                  compareNormalize
                    ? "bg-amber-500/20 text-amber-300"
                    : "text-charcoal-400 hover:text-charcoal-100",
                )}
              >
                %
              </button>
              <button
                type="button"
                onClick={clearComparison}
                className="text-charcoal-400 hover:text-charcoal-100 font-mono text-[10px]"
                aria-label="Remove comparison overlay"
              >
                ×
              </button>
            </>
          ) : null}
        </form>
      </div>

      {/* Chart */}
      <div className="relative min-h-0 flex-1">
        <div ref={containerRef} className="absolute inset-0" data-testid="chart-container" />
        {priceState === "loading" ? (
          <div className="text-charcoal-400 absolute inset-0 flex items-center justify-center font-mono text-sm">
            Loading {symbol}…
          </div>
        ) : null}
        {priceState === "error" ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-6 text-center">
            <p className="text-negative font-mono text-sm">{priceError}</p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSymbol((current) => `${current}`)}
            >
              Retry
            </Button>
          </div>
        ) : null}
      </div>

      {/* Drawings inspector — list of drawings on this panel */}
      {drawings.length > 0 ? (
        <div className="border-charcoal-700 max-h-24 overflow-y-auto border-t px-3 py-1.5">
          <div className="mb-1 flex items-center gap-2">
            <span className="text-charcoal-500 font-mono text-[10px] tracking-widest uppercase">
              Drawings
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            {drawings.map((drawing) => {
              const active = selectedDrawingId === drawing.id;
              return (
                <span
                  key={drawing.id}
                  className={cn(
                    "rounded-control flex items-center gap-1 border px-1.5 py-0.5 font-mono text-[10px]",
                    active
                      ? "border-amber-500 bg-amber-500/15 text-amber-300"
                      : "border-charcoal-700 text-charcoal-400",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => onSelectDrawing(drawing.id)}
                    className="font-mono"
                    aria-label={`Select ${drawing.kind}`}
                    aria-pressed={active}
                  >
                    {drawing.kind}
                  </button>
                  <button
                    type="button"
                    onClick={() => onToggleLock(drawing.id, !drawing.locked)}
                    aria-pressed={!!drawing.locked}
                    aria-label={drawing.locked ? "Unlock drawing" : "Lock drawing"}
                    className={cn("px-1 hover:text-amber-300", drawing.locked && "text-amber-300")}
                  >
                    {drawing.locked ? "🔒" : "🔓"}
                  </button>
                  <button
                    type="button"
                    onClick={() => onDeleteDrawing(drawing.id)}
                    className="px-1 hover:text-red-400"
                    aria-label="Delete drawing"
                  >
                    ×
                  </button>
                </span>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* Indicator selector — grouped by category so 50 entries stay scannable */}
      <div className="border-charcoal-700 max-h-56 overflow-y-auto border-t px-3 py-2">
        <div className="mb-1.5 flex items-center gap-2">
          <span className="text-charcoal-200 font-mono text-xs tracking-wide uppercase">
            Indicators
          </span>
          {indicatorState === "loading" ? (
            <span className="text-charcoal-400 font-mono text-xs">computing…</span>
          ) : null}
          {indicatorState === "error" ? (
            <span className="text-negative font-mono text-xs">{indicatorError}</span>
          ) : null}
          {selected.size > 0 ? (
            <button
              type="button"
              onClick={() => setSelected(new Set())}
              className="text-charcoal-400 hover:text-charcoal-100 ml-auto font-mono text-xs underline-offset-2 hover:underline"
            >
              Clear ({selected.size})
            </button>
          ) : null}
        </div>
        <div className="space-y-2">
          {indicatorsByCategory().map((group) => (
            <div key={group.category}>
              <div className="text-charcoal-500 mb-1 font-mono text-[10px] tracking-widest uppercase">
                {group.label}
              </div>
              <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-4">
                {group.indicators.map(renderIndicatorButton)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

ChartPanel.displayName = "ChartPanel";

export default ChartPanel;
