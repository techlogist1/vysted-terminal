"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type HistogramData,
  type UTCTimestamp,
} from "lightweight-charts";

import {
  CHART_BORDER,
  CHART_CROSSHAIR,
  CHART_GRID,
  CHART_SURFACE,
  CHART_TEXT,
  NEGATIVE as NEGATIVE_COLOR,
  POSITIVE as POSITIVE_COLOR,
} from "@/lib/chart-theme";
import type { EarningsSurprise } from "../../../types/earnings";

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

const POSITIVE = POSITIVE_COLOR;
const NEGATIVE = NEGATIVE_COLOR;

function toChartTime(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

interface Props {
  surprises: EarningsSurprise[];
  /** Optional cap on the most-recent N quarters to render. Defaults to 12. */
  limit?: number;
}

/**
 * Histogram chart of recent earnings surprises (EPS actual minus estimate).
 * Positive surprises render in the green positive colour, negatives in red.
 * The chart renders at the parent container's intrinsic size; the caller
 * is responsible for giving it a sized div.
 */
export function EarningsSurpriseChart({ surprises, limit = 12 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const chart = createChart(container, { ...CHART_THEME, autoSize: true });
    chartRef.current = chart;
    const series = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      priceLineVisible: false,
      lastValueVisible: false,
      title: "Surprise (EPS $)",
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
    if (!series) {
      return;
    }
    if (surprises.length === 0) {
      series.setData([]);
      return;
    }
    // Sort newest-first → reverse for chart (oldest-first).
    const trimmed = [...surprises].sort(
      (a, b) => new Date(a.reported_date).getTime() - new Date(b.reported_date).getTime(),
    );
    const tail = trimmed.slice(-limit);
    const data: HistogramData<UTCTimestamp>[] = tail.map((entry) => ({
      time: toChartTime(entry.reported_date),
      value: entry.eps_surprise,
      color: entry.eps_surprise >= 0 ? POSITIVE : NEGATIVE,
    }));
    // Two surprises sharing a reported_date floor to the same second-resolution
    // timestamp; lightweight-charts throws "data must be asc ordered by time"
    // on duplicates, so collapse equal-time points (keep the latest) before
    // setData — mirrors MacroChart's dedupe (hunt-data-edge).
    const deduped: HistogramData<UTCTimestamp>[] = [];
    for (const point of data) {
      const previous = deduped[deduped.length - 1];
      if (previous && (point.time as number) === (previous.time as number)) {
        deduped[deduped.length - 1] = point;
        continue;
      }
      deduped.push(point);
    }
    series.setData(deduped);
    chartRef.current?.timeScale().fitContent();
  }, [surprises, limit]);

  return (
    <div className="relative h-48 w-full" data-testid="earnings-surprise-chart">
      <div ref={containerRef} className="h-full w-full" />
      {surprises.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-charcoal-400 font-mono text-xs">
            No surprise history available for this symbol.
          </p>
        </div>
      )}
    </div>
  );
}
