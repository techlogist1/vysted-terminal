import type { VystedModule } from "@/lib/module-registry";

import { AnalystRatingsPanel } from "./AnalystRatingsPanel";

/**
 * Analyst Ratings module — Phase 6 (Teammate E) surface.
 *
 * Surfaces the AnalystRatingsPanel: a symbol input + three tabs —
 * History (rating changes), Price Targets (target timeline), Individual
 * (per-firm forecasts with current rating + target + 1y accuracy + star
 * rating where available).
 */
export const analystRatingsModule: VystedModule = {
  id: "analyst-ratings",
  title: "Analyst Ratings",
  panels: [
    {
      id: "analyst-ratings",
      title: "Analyst Ratings",
      icon: "users",
      component: "analyst-ratings-panel",
      singleton: true,
      defaultSize: { w: 6, h: 7 },
    },
  ],
  commands: [
    {
      id: "analyst-ratings.open",
      trigger: "ratings",
      title: "Open Analyst Ratings",
      description: "Per-symbol ratings history, price targets, and individual analyst tracks",
      icon: "users",
      opensPanel: "analyst-ratings",
    },
  ],
  panelComponents: {
    "analyst-ratings-panel": AnalystRatingsPanel,
  },
};
