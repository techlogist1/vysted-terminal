"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FlaskConical, ArrowUp, ArrowDown, ReceiptText } from "lucide-react";
import {
  AreaSeries,
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type AreaData,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";

import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import {
  ACCENT_CORAL,
  CHART_BORDER,
  CHART_CROSSHAIR,
  CHART_GRID,
  CHART_SURFACE,
  CHART_TEXT,
  NEGATIVE as NEGATIVE_COLOR,
  negativeFill,
} from "@/lib/chart-theme";
import { cn } from "@/lib/utils";
import { usePanelContextBus } from "@/store/panel-context";
import { useBacktestStore, type BacktestRunState } from "@/store/backtest";
import type { BacktestTrade } from "../../../types/backtest";

// ---------------------------------------------------------------------------
// Chart theming — reused from ChartPanel for visual continuity
// ---------------------------------------------------------------------------

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

const NEGATIVE = NEGATIVE_COLOR;
const AMBER = ACCENT_CORAL;

function toChartTime(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

function formatMoney(value: number, fractionDigits = 0): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

function formatPercent(value: number, digits = 2): string {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;
}

// ---------------------------------------------------------------------------
// Equity curve + drawdown subchart
// ---------------------------------------------------------------------------

interface EquityChartProps {
  equityCurve: BacktestRunState["result"] extends infer R
    ? R extends { equityCurve: infer C }
      ? C
      : never
    : never;
}

function EquityChart({ equityCurve }: EquityChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const equitySeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const drawdownSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const chart = createChart(container, {
      ...CHART_THEME,
      autoSize: true,
    });
    chartRef.current = chart;

    // Pane 0 — equity curve as a line series.
    const equitySeries = chart.addSeries(
      LineSeries,
      {
        color: AMBER,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        title: "Equity",
      },
      0,
    );
    equitySeriesRef.current = equitySeries;

    // Pane 1 — drawdown as a shaded area below the equity line.
    const drawdownSeries = chart.addSeries(
      AreaSeries,
      {
        topColor: negativeFill(0.45),
        bottomColor: negativeFill(0.05),
        lineColor: NEGATIVE,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: true,
        title: "Drawdown %",
      },
      1,
    );
    drawdownSeriesRef.current = drawdownSeries;

    return () => {
      chart.remove();
      chartRef.current = null;
      equitySeriesRef.current = null;
      drawdownSeriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const equity = equitySeriesRef.current;
    const drawdown = drawdownSeriesRef.current;
    if (!equity || !drawdown) {
      return;
    }
    if (!equityCurve || equityCurve.length === 0) {
      equity.setData([]);
      drawdown.setData([]);
      return;
    }
    const equityData: LineData<Time>[] = [];
    const drawdownData: AreaData<Time>[] = [];
    for (const point of equityCurve) {
      const time = toChartTime(point.timestamp);
      if (Number.isNaN(time)) {
        continue;
      }
      equityData.push({ time, value: point.equity });
      drawdownData.push({ time, value: point.drawdownPct * 100 });
    }
    // De-dup + sort defensive — lightweight-charts rejects unordered times.
    const uniqEquity = Array.from(
      new Map(equityData.map((p) => [p.time as number, p])).values(),
    ).sort((a, b) => (a.time as number) - (b.time as number));
    const uniqDrawdown = Array.from(
      new Map(drawdownData.map((p) => [p.time as number, p])).values(),
    ).sort((a, b) => (a.time as number) - (b.time as number));
    equity.setData(uniqEquity);
    drawdown.setData(uniqDrawdown);
    chartRef.current?.timeScale().fitContent();
  }, [equityCurve]);

  return (
    <div className="relative min-h-0 flex-1">
      <div ref={containerRef} className="absolute inset-0" data-testid="equity-chart-container" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trade log table
// ---------------------------------------------------------------------------

type TradeSortKey = "enteredAt" | "pnl" | "symbol";

interface TradeTableProps {
  trades: BacktestTrade[];
}

function TradeTable({ trades }: TradeTableProps) {
  const [sortKey, setSortKey] = useState<TradeSortKey>("enteredAt");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    const list = [...trades];
    list.sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      if (sortKey === "pnl") {
        const an = (a.pnl ?? 0) as number;
        const bn = (b.pnl ?? 0) as number;
        return direction === "asc" ? an - bn : bn - an;
      }
      if (av < bv) return direction === "asc" ? -1 : 1;
      if (av > bv) return direction === "asc" ? 1 : -1;
      return 0;
    });
    return list;
  }, [trades, sortKey, direction]);

  const handleSort = useCallback(
    (key: TradeSortKey) => {
      if (key === sortKey) {
        setDirection((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setDirection(key === "pnl" ? "desc" : "asc");
      }
    },
    [sortKey],
  );

  if (trades.length === 0) {
    return (
      <EmptyState
        dense
        icon={ReceiptText}
        headline="No trades yet"
        hint="Fills appear here as the strategy trades."
      />
    );
  }

  // Auto table layout + nowrap cells: every column takes the width its widest
  // value needs — no fixed <colgroup> widths clipping prices mid-number.
  return (
    <div
      className={
        "max-h-64 overflow-x-auto overflow-y-auto" /* tokens-ok: trade-log scroll cap - layout, not rhythm */
      }
    >
      <table className="w-full border-collapse">
        <thead className="bg-charcoal-900 sticky top-0">
          <tr className="text-charcoal-400 border-charcoal-700 text-micro border-b text-left font-mono whitespace-nowrap uppercase">
            <th
              className={cn(
                "cursor-pointer px-3 py-1 font-medium",
                sortKey === "symbol" ? "text-charcoal-100" : "text-charcoal-400",
              )}
              onClick={() => handleSort("symbol")}
            >
              Symbol
              {sortKey === "symbol" ? (
                direction === "asc" ? (
                  <ArrowUp className="ml-0.5 inline size-3" />
                ) : (
                  <ArrowDown className="ml-0.5 inline size-3" />
                )
              ) : (
                <span className="text-charcoal-600 ml-0.5">↕</span>
              )}
            </th>
            <th className="px-3 py-1 font-medium">Side</th>
            <th
              className={cn(
                "cursor-pointer px-3 py-1 font-medium",
                sortKey === "enteredAt" ? "text-charcoal-100" : "text-charcoal-400",
              )}
              onClick={() => handleSort("enteredAt")}
            >
              Entered
              {sortKey === "enteredAt" ? (
                direction === "asc" ? (
                  <ArrowUp className="ml-0.5 inline size-3" />
                ) : (
                  <ArrowDown className="ml-0.5 inline size-3" />
                )
              ) : (
                <span className="text-charcoal-600 ml-0.5">↕</span>
              )}
            </th>
            <th className="px-3 py-1 font-medium">Exited</th>
            <th className="px-3 py-1 text-right font-medium">Entry</th>
            <th className="px-3 py-1 text-right font-medium">Exit</th>
            <th className="px-3 py-1 text-right font-medium">Qty</th>
            <th
              className={cn(
                "cursor-pointer px-3 py-1 text-right font-medium",
                sortKey === "pnl" ? "text-charcoal-100" : "text-charcoal-400",
              )}
              onClick={() => handleSort("pnl")}
            >
              P&amp;L
              {sortKey === "pnl" ? (
                direction === "asc" ? (
                  <ArrowUp className="ml-0.5 inline size-3" />
                ) : (
                  <ArrowDown className="ml-0.5 inline size-3" />
                )
              ) : (
                <span className="text-charcoal-600 ml-0.5">↕</span>
              )}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((trade) => {
            const pnl = trade.pnl ?? null;
            const positive = (pnl ?? 0) > 0;
            return (
              <tr
                key={trade.id}
                className="border-charcoal-800 hover:bg-charcoal-800/40 text-caption border-b font-mono"
              >
                <td className="text-charcoal-100 px-3 py-1 whitespace-nowrap">{trade.symbol}</td>
                <td className="text-charcoal-300 px-3 py-1 whitespace-nowrap">{trade.side}</td>
                <td className="text-charcoal-300 px-3 py-1 whitespace-nowrap tabular-nums">
                  {trade.enteredAt.slice(0, 10)}
                </td>
                <td className="text-charcoal-300 px-3 py-1 whitespace-nowrap tabular-nums">
                  {trade.exitedAt ? trade.exitedAt.slice(0, 10) : "—"}
                </td>
                <td className="text-charcoal-300 px-3 py-1 text-right whitespace-nowrap tabular-nums">
                  {trade.entryPrice.toFixed(2)}
                </td>
                <td className="text-charcoal-300 px-3 py-1 text-right whitespace-nowrap tabular-nums">
                  {trade.exitPrice ? trade.exitPrice.toFixed(2) : "—"}
                </td>
                <td className="text-charcoal-300 px-3 py-1 text-right whitespace-nowrap tabular-nums">
                  {trade.quantity.toLocaleString("en-US")}
                </td>
                <td
                  className={cn(
                    "px-3 py-1 text-right whitespace-nowrap tabular-nums",
                    pnl === null
                      ? "text-charcoal-400"
                      : positive
                        ? "text-positive"
                        : "text-negative",
                  )}
                >
                  {pnl === null ? "—" : formatMoney(pnl, 0)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Walk-forward strip
// ---------------------------------------------------------------------------

interface WalkForwardStripProps {
  slices: NonNullable<BacktestRunState["result"]>["walkForwardSlices"] | null | undefined;
}

function WalkForwardStrip({ slices }: WalkForwardStripProps) {
  if (!slices || slices.length === 0) {
    return null;
  }
  return (
    <div className="border-charcoal-700 flex items-center gap-2 overflow-x-auto border-t px-3 py-2">
      <span className="text-charcoal-500 text-micro mr-1 font-mono tracking-widest uppercase">
        Walk-fwd
      </span>
      {slices.map((slice) => {
        const positive = slice.totalReturn >= 0;
        return (
          <div
            key={slice.index}
            className={cn(
              "rounded-control text-micro min-w-32 border px-2 py-1 font-mono",
              positive ? "border-positive/60" : "border-negative/60",
            )}
            title={`${slice.startDate} → ${slice.endDate}`}
          >
            <div className="text-charcoal-400">
              #{slice.index + 1} {slice.startDate.slice(0, 7)}–{slice.endDate.slice(0, 7)}
            </div>
            <div
              className={cn("mt-0.5 font-semibold", positive ? "text-positive" : "text-negative")}
            >
              {formatPercent(slice.totalReturn)}
            </div>
            <div className="text-charcoal-400">
              S {slice.sharpe.toFixed(2)} · {slice.trades}t
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Result view — top-level
// ---------------------------------------------------------------------------

interface BacktestResultViewProps {
  run: BacktestRunState | null;
  /** Invoked when the user clicks "Open in Strategy Critic". */
  onOpenInCritic?: (runId: string) => void;
}

export function BacktestResultView({ run, onOpenInCritic }: BacktestResultViewProps) {
  const startRun = useBacktestStore((s) => s.startRun);
  // Publish a context snapshot so the chat sidebar's Strategy Critic
  // invocation can pick up the focused run id.
  const publishPanelContext = usePanelContextBus((state) => state.publish);
  const unregisterPanelContext = usePanelContextBus((state) => state.unregisterSource);
  const runId = run?.runId ?? null;
  const strategyId = run?.request.strategyId ?? null;
  const status = run?.status ?? null;

  useEffect(() => {
    if (!runId) {
      return;
    }
    publishPanelContext({
      source: "backtest-panel",
      kind: "snapshot",
      payload: {
        runId,
        strategyId,
        status,
      },
      emittedAt: Date.now(),
    });
  }, [publishPanelContext, runId, strategyId, status]);

  useEffect(() => {
    return () => {
      unregisterPanelContext("backtest-panel");
    };
  }, [unregisterPanelContext]);

  if (!run) {
    return (
      <EmptyState
        icon={FlaskConical}
        headline="Run your first backtest"
        hint="Select a strategy on the left, set your date range, then click Run."
        className="h-full justify-center pt-0"
      />
    );
  }

  const metrics = run.result?.metrics;
  const progressPct =
    run.totalBars > 0 ? Math.min(100, Math.round((run.barsProcessed / run.totalBars) * 100)) : 0;

  return (
    <div className="flex h-full min-h-0 flex-col" data-run-id={run.runId}>
      {/* Header — status + metrics */}
      <div className="border-charcoal-700 text-caption border-b px-3 py-2 font-mono">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="text-charcoal-200">
            {run.request.strategyId} · {run.request.symbols.join(", ")}
          </span>
          {run.status === "streaming" && (
            <span className="text-charcoal-300" data-testid="streaming-progress">
              running… {run.barsProcessed}/{run.totalBars} ({progressPct}%)
            </span>
          )}
          {run.status === "pending" && <span className="text-charcoal-300">starting…</span>}
          {run.status === "error" && (
            <span className="text-negative" data-testid="run-error">
              error: {run.error}
            </span>
          )}
          {metrics && (
            <>
              <span>
                Return:{" "}
                <span className={metrics.totalReturn >= 0 ? "text-positive" : "text-negative"}>
                  {formatPercent(metrics.totalReturn)}
                </span>
              </span>
              <span>
                Sharpe: <span className="text-charcoal-100">{metrics.sharpe.toFixed(2)}</span>
              </span>
              <span>
                Sortino: <span className="text-charcoal-100">{metrics.sortino.toFixed(2)}</span>
              </span>
              <span>
                Calmar: <span className="text-charcoal-100">{metrics.calmar.toFixed(2)}</span>
              </span>
              <span>
                Max DD:{" "}
                <span className="text-negative">{formatPercent(metrics.maxDrawdownPct)}</span>
              </span>
              <span>
                Win rate:{" "}
                <span className="text-charcoal-100">{(metrics.winRate * 100).toFixed(1)}%</span>
              </span>
              <span>
                Trades: <span className="text-charcoal-100">{metrics.tradeCount}</span>
              </span>
            </>
          )}
        </div>
        {metrics && (
          <div className="mt-1 flex items-center justify-between">
            <span className="text-charcoal-500">
              {run.request.startDate} → {run.request.endDate} ·{" "}
              {formatMoney(run.request.initialCapital)} initial
            </span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => onOpenInCritic?.(run.runId)}
              data-testid="open-in-critic"
            >
              Open in Strategy Critic
            </Button>
          </div>
        )}
      </div>

      {/* Equity curve + drawdown */}
      {run.result ? (
        <EquityChart equityCurve={run.result.equityCurve} />
      ) : run.status === "error" ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
          <p className="text-negative text-caption font-mono">{run.error}</p>
          <Button size="sm" variant="outline" onClick={() => void startRun(run.request)}>
            Retry
          </Button>
        </div>
      ) : (
        <div className="text-charcoal-400 text-caption flex flex-1 items-center justify-center font-mono">
          computing equity curve…
        </div>
      )}

      {/* Walk-forward strip */}
      <WalkForwardStrip slices={run.result?.walkForwardSlices ?? null} />

      {/* Trade log */}
      <div className="border-charcoal-700 border-t">
        <div className="text-charcoal-500 text-micro px-3 pt-2 font-mono tracking-widest uppercase">
          Trades ({run.trades.length})
        </div>
        <TradeTable trades={run.trades} />
      </div>
    </div>
  );
}
