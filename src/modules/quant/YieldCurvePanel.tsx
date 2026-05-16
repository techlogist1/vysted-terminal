"use client";

/**
 * Yield Curve Panel — Teammate Q Phase 6.
 *
 * Lets the user paste a grid of (type, tenor, unit, rate) instruments
 * for a depo + swap bootstrap, then renders the resulting
 * piecewise-linear zero curve via lightweight-charts. The user starts
 * with a US Treasury preset (1mo / 3mo / 6mo deposits + 2y / 5y / 10y /
 * 30y swaps) — the panel is a quant research surface, not a productive
 * trading interface, so editable presets are the right level of polish
 * for v0.6.0.
 */

import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { Activity } from "lucide-react";
import {
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";

import { Button } from "@/components/ui/button";
import { useQuantStore } from "@/store/quant";

import type { YieldCurveInstrument, YieldCurveRequest } from "../../../types/quant";

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

/** Preset matching the smoke-test in the spec. Approximate US Treasury 2026. */
const DEFAULT_INSTRUMENTS: YieldCurveInstrument[] = [
  { type: "deposit", tenor: 1, tenor_unit: "months", rate: 0.041 },
  { type: "deposit", tenor: 3, tenor_unit: "months", rate: 0.043 },
  { type: "deposit", tenor: 6, tenor_unit: "months", rate: 0.044 },
  { type: "swap", tenor: 2, tenor_unit: "years", rate: 0.045 },
  { type: "swap", tenor: 5, tenor_unit: "years", rate: 0.047 },
  { type: "swap", tenor: 10, tenor_unit: "years", rate: 0.05 },
  { type: "swap", tenor: 30, tenor_unit: "years", rate: 0.052 },
];

const DEFAULT_VALUATION_DATE = "2026-05-16";

export function YieldCurvePanel() {
  const lastResult = useQuantStore((s) => s.lastYieldCurve);
  const status = useQuantStore((s) => s.yieldCurveStatus);
  const error = useQuantStore((s) => s.yieldCurveError);
  const bootstrap = useQuantStore((s) => s.bootstrapYieldCurve);

  const [valuationDate, setValuationDate] = useState(DEFAULT_VALUATION_DATE);
  const [instruments, setInstruments] = useState<YieldCurveInstrument[]>(DEFAULT_INSTRUMENTS);
  const [sampleCount, setSampleCount] = useState("30");

  const isRunning = status === "loading";

  const handleBootstrap = useCallback(async () => {
    const req: YieldCurveRequest = {
      valuation_date: valuationDate,
      instruments,
      sample_count: Number(sampleCount) || 30,
    };
    try {
      await bootstrap(req);
    } catch {
      // surfaced via store
    }
  }, [valuationDate, instruments, sampleCount, bootstrap]);

  const updateRow = useCallback((idx: number, patch: Partial<YieldCurveInstrument>) => {
    setInstruments((rows) => rows.map((row, i) => (i === idx ? { ...row, ...patch } : row)));
  }, []);

  // Chart wiring
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const chart = createChart(container, { ...CHART_THEME, autoSize: true });
    chartRef.current = chart;
    const series = chart.addSeries(LineSeries, {
      color: AMBER,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      title: "Zero",
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
    if (!series || !lastResult) {
      return;
    }
    const data = lastResult.curve.map((p) => ({
      time: Math.floor(new Date(p.date).getTime() / 1000) as UTCTimestamp,
      value: p.zero_rate * 100, // percent for display
    }));
    series.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [lastResult]);

  return (
    <div className="bg-charcoal-900 flex h-full min-h-0 w-full">
      <aside
        className="border-charcoal-700 flex w-80 flex-col gap-3 overflow-y-auto border-r p-3"
        data-testid="yield-curve-form"
      >
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-300 font-mono text-[10px]">Valuation date</span>
          <input
            type="date"
            value={valuationDate}
            onChange={(e) => setValuationDate(e.target.value)}
            disabled={isRunning}
            data-testid="field-valuation-date"
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs outline-none focus-visible:border-amber-500 disabled:opacity-50"
          />
        </label>

        <div className="flex flex-col gap-1.5">
          <span className="text-charcoal-500 font-mono text-[10px] tracking-widest uppercase">
            Instruments
          </span>
          <div className="text-charcoal-500 grid grid-cols-12 gap-1 font-mono text-[9px] uppercase">
            <span className="col-span-3">Type</span>
            <span className="col-span-3">Tenor</span>
            <span className="col-span-2">Unit</span>
            <span className="col-span-4">Rate</span>
          </div>
          {instruments.map((row, idx) => (
            <div
              key={idx}
              className="grid grid-cols-12 items-center gap-1"
              data-testid={`inst-${idx}`}
            >
              <select
                value={row.type}
                onChange={(e) => updateRow(idx, { type: e.target.value as "deposit" | "swap" })}
                disabled={isRunning}
                className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control col-span-3 h-7 border px-1 font-mono text-[10px] outline-none focus-visible:border-amber-500"
              >
                <option value="deposit">depo</option>
                <option value="swap">swap</option>
              </select>
              <input
                type="number"
                min={1}
                value={row.tenor}
                onChange={(e) => updateRow(idx, { tenor: Number(e.target.value) || 1 })}
                disabled={isRunning}
                className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control col-span-3 h-7 border px-1 font-mono text-[10px] outline-none focus-visible:border-amber-500"
              />
              <select
                value={row.tenor_unit}
                onChange={(e) =>
                  updateRow(idx, { tenor_unit: e.target.value as "months" | "years" })
                }
                disabled={isRunning}
                className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control col-span-2 h-7 border px-1 font-mono text-[10px] outline-none focus-visible:border-amber-500"
              >
                <option value="months">mo</option>
                <option value="years">yr</option>
              </select>
              <input
                type="number"
                step="0.001"
                value={row.rate}
                onChange={(e) => updateRow(idx, { rate: Number(e.target.value) || 0 })}
                disabled={isRunning}
                className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control col-span-4 h-7 border px-1 font-mono text-[10px] outline-none focus-visible:border-amber-500"
              />
            </div>
          ))}
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-charcoal-300 font-mono text-[10px]">Sample points</span>
          <input
            type="number"
            min={3}
            max={200}
            value={sampleCount}
            onChange={(e) => setSampleCount(e.target.value)}
            disabled={isRunning}
            data-testid="field-sample-count"
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs outline-none focus-visible:border-amber-500 disabled:opacity-50"
          />
        </label>

        <Button
          type="button"
          onClick={handleBootstrap}
          disabled={isRunning}
          size="sm"
          variant="default"
          className="mt-auto"
          data-testid="bootstrap-curve"
        >
          <Activity />
          {isRunning ? "Bootstrapping…" : "Bootstrap"}
        </Button>
      </aside>

      <section className="flex min-h-0 flex-1 flex-col p-4">
        {error && (
          <p
            className="text-negative bg-negative/10 border-negative/30 rounded-control mb-3 border p-2 font-mono text-xs"
            role="alert"
            data-testid="yield-curve-error"
          >
            {error}
          </p>
        )}

        <div className="border-charcoal-700 bg-charcoal-850 rounded-control mb-3 border p-2">
          <div className="text-charcoal-500 mb-1 font-mono text-[10px] tracking-widest uppercase">
            Zero curve (continuously compounded, %)
          </div>
          <div ref={containerRef} className="h-72 w-full" data-testid="yield-curve-chart" />
        </div>

        {lastResult && lastResult.curve.length > 0 && (
          <div
            className="border-charcoal-700 bg-charcoal-850 rounded-control border p-3"
            data-testid="yield-curve-table"
          >
            <div className="text-charcoal-500 mb-2 font-mono text-[10px] tracking-widest uppercase">
              Sampled curve · {lastResult.curve.length} points · computed in{" "}
              {lastResult.duration_ms.toFixed(1)} ms
            </div>
            <div className="text-charcoal-300 grid grid-cols-4 gap-2 font-mono text-[10px]">
              <span className="text-charcoal-500">Tenor (y)</span>
              <span className="text-charcoal-500">Date</span>
              <span className="text-charcoal-500">Zero rate</span>
              <span className="text-charcoal-500">DF</span>
              {lastResult.curve.map((p, idx) => (
                <Fragment key={`pt-${idx}-${p.date}`}>
                  <span>{p.tenor_years.toFixed(3)}</span>
                  <span>{p.date}</span>
                  <span className="text-amber-200">{(p.zero_rate * 100).toFixed(3)}%</span>
                  <span>{p.discount_factor.toFixed(5)}</span>
                </Fragment>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
