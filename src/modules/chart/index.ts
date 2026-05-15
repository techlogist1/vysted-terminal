import type { VystedModule } from "@/lib/module-registry";

import ChartPanel from "./ChartPanel";

/**
 * Chart module — owned by Teammate A (Phase 1.B).
 *
 * Ships the lightweight-charts chart panel: a candlestick chart with a symbol
 * input, an eight-step timeframe selector, and a 20-indicator multi-select
 * whose indicators are computed server-side and rendered as price-pane overlays
 * or synced oscillator panes. The module id, the `chart-panel` component id,
 * and the `chart` panel id are kept stable — `src/modules/index.ts` and the
 * first-launch layout reference them.
 */
export const chartModule: VystedModule = {
  id: "chart",
  title: "Chart",
  panels: [
    {
      id: "chart",
      title: "Chart",
      icon: "line-chart",
      component: "chart-panel",
      // Phase 2 makes the chart non-singleton so the user can open multiple
      // chart panels and opt them into crosshair / zoom / symbol sync.
      singleton: false,
      defaultSize: { w: 8, h: 6 },
    },
  ],
  commands: [
    {
      id: "chart.open",
      trigger: "chart",
      title: "Open Chart",
      description: "Price chart with indicators",
      icon: "line-chart",
      opensPanel: "chart",
    },
  ],
  panelComponents: {
    "chart-panel": ChartPanel,
  },
};
