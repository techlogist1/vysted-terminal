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
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";

import { Button } from "@/components/ui/button";
import { SidecarError, sidecarApi } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import type { IndicatorResponse, OHLCVSeries } from "../../../types/data";
import { fetchIndicators } from "./api";
import { IchimokuCloudPrimitive } from "./ichimoku-cloud-primitive";
import { INDICATOR_CATALOG, INDICATOR_COLORS, type IndicatorDef } from "./indicators";
import { VolumeProfilePrimitive } from "./volume-profile-primitive";

/** Bar intervals the chart panel exposes — mirrors the sidecar's `timeframe`. */
const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

const DEFAULT_SYMBOL = "SPY";
const DEFAULT_TIMEFRAME: Timeframe = "1d";

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

type LoadState = "idle" | "loading" | "ready" | "error";

/**
 * Chart panel — a lightweight-charts candlestick chart with a symbol input, a
 * timeframe selector, and a 20-indicator multi-select. Selected indicators are
 * computed server-side; price-pane overlays draw on the candle pane and
 * oscillators each get their own synced pane below it.
 */
function ChartPanel() {
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

  const [symbolInput, setSymbolInput] = useState(DEFAULT_SYMBOL);
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
  const [timeframe, setTimeframe] = useState<Timeframe>(DEFAULT_TIMEFRAME);
  const [selected, setSelected] = useState<Set<string>>(() => new Set());

  const [priceState, setPriceState] = useState<LoadState>("idle");
  const [priceError, setPriceError] = useState<string | null>(null);
  const [indicatorState, setIndicatorState] = useState<LoadState>("idle");
  const [indicatorError, setIndicatorError] = useState<string | null>(null);
  const [provider, setProvider] = useState<string | null>(null);

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
    return () => {
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      indicatorSeriesRef.current = [];
      volumeProfileRef.current = null;
      ichimokuCloudRef.current = null;
      sarMarkersRef.current = null;
      candleDataRef.current = [];
    };
  }, []);

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

  // --- handlers -----------------------------------------------------------
  const submitSymbol = useCallback(() => {
    const next = symbolInput.trim().toUpperCase();
    if (next.length > 0) {
      setSymbol(next);
      setSymbolInput(next);
    }
  }, [symbolInput]);

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
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
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

        <div className="text-charcoal-400 ml-auto font-mono text-xs">
          <span className="text-charcoal-200">{symbol}</span>
          {provider ? <span className="ml-2">via {provider}</span> : null}
        </div>
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

      {/* Indicator selector */}
      <div className="border-charcoal-700 max-h-44 overflow-y-auto border-t px-3 py-2">
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
        <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-4">
          {INDICATOR_CATALOG.map(renderIndicatorButton)}
        </div>
      </div>
    </div>
  );
}

ChartPanel.displayName = "ChartPanel";

export default ChartPanel;
