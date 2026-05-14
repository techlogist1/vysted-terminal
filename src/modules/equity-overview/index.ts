import type { VystedModule } from "@/lib/module-registry";

import { EquityOverviewPanel } from "./EquityOverviewPanel";

/**
 * Equity Overview module — price, valuation ratios, financial-statement
 * excerpts, and analyst ratings for a selected symbol in one view. Owned by
 * Teammate B (Phase 1.B).
 */
export const equityOverviewModule: VystedModule = {
  id: "equity-overview",
  title: "Equity Overview",
  panels: [
    {
      id: "equity-overview",
      title: "Equity Overview",
      icon: "building-2",
      component: "equity-overview-panel",
      singleton: true,
      defaultSize: { w: 5, h: 6 },
    },
  ],
  commands: [
    {
      id: "equity-overview.open",
      trigger: "equity",
      title: "Open Equity Overview",
      description: "Fundamentals, statements, and analyst ratings",
      icon: "building-2",
      opensPanel: "equity-overview",
    },
  ],
  panelComponents: {
    "equity-overview-panel": EquityOverviewPanel,
  },
};
