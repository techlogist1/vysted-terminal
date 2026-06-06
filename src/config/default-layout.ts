import type { DockviewApi, IDockviewPanel } from "dockview";

/**
 * The first-launch cockpit (FR-032): a minimal, populated starter set — the
 * Chart dominates the left with Equity Overview as a tab beside it; Watchlist /
 * News / Portfolio stack down the right column. The AGENT is no longer a panel
 * here — it is the shell's primary column (`AgentDock`, FR-001), always present
 * beside this cockpit. Settings is intentionally not opened by default — it is
 * reached via the command palette.
 *
 * Each panel is placed only if its module is enabled, and a panel's reference
 * position is honoured only when that reference actually got placed — so a user
 * who disabled a module still gets a coherent layout rather than a crash.
 *
 * After placement we resize the chart group + the right column via
 * `panel.api.setSize`, which is the reliable pixel-precise resize path —
 * dockview's `addPanel({initialWidth,…})` redistributes proportionally as later
 * panels are added, so the final ratios don't match the per-panel initial
 * requests. We size the chart group to ~60% of the host width and the
 * right-column stack splits the remaining width. Users can drag freely after.
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

/** Chart-group share of the cockpit width (chart-dominant; agent is the shell column). */
const CHART_WIDTH_FRACTION = 0.6;
/** Right-column panel share of the total host height (one-third per panel). */
const RIGHT_COLUMN_PANEL_HEIGHT_FRACTION = 1 / 3;

/** Build the first-launch layout, skipping panels whose module is disabled. */
export function applyDefaultLayout(api: DockviewApi, enabledPanelIds: Set<string>): void {
  const placed = new Set<string>();
  const panels = new Map<string, IDockviewPanel>();

  for (const panel of DEFAULT_PANELS) {
    if (!enabledPanelIds.has(panel.id)) {
      continue;
    }
    // dockview only honours a position when its `referencePanel` is already
    // placed — drop the position entirely otherwise so the panel still lands.
    const position =
      panel.position && placed.has(panel.position.referencePanel) ? panel.position : undefined;
    const created = api.addPanel({
      id: panel.id,
      component: panel.component,
      title: panel.title,
      position,
    });
    panels.set(panel.id, created);
    placed.add(panel.id);
  }

  // Resize after all panels are placed so the final ratios are stable. Setting
  // the chart group's width pushes the right column to fill the remainder;
  // setting heights on watchlist + news lets portfolio claim the rest of the
  // right-column height. `api.width` / `api.height` are 0 in non-browser
  // (test) environments — guard so the call still no-ops cleanly there.
  const hostWidth = typeof api.width === "number" ? api.width : 0;
  const hostHeight = typeof api.height === "number" ? api.height : 0;
  if (hostWidth > 0) {
    panels.get("chart")?.api.setSize({ width: Math.round(hostWidth * CHART_WIDTH_FRACTION) });
  }
  if (hostHeight > 0) {
    const panelHeight = Math.round(hostHeight * RIGHT_COLUMN_PANEL_HEIGHT_FRACTION);
    panels.get("watchlist")?.api.setSize({ height: panelHeight });
    panels.get("news")?.api.setSize({ height: panelHeight });
  }
}
