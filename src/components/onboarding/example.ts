/**
 * The tour's example per path (R16 contract, Wave 2): an agent path asks the
 * agent through the one send path (agent-command channel → ChatSidebar's
 * handleSend, provider/§6.5 gate included); the skip path charts Reliance on
 * NSE through the always-consumed chart-command channel (keyless data, daily
 * bars — the India lane serves end-of-day only).
 */

import { loadSymbolIntoChart } from "@/lib/host-actions";
import { useAgentCommandStore } from "@/store/agent-command";
import { useAgentDockStore } from "@/store/agent-dock";

export const EXAMPLE_QUESTION = "How has Reliance Industries done over the past year?";
export const EXAMPLE_SYMBOL = "RELIANCE.NS";

export function askAgent(question: string = EXAMPLE_QUESTION): void {
  useAgentDockStore.getState().setCollapsed(false);
  useAgentCommandStore.getState().send(question);
}

export function showChartExample(): void {
  loadSymbolIntoChart(EXAMPLE_SYMBOL, "1d", "IN");
}
