import type { VystedModule } from "@/lib/module-registry";

import { EarningsCalendarPanel } from "./EarningsCalendarPanel";

/**
 * Earnings module — Phase 6 (Teammate E) surface.
 *
 * Surfaces the EarningsCalendarPanel: a date-window picker + watchlist
 * filter + sortable table of upcoming earnings events with consensus
 * EPS estimate and dispersion. Selecting a row reveals an inline
 * drill-down with the surprise chart (last N quarters' actual-vs-estimate
 * as a histogram) and the EPS estimate grid (mean / median / high / low
 * / stddev / analyst count) for the next upcoming report.
 */
export const earningsModule: VystedModule = {
  id: "earnings",
  title: "Earnings",
  panels: [
    {
      id: "earnings-calendar",
      title: "Earnings Calendar",
      icon: "calendar",
      component: "earnings-calendar-panel",
      singleton: true,
      defaultSize: { w: 8, h: 7 },
    },
  ],
  commands: [
    {
      id: "earnings.open-calendar",
      trigger: "earnings",
      title: "Open Earnings Calendar",
      description: "Upcoming earnings with consensus + dispersion",
      icon: "calendar",
      opensPanel: "earnings-calendar",
    },
  ],
  panelComponents: {
    "earnings-calendar-panel": EarningsCalendarPanel,
  },
};
