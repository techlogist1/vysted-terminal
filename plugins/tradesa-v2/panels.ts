/**
 * Tradesa V2 wrapper — companion panel-components map.
 *
 * The bootstrap glue (``src/lib/plugin-bootstrap.ts::moduleForPlugin``)
 * dynamic-imports this file when a plugin contributes panels, and merges
 * the exported ``panelComponents`` map into the synthesized
 * ``VystedModule`` so dockview can resolve a React component for each
 * ``PanelSpec.component`` id.
 *
 * **Convention** (the "Trading-System Wrapper" plugin pattern documented
 * in ``docs/PLUGIN_DEVELOPMENT.md``): plugins that contribute panels
 * ship two files alongside ``index.ts``:
 *
 *   - ``panels.ts``   — this file. Exports ``panelComponents`` mapping
 *                      ``PanelSpec.component`` ids to React function
 *                      components.
 *   - ``connection.ts`` — implementation of the bot-specific data adapter.
 *
 * As of v0.6.5 every panel ships a full implementation (Positions /
 * TradeHistory / BrainDecisions / Sentinel / Health / Settings /
 * MetaAgents) — all backed by the read-only Supabase wrapper, all
 * graceful-degradation aware via _PanelShell.tsx, all covered by
 * per-panel Vitest. The v0.6.5 plan's Phase-B placeholder-shells step
 * was collapsed into the same A8 commit as the entry, because
 * panels.ts must compile against real components for the dockview
 * registration to round-trip.
 */

import type { FunctionComponent } from "react";

import { BrainDecisionsPanel } from "./components/BrainDecisionsPanel";
import { HealthPanel } from "./components/HealthPanel";
import { MetaAgentsPanel } from "./components/MetaAgentsPanel";
import { PositionsPanel } from "./components/PositionsPanel";
import { SentinelPanel } from "./components/SentinelPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { TradeHistoryPanel } from "./components/TradeHistoryPanel";

/**
 * Map from ``PanelSpec.component`` id (declared in ``index.ts``) to the
 * React component the bootstrap glue registers with dockview.
 *
 * Order matches ``panels[]`` in ``index.ts`` for audit-trail symmetry.
 */
export const panelComponents: Record<string, FunctionComponent> = {
  "tradesa-v2-positions": PositionsPanel,
  "tradesa-v2-trade-history": TradeHistoryPanel,
  "tradesa-v2-brain": BrainDecisionsPanel,
  "tradesa-v2-sentinel": SentinelPanel,
  "tradesa-v2-health": HealthPanel,
  "tradesa-v2-settings": SettingsPanel,
  "tradesa-v2-meta-agents": MetaAgentsPanel,
};

export default panelComponents;
