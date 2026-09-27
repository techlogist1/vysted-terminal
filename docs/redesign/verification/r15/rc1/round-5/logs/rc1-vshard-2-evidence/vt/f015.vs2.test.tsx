import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { writeFileSync } from "node:fs";
import { usePanelContextBus } from "@/store/panel-context";
import { captureTerminalState, captureAgentContext, focusedSymbolFromBus } from "@/modules/chat/context-provider";
import { SuggestionChips } from "@/modules/chat/SuggestionChips";

const out: Record<string, unknown> = {};
function pub(source: string, payload: Record<string, unknown>) {
  usePanelContextBus.getState().publish({ source, kind: "snapshot", payload, emittedAt: Date.now() } as never);
}
function chips(): string[] {
  cleanup();
  render(<SuggestionChips />);
  return screen.queryAllByRole("button").map((b) => b.textContent ?? "");
}
function scenario(name: string, focus: string) {
  usePanelContextBus.getState().setFocusedSource(focus);
  const bus = usePanelContextBus.getState();
  const st = captureTerminalState();
  const ctx = captureAgentContext();
  out[name] = {
    focus,
    helper: focusedSymbolFromBus(bus.lastEventBySource, focus),
    snapshotFocusedSymbol: st.focusedSymbol,
    snapshotFocusedPanel: (ctx.bySource.__terminal__ as { focusedPanel: string | null }).focusedPanel,
    charts: st.charts,
    otherPanels: st.otherPanels,
    chips: chips(),
  };
}
beforeEach(() => {
  usePanelContextBus.setState({ lastEventBySource: {}, focusedSource: null, updatedAt: 0 } as never);
});
describe("f015", () => {
  it("repro: equity-overview INFY focused, chart SPY", () => {
    pub("chart", { symbol: "SPY", timeframe: "1D", activeIndicators: [] });
    pub("equity-overview", { ticker: "INFY", loadedSections: ["quote"] });
    scenario("repro_equity_infy", "equity-overview");
    const r = out.repro_equity_infy as { helper: string; snapshotFocusedSymbol: string; chips: string[] };
    expect(r.helper).toBe("INFY");
    expect(r.snapshotFocusedSymbol).toBe("INFY");
    expect(r.chips.some((c) => c.includes("$INFY"))).toBe(true);
  });
  it("fresh: second chart focused, analyst-ratings focused, sec-filings focused", () => {
    pub("chart", { symbol: "SPY", timeframe: "1D", activeIndicators: [] });
    pub("chart-2", { symbol: "NVDA", timeframe: "1H", activeIndicators: ["vwap"] });
    pub("analyst-ratings", { symbol: "msft", tab: "history" });
    pub("sec-filings", { identifier: "AAPL", formFilter: "10-K", tab: "list", filingCount: 12 });
    scenario("fresh_chart2", "chart-2");
    scenario("fresh_analyst_lowercase", "analyst-ratings");
    scenario("fresh_sec_identifier", "sec-filings");
    writeFileSync(__dirname + "/f015.json", JSON.stringify(out, null, 2));
  });
});
