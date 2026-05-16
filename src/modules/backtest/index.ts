import type { VystedModule } from "@/lib/module-registry";

import { BacktestPanel } from "./BacktestPanel";

/**
 * Backtest module — Phase 4 (Teammate K v0.5.0) surface.
 *
 * Surfaces the BacktestPanel: a strategy picker, params form, run
 * controls, and a result view with equity curve + drawdown + trade
 * log + walk-forward strip. Selecting a strategy renders a form from
 * its ``paramsSchema``; clicking Run streams ``POST /backtest/run`` and
 * paints the result on completion.
 *
 * The "Open in Strategy Critic" button on the result view bridges to
 * the chat sidebar (Phase 3) — the panel publishes a context snapshot
 * carrying the run id, and the critic resolves it via the
 * ``backtest_summary`` agent tool. End-to-end demo = BLUEPRINT Use
 * Case 2.
 */
export const backtestModule: VystedModule = {
  id: "backtest",
  title: "Backtest",
  panels: [
    {
      id: "backtest",
      title: "Backtest",
      icon: "test-tube",
      component: "backtest-panel",
      singleton: true,
      defaultSize: { w: 8, h: 8 },
    },
  ],
  commands: [
    {
      id: "backtest.open",
      trigger: "backtest",
      title: "Open Backtest",
      description: "Run a backtest and critique with the Strategy Critic",
      icon: "test-tube",
      opensPanel: "backtest",
    },
  ],
  panelComponents: {
    "backtest-panel": BacktestPanel,
  },
};
