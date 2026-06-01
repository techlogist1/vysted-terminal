import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

import {
  applyHostAction,
  describeHostAction,
  HOST_ACTION_NAMES,
  isHostActionMutation,
  routeOrderProposal,
} from "@/lib/host-actions";
import { useBrokersStore } from "@/store/brokers";
import { useChartCommandStore } from "@/store/chart-command";
import { useOrdersStore } from "@/store/orders";
import { useSymbolsStore } from "@/store/symbols";

describe("host-actions", () => {
  beforeEach(() => {
    useChartCommandStore.setState({ command: null, activeSymbol: null });
    useSymbolsStore.setState({ entries: [] });
    useOrdersStore.setState({ proposals: [], activeProposalId: null });
    useBrokersStore.setState({ byId: {} });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("classifies the catalog host actions as mutations to gate", () => {
    expect([...HOST_ACTION_NAMES].sort()).toEqual(
      [
        "add_to_watchlist",
        "arrange_layout",
        "close_panel",
        "focus_panel",
        "open_panel",
        "propose_order",
        "publish_brief",
        "set_chart_indicators",
        "set_chart_symbol",
      ].sort(),
    );
    expect(isHostActionMutation("set_chart_symbol")).toBe(true);
    expect(isHostActionMutation("close_panel")).toBe(true);
    expect(isHostActionMutation("arrange_layout")).toBe(true);
    expect(isHostActionMutation("propose_order")).toBe(true);
    expect(isHostActionMutation("price_data")).toBe(false);
    expect(isHostActionMutation("get_terminal_state")).toBe(false);
  });

  it("panel-control actions describe + apply (gated, no auto-apply)", () => {
    // describe produces a reviewable diff with the "panel" kind
    const close = describeHostAction("close_panel", { panel: "news" });
    expect(close.kind).toBe("panel");
    expect(close.title).toMatch(/Close/);
    expect(close.after).toMatch(/closed/i);

    const focus = describeHostAction("focus_panel", { panel: "chart" });
    expect(focus.after).toMatch(/Chart/);

    const reset = describeHostAction("arrange_layout", { pattern: "default" });
    expect(reset.after).toMatch(/default/i);
    const maximise = describeHostAction("arrange_layout", { pattern: "focus", panel: "chart" });
    expect(maximise.after).toMatch(/maximised|Chart/);

    // apply returns a label (the dockview ops no-op cleanly with no api in jsdom)
    expect(applyHostAction("close_panel", { panel: "news" })).toMatch(/Closed/);
    expect(applyHostAction("focus_panel", { panel: "chart" })).toMatch(/Focused/);
    expect(applyHostAction("arrange_layout", { pattern: "default" })).toMatch(/default/i);
    // focus pattern with no open target panel can't apply -> null (re-pends)
    expect(applyHostAction("arrange_layout", { pattern: "focus", panel: "chart" })).toBeNull();
  });

  it("applyHostAction(set_chart_symbol) commands the chart to load the symbol", () => {
    const label = applyHostAction("set_chart_symbol", { symbol: "NVDA" });
    expect(label).toMatch(/NVDA/);
    // The always-consumed command channel (NOT the opt-in sync bus) — BUG-6 fix.
    expect(useChartCommandStore.getState().command?.symbol).toBe("NVDA");
  });

  it("applyHostAction(add_to_watchlist) tracks the symbol", () => {
    applyHostAction("add_to_watchlist", { symbol: "tsla", asset_class: "equity" });
    expect(useSymbolsStore.getState().entries.map((e) => e.symbol)).toContain("TSLA");
  });

  it("set_chart_indicators describes + applies the indicator selection (B2)", () => {
    useChartCommandStore.setState({ activeIndicators: ["rsi"] });
    const diff = describeHostAction("set_chart_indicators", {
      indicators: ["ma", "volume", "rsi", "macd"],
    });
    expect(diff.kind).toBe("chart");
    expect(diff.before).toContain("rsi");
    expect(diff.after).toContain("macd");

    const label = applyHostAction("set_chart_indicators", { indicators: ["ma", "rsi"] });
    expect(label).toMatch(/ma, rsi/);
    expect(useChartCommandStore.getState().indicatorCommand?.indicators).toEqual(["ma", "rsi"]);
  });

  it("arrange_layout describes the named templates (B2)", () => {
    const research = describeHostAction("arrange_layout", {
      pattern: "research-cockpit",
      symbol: "NVDA",
    });
    expect(research.kind).toBe("panel");
    expect(research.title).toMatch(/research cockpit/i);
    expect(research.after).toContain("NVDA");

    const compare = describeHostAction("arrange_layout", {
      pattern: "compare",
      symbols: ["AAPL", "MSFT"],
    });
    expect(compare.after).toMatch(/AAPL vs MSFT/);
  });

  it("set_chart_symbol opens a chart when none is open (AUTO 'no panels' fix)", async () => {
    const { useWorkspaceStore } = await import("@/store/workspace");
    const openPanel = vi.fn();
    // No chart panel on screen → ensureChartOpen must open one before loading.
    useWorkspaceStore.setState({
      dockviewApi: { panels: [] } as never,
      openPanel,
    } as never);
    applyHostAction("set_chart_symbol", { symbol: "TATASTEEL" });
    expect(openPanel).toHaveBeenCalledWith("chart");
    expect(useChartCommandStore.getState().command?.symbol).toBe("TATASTEEL");

    // A chart already open (by component, robust to generated ids) → do NOT re-open.
    openPanel.mockClear();
    useWorkspaceStore.setState({
      dockviewApi: { panels: [{ api: { component: "chart-panel" } }] } as never,
      openPanel,
    } as never);
    applyHostAction("set_chart_symbol", { symbol: "RELIANCE" });
    expect(openPanel).not.toHaveBeenCalled();
  });

  it("applyHostAction does NOT place an order (orders never apply directly)", () => {
    const label = applyHostAction("propose_order", { symbol: "AAPL", side: "buy", quantity: 1 });
    expect(label).toBeNull();
    expect(useOrdersStore.getState().proposals).toHaveLength(0);
  });

  it("describeHostAction renders a reviewable old→new diff per kind", () => {
    useChartCommandStore.setState({ activeSymbol: "SPY" });
    const chart = describeHostAction("set_chart_symbol", { symbol: "NVDA", timeframe: "1d" });
    expect(chart.kind).toBe("chart");
    expect(chart.before).toContain("SPY");
    expect(chart.after).toContain("NVDA");

    const order = describeHostAction("propose_order", { symbol: "AAPL", side: "buy", quantity: 2 });
    expect(order.kind).toBe("order");
    expect(order.after).toMatch(/confirm-before-place/);
  });

  it("routeOrderProposal posts source=ai-agent and opens the §6.5 dialog (FR-011)", async () => {
    const proposal = {
      proposalId: "p-1",
      broker: "kite",
      symbol: "AAPL",
      side: "buy",
      type: "market",
      quantity: 1,
      source: "ai-agent",
    };
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => proposal,
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    const result = await routeOrderProposal(
      { symbol: "AAPL", side: "buy", quantity: 1, order_type: "market" },
      { agentId: "copilot", agentName: "Copilot" },
    );
    expect(result.ok).toBe(true);

    const [, init] = (fetchMock as unknown as { mock: { calls: [string, RequestInit][] } }).mock
      .calls[0];
    const body = JSON.parse(String(init.body));
    expect(body.source).toBe("ai-agent");
    expect(body.sourceDetails).toEqual({ agentId: "copilot", agentName: "Copilot" });
    // The proposal lands in the inbox and the dialog is opened — but placement
    // still requires the human confirm in the §6.5 dialog.
    expect(useOrdersStore.getState().proposals.map((p) => p.proposal.proposalId)).toContain("p-1");
    expect(useOrdersStore.getState().activeProposalId).toBe("p-1");
  });

  it("routeOrderProposal targets the connected broker, not a hardcoded kite", async () => {
    useBrokersStore.setState({
      byId: {
        alpaca: {
          broker: "alpaca",
          status: "connected",
          mode: "paper",
          readOnly: true,
        },
      },
    } as never);
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ proposalId: "p-2", broker: "alpaca" }),
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);
    await routeOrderProposal({ symbol: "MSFT", side: "buy", quantity: 1 }, {});
    const [url] = (fetchMock as unknown as { mock: { calls: [string][] } }).mock.calls[0];
    expect(url).toContain("/brokers/alpaca/orders");
  });

  it("routeOrderProposal surfaces a broker error without throwing", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      statusText: "blocked",
      json: async () => ({ detail: "kill switch fired" }),
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);
    const result = await routeOrderProposal({ symbol: "AAPL", side: "buy", quantity: 1 }, {});
    expect(result.ok).toBe(false);
    expect(result.error).toBe("kill switch fired");
    expect(useOrdersStore.getState().proposals).toHaveLength(0);
  });
});
