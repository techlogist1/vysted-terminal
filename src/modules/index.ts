import type { VystedModule } from "@/lib/module-registry";

import { chartModule } from "./chart";
import { equityOverviewModule } from "./equity-overview";
import { newsModule } from "./news";
import { platformModule } from "./platform";
import { portfolioModule } from "./portfolio";
import { watchlistModule } from "./watchlist";

/**
 * The complete first-party module registry. This file is intentionally complete
 * — Phase 1.B teammates fill in their own module file under `src/modules/<id>/`
 * and never edit this one, so parallel work never contends on it.
 */
export const vystedModules: VystedModule[] = [
  chartModule,
  watchlistModule,
  newsModule,
  portfolioModule,
  equityOverviewModule,
  platformModule,
];
