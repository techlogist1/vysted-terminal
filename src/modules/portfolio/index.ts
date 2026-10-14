import type { VystedModule } from "@/lib/module-registry";

import { PortfolioPanel } from "./PortfolioPanel";

/**
 * Portfolio module — multiple NAMED portfolios of manually tracked holdings
 * (frontend store, persisted in the workspace blob; no broker sync), with P&L,
 * weight, and concentration computed client-side from live quotes.
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
