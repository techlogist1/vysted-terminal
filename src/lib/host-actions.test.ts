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
import { composeBriefMarkdown } from "@/lib/brief-ingest";
import { useBriefStore } from "@/store/brief";
import { useBrokersStore } from "@/store/brokers";
import { useChartCommandStore } from "@/store/chart-command";
import { useOrdersStore } from "@/store/orders";
import { useScreenerStore } from "@/store/screener";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";

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
        "open_company_overview",
        "open_panel",
        "propose_order",
        "publish_brief",
        "set_chart_indicators",
        "set_chart_symbol",
        "write_screener_filters",
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

  it("write_screener_filters describes + writes a nested AND/OR tree into the panel", () => {
    useScreenerStore.getState().__resetForTests();
    const openPanel = vi.fn();
    useWorkspaceStore.setState({ openPanel } as never);

    const input = {
      criteria: [{ field: "pe_ratio", operator: "lt", value: 15 }],
      group: {
        combinator: "or",
        criteria: [
          { field: "roe", operator: "gt", value: 0.2 },
          {
            combinator: "and",
            criteria: [
              { field: "dividend_yield", operator: "gt", value: 0.03 },
              { field: "debt_to_equity", operator: "lt", value: 1 },
            ],
          },
        ],
      },
      universe: "sp500",
    };

    const diff = describeHostAction("write_screener_filters", input);
    expect(diff.kind).toBe("panel");
    expect(diff.after).toMatch(/nested AND\/OR/);
    expect(diff.after).toMatch(/sp500/);

    const label = applyHostAction("write_screener_filters", input);
    expect(label).toMatch(/screener criteria/i);
    // The nested tree round-trips into the store + advanced mode flips on.
    const s = useScreenerStore.getState();
    expect(s.advanced).toBe(true);
    expect(s.group?.combinator).toBe("or");
    expect(s.group?.criteria).toHaveLength(2);
    expect(s.universe).toBe("sp500");
    // The panel is staged for the user to review + Run.
    expect(openPanel).toHaveBeenCalledWith("screener-panel");
  });

  it("write_screener_filters with no well-formed criteria can't apply (re-pends)", () => {
    useScreenerStore.getState().__resetForTests();
    // Malformed: missing value / unknown operator -> dropped -> nothing to write.
    expect(
      applyHostAction("write_screener_filters", { criteria: [{ field: "pe_ratio" }] }),
    ).toBeNull();
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

  // --- WS3: honest web banner — briefFromInput reconciliation ----------------

  it("publish_brief never default-trues a true outage (web_available:false, no sources)", () => {
    useBriefStore.getState().clearBrief();
    // A genuine outage: explicit web_available false AND zero sources → the honest
    // structured-only state survives (webAvailable false). This is the legitimate
    // affordance WS3 must preserve, not delete.
    applyHostAction("publish_brief", {
      query: "Apple outlook",
      symbol: "AAPL",
      mode: "fast",
      markdown: "## Brief\nStructured only.",
      sources: [],
      web_available: false,
    });
    const brief = useBriefStore.getState().brief;
    expect(brief?.webAvailable).toBe(false);
    expect(brief?.sourceCount).toBe(0);
  });

  it("publish_brief never false-flags a sourced brief (symptom #2 fix)", () => {
    useBriefStore.getState().clearBrief();
    // The bug: a brief cites sources yet web_available is false → "N sources" AND
    // a "web unavailable" banner fire together. Reconciliation: any cited source
    // forces webAvailable true regardless of the (stale/omitted) flag.
    applyHostAction("publish_brief", {
      query: "Apple outlook",
      symbol: "AAPL",
      mode: "deep",
      markdown: "## Brief\nText [1].",
      sources: [{ url: "https://sec.gov/x", title: "10-K", domain: "sec.gov" }],
      web_available: false,
    });
    const brief = useBriefStore.getState().brief;
    expect(brief?.sourceCount).toBe(1);
    expect(brief?.webAvailable).toBe(true); // reconciled — never contradictory
  });

  it("publish_brief: omitted web_available does not default-true a sourceless run", () => {
    useBriefStore.getState().clearBrief();
    // The model omits the flag AND there are no sources → derive FALSE from the
    // (lack of) evidence rather than implying the web ran. (Old code default-trued.)
    applyHostAction("publish_brief", {
      query: "Apple outlook",
      symbol: "AAPL",
      mode: "fast",
      markdown: "## Brief\nStructured only.",
      sources: [],
    });
    const brief = useBriefStore.getState().brief;
    expect(brief?.sourceCount).toBe(0);
    expect(brief?.webAvailable).toBe(false);
  });

  it("publish_brief forwards web_reason for the honest transient banner copy", () => {
    useBriefStore.getState().clearBrief();
    applyHostAction("publish_brief", {
      query: "Apple outlook",
      symbol: "AAPL",
      mode: "fast",
      markdown: "## Brief\nStructured only.",
      sources: [],
      web_available: false,
      web_reason: "rate_limited",
      note: "Web search was rate-limited — retry in a moment",
    });
    const brief = useBriefStore.getState().brief;
    expect(brief?.webAvailable).toBe(false);
    expect(brief?.webReason).toBe("rate_limited");
    expect(brief?.note).toMatch(/rate-limited/i);
  });

  it("describeHostAction(publish_brief) only tags structured-only with zero sources", () => {
    // A sourced brief is never labelled "structured-data-only" even if the model
    // omitted/zeroed the web flag — no contradictory "N sources · structured-only".
    const sourced = describeHostAction("publish_brief", {
      symbol: "AAPL",
      mode: "deep",
      sources: [{ url: "https://sec.gov/x", title: "10-K" }],
      web_available: false,
    });
    expect(sourced.after).not.toMatch(/structured-data-only/);
    expect(sourced.after).toMatch(/1 cited source/);

    const structuredOnly = describeHostAction("publish_brief", {
      symbol: "AAPL",
      mode: "fast",
      sources: [],
      web_available: false,
    });
    expect(structuredOnly.after).toMatch(/structured-data-only/);
  });

  // --- WS4: depth carries forward across a re-publish (fixes #5) --------------

  it("a depth-less re-publish preserves the prior run's depth tier (fixes #5)", () => {
    useBriefStore.getState().clearBrief();
    // The runtime auto-publish stamps the real tier (heavy) for this run.
    applyHostAction("publish_brief", {
      query: "NVDA deep dive",
      symbol: "NVDA",
      depth: "heavy",
      markdown: "## Brief\nFull report [1].",
      sources: [{ url: "https://sec.gov/nvda", title: "10-K", domain: "sec.gov" }],
    });
    expect(useBriefStore.getState().brief?.depth).toBe("heavy");

    // The model then re-publishes the SAME run with prose only — no depth, no deep
    // mode. The tier must NOT clobber back to quick (the "Go all out reappears
    // after a heavy run" bug): the prior heavy tier carries forward.
    applyHostAction("publish_brief", {
      query: "NVDA deep dive",
      symbol: "NVDA",
      markdown: "## Brief\nFull report, refined [1].",
      sources: [{ url: "https://sec.gov/nvda", title: "10-K", domain: "sec.gov" }],
    });
    expect(useBriefStore.getState().brief?.depth).toBe("heavy");
  });

  it("heavy survives a mode='DEEP' re-publish (MAX tier, never shallowed)", () => {
    useBriefStore.getState().clearBrief();
    applyHostAction("publish_brief", {
      query: "AAPL outlook",
      symbol: "AAPL",
      depth: "heavy",
      markdown: "## Brief\nDeepest run.",
      sources: [],
      web_available: false,
    });
    expect(useBriefStore.getState().brief?.depth).toBe("heavy");

    // A re-publish carrying only a shallower `mode='DEEP'` (tier deep) must not
    // shallow the heavy tier — the MAX of {own, prior} for the same symbol wins.
    applyHostAction("publish_brief", {
      query: "AAPL outlook",
      symbol: "AAPL",
      mode: "DEEP",
      markdown: "## Brief\nDeep run.",
      sources: [],
      web_available: false,
    });
    expect(useBriefStore.getState().brief?.depth).toBe("heavy");
    // The mode badge still collapses heavy → DEEP.
    expect(useBriefStore.getState().brief?.mode).toBe("DEEP");
  });

  it("an explicit deeper re-publish on the SAME symbol escalates the tier", () => {
    useBriefStore.getState().clearBrief();
    applyHostAction("publish_brief", {
      query: "MSFT",
      symbol: "MSFT",
      depth: "quick",
      markdown: "## Brief\nFast pass.",
      sources: [],
      web_available: false,
    });
    expect(useBriefStore.getState().brief?.depth).toBe("quick");

    applyHostAction("publish_brief", {
      query: "MSFT",
      symbol: "MSFT",
      depth: "deep",
      markdown: "## Brief\nDeeper.",
      sources: [],
      web_available: false,
    });
    expect(useBriefStore.getState().brief?.depth).toBe("deep");
  });

  it("a DIFFERENT symbol does not inherit the prior brief's depth", () => {
    useBriefStore.getState().clearBrief();
    applyHostAction("publish_brief", {
      query: "NVDA",
      symbol: "NVDA",
      depth: "heavy",
      markdown: "## Brief\nHeavy NVDA.",
      sources: [],
      web_available: false,
    });
    // A fresh quick run on a DIFFERENT symbol must start at quick, not inherit
    // NVDA's heavy tier (the recency/same-symbol guard rules out contamination).
    applyHostAction("publish_brief", {
      query: "TSLA",
      symbol: "TSLA",
      markdown: "## Brief\nQuick TSLA.",
      sources: [],
      web_available: false,
    });
    expect(useBriefStore.getState().brief?.depth).toBe("quick");
  });

  // --- WS4: Copy-markdown uses the pure composer (incl. ## Sources) -----------

  it("Copy-markdown is composeBriefMarkdown output including the ## Sources appendix", () => {
    useBriefStore.getState().clearBrief();
    applyHostAction("publish_brief", {
      query: "Apple moat",
      symbol: "AAPL",
      mode: "deep",
      markdown: "Apple's moat is its ecosystem [1].",
      sources: [{ url: "https://sec.gov/aapl", title: "10-K", domain: "sec.gov" }],
    });
    const brief = useBriefStore.getState().brief!;
    // The "Copy markdown" button writes exactly composeBriefMarkdown(brief) to the
    // clipboard — a pure transform that always appends the Sources appendix.
    const md = composeBriefMarkdown(brief);
    expect(md).toContain("# Apple moat");
    expect(md).toContain("Apple's moat is its ecosystem [1].");
    expect(md).toContain("## Sources");
    expect(md).toContain("[1] 10-K — https://sec.gov/aapl");
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
