"use client";

/**
 * Yield Curve — depo + swap bootstrap of a piecewise-linear zero curve.
 *
 * R7 layout (VYSTED_DESIGN.md):
 *
 *   ┌──────────────┬──────────────────────────────────────────────────┐
 *   │ INPUT RAIL   │ ZERO CURVE — lightweight-charts line             │
 *   │  valuation   ├──────────────────────────────────────────────────┤
 *   │  instrument  │ SAMPLED CURVE — full-width DataTable             │
 *   │  grid of     │   tenor · date · zero rate · discount factor     │
 *   │  32px inputs ├──────────────────────────────────────────────────┤
 *   │  inline      │ N points · computed in N ms                      │
 *   │  validation  │                                                  │
 *   │ [Bootstrap]  │                                                  │
 *   └──────────────┴──────────────────────────────────────────────────┘
 *
 * Every instrument-grid control sits on the 32px ladder at text-body;
 * validation (ordered tenors aside — the engine owns that) is an honest
 * inline line. Before the first bootstrap the results column is the shared
 * composed EmptyState (the chart only mounts with data, never an empty frame);
 * the sampled curve renders through the one shared DataTable primitive.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity } from "lucide-react";
import {
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";

import { DataTable, type DataColumn } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import {
  ACCENT_CORAL,
  CHART_BORDER,
  CHART_CROSSHAIR,
  CHART_GRID,
  CHART_SURFACE,
  CHART_TEXT,
} from "@/lib/chart-theme";
import { useQuantStore } from "@/store/quant";

import type {
  YieldCurveInstrument,
  YieldCurvePoint,
  YieldCurveRequest,
} from "../../../types/quant";

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

/** Shared classes for the dense instrument-grid controls — 32px ladder,
 *  text-body, inset fill (the rail is narrow, so padding drops to 8px). */
const gridControlClass =
  "bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 border px-2 outline-none disabled:opacity-50";

const CURVE_COLUMNS: DataColumn<YieldCurvePoint>[] = [
  {
    key: "tenor_years",
    header: "Tenor (y)",
    numeric: true,
    width: "20%",
    format: (p) => p.tenor_years.toFixed(3),
  },
  { key: "date", header: "Date", tier: "secondary", width: "30%", format: (p) => p.date },
  {
    key: "zero_rate",
    header: "Zero rate",
    numeric: true,
    width: "25%",
    format: (p) => `${(p.zero_rate * 100).toFixed(3)}%`,
  },
  {
    key: "discount_factor",
    header: "DF",
    numeric: true,
    tier: "secondary",
    width: "25%",
    format: (p) => p.discount_factor.toFixed(5),
  },
];

/** Pulse skeleton mirroring the result layout — first bootstrap only. */
function ResultSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-8" data-testid="yield-curve-skeleton">
      <div className="border-charcoal-700 rounded-none border p-6">
        <div className="bg-charcoal-800 h-3 w-40 rounded-none" />
        <div className="bg-charcoal-800 mt-3 h-56 w-full rounded-none" />
      </div>
      <div className="border-charcoal-700 rounded-none border p-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-charcoal-800 mt-2 h-3 w-full rounded-none first:mt-0" />
        ))}
      </div>
    </div>
  );
}

