import type { VystedModule } from "@/lib/module-registry";

import { SecFilingsPanel } from "./SecFilingsPanel";

/**
 * SEC EDGAR filings module — BLUEPRINT Module 31 (Phase 6 / v0.6.0).
 *
 * Surfaces a single panel that exposes the sec-edgar-mcp subprocess's
 * Company / Filings / Insider Trading tool surface:
 *
 *   - Symbol/CIK search + form-type filter
 *   - Sortable filings list (10-K / 10-Q / 8-K / DEF 14A / Forms 3-5)
 *   - FilingViewer with section navigation rail + "View on EDGAR" link
 *   - Insider tab (Forms 3/4/5 transactions for the same issuer)
 *
 * Backend lives under `sidecar/services/sec_filings_provider.py` +
 * `sidecar/routers/sec_filings.py`. The sec-edgar-mcp subprocess is
 * spawned by `src-tauri/src/sec_edgar_mcp.rs` via the same Tauri Rust
 * `Command::new` pattern openbb-mcp uses (v0.4.0 precedent).
 */
export const secFilingsModule: VystedModule = {
  id: "sec-filings",
  title: "SEC Filings",
  panels: [
    {
      id: "sec-filings",
      title: "SEC Filings",
      icon: "file-text",
      component: "sec-filings-panel",
      singleton: true,
      defaultSize: { w: 10, h: 8 },
    },
  ],
  commands: [
    {
      id: "sec-filings.open",
      trigger: "sec filings",
      title: "Open SEC Filings",
      description: "Read 10-K / 10-Q / 8-K filings and insider transactions",
      icon: "file-text",
      opensPanel: "sec-filings",
    },
  ],
  panelComponents: {
    "sec-filings-panel": SecFilingsPanel,
  },
};

export { SecFilingsPanel } from "./SecFilingsPanel";
export { FilingsListTable } from "./FilingsListTable";
export { FilingViewer } from "./FilingViewer";
export { InsiderTradingTable } from "./InsiderTradingTable";
