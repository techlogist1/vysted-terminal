import type { VystedModule } from "@/lib/module-registry";

import { MacroPanel } from "./MacroPanel";

/**
 * Macro module — owned by Teammate M (Phase 6 / v0.6.0).
 *
 * Ships the Macro panel, a four-provider time-series viewer for FRED, ECB,
 * IMF, and World Bank. The picker on top lets the user switch provider +
 * search + pick from a curated "Featured" tab; the chart below renders the
 * loaded series in lightweight-charts. Module id, the ``macro-panel``
 * component id, and the ``macro`` panel id are kept stable — ``src/modules/
 * index.ts`` references them.
 */
export const macroModule: VystedModule = {
  id: "macro",
  title: "Macro",
  panels: [
    {
      id: "macro",
      title: "Macro",
      icon: "trending-up",
      component: "macro-panel",
      singleton: false,
      defaultSize: { w: 8, h: 6 },
    },
  ],
  commands: [
    {
      id: "macro.open",
      trigger: "macro",
      title: "Open Macro",
      description: "FRED / ECB / IMF / World Bank time series",
      icon: "trending-up",
      opensPanel: "macro",
    },
  ],
  panelComponents: {
    "macro-panel": MacroPanel,
  },
};
