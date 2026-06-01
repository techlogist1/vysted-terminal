/**
 * Chart command channel — the host's direct "load this symbol" path to the chart.
 *
 * Distinct from `chart-sync` (the OPT-IN cross-chart broadcast a chart only hears
 * when the user toggles symbol-sync): this channel is ALWAYS consumed by every
 * chart panel, so an agent host-action (`set_chart_symbol`) or a command-palette
 * symbol pick actually lands on the open chart instead of being silently dropped
 * (the "load Apple loaded SPY" bug — BUG-6). It also carries the chart's real
 * displayed symbol back so the diff gate can show an accurate before-state.
 */

import { create } from "zustand";

interface ChartCommandState {
  /** Most recent "load this symbol" command from the host (agent / palette).
   *  `seq` bumps on every issue so equal symbols still re-trigger consumers. */
  command: { symbol: string; timeframe?: string; seq: number } | null;
  /** The active chart's currently-displayed symbol — reported by ChartPanel so
   *  the host can render an accurate "before" in the proposed-change diff. */
  activeSymbol: string | null;
  /** Host → chart: load a symbol (and optional timeframe). */
  loadSymbol: (symbol: string, timeframe?: string) => void;
  /** Chart → store: report the active chart's displayed symbol. */
  reportActiveSymbol: (symbol: string) => void;
}

export const useChartCommandStore = create<ChartCommandState>((set) => ({
  command: null,
  activeSymbol: null,
  loadSymbol: (symbol, timeframe) =>
    set((state) => ({ command: { symbol, timeframe, seq: (state.command?.seq ?? 0) + 1 } })),
  reportActiveSymbol: (symbol) => set({ activeSymbol: symbol }),
}));

/** Test helper: reset the chart-command store. */
export function resetChartCommandStoreForTests(): void {
  useChartCommandStore.setState({ command: null, activeSymbol: null });
}
