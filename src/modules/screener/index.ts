import type { VystedModule } from "@/lib/module-registry";

import { ScreenerPanel } from "./ScreenerPanel";

/**
 * Screener module — Phase 6 (Teammate Sc backend; v0.6.1 lead-completed frontend).
 *
 * BLUEPRINT §7 Phase 6 names "screener / scanner panel" as a Phase 6
 * deliverable. Backend ships at v0.6.0 (see ``services/screener.py`` +
 * ``routers/screener.py`` + the ``screener_run`` agent tool +
 * ``analysis.screener_query`` workflow node). Frontend (this module)
 * lead-completed in v0.6.1 after Teammate Sc's agent terminated on a
 * socket-closed error mid-execution.
 */
export const screenerModule: VystedModule = {
  id: "screener",
  title: "Screener",
  panels: [
    {
      id: "screener-panel",
      title: "Screener",
      icon: "filter",
      component: "screener-panel",
      singleton: true,
      defaultSize: { w: 9, h: 8 },
    },
  ],
  commands: [
    {
      id: "screener.open",
      trigger: "screener",
      title: "Open Screener",
      description: "Filter a curated universe by AND-combined criteria",
      icon: "filter",
      opensPanel: "screener-panel",
    },
  ],
  panelComponents: {
    "screener-panel": ScreenerPanel,
  },
};
