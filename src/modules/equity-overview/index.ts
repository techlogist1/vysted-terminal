import { createPlaceholderPanel } from "@/components/PlaceholderPanel";
import type { VystedModule } from "@/lib/module-registry";

/**
 * Equity Overview module — placeholder. Owned by Teammate B (Phase 1.B).
 *
 * Teammate B replaces `panelComponents["equity-overview-panel"]` with the real
 * panel (price + ratios + statement excerpts + analyst ratings for the selected
 * symbol). Keep the module id, the `equity-overview-panel` component id, and the
 * `equity-overview` panel id stable.
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
    "equity-overview-panel": createPlaceholderPanel("Equity Overview"),
  },
};
