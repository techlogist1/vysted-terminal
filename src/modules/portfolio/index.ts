import type { VystedModule } from "@/lib/module-registry";

import { PortfolioPanel } from "./PortfolioPanel";

/**
 * Portfolio module — manual positions from the sidecar SQLite store, with P&L,
 * weight, and basic risk metrics computed client-side. Owned by Teammate B
 * (Phase 1.B).
 */
export const portfolioModule: VystedModule = {
  id: "portfolio",
  title: "Portfolio",
  panels: [
    {
      id: "portfolio",
      title: "Portfolio",
      icon: "briefcase",
      component: "portfolio-panel",
      singleton: true,
      defaultSize: { w: 4, h: 5 },
    },
  ],
  commands: [
    {
      id: "portfolio.open",
      trigger: "portfolio",
      title: "Open Portfolio",
      description: "Positions, P&L, and risk metrics",
      icon: "briefcase",
      opensPanel: "portfolio",
    },
  ],
  panelComponents: {
    "portfolio-panel": PortfolioPanel,
  },
};