export function YieldCurvePanel() {
  const lastResult = useQuantStore((s) => s.lastYieldCurve);
  const status = useQuantStore((s) => s.yieldCurveStatus);
  const error = useQuantStore((s) => s.yieldCurveError);
  const bootstrap = useQuantStore((s) => s.bootstrapYieldCurve);

  const [valuationDate, setValuationDate] = useState(DEFAULT_VALUATION_DATE);
  const [instruments, setInstruments] = useState<YieldCurveInstrument[]>(DEFAULT_INSTRUMENTS);
  const [sampleCount, setSampleCount] = useState("30");

  const isRunning = status === "loading";
  const hasResult = lastResult !== null && lastResult.curve.length > 0;

  // Honest inline validation — surfaced in the rail, never a silent NaN POST.
  const validationError = useMemo(() => {
    if (valuationDate === "") {
      return "Valuation date is required.";
    }
    const samples = Number(sampleCount);
    if (sampleCount.trim() === "" || !Number.isInteger(samples) || samples < 3 || samples > 200) {
      return "Sample points must be a whole number from 3 to 200.";
    }
    for (const [idx, row] of instruments.entries()) {
      if (!Number.isFinite(row.tenor) || row.tenor < 1) {
        return `Instrument ${idx + 1}: tenor must be ≥ 1.`;
      }
      if (!Number.isFinite(row.rate) || row.rate <= 0) {
        return `Instrument ${idx + 1}: rate must be positive.`;
      }
    }
    return null;
  }, [valuationDate, sampleCount, instruments]);

  const handleBootstrap = useCallback(async () => {
    if (validationError !== null) {
      return;
    }
    const req: YieldCurveRequest = {
      valuation_date: valuationDate,
      instruments,
      sample_count: Number(sampleCount),
    };
    try {
      await bootstrap(req);
    } catch {
      // surfaced via store
    }
  }, [validationError, valuationDate, instruments, sampleCount, bootstrap]);

  const updateRow = useCallback((idx: number, patch: Partial<YieldCurveInstrument>) => {
    setInstruments((rows) => rows.map((row, i) => (i === idx ? { ...row, ...patch } : row)));
  }, []);

  // Chart wiring — the chart mounts only once there is a curve to draw (the
  // empty state owns the pre-bootstrap surface), so the create-effect keys on
  // `hasResult` instead of running once on mount.
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!hasResult) {
      return;
    }
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const chart = createChart(container, { ...CHART_THEME, autoSize: true });
    chartRef.current = chart;
    const series = chart.addSeries(LineSeries, {
      color: ACCENT_CORAL,
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
  }, [hasResult]);

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
  }, [lastResult, hasResult]);

  return (
    <div className="bg-charcoal-900 flex h-full min-h-0 w-full">
      {/* --- Input rail ----------------------------------------------------- */}
      <aside
        className="border-charcoal-700 flex w-80 shrink-0 flex-col gap-6 overflow-y-auto border-r p-6"
        data-testid="yield-curve-form"
      >
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-500 text-micro">Valuation date</span>
          <input
            type="date"
            value={valuationDate}
            onChange={(e) => setValuationDate(e.target.value)}
            disabled={isRunning}
            data-testid="field-valuation-date"
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 border px-3 tabular-nums outline-none disabled:opacity-50"
          />
        </label>

        <div className="flex flex-col gap-2">
          <span className="text-charcoal-500 text-micro">Instruments</span>
          <div className="text-charcoal-500 text-micro grid grid-cols-12 gap-1">
            <span className="col-span-3">Type</span>
            <span className="col-span-3">Tenor</span>
            <span className="col-span-2">Unit</span>
            <span className="col-span-4 text-right">Rate</span>
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
                aria-label={`Instrument ${idx + 1} type`}
                className={`${gridControlClass} col-span-3`}
              >
                <option value="deposit">depo</option>
                <option value="swap">swap</option>
              </select>
              <input
                type="number"
                min={1}
                value={row.tenor}
                onChange={(e) => updateRow(idx, { tenor: Number(e.target.value) })}
                disabled={isRunning}
                aria-label={`Instrument ${idx + 1} tenor`}
                className={`${gridControlClass} col-span-3 tabular-nums`}
              />
              <select
                value={row.tenor_unit}
                onChange={(e) =>
                  updateRow(idx, { tenor_unit: e.target.value as "months" | "years" })
                }
                disabled={isRunning}
                aria-label={`Instrument ${idx + 1} tenor unit`}
                className={`${gridControlClass} col-span-2 px-1`}
              >
                <option value="months">mo</option>
                <option value="years">yr</option>
              </select>
              <input
                type="number"
                step="0.001"
                value={row.rate}
                onChange={(e) => updateRow(idx, { rate: Number(e.target.value) })}
                disabled={isRunning}
                aria-label={`Instrument ${idx + 1} rate`}
                className={`${gridControlClass} col-span-4 text-right tabular-nums`}
              />
            </div>
          ))}
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-charcoal-500 text-micro">Sample points</span>
          <input
            type="number"
            min={3}
            max={200}
            value={sampleCount}
            onChange={(e) => setSampleCount(e.target.value)}
            disabled={isRunning}
            data-testid="field-sample-count"
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 border px-3 tabular-nums outline-none disabled:opacity-50"
          />
        </label>

        {validationError !== null && (
          <p
            className="text-negative text-caption"
            role="alert"
            data-testid="yield-curve-validation"
          >
            {validationError}
          </p>
        )}

        <Button
          type="button"
          onClick={handleBootstrap}
          disabled={isRunning || validationError !== null}
          size="sm"
          variant="default"
          className="mt-auto"
          data-testid="bootstrap-curve"
        >
          <Activity />
          {isRunning ? "Bootstrapping…" : "Bootstrap"}
        </Button>
      </aside>

      {/* --- Results -------------------------------------------------------- */}
      <section className="flex min-h-0 min-w-0 flex-1 flex-col gap-8 overflow-y-auto p-6">
        {error && (
          <p
            className="text-negative bg-negative/10 border-negative/30 text-caption rounded-none border px-3 py-2"
            role="alert"
            data-testid="yield-curve-error"
          >
            {error}
          </p>
        )}

        {!hasResult && !isRunning && (
          <EmptyState
            icon={Activity}
            headline="No curve bootstrapped"
            hint="Adjust the deposit + swap instruments on the left and bootstrap — the zero curve and its sampled points land here."
            cta={{ label: "Bootstrap curve", onClick: () => void handleBootstrap(), primary: true }}
          />
        )}

        {!hasResult && isRunning && <ResultSkeleton />}

        {hasResult && lastResult && (
          <div className="flex flex-col gap-8" data-testid="yield-curve-result">
            <div className="border-charcoal-700 rounded-none border">
              <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
                Zero curve (continuously compounded, %)
              </h3>
              <div className="p-3">
                <div ref={containerRef} className="h-72 w-full" data-testid="yield-curve-chart" />
              </div>
            </div>

            <div
              className="border-charcoal-700 rounded-none border"
              data-testid="yield-curve-table"
            >
              <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
                Sampled curve
              </h3>
              <DataTable
                columns={CURVE_COLUMNS}
                rows={lastResult.curve}
                rowKey={(p, i) => `${p.date}-${i}`}
                data-testid="yield-curve-points"
              />
            </div>

            <div className="text-charcoal-500 text-micro">
              {lastResult.curve.length} points · computed in {lastResult.duration_ms.toFixed(1)} ms
              · piecewise-linear zero bootstrap
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
