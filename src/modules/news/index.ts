import type { VystedModule } from "@/lib/module-registry";

import { NewsFeedPanel } from "./NewsFeedPanel";

/**
 * News module — owned by Teammate C (Phase 1.B).
 *
 * Contributes the News Feed panel: a scrollable feed of headlines with a
 * per-item lexicon sentiment indicator, tagged with the watchlist symbols each
 * item mentions. The module id, the `news-panel` component id, and the `news`
 * panel id are kept stable.
 */
export const newsModule: VystedModule = {
  id: "news",
  title: "News",
  panels: [
    {
      id: "news",
      title: "News",
      icon: "newspaper",
      component: "news-panel",
      singleton: true,
      defaultSize: { w: 4, h: 6 },
    },
  ],
  commands: [
    {
      id: "news.open",
      trigger: "news",
      title: "Open News Feed",
      description: "Headlines with sentiment scoring",
      icon: "newspaper",
      opensPanel: "news",
    },
  ],
  panelComponents: {
    "news-panel": NewsFeedPanel,
  },
};
