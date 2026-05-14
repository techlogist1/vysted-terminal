import { createPlaceholderPanel } from "@/components/PlaceholderPanel";
import type { VystedModule } from "@/lib/module-registry";

/**
 * Chart module — placeholder. Owned by Teammate A (Phase 1.B).
 *
 * Teammate A replaces `panelComponents["chart-panel"]` with the real
 * lightweight-charts chart panel (multi-pane sync, symbol + timeframe controls,
 * 20-indicator selector) and may extend `panels` / `commands`. Keep the module
 * id, the `chart-panel` component id, and the `chart` panel id stable —
 * `src/modules/index.ts` and the first-launch layout reference them.
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
    "chart-panel": createPlaceholderPanel("Chart"),
  },
};
