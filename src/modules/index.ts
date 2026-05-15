import type { VystedModule } from "@/lib/module-registry";

import { chartModule } from "./chart";
import { chatModule } from "./chat";
import { equityOverviewModule } from "./equity-overview";
import { newsModule } from "./news";
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
];
