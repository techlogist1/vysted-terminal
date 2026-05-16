"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
} from "lightweight-charts";

import type { PriceTargetEntry } from "../../../types/analyst";

const CHART_THEME = {
  layout: {
    background: { color: "#1c1916" },
    textColor: "#c9c2b2",
    fontFamily: "var(--font-jetbrains-mono), ui-monospace, 'SF Mono', monospace",
  },
  grid: {
    vertLines: { color: "#2a2620" },
    horzLines: { color: "#2a2620" },
  },
  rightPriceScale: { borderColor: "#3a352c" },
  timeScale: { borderColor: "#3a352c", timeVisible: false, secondsVisible: false },
  crosshair: { vertLine: { color: "#4d4639" }, horzLine: { color: "#4d4639" } },
} as const;

const AMBER = "#e8b441";

function toChartTime(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

interface Props {
  history: PriceTargetEntry[];
}

/**
 * Line chart of price-target values over time. Aggregates points across
 * firms; the panel chart is intentionally one line — per-firm overlays
 * belong in a future drill-down once we have richer track data.
 */
export function PriceTargetTimeline({ history }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chart = createChart(container, { ...CHART_THEME, autoSize: true });
    chartRef.current = chart;
    const series = chart.addSeries(LineSeries, {
      color: AMBER,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      title: "Price Target",
    });
    seriesRef.current = series;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    if (history.length === 0) {
      series.setData([]);
      return;
    }
    // Sort oldest-first for the chart; collapse duplicate-time entries by
    // averaging targets — common when several firms re-rate on the same day.
    const buckets = new Map<number, { sum: number; count: number }>();
    for (const entry of history) {
      const time = toChartTime(entry.date) as number;
      const bucket = buckets.get(time) ?? { sum: 0, count: 0 };
      bucket.sum += entry.target_to;
      bucket.count += 1;
      buckets.set(time, bucket);
    }
    const data: LineData<UTCTimestamp>[] = Array.from(buckets.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([time, { sum, count }]) => ({
        time: time as UTCTimestamp,
        value: sum / count,
      }));
    series.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [history]);

  return (
    <div ref={containerRef} className="h-64 w-full" data-testid="price-target-timeline-chart" />
  );
}
