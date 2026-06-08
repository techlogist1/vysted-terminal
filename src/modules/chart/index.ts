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
      // Singleton (fixes #7): openPanel('chart') REUSES the literal-id 'chart'
      // panel instead of minting a fresh `chart-<ts>-<rand>` each time, so the
      // command-palette "Open Chart" and `ensureChartOpen` retarget the existing
      // tab rather than spawning a duplicate. (The Phase-2 multi-chart flag was
      // never finished — abandoned here; default-layout / layout-templates /
      // ensureChartOpen all already address the literal 'chart' id.)
      singleton: true,
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
