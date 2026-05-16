import type { VystedModule } from "@/lib/module-registry";

import { agentBuilderModule } from "./agent-builder";
import { chartModule } from "./chart";
import { chatModule } from "./chat";
import { equityOverviewModule } from "./equity-overview";
import { newsModule } from "./news";
import { nodeEditorModule } from "./node-editor";
import { platformModule } from "./platform";
import { pluginManagerModule } from "./plugin-manager";
import { portfolioModule } from "./portfolio";
import { watchlistModule } from "./watchlist";

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
];
