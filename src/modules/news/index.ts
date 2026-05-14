import { createPlaceholderPanel } from "@/components/PlaceholderPanel";
import type { VystedModule } from "@/lib/module-registry";

/**
 * News module — placeholder. Owned by Teammate C (Phase 1.B).
 *
 * Teammate C replaces `panelComponents["news-panel"]` with the real news feed
 * (filtered to watchlist symbols, per-item sentiment score). Keep the module
 * id, the `news-panel` component id, and the `news` panel id stable.
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
    "news-panel": createPlaceholderPanel("News"),
  },
};
