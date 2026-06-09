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

import { Lock, Unlock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { type Freshness, StalenessBadge } from "@/components/DataBadges";
import {
  CHART_BORDER,
  CHART_CROSSHAIR,
  CHART_GRID,
  CHART_SURFACE,
  CHART_TEXT,
  NEGATIVE,
  NEUTRAL,
  POSITIVE,
} from "@/lib/chart-theme";
import { sessionLabelFromFreshness } from "@/lib/market-session";
import { SidecarError, sidecarApi } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { useChartCommandStore } from "@/store/chart-command";
import { newDrawingId, useChartDrawingsStore } from "@/store/chart-drawings";
import {
  selectSubscriptions,
  useChartSyncBus,
  type CrosshairBroadcast,
  type SymbolBroadcast,
  type VisibleRangeBroadcast,
} from "@/store/chart-sync";
import { usePanelContextBus } from "@/store/panel-context";
import type { IndicatorResponse, OHLCVSeries } from "../../../types/data";
import type { DrawingKind, DrawingPoint, DrawingSpec } from "../../../types/drawings";
import { fetchIndicators } from "./api";
import { DrawingPrimitive } from "./drawings/base";
import { createDrawingPrimitive, DEFAULT_DRAWING_STYLE, pointsRequired } from "./drawings/factory";
import { IchimokuCloudPrimitive } from "./ichimoku-cloud-primitive";
import { INDICATOR_COLORS, indicatorByKey } from "./indicators";
import {
  CompareMenu,
  DRAWING_CHIP_LABELS,
  DrawMenu,
  IndicatorsMenu,
  SyncMenu,
  ToolbarDisclosure,
} from "./toolbar";
import { VolumeProfilePrimitive } from "./volume-profile-primitive";

/** Bar intervals the chart panel exposes — mirrors the sidecar's `timeframe`. */
const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

const DEFAULT_SYMBOL = "SPY";
const DEFAULT_TIMEFRAME: Timeframe = "1d";

/** The toolbar's disclosure popovers — at most one is open at a time. */
type ToolbarMenu = "draw" | "indicators" | "compare" | "sync";

/** Vysted dark palette, applied to the lightweight-charts canvas. */
const CHART_THEME = {
  layout: {
    background: { color: CHART_SURFACE }, // charcoal-900
    textColor: CHART_TEXT, // charcoal-200
    fontFamily: "var(--font-jetbrains-mono), ui-monospace, 'SF Mono', 'Cascadia Mono', monospace",
  },
  grid: {
    vertLines: { color: CHART_GRID }, // charcoal-800
    horzLines: { color: CHART_GRID },
  },
  rightPriceScale: { borderColor: CHART_BORDER }, // charcoal-700
  timeScale: { borderColor: CHART_BORDER, timeVisible: true, secondsVisible: false },
  crosshair: { vertLine: { color: CHART_CROSSHAIR }, horzLine: { color: CHART_CROSSHAIR } },
} as const;

const CANDLE_THEME = {
  upColor: POSITIVE, // positive
  downColor: NEGATIVE, // negative
  borderUpColor: POSITIVE,
  borderDownColor: NEGATIVE,
  wickUpColor: POSITIVE,
  wickDownColor: NEGATIVE,
} as const;

const COMPARISON_LINE_COLOR = NEUTRAL; // sage-400

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
 * Chart panel — a lightweight-charts candlestick chart behind a single calm
 * toolbar row: symbol input, the eight-step timeframe segmented control, and
 * four disclosure popovers (Draw / Indicators / Compare / Sync). The full
 * 50-indicator catalog, the ten drawing tools, the comparison overlay, and the
 * three opt-in sync flavors all stay reachable through the popovers; active
 * selections surface as removable chips (an earned indicator-chip row appears
 * only when ≥1 indicator is live). Drawings persist via the workspace store.
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
  // Raw OHLCV cache for the comparison symbol — avoids re-fetching on normalize toggle.
  const comparisonDataCacheRef = useRef<{
    symbol: string;
    timeframe: string;
    series: OHLCVSeries;
  } | null>(null);

  // --- form / data state --------------------------------------------------
  const [symbolInput, setSymbolInput] = useState(DEFAULT_SYMBOL);
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
  const [timeframe, setTimeframe] = useState<Timeframe>(DEFAULT_TIMEFRAME);
  const [selected, setSelected] = useState<Set<string>>(() => new Set());

  // --- toolbar disclosure state --------------------------------------------
  const [openMenu, setOpenMenu] = useState<ToolbarMenu | null>(null);
  const [indicatorQuery, setIndicatorQuery] = useState("");

  const [priceState, setPriceState] = useState<LoadState>("idle");
  const [priceError, setPriceError] = useState<string | null>(null);
  // Bumped to force a price re-fetch (Retry) even when symbol/timeframe are
  // unchanged — a plain `setSymbol(s => s)` is an Object.is no-op and never reruns.
  const [retryNonce, setRetryNonce] = useState(0);
  const [indicatorState, setIndicatorState] = useState<LoadState>("idle");
  const [indicatorError, setIndicatorError] = useState<string | null>(null);
  // Bumped to force an indicator re-fetch (Retry) without deselecting+reselecting.
  const [indicatorRetryNonce, setIndicatorRetryNonce] = useState(0);
  const [provider, setProvider] = useState<string | null>(null);
  // Calendar-aware staleness of the series' last bar (FR-041 / SC-019).
  const [freshness, setFreshness] = useState<Freshness | null>(null);

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
  // Tracks whether the active overlay actually rendered points. A fetch that
  // rejects or returns an empty series flips this to "error" so the compare
  // chip can dim + flag "no data" instead of silently showing nothing.
  const [compareState, setCompareState] = useState<"ok" | "error">("ok");

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
        const candleData = toCandlestickData(series);
        if (candleData.length === 0) {
          // Bug-2: an all-providers-empty history now returns a clean 200 (not a
          // 502). Clear the PRIOR symbol's series so its candles don't linger
          // behind the empty-state overlay — the chart must visibly show "No price
          // data", not the previous symbol's chart.
          candleSeriesRef.current?.setData([]);
          candleDataRef.current = [];
          setProvider(series.provider);
          setFreshness(series.freshness ?? null);
          setPriceError(
            series.reason === "in_eod_only"
              ? "No EOD data for this symbol. BSE/NSE serve end-of-day only — intraday/realtime needs a BYOK broker (Kite/Upstox/Dhan)."
              : "No price data for this symbol",
          );
          setPriceState("error");
          return;
        }
        const candleSeries = candleSeriesRef.current;
        if (candleSeries) {
          candleSeries.setData(candleData);
          candleDataRef.current = candleData;
          chartRef.current?.timeScale().fitContent();
        }
        setProvider(series.provider);
        setFreshness(series.freshness ?? null);
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
  }, [symbol, timeframe, retryNonce]);

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
        color: isUptrend ? NEUTRAL : NEGATIVE,
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
  }, [
    symbol,
    timeframe,
    selectedKeys,
    renderIndicators,
    clearIndicatorSeries,
    indicatorRetryNonce,
  ]);

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
      // Bug-3: candleSeriesRef can be momentarily null while the series remounts
      // during a synced timeframe switch. The old `!` non-null assertion handed
      // `setCrosshairPosition` a null series → runtime throw. Skip this sync tick;
      // the next broadcast re-syncs once the series is live again.
      const series = candleSeriesRef.current;
      if (!series) {
        return;
      }
      chartRef.current?.setCrosshairPosition(NaN, broadcast.time as Time, series);
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
      // Bug-3: a synced timeframe switch broadcasts a range computed against the
      // OTHER chart's just-replaced data, so from/to can be non-finite or inverted
      // while this chart's series is remounting. lightweight-charts throws on an
      // invalid range and React surfaces an error overlay. Validate (finite +
      // from<to), require a live chart+series, and try/catch the apply.
      const from = broadcast.from as unknown as number;
      const to = broadcast.to as unknown as number;
      if (!Number.isFinite(from) || !Number.isFinite(to) || from >= to) {
        return;
      }
      const chart = chartRef.current;
      if (!chart || !candleSeriesRef.current) {
        return;
      }
      try {
        chart
          .timeScale()
          .setVisibleRange({ from: from as unknown as Time, to: to as unknown as Time });
      } catch {
        // Transient: the series was replaced between the broadcast and this apply.
        // The next broadcast (or the autosave-driven re-fit) re-syncs the range.
      }
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

  // Host command channel — ALWAYS consumed (unlike the opt-in symbol sync above),
  // so an agent `set_chart_symbol` or a command-palette symbol pick actually lands
  // on this chart (BUG-6 fix). A new command bumps `seq`, so the effect re-runs;
  // on mount it adopts any pending command (covers "open a chart, then load X").
  const chartCommand = useChartCommandStore((state) => state.command);
  useEffect(() => {
    // Indirect through a handler (matches the symbol-sync effect above) so the
    // store→local-state sync isn't flagged as a direct setState-in-effect.
    const applyCommand = (cmd: { symbol: string; timeframe?: string }) => {
      setSymbol(cmd.symbol);
      setSymbolInput(cmd.symbol);
      if (cmd.timeframe && (TIMEFRAMES as readonly string[]).includes(cmd.timeframe)) {
        setTimeframe(cmd.timeframe as Timeframe);
      }
    };
    if (chartCommand) {
      applyCommand(chartCommand);
    }
  }, [chartCommand]);

  // Report the displayed symbol so the diff gate's "before" reflects the real
  // chart state (not the stale sync-bus value).
  useEffect(() => {
    useChartCommandStore.getState().reportActiveSymbol(symbol);
  }, [symbol]);

  // Host command channel — indicator selection. Mirrors the symbol command above:
  // ALWAYS consumed, `seq`-gated, scoped by optional symbol so a multi-chart
  // workspace only retargets the matching chart. The new selection drives the
  // existing fetch/render effect (we only swap local state here).
  const indicatorCommand = useChartCommandStore((state) => state.indicatorCommand);
  useEffect(() => {
    const applyCommand = (cmd: { symbol?: string; indicators: string[] }) => {
      if (cmd.symbol && cmd.symbol.toUpperCase() !== symbol.toUpperCase()) {
        return;
      }
      setSelected(new Set(cmd.indicators));
    };
    if (indicatorCommand) {
      applyCommand(indicatorCommand);
    }
    // `symbol` intentionally omitted from deps: re-running on every symbol change
    // would replay a stale command. The seq-bumped command object is the trigger;
    // the symbol guard is read fresh inside the handler at command time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indicatorCommand]);

  // Report the active indicator selection so the diff gate's "before" reflects
  // the real chart state. `selectedKeys` is the sorted, memoised projection.
  useEffect(() => {
    useChartCommandStore.getState().reportActiveIndicators(selectedKeys);
  }, [selectedKeys]);

  // Host command channel — comparison overlay. Mirrors the symbol command:
  // ALWAYS consumed, `seq`-gated. Drives the existing comparison overlay effect.
  const comparisonCommand = useChartCommandStore((state) => state.comparisonCommand);
  useEffect(() => {
    const applyCommand = (cmd: { symbol: string }) => {
      setCompareSymbol(cmd.symbol);
      setCompareInput(cmd.symbol);
    };
    if (comparisonCommand) {
      applyCommand(comparisonCommand);
    }
  }, [comparisonCommand]);

  // Report the active comparison-overlay symbol (or null) for the diff gate.
  useEffect(() => {
    useChartCommandStore.getState().reportActiveComparison(compareSymbol);
  }, [compareSymbol]);

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

  // --- panel-context bus: publish snapshot on state change ----------------
  // Reads `state.publish` / `state.unregisterSource` as bare function refs so
  // the effect's deps are stable across renders (Zustand returns the same
  // function pointer between sets). The frozen empty refs pattern is not
  // strictly required here because we depend on primitives (symbol, timeframe,
  // selectedKeys joined as a string, drawings.length) — but the discipline
  // from the Phase-2 chart-sync gotcha is preserved.
  const publishPanelContext = usePanelContextBus((state) => state.publish);
  const unregisterPanelContext = usePanelContextBus((state) => state.unregisterSource);

  useEffect(() => {
    const source = `chart-${panelId}`;
    publishPanelContext({
      source,
      kind: "snapshot",
      payload: {
        symbol,
        timeframe,
        activeIndicators: selectedKeys,
        drawingCount: drawings.length,
      },
      emittedAt: Date.now(),
    });
  }, [
    panelId,
    publishPanelContext,
    symbol,
    timeframe,
    // `selectedKeys` is memoised in this component (sorted, stable per
    // selection set) so depending on the array itself is safe.
    selectedKeys,
    drawings.length,
  ]);

  useEffect(() => {
    // Drop the panel's most-recent context event on unmount so a closed chart
    // does not leak into the chat sidebar's snapshot. The source identifier
    // mirrors the publish payload's `source` field.
    const source = `chart-${panelId}`;
    return () => {
      unregisterPanelContext(source);
    };
  }, [panelId, unregisterPanelContext]);

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

    // `addOverlay` reports through the setState callbacks (never a synchronous
    // effect-body setState): "ok" once a non-empty overlay renders, "error" on
    // an empty series. The async `load` path also flags "error" on a rejection.
    const addOverlay = (rawSeries: OHLCVSeries) => {
      if (cancelled || !chartRef.current) {
        return;
      }
      const data = toComparisonLineData(rawSeries, compareNormalize);
      if (data.length === 0) {
        setCompareState("error");
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
      setCompareState("ok");
    };

    // Use the cached OHLCV when only normalize toggled — avoids a network
    // round-trip and the visible blink of series-remove + async re-add. The
    // microtask defers the overlay add so the report is a callback, not a
    // synchronous setState in the effect body.
    const cache = comparisonDataCacheRef.current;
    if (cache && cache.symbol === compareSymbol && cache.timeframe === timeframe) {
      void Promise.resolve().then(() => addOverlay(cache.series));
      return () => {
        cancelled = true;
      };
    }

    const load = async () => {
      try {
        const rawSeries = await sidecarApi.history(compareSymbol, timeframe);
        if (cancelled) {
          return;
        }
        comparisonDataCacheRef.current = { symbol: compareSymbol, timeframe, series: rawSeries };
        addOverlay(rawSeries);
      } catch {
        // Comparison-overlay failures are non-fatal to the primary chart — the
        // main error path already surfaces upstream issues. Flag the chip so the
        // empty overlay is explained rather than silently missing.
        if (!cancelled) {
          setCompareState("error");
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [compareSymbol, compareNormalize, timeframe, symbol]);

  // --- handlers -----------------------------------------------------------
  const submitSymbol = useCallback(() => {
    const next = symbolInput.trim().toUpperCase();
    if (next.length > 0) {
      setSymbol(next);
      setSymbolInput(next);
      broadcastSymbol(panelId, next);
    }
  }, [broadcastSymbol, panelId, symbolInput]);

  /** Open/close one disclosure popover; opening Indicators resets its search. */
  const handleMenuChange = useCallback((menu: ToolbarMenu, open: boolean) => {
    setOpenMenu(open ? menu : null);
    if (menu === "indicators" && open) {
      setIndicatorQuery("");
    }
  }, []);

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

  const clearAllIndicators = useCallback(() => {
    setSelected(new Set());
  }, []);

  const submitComparison = useCallback(() => {
    const next = compareInput.trim().toUpperCase();
    setCompareSymbol(next.length > 0 ? next : null);
    if (next.length > 0) {
      setCompareInput(next);
    }
    setOpenMenu(null);
  }, [compareInput]);

  const clearComparison = useCallback(() => {
    setCompareInput("");
    setCompareSymbol(null);
    setCompareState("ok");
  }, []);

  /** Arm a drawing tool from the Draw popover (re-selecting disarms). */
  const onArmTool = useCallback((kind: DrawingKind) => {
    setActiveTool((current) => (current === kind ? null : kind));
    setDraftPoints([]);
    setSelectedDrawingId(null);
    setOpenMenu(null);
  }, []);

  /** Disarm via the active-tool chip's [x] (Escape does the same). */
  const onDisarmTool = useCallback(() => {
    setActiveTool(null);
    setDraftPoints([]);
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

  const remainingPoints = activeTool ? pointsRequired(activeTool) - draftPoints.length : 0;
  const syncCount =
    Number(syncSubscriptions.crosshair) +
    Number(syncSubscriptions.visibleRange) +
    Number(syncSubscriptions.symbol);

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col" data-panel-id={panelId}>
      {/* The one toolbar row — symbol, timeframes, disclosures, chips, status */}
      <div
        className="relative z-20 flex flex-wrap items-center gap-2 border-b px-3 py-2"
        style={{ borderColor: "var(--hairline-strong)" }}
      >
        <form
          className="flex items-center gap-1"
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
            className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 rounded-control text-body placeholder:text-charcoal-500 focus-visible:border-charcoal-500 h-6 w-24 border px-2 font-mono uppercase outline-none"
          />
          <Button type="submit" size="xs" variant="outline">
            Load
          </Button>
        </form>

        {/* Timeframe segmented control — the eight intervals stay load-bearing. */}
        <div
          className="border-charcoal-700 rounded-control flex items-center border"
          role="group"
          aria-label="Timeframe"
        >
          {TIMEFRAMES.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setTimeframe(option)}
              aria-pressed={timeframe === option}
              className={cn(
                "rounded-control text-caption h-6 px-2 font-mono transition-colors",
                timeframe === option
                  ? "bg-charcoal-875 text-charcoal-100"
                  : "text-charcoal-400 hover:text-charcoal-100",
              )}
            >
              {option}
            </button>
          ))}
        </div>

        <span
          aria-hidden
          className="h-4 w-px"
          style={{ backgroundColor: "var(--hairline-strong)" }}
        />

        {/* Disclosure triggers — the entire tool surface, quiet until asked. */}
        <ToolbarDisclosure
          label="Draw"
          open={openMenu === "draw"}
          onOpenChange={(open) => handleMenuChange("draw", open)}
          menuLabel="Drawing tools"
          widthClass="w-72"
        >
          <DrawMenu activeTool={activeTool} onArm={onArmTool} />
        </ToolbarDisclosure>
        <ToolbarDisclosure
          label="Indicators"
          count={selected.size}
          open={openMenu === "indicators"}
          onOpenChange={(open) => handleMenuChange("indicators", open)}
          menuLabel="Indicators"
          widthClass="w-96"
        >
          <IndicatorsMenu
            selected={selected}
            query={indicatorQuery}
            onQueryChange={setIndicatorQuery}
            onToggle={toggleIndicator}
            onClearAll={clearAllIndicators}
          />
        </ToolbarDisclosure>
        <ToolbarDisclosure
          label="Compare"
          count={compareSymbol ? 1 : 0}
          open={openMenu === "compare"}
          onOpenChange={(open) => handleMenuChange("compare", open)}
          menuLabel="Comparison overlay"
          widthClass="w-72"
        >
          <CompareMenu
            value={compareInput}
            onChange={setCompareInput}
            onSubmit={submitComparison}
          />
        </ToolbarDisclosure>
        <ToolbarDisclosure
          label="Sync"
          count={syncCount}
          open={openMenu === "sync"}
          onOpenChange={(open) => handleMenuChange("sync", open)}
          menuLabel="Chart sync"
          widthClass="w-64"
        >
          <SyncMenu
            subscriptions={syncSubscriptions}
            onToggle={(flavor) => setSubscription(panelId, flavor, !syncSubscriptions[flavor])}
          />
        </ToolbarDisclosure>

        {/* Armed-tool chip — appears only while a drawing tool is live. */}
        {activeTool ? (
          <span
            className="rounded-control border-charcoal-700 bg-charcoal-875 text-caption text-charcoal-200 flex h-6 items-center gap-1 border px-2 font-mono"
            data-testid="active-tool-chip"
          >
            {DRAWING_CHIP_LABELS[activeTool]}
            <span className="text-charcoal-500">
              {remainingPoints} {remainingPoints === 1 ? "point" : "points"} left
            </span>
            <button
              type="button"
              onClick={onDisarmTool}
              aria-label="Disarm drawing tool"
              className="text-charcoal-400 hover:text-charcoal-100 px-1 transition-colors"
            >
              ×
            </button>
          </span>
        ) : null}

        {/* Comparison chip — symbol, no-data flag, % normalize, remove. */}
        {compareSymbol ? (
          <span
            className={cn(
              "rounded-control border-charcoal-700 text-caption flex h-6 items-center gap-1 border px-2 font-mono",
              compareState === "error" ? "text-charcoal-500" : "text-charcoal-300",
            )}
            title={
              compareState === "error" ? `No comparison data for ${compareSymbol}` : compareSymbol
            }
            data-testid="compare-chip"
          >
            {compareSymbol}
            {compareState === "error" ? (
              <span aria-hidden className="text-warning" title="No data">
                !
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => setCompareNormalize((current) => !current)}
              aria-pressed={compareNormalize}
              aria-label="Normalize comparison"
              className={cn(
                "rounded-control px-1 transition-colors",
                compareNormalize
                  ? "bg-charcoal-850 text-charcoal-100"
                  : "text-charcoal-400 hover:text-charcoal-100",
              )}
            >
              %
            </button>
            <button
              type="button"
              onClick={clearComparison}
              aria-label="Remove comparison overlay"
              className="text-charcoal-400 hover:text-charcoal-100 px-1 transition-colors"
            >
              ×
            </button>
          </span>
        ) : null}

        {/* Status cluster — symbol, provider, freshness, session. */}
        <div className="text-charcoal-400 text-caption ml-auto flex min-w-0 items-center gap-2 font-mono">
          <span className="text-charcoal-200">{symbol}</span>
          {provider && priceState === "ready" ? <span>via {provider}</span> : null}
          {/* Calendar-aware freshness so a stale series is never read as current. */}
          {freshness && priceState === "ready" ? <StalenessBadge freshness={freshness} /> : null}
          {/* FR-118 session hint — the OHLCV series carries freshness but no
              provider market_state, so the chart derives a humanized closed /
              stale label from freshness rather than presenting EOD bars as live. */}
          {priceState === "ready" && sessionLabelFromFreshness(freshness) ? (
            <span
              className="text-charcoal-500 truncate tracking-wide"
              title={`Session: ${sessionLabelFromFreshness(freshness)}`}
            >
              {sessionLabelFromFreshness(freshness)}
            </span>
          ) : null}
        </div>
      </div>

      {/* Earned indicator-chip row — exists only while ≥1 indicator is active. */}
      {selected.size > 0 ? (
        <div
          className="flex flex-wrap items-center gap-1 border-b px-3 py-1"
          style={{ borderColor: "var(--hairline-strong)" }}
          data-testid="indicator-chip-row"
        >
          {selectedKeys.map((key) => {
            const label = indicatorByKey(key)?.label ?? key;
            return (
              <span
                key={key}
                className="rounded-control border-charcoal-700 text-caption text-charcoal-300 flex h-6 items-center gap-1 border px-2 font-mono"
              >
                {label}
                <button
                  type="button"
                  onClick={() => toggleIndicator(key)}
                  aria-label={`Remove ${label}`}
                  className="text-charcoal-400 hover:text-charcoal-100 px-1 transition-colors"
                >
                  ×
                </button>
              </span>
            );
          })}
          {indicatorState === "loading" ? (
            <span className="text-charcoal-400 text-caption font-mono">computing…</span>
          ) : null}
          {indicatorState === "error" ? (
            <>
              <span className="text-negative text-caption font-mono">{indicatorError}</span>
              <button
                type="button"
                onClick={() => setIndicatorRetryNonce((n) => n + 1)}
                aria-label="Retry indicators"
                className="text-charcoal-400 text-caption hover:text-charcoal-100 font-mono transition-colors"
              >
                Retry
              </button>
            </>
          ) : null}
          <button
            type="button"
            onClick={clearAllIndicators}
            className="text-charcoal-400 hover:text-charcoal-100 text-caption ml-auto font-mono underline-offset-2 hover:underline"
          >
            Clear all ({selected.size})
          </button>
        </div>
      ) : null}

      {/* Chart — the canvas gets every row the old indicator wall used to eat. */}
      <div className="relative min-h-0 flex-1">
        <div ref={containerRef} className="absolute inset-0" data-testid="chart-container" />
        {priceState === "loading" ? (
          <div className="text-charcoal-400 bg-charcoal-950/80 text-body absolute inset-0 z-10 flex items-center justify-center font-mono">
            Loading {symbol}…
          </div>
        ) : null}
        {priceState === "error" ? (
          // z-10 + opaque surface: the lightweight-charts canvas paints its grid
          // ABOVE a transparent sibling, so without this the empty-state message is
          // occluded by the (now-cleared) chart (Bug-2 — the chart must visibly show
          // "No price data", not a blank grid the user can't read text over).
          <div className="bg-charcoal-950/92 absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 p-6 text-center">
            <p className="text-negative text-body font-mono">{priceError}</p>
            <Button size="sm" variant="outline" onClick={() => setRetryNonce((n) => n + 1)}>
              Retry
            </Button>
          </div>
        ) : null}
      </div>

      {/* Drawings inspector — earned row, exists only when drawings exist. */}
      {drawings.length > 0 ? (
        <div
          className="max-h-24 overflow-y-auto border-t px-3 py-1"
          style={{ borderColor: "var(--hairline-strong)" }}
        >
          <div className="mb-1 flex items-center gap-2">
            <span className="text-charcoal-500 text-micro font-mono">Drawings</span>
            <button
              type="button"
              onClick={onClearAllDrawings}
              className="text-charcoal-400 hover:text-charcoal-100 text-caption ml-auto font-mono underline-offset-2 hover:underline"
            >
              Clear drawings ({drawings.length})
            </button>
          </div>
          <div className="flex flex-wrap gap-1">
            {drawings.map((drawing) => {
              const active = selectedDrawingId === drawing.id;
              return (
                <span
                  key={drawing.id}
                  className={cn(
                    "rounded-control text-caption flex h-6 items-center gap-1 border px-2 font-mono",
                    active
                      ? "bg-charcoal-875 border-charcoal-600/50 text-charcoal-300"
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
                    {DRAWING_CHIP_LABELS[drawing.kind] ?? drawing.kind}
                  </button>
                  <button
                    type="button"
                    onClick={() => onToggleLock(drawing.id, !drawing.locked)}
                    aria-pressed={!!drawing.locked}
                    aria-label={drawing.locked ? "Unlock drawing" : "Lock drawing"}
                    className={cn(
                      "hover:text-charcoal-100 px-1",
                      drawing.locked && "text-charcoal-300",
                    )}
                  >
                    {drawing.locked ? (
                      <Lock className="size-2.5" />
                    ) : (
                      <Unlock className="size-2.5" />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => onDeleteDrawing(drawing.id)}
                    className="hover:text-negative px-1"
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
    </div>
  );
}

ChartPanel.displayName = "ChartPanel";

export default ChartPanel;
