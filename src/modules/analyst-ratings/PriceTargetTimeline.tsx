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
import { currencyAffix } from "@/lib/format";

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
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  // R15-DATA-069: how many targets were revised into each point's mean, keyed
  // by the same UTCTimestamp the series data uses — read by the crosshair
  // tooltip below, never rendered as a fake per-firm data point.
  const countsRef = useRef<Map<number, number>>(new Map());

  const hasData = history.length > 0;
  // R15-DATA-031: "Price Target" carried no unit at all — label it with the
  // data's own currency instead of leaving the line unlabelled.
  const currency = history[0]?.currency ?? null;

  useEffect(() => {
    if (!hasData) return;
    const container = containerRef.current;
    if (!container) return;
    const chart = createChart(container, { ...CHART_THEME, autoSize: true });
    chartRef.current = chart;
    const { prefix, suffix } = currencyAffix(currency);
    const series = chart.addSeries(LineSeries, {
      color: AMBER,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      // R15-DATA-069: a point is the MEAN of every target revised that day,
      // never a single firm's figure — say so, so the line is never read as
      // one analyst's track.
      title: `Mean of targets revised that day (${prefix}${suffix})`,
    });
    seriesRef.current = series;
    const tooltip = tooltipRef.current;
    const onCrosshair: Parameters<typeof chart.subscribeCrosshairMove>[0] = (param) => {
      if (!tooltip) return;
      const time = param.time as number | undefined;
      const point = param.point;
      if (time === undefined || !point || !param.seriesData.has(series)) {
        tooltip.style.display = "none";
        return;
      }
      const n = countsRef.current.get(time) ?? 1;
      tooltip.textContent = n === 1 ? "1 target" : `${n} targets revised`;
      tooltip.style.display = "block";
      tooltip.style.left = `${point.x + 12}px`;
      tooltip.style.top = `${point.y + 8}px`;
    };
    chart.subscribeCrosshairMove(onCrosshair);
    return () => {
      chart.unsubscribeCrosshairMove(onCrosshair);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [hasData, currency]);

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
    const counts = new Map<number, number>();
    const data: LineData<UTCTimestamp>[] = Array.from(buckets.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([time, { sum, count }]) => {
        counts.set(time, count);
        return { time: time as UTCTimestamp, value: sum / count };
      });
    countsRef.current = counts;
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
      className={"relative h-64 w-full" /* tokens-ok: chart canvas height — layout, not rhythm */}
      data-testid="price-target-timeline-chart"
    >
      <div ref={containerRef} className="h-full w-full" />
      <div
        ref={tooltipRef}
        data-testid="price-target-timeline-tooltip"
        className="border-border bg-popover text-popover-foreground pointer-events-none absolute z-10 hidden rounded border px-2 py-1 text-xs shadow-sm"
      />
    </div>
  );
}
