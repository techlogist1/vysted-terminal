"use client";

import { useEffect, useRef } from "react";
import { LineChart } from "lucide-react";
import {
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
} from "lightweight-charts";

import { EmptyState } from "@/components/EmptyState";
import {
  ACCENT_CORAL,
  CHART_BORDER,
  CHART_CROSSHAIR,
  CHART_GRID,
  CHART_SURFACE,
  CHART_TEXT,
} from "@/lib/chart-theme";

import type { PriceTargetEntry } from "../../../types/analyst";

const CHART_THEME = {
  layout: {
    background: { color: CHART_SURFACE },
    textColor: CHART_TEXT,
    fontFamily: "var(--font-jetbrains-mono), ui-monospace, 'SF Mono', monospace",
  },
  grid: {
    vertLines: { color: CHART_GRID },
    horzLines: { color: CHART_GRID },
  },
  rightPriceScale: { borderColor: CHART_BORDER },
  timeScale: { borderColor: CHART_BORDER, timeVisible: false, secondsVisible: false },
  crosshair: { vertLine: { color: CHART_CROSSHAIR }, horzLine: { color: CHART_CROSSHAIR } },
} as const;

const AMBER = ACCENT_CORAL;

function toChartTime(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

interface Props {
  history: PriceTargetEntry[];
}

/**
 * Line chart of price-target values over time. Aggregates points across
 * firms; the panel chart is intentionally one line — per-firm overlays
 * belong in a future drill-down once we have richer track data. With no
 * history the surface is the composed dense EmptyState — never an empty
 * chart frame with a prose overlay.
 */
export function PriceTargetTimeline({ history }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  const hasData = history.length > 0;

  useEffect(() => {
    if (!hasData) return;
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
  }, [hasData]);

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

  if (!hasData) {
    return (
      <div data-testid="price-target-timeline-chart">
        <EmptyState
          dense
          icon={LineChart}
          headline="No price-target history"
          hint="Consensus target moves chart here once covering firms publish revisions."
        />
      </div>
    );
  }

  return (
    <div
      className={"h-64 w-full" /* tokens-ok: chart canvas height — layout, not rhythm */}
      data-testid="price-target-timeline-chart"
    >
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}
