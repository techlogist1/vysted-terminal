/**
 * Chart command channel — the host's direct "load this symbol" path to the chart.
 *
 * Distinct from `chart-sync` (the OPT-IN cross-chart broadcast a chart only hears
 * when the user toggles symbol-sync): this channel is ALWAYS consumed by every
 * chart panel, so an agent host-action (`set_chart_symbol`) or a command-palette
 * symbol pick actually lands on the open chart instead of being silently dropped
 * (the "load Apple loaded SPY" bug — BUG-6). It also carries the chart's real
 * displayed symbol back so the diff gate can show an accurate before-state.
 *
 * The same pattern (host → chart command, chart → store report) carries two more
 * host actions: setting the active indicator selection and toggling a comparison
 * overlay, each with its own `seq` so an identical re-issue still re-triggers.
 */

import { create } from "zustand";

interface ChartCommandState {
  /** Most recent "load this symbol" command from the host (agent / palette).
   *  `seq` bumps on every issue so equal symbols still re-trigger consumers. */
  command: { symbol: string; timeframe?: string; seq: number } | null;
  /** The active chart's currently-displayed symbol — reported by ChartPanel so
   *  the host can render an accurate "before" in the proposed-change diff. */
  activeSymbol: string | null;
  /** Host → chart: set the indicator selection (optionally scoped to a symbol so
   *  a multi-chart workspace only retargets the matching chart). `seq` bumps on
   *  every issue so an identical indicator set still re-triggers consumers. */
  indicatorCommand: { symbol?: string; indicators: string[]; seq: number } | null;
  /** The active chart's currently-selected indicator keys — reported by
   *  ChartPanel so the host's diff gate can render an accurate "before". */
  activeIndicators: string[];
  /** Host → chart: toggle a comparison overlay onto the chart. `seq` bumps on
   *  every issue so an identical symbol still re-triggers consumers. */
  comparisonCommand: { symbol: string; seq: number } | null;
  /** The active chart's currently-displayed comparison overlay symbol (or null)
   *  — reported by ChartPanel for the host's diff gate. */
  activeComparison: string | null;
  /** Host → chart: load a symbol (and optional timeframe). */
  loadSymbol: (symbol: string, timeframe?: string) => void;
  /** Chart → store: report the active chart's displayed symbol. */
  reportActiveSymbol: (symbol: string) => void;
  /** Host → chart: set the indicator selection (optionally scoped to a symbol). */
  setIndicators: (indicators: string[], symbol?: string) => void;
  /** Chart → store: report the active chart's selected indicator keys. */
  reportActiveIndicators: (keys: string[]) => void;
  /** Host → chart: set the comparison-overlay symbol. */
  setComparison: (symbol: string) => void;
  /** Chart → store: report the active chart's comparison-overlay symbol (or null). */
  reportActiveComparison: (symbol: string | null) => void;
}

export const useChartCommandStore = create<ChartCommandState>((set) => ({
  command: null,
  activeSymbol: null,
  indicatorCommand: null,
  activeIndicators: [],
  comparisonCommand: null,
  activeComparison: null,
  loadSymbol: (symbol, timeframe) =>
    set((state) => ({ command: { symbol, timeframe, seq: (state.command?.seq ?? 0) + 1 } })),
  reportActiveSymbol: (symbol) => set({ activeSymbol: symbol }),
  setIndicators: (indicators, symbol) =>
    set((state) => ({
      indicatorCommand: {
        symbol,
        indicators,
        seq: (state.indicatorCommand?.seq ?? 0) + 1,
      },
    })),
  reportActiveIndicators: (keys) => set({ activeIndicators: keys }),
  setComparison: (symbol) =>
    set((state) => ({
      comparisonCommand: { symbol, seq: (state.comparisonCommand?.seq ?? 0) + 1 },
    })),
  reportActiveComparison: (symbol) => set({ activeComparison: symbol }),
}));

/** Test helper: reset the chart-command store. */
export function resetChartCommandStoreForTests(): void {
  useChartCommandStore.setState({
    command: null,
    activeSymbol: null,
    indicatorCommand: null,
    activeIndicators: [],
    comparisonCommand: null,
    activeComparison: null,
  });
}
