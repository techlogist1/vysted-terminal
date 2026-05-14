import { createPlaceholderPanel } from "@/components/PlaceholderPanel";
import type { VystedModule } from "@/lib/module-registry";

/**
 * Portfolio module — placeholder. Owned by Teammate B (Phase 1.B).
 *
 * Teammate B replaces `panelComponents["portfolio-panel"]` with the real
 * portfolio panel (positions from SQLite, P&L, weight, basic risk metrics).
 * Keep the module id, the `portfolio-panel` component id, and the `portfolio`
 * panel id stable.
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
    "portfolio-panel": createPlaceholderPanel("Portfolio"),
  },
};
