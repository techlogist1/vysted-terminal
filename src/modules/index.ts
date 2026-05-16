import type { VystedModule } from "@/lib/module-registry";

import { agentBuilderModule } from "./agent-builder";
import { backtestModule } from "./backtest";
import { brokerConnectModule } from "./broker-connect";
import { chartModule } from "./chart";
import { chatModule } from "./chat";
import { equityOverviewModule } from "./equity-overview";
import { newsModule } from "./news";
import { nodeEditorModule } from "./node-editor";
import { platformModule } from "./platform";
import { pluginManagerModule } from "./plugin-manager";
import { portfolioModule } from "./portfolio";
import { safetyModule } from "./safety";
import { watchlistModule } from "./watchlist";
// Phase 6 — uncomment per teammate at integration time. Each teammate owns
// exactly one (or two) of the six entries below; the commented stubs land in
// foundation so the per-teammate merge sees an additive-only diff.
// import { macroModule } from "./macro";                       // Teammate M
import { secFilingsModule } from "./sec"; // Teammate F
// import { earningsModule } from "./earnings";                 // Teammate E
// import { analystRatingsModule } from "./analyst-ratings";    // Teammate E
// import { quantModule } from "./quant";                       // Teammate Q
// import { screenerModule } from "./screener";                 // Teammate Sc

/**
 * The complete first-party module registry. This file is intentionally complete
 * — Phase 1.B teammates fill in their own module file under `src/modules/<id>/`
 * and never edit this one, so parallel work never contends on it.
 *
 * Phase 2 adds `pluginManagerModule` (Teammate B) — it is a first-party
 * module by virtue of being how the user sees the plugin runtime, even though
 * what it surfaces is plugin-contributed.
 *
 * Phase 3 adds `agentBuilderModule` (Teammate C) — BLUEPRINT Module 36, the
 * Custom Agent Builder. It is separate from the 12 first-party AI agents and
 * lives here because it is a host-side authoring surface, not an agent itself.
 *
 * Phase 4 adds `nodeEditorModule` (Teammate N) — the visual workflow
 * composition surface (react-flow canvas + palette + run overlay) that
 * persists workflows to the sidecar via `/workflow/save` and runs them
 * via the `/workflow/run` SSE stream.
 *
 * Phase 4 / v0.5.0 adds `backtestModule` (Teammate K) — the strategy backtest
 * + Strategy Critic surface (BLUEPRINT Use Case 2).
 *
 * v0.5.0 adds `safetyModule` (Teammate S) — the audit-log viewer panel +
 * the always-mounted KillSwitchToolbar / OrderConfirmationDialog / DisclaimerFlow
 * surfaces (exported from `src/modules/safety/index.ts`).
 *
 * v0.5.0 adds `brokerConnectModule` (Teammate S, depends on Teammates I/G/X
 * for the underlying broker adapters) — the connection-manager panel +
 * manual order-entry surface.
 */
export const vystedModules: VystedModule[] = [
  chartModule,
  watchlistModule,
  newsModule,
  portfolioModule,
  equityOverviewModule,
  chatModule,
  platformModule,
  pluginManagerModule,
  agentBuilderModule,
  nodeEditorModule,
  backtestModule,
  brokerConnectModule,
  safetyModule,
  // Phase 6 (v0.6.0) — each teammate uncomments their entry at integration.
  // The line order matches the v0.6.0 plan's merge order (M → F → Q → E → Sc)
  // so audit drift is easy to spot.
  // macroModule,            // Teammate M
  secFilingsModule, // Teammate F
  // quantModule,            // Teammate Q
  // earningsModule,         // Teammate E
  // analystRatingsModule,   // Teammate E
  // screenerModule,         // Teammate Sc
];
