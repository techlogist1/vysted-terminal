import type { DockviewApi } from "dockview";

/**
 * The first-launch panel arrangement (BLUEPRINT §5.1): the Chart dominates the
 * left, with Equity Overview as a tab beside it; Watchlist / News / Portfolio
 * stack down the right. Settings is intentionally not opened by default — it is
 * reached via cmd+K. The AI chat sidebar named in §5.1 arrives in Phase 3.
 *
 * Each panel is placed only if its module is enabled, and a panel's reference
 * position is honoured only when that reference actually got placed — so a user
 * who disabled a module still gets a coherent layout rather than a crash.
 */

type Direction = "right" | "below" | "within";

interface PlacedPanel {
  id: string;
  component: string;
  title: string;
  position?: { referencePanel: string; direction: Direction };
}

const DEFAULT_PANELS: PlacedPanel[] = [
  { id: "chart", component: "chart-panel", title: "Chart" },
  {
    id: "equity-overview",
    component: "equity-overview-panel",
    title: "Equity Overview",
    position: { referencePanel: "chart", direction: "within" },
  },
  {
    id: "watchlist",
    component: "watchlist-panel",
    title: "Watchlist",
    position: { referencePanel: "chart", direction: "right" },
  },
  {
    id: "news",
    component: "news-panel",
    title: "News",
    position: { referencePanel: "watchlist", direction: "below" },
  },
  {
    id: "portfolio",
    component: "portfolio-panel",
    title: "Portfolio",
    position: { referencePanel: "news", direction: "below" },
  },
];

/** Build the first-launch layout, skipping panels whose module is disabled. */
export function applyDefaultLayout(api: DockviewApi, enabledPanelIds: Set<string>): void {
  const placed = new Set<string>();
  for (const panel of DEFAULT_PANELS) {
    if (!enabledPanelIds.has(panel.id)) {
      continue;
    }
    const position =
      panel.position && placed.has(panel.position.referencePanel) ? panel.position : undefined;
    api.addPanel({
      id: panel.id,
      component: panel.component,
      title: panel.title,
      position,
    });
    placed.add(panel.id);
  }
}
