"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { selectActiveRun, useBacktestStore } from "@/store/backtest";
import { useChatHistoryStore } from "@/store/chat-history";
import type { BacktestRequest } from "../../../types/backtest";

import { BacktestResultView } from "./BacktestResultView";
import { ParamsForm, StrategyPicker } from "./strategy-picker";

const DEFAULT_SYMBOL = "SPY";
const DEFAULT_START = "2024-01-01";
const DEFAULT_END = "2025-12-31";
const DEFAULT_CAPITAL = 100_000;

/**
 * Backtest panel — strategy picker + params form + run controls + a
 * result view that surfaces equity curve, drawdown, trade log, and
 * walk-forward slice strip.
 *
 * State machine summary:
 *
 *   idle → click Run → store.startRun → run-start (sidecar assigns runId)
 *   → progress... → run-complete → result rendered
 *
 * The "Open in Strategy Critic" button bridges Phase 4 (backtest) to
 * Phase 3 (chat sidebar): it preloads a `/critique` chat prompt
 * referencing the active run id; the chat sidebar's panel-context
 * snapshot already carries the run id thanks to the publish hook in
 * BacktestResultView. The Strategy Critic agent's tools list includes
 * ``backtest_summary``, which resolves the run id back to a digest.
 */
export function BacktestPanel() {
  const strategies = useBacktestStore((s) => s.strategies);
  const catalogueStatus = useBacktestStore((s) => s.catalogueStatus);
  const catalogueError = useBacktestStore((s) => s.catalogueError);
  const refreshStrategies = useBacktestStore((s) => s.refreshStrategies);
  const startRun = useBacktestStore((s) => s.startRun);
  const activeRun = useBacktestStore(selectActiveRun);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [symbols, setSymbols] = useState(DEFAULT_SYMBOL);
  const [startDate, setStartDate] = useState(DEFAULT_START);
  const [endDate, setEndDate] = useState(DEFAULT_END);
  const [capital, setCapital] = useState(DEFAULT_CAPITAL);
  const [walkForwardSlices, setWalkForwardSlices] = useState(1);

  // Pre-fill the chat composer when the user opens a Strategy Critic
  // from a result. Reads `appendUserMessage` once to keep deps stable.
  const appendUserMessage = useChatHistoryStore((s) => s.appendUserMessage);

  // Load the strategy catalogue on mount.
  useEffect(() => {
    if (catalogueStatus === "idle") {
      void refreshStrategies();
    }
  }, [catalogueStatus, refreshStrategies]);

  // Auto-select the first strategy as soon as the catalogue arrives.
  // The setState is gated on a strictly-monotonic transition (null →
  // first id), so cascading renders are bounded to one extra paint.
  useEffect(() => {
    if (!selectedId && strategies.length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedId(strategies[0].id);
    }
  }, [selectedId, strategies]);

  const selectedSpec = useMemo(
    () => strategies.find((s) => s.id === selectedId) ?? null,
    [strategies, selectedId],
  );

  // Reset params when the strategy changes — populate from schema
  // defaults. The setState fires once per strategy id transition; the
  // resulting cascading render is bounded to one extra paint, which is
  // the minimum work needed to re-render the params form with the new
  // strategy's schema.
  useEffect(() => {
    if (!selectedSpec) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setParams({});
      return;
    }
    const schema = selectedSpec.paramsSchema as
      | { properties?: Record<string, { default?: unknown }> }
      | undefined;
    const defaults: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(schema?.properties ?? {})) {
      if (value && typeof value === "object" && "default" in (value as object)) {
        defaults[key] = (value as { default?: unknown }).default;
      }
    }
    setParams(defaults);
  }, [selectedSpec]);

  const isRunning = activeRun?.status === "pending" || activeRun?.status === "streaming";
  const canRun = !!selectedSpec && !isRunning;

  const handleRun = useCallback(async () => {
    if (!selectedSpec) {
      return;
    }
    const request: BacktestRequest = {
      strategyId: selectedSpec.id,
      params,
      symbols: symbols
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean),
      startDate,
      endDate,
      initialCapital: capital,
      walkForwardSlices,
    };
    await startRun(request);
  }, [selectedSpec, params, symbols, startDate, endDate, capital, walkForwardSlices, startRun]);

  const handleOpenInCritic = useCallback(
    (runId: string) => {
      // Drop a slash-command into the chat composer that the sidebar
      // parses into a Strategy Critic invocation. The agent receives
      // the focused panel's snapshot (published by BacktestResultView)
      // and resolves the run id via its backtest_summary tool.
      appendUserMessage(
        `/agent strategy_critic Please critique my latest backtest (run id ${runId}). ` +
          "Use the backtest_summary tool to load the run and apply your 9-section framework.",
      );
    },
    [appendUserMessage],
  );

  return (
    <div className="bg-charcoal-900 flex h-full min-h-0 w-full">
      {/* Left rail — controls */}
      <aside className="border-charcoal-700 flex w-72 flex-col gap-3 overflow-y-auto border-r p-3">
        <StrategyPicker
          strategies={strategies}
          selectedId={selectedId}
          onSelect={setSelectedId}
          disabled={isRunning}
        />
        {catalogueStatus === "loading" && (
          <p className="text-charcoal-400 font-mono text-xs">Loading strategies…</p>
        )}
        {catalogueStatus === "error" && (
          <p className="text-negative font-mono text-xs">
            {catalogueError ?? "Failed to load strategies"}
          </p>
        )}

        {selectedSpec && (
          <ParamsForm
            schema={selectedSpec.paramsSchema as Record<string, unknown>}
            values={params}
            onChange={setParams}
            disabled={isRunning}
          />
        )}

        <div className="flex flex-col gap-1.5">
          <span className="text-charcoal-500 font-mono text-[10px] tracking-widest uppercase">
            Universe
          </span>
          <label className="flex flex-col gap-1">
            <span className="text-charcoal-300 font-mono text-[10px]">Symbols (comma-sep)</span>
            <input
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
              disabled={isRunning}
              spellCheck={false}
              aria-label="Symbols"
              className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs uppercase outline-none focus-visible:border-amber-500 disabled:opacity-50"
            />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="flex flex-col gap-1">
              <span className="text-charcoal-300 font-mono text-[10px]">Start</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                disabled={isRunning}
                aria-label="Start date"
                className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs outline-none focus-visible:border-amber-500 disabled:opacity-50"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-charcoal-300 font-mono text-[10px]">End</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                disabled={isRunning}
                aria-label="End date"
                className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs outline-none focus-visible:border-amber-500 disabled:opacity-50"
              />
            </label>
          </div>
          <label className="flex flex-col gap-1">
            <span className="text-charcoal-300 font-mono text-[10px]">Initial capital</span>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              disabled={isRunning}
              aria-label="Initial capital"
              className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs outline-none focus-visible:border-amber-500 disabled:opacity-50"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-charcoal-300 font-mono text-[10px]">Walk-forward slices</span>
            <input
              type="number"
              min={1}
              max={10}
              value={walkForwardSlices}
              onChange={(e) =>
                setWalkForwardSlices(Math.max(1, Math.min(10, Number(e.target.value) || 1)))
              }
              disabled={isRunning}
              aria-label="Walk-forward slices"
              className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs outline-none focus-visible:border-amber-500 disabled:opacity-50"
            />
          </label>
        </div>

        <Button
          type="button"
          onClick={handleRun}
          disabled={!canRun}
          size="sm"
          variant="default"
          aria-label="Run backtest"
          className={cn("mt-auto", !canRun && "cursor-not-allowed")}
          data-testid="run-backtest"
        >
          <Play />
          {isRunning ? "Running…" : "Run backtest"}
        </Button>
      </aside>

      {/* Main column — result view */}
      <section className="flex min-h-0 flex-1 flex-col">
        <BacktestResultView run={activeRun} onOpenInCritic={handleOpenInCritic} />
      </section>
    </div>
  );
}
