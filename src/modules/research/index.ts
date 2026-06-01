import type { VystedModule } from "@/lib/module-registry";

import { BriefPanel } from "./BriefPanel";

/**
 * Research module — the B+A research output surface (FR-074, PASS_B_RESEARCH
 * B.5).
 *
 * Contributes the Brief panel: the rendered output of JARVIS' research pipeline
 * — a markdown body with inline `[n]` citation chips, a cited-sources tray, a
 * FAST/DEEP mode + cost header, and an honest "structured-data-only" state when
 * no web-search backend is configured. The module id, the `brief-panel`
 * component id, and the `brief` panel id are kept stable.
 */
export const researchModule: VystedModule = {
  id: "research",
  title: "Research",
  panels: [
    {
      id: "brief",
      title: "Brief",
      icon: "flask-conical",
      component: "brief-panel",
      singleton: true,
      defaultSize: { w: 4, h: 7 },
    },
  ],
  commands: [
    {
      id: "research.open",
      trigger: "brief",
      title: "Open Research Brief",
      description: "JARVIS' cited research output",
      icon: "flask-conical",
      opensPanel: "brief",
    },
  ],
  panelComponents: {
    "brief-panel": BriefPanel,
  },
};
