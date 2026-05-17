"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
} from "lightweight-charts";

import type { MacroSeriesExtended } from "../../../types/macro";

/** Vysted dark palette, applied to the lightweight-charts canvas. Same shape
 * as the equity chart's :const:`CHART_THEME` so the panels feel consistent. */
const CHART_THEME = {
  layout: {
    background: { color: "#1c1916" }, // charcoal-900
    textColor: "#c9c2b2", // charcoal-200
    fontFamily: "var(--font-jetbrains-mono), ui-monospace, 'SF Mono', 'Cascadia Mono', monospace",
  },
  grid: {
    vertLines: { color: "#2a2620" },
    horzLines: { color: "#2a2620" },
  },
  rightPriceScale: { borderColor: "#3a352c" },
  timeScale: { borderColor: "#3a352c", timeVisible: false, secondsVisible: false },
  crosshair: { vertLine: { color: "#4d4639" }, horzLine: { color: "#4d4639" } },
} as const;

const LINE_COLOR = "#c39a3e"; // amber-600 — Vysted accent

interface Props {
  series: MacroSeriesExtended;
  /** Optional override to start in log scale. */
  defaultLogScale?: boolean;
}

/**
 * Single-line macro time-series chart.
 *
 * Reuses the same lightweight-charts canvas the equity chart uses, but with
 * a line series (macro time series are typically scalar values without
 * OHLC structure) and a daily-or-coarser time scale. The toggle in the
 * header switches between linear and log price scales — useful for
 * series like CPI that span many orders of magnitude.
 *
 * Missing observations (`value === null`) are skipped — lightweight-charts
 * expects strictly-increasing time + non-null values per LineData point.
 */
export function MacroChart({ series, defaultLogScale = false }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const [logScale, setLogScale] = useState<boolean>(defaultLogScale);

  // Convert observations to lightweight-charts LineData, dropping nulls
  // and sorting by time (the API requires strictly-ascending time).
  const lineData: LineData[] = useMemo(() => {
    const points: LineData[] = [];
    for (const obs of series.observations) {
      if (obs.value === null) continue;
      const ts = Math.floor(new Date(obs.date).getTime() / 1000);
      if (!Number.isFinite(ts)) continue;
      points.push({ time: ts as UTCTimestamp, value: obs.value });
    }
    points.sort((a, b) => (a.time as number) - (b.time as number));
    // De-duplicate any equal-time entries (some providers emit dup rows).
    const deduped: LineData[] = [];
    let last: number | null = null;
    for (const p of points) {
      if (last !== null && (p.time as number) === last) continue;
      deduped.push(p);
      last = p.time as number;
    }
    return deduped;
  }, [series.observations]);

  // Mount the chart once; tear it down on unmount.
  useEffect(() => {
    const host = containerRef.current;
    if (!host) return;
    const chart = createChart(host, {
      ...CHART_THEME,
      autoSize: true,
    });
    const line = chart.addSeries(LineSeries, {
      color: LINE_COLOR,
      lineWidth: 2,
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });
    chartRef.current = chart;
    seriesRef.current = line;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Push data whenever the underlying series changes.
  useEffect(() => {
    if (!seriesRef.current) return;
    seriesRef.current.setData(lineData);
    chartRef.current?.timeScale().fitContent();
  }, [lineData]);

  // Toggle log scale on the right price scale when the prop changes.
  useEffect(() => {
    chartRef.current?.priceScale("right").applyOptions({ mode: logScale ? 1 : 0 });
  }, [logScale]);

  return (
    <div className="flex h-full flex-col" data-testid="macro-chart">
      <div className="border-charcoal-800 flex items-center justify-between gap-2 border-b px-3 py-1.5">
        <div className="flex min-w-0 flex-col">
          <span className="text-charcoal-100 truncate font-mono text-[12px]">{series.title}</span>
          <span className="text-charcoal-500 truncate font-mono text-[10px]">
            {series.series_id} • {series.provider}
            {series.units ? ` • ${series.units}` : ""}
            {series.frequency ? ` • ${series.frequency}` : ""}
          </span>
        </div>
        <label className="text-charcoal-400 flex items-center gap-1.5 font-mono text-[11px]">
          <input
            type="checkbox"
            checked={logScale}
            onChange={(e) => setLogScale(e.target.checked)}
            data-testid="macro-log-toggle"
          />
          log
        </label>
      </div>
      <div ref={containerRef} className="flex-1" data-testid="macro-chart-canvas" />
      <div className="border-charcoal-800 text-charcoal-500 border-t px-3 py-1 font-mono text-[10px]">
        {lineData.length} observations
        {series.last_updated ? ` • updated ${formatDate(series.last_updated)}` : ""}
        {series.source_url ? (
          <>
            {" • "}
            <a
              href={series.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber-600 hover:underline"
            >
              source
            </a>
          </>
        ) : null}
      </div>
    </div>
  );
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}
