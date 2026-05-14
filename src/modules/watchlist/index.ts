import type { VystedModule } from "@/lib/module-registry";

import { WatchlistPanel } from "./WatchlistPanel";

/**
 * Watchlist module — pre-loaded symbols, add/remove, polled live quotes.
 * Owned by Teammate B (Phase 1.B).
 */
export const watchlistModule: VystedModule = {
  id: "watchlist",
  title: "Watchlist",
  panels: [
    {
      id: "watchlist",
      title: "Watchlist",
      icon: "list",
      component: "watchlist-panel",
      singleton: true,
      defaultSize: { w: 3, h: 6 },
    },
  ],
  commands: [
    {
      id: "watchlist.open",
      trigger: "watchlist",
      title: "Open Watchlist",
      description: "Tracked symbols with live quotes",
      icon: "list",
      opensPanel: "watchlist",
    },
  ],
  panelComponents: {
    "watchlist-panel": WatchlistPanel,
  },
};
