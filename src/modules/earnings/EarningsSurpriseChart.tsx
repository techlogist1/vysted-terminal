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

import type { EarningsSurprise } from "../../../types/earnings";

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

const POSITIVE = "#4ec9a3";
const NEGATIVE = "#c8654b";

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
    series.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [surprises, limit]);

  return <div ref={containerRef} className="h-48 w-full" data-testid="earnings-surprise-chart" />;
}
