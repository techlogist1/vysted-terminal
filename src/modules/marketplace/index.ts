import type { VystedModule } from "@/lib/module-registry";

import { MarketplacePanel } from "./MarketplacePanel";

/**
 * Marketplace module (FR-050, US10) — the app's primary extensibility front
 * door: install/enable/configure/remove brokers, data providers, panels, and
 * agents under one lifecycle. Distinct from the plugin-manager (which shows
 * runtime health of loaded plugins); the marketplace is where capability is
 * gained. The configure form doubles as the BYOK credentials hub (FR-034).
 */
export const marketplaceModule: VystedModule = {
  id: "marketplace",
  title: "Marketplace",
  panels: [
    {
      id: "marketplace",
      title: "Marketplace",
      icon: "store",
      component: "marketplace-panel",
      singleton: true,
      defaultSize: { w: 8, h: 10 },
    },
  ],
  commands: [
    {
      id: "marketplace.open",
      trigger: "marketplace",
      title: "Open Marketplace",
      description:
        "Install, enable, configure, and remove extensions (brokers, data, panels, agents)",
      icon: "store",
      opensPanel: "marketplace",
    },
  ],
  panelComponents: {
    "marketplace-panel": MarketplacePanel,
  },
};
