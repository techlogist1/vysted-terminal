import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

import {
  applyHostAction,
  applyHostActionAsync,
  describeHostAction,
  HOST_ACTION_NAMES,
  isHostActionMutation,
  publishAckStatus,
  routeOrderProposal,
} from "@/lib/host-actions";
import { composeBriefMarkdown } from "@/lib/brief-ingest";
import { resetBriefStoreForTests, useBriefStore } from "@/store/brief";
import { useBrokersStore } from "@/store/brokers";
import { useChartCommandStore } from "@/store/chart-command";
import { resetEquityCommandStoreForTests, useEquityCommandStore } from "@/store/equity-command";
import { useNotesStore } from "@/store/notes";
import { useOrdersStore } from "@/store/orders";
import { usePortfoliosStore } from "@/store/portfolios";
import { useScreenerStore } from "@/store/screener";
import { resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";

describe("host-actions", () => {
  beforeEach(() => {
    useChartCommandStore.setState({ command: null, activeSymbol: null });
    resetEquityCommandStoreForTests();
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
        "portfolio_add_position",
        "portfolio_delete_position",
        "portfolio_update_position",
        "propose_order",
        "publish_brief",
        "remove_from_watchlist",
        "save_layout",
        "save_screen",
        "set_chart_indicators",
        "set_chart_symbol",
        "set_region",
        "write_note",
        "write_screener_filters",
      ].sort(),
    );
    expect(isHostActionMutation("set_chart_symbol")).toBe(true);
    expect(isHostActionMutation("close_panel")).toBe(true);
    expect(isHostActionMutation("arrange_layout")).toBe(true);
    expect(isHostActionMutation("propose_order")).toBe(true);
    expect(isHostActionMutation("portfolio_add_position")).toBe(true);
    expect(isHostActionMutation("write_note")).toBe(true);
    expect(isHostActionMutation("set_region")).toBe(true);
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

    // apply narrates TRUTHFULLY with no layout on screen (jsdom: no dockview
    // api): closing a not-open panel reports the already-true end state, and
    // focusing a not-yet-open singleton reports the open-and-focus it issued.
    useWorkspaceStore.setState({ dockviewApi: null, openPanel: vi.fn() } as never);
    expect(applyHostAction("close_panel", { panel: "news" })).toBe("News was already closed");
    expect(applyHostAction("focus_panel", { panel: "chart" })).toBe("Opened and focused Chart");
    expect(applyHostAction("arrange_layout", { pattern: "default" })).toMatch(/default/i);
    // focus pattern with no open target panel can't apply -> null (re-pends)
    expect(applyHostAction("arrange_layout", { pattern: "focus", panel: "chart" })).toBeNull();
  });

  // --- grounded narration (R8 seams deliverable 5): no fake success labels ----

  it("open/close/focus on an UNKNOWN panel id return null — never a fake success", () => {
    useWorkspaceStore.setState({ dockviewApi: null, openPanel: vi.fn() } as never);
    expect(applyHostAction("open_panel", { panel: "flux-capacitor" })).toBeNull();
    expect(applyHostAction("close_panel", { panel: "flux-capacitor" })).toBeNull();
    expect(applyHostAction("focus_panel", { panel: "flux-capacitor" })).toBeNull();
  });

  it("open_panel('screener') opens the REGISTERED id (kills the screener id drift)", () => {
    const openPanel = vi.fn();
    useWorkspaceStore.setState({
      // The fake layout already shows the screener component, so the
      // post-open verification sees the panel on screen.
      dockviewApi: {
        panels: [{ api: { component: "screener-panel" } }],
        getPanel: () => undefined,
      } as never,
      openPanel,
    } as never);
    expect(applyHostAction("open_panel", { panel: "screener" })).toBe("Opened Screener");
    // The registered PanelSpec id — NOT the bare "screener" that no-ops.
    expect(openPanel).toHaveBeenCalledWith("screener-panel");
  });

  it("open_panel returns null when the panel did not actually open (disabled module)", () => {
    const openPanel = vi.fn(); // a no-op open — the module is disabled
    useWorkspaceStore.setState({
      dockviewApi: { panels: [], getPanel: () => undefined } as never,
      openPanel,
    } as never);
    expect(applyHostAction("open_panel", { panel: "news" })).toBeNull();
    expect(openPanel).toHaveBeenCalledWith("news");
  });

  it("close_panel closes an OPEN panel and says so; focus_panel focuses it", () => {
    const closeSpy = vi.fn();
    const setActiveSpy = vi.fn();
    const newsPanel = {
      api: { component: "news-panel", close: closeSpy, setActive: setActiveSpy },
    };
    useWorkspaceStore.setState({
      dockviewApi: {
        panels: [newsPanel],
        getPanel: (id: string) => (id === "news" ? newsPanel : undefined),
      } as never,
      openPanel: vi.fn(),
    } as never);
    expect(applyHostAction("focus_panel", { panel: "news" })).toBe("Focused News");
    expect(setActiveSpy).toHaveBeenCalledTimes(1);
    expect(applyHostAction("close_panel", { panel: "news" })).toBe("Closed News");
    expect(closeSpy).toHaveBeenCalledTimes(1);
  });

  it("focus_panel returns null when the panel can neither be found nor opened", () => {
    useWorkspaceStore.setState({
      dockviewApi: { panels: [], getPanel: () => undefined } as never,
      openPanel: vi.fn(), // no-op open: the module is disabled
    } as never);
    expect(applyHostAction("focus_panel", { panel: "news" })).toBeNull();
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

  // --- open_panel carries its arguments (R8 seams deliverable 3) -------------

  it("describeHostAction(open_panel) renders the symbol for a symbol-aware panel", () => {
    const diff = describeHostAction("open_panel", {
      panel: "equity-overview",
      symbol: "SAKSOFT.NS",
    });
    expect(diff.title).toBe("Open Equity Overview — SAKSOFT.NS");
    expect(diff.after).toContain("SAKSOFT.NS loaded");

    // A stray symbol on a non-symbol-aware panel is NOT promised in the diff —
    // the description must match exactly what the apply will do.
    const plain = describeHostAction("open_panel", { panel: "news", symbol: "NVDA" });
    expect(plain.title).toBe("Open News");
    expect(plain.after).not.toContain("NVDA");
  });

  it("open_panel(equity-overview, symbol) opens the panel AND routes the symbol via the equity-command channel", () => {
    const openPanel = vi.fn();
    useWorkspaceStore.setState({ dockviewApi: null, openPanel } as never);
    const label = applyHostAction("open_panel", {
      panel: "equity-overview",
      symbol: "SAKSOFT.NS",
    });
    expect(label).toBe("Opened Equity Overview — SAKSOFT.NS");
    // The panel is opened first so the command has a consumer…
    expect(openPanel).toHaveBeenCalledWith("equity-overview");
    // …and the symbol rides the always-consumed equity-command channel. The
    // store RETAINS the command, so a panel that mounts after this still sees it.
    expect(useEquityCommandStore.getState().command).toMatchObject({ symbol: "SAKSOFT.NS" });
  });

  it("open_panel resolves aliases — 'overview' routes the symbol like 'equity-overview'", () => {
    const openPanel = vi.fn();
    useWorkspaceStore.setState({ dockviewApi: null, openPanel } as never);
    applyHostAction("open_panel", { panel: "overview", symbol: "RELIANCE.NS" });
    expect(openPanel).toHaveBeenCalledWith("equity-overview");
    expect(useEquityCommandStore.getState().command).toMatchObject({ symbol: "RELIANCE.NS" });
  });

  it("open_panel(chart, symbol) routes through the chart-command channel", () => {
    const openPanel = vi.fn();
    useWorkspaceStore.setState({ dockviewApi: { panels: [] } as never, openPanel } as never);
    const label = applyHostAction("open_panel", { panel: "chart", symbol: "NVDA" });
    expect(label).toBe("Opened Chart — NVDA");
    expect(openPanel).toHaveBeenCalledWith("chart");
    expect(useChartCommandStore.getState().command?.symbol).toBe("NVDA");
  });

  it("open_panel ignores a stray symbol on a non-symbol-aware panel", () => {
    const openPanel = vi.fn();
    useWorkspaceStore.setState({ dockviewApi: null, openPanel } as never);
    const label = applyHostAction("open_panel", { panel: "news", symbol: "NVDA" });
    expect(label).toBe("Opened News");
    expect(openPanel).toHaveBeenCalledWith("news");
    // Neither command channel fires for a panel that consumes no symbol.
    expect(useEquityCommandStore.getState().command).toBeNull();
    expect(useChartCommandStore.getState().command).toBeNull();
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

describe("briefFromInput backend carry (R9 gate 2, R10 run-scoped)", () => {
  it("keeps the engine's backend id when the model's SAME-RUN re-publish omits it", () => {
    // The engine's auto-publish carried the execution record; the runtime
    // injects the SAME record onto the model's own re-publish (R10 D38/D39).
    useBriefStore.setState({
      brief: {
        query: "infosys",
        symbol: "INFY.NS",
        mode: "FAST",
        depth: "quick",
        markdown: "",
        sources: [],
        sourceCount: 0,
        webAvailable: true,
        backend: "keyless-fallback",
        execution: { runId: "run-1", requestedDepth: "normal", loop: "fast" },
        createdAt: Date.now() - 3_000,
      } as never,
    });
    const described = describeHostAction("publish_brief", {
      symbol: "INFY.NS",
      markdown: "## Infosys — Quick Brief\nProse.",
      sources: [{ url: "https://example.com", title: "t" }],
      execution: { run_id: "run-1", requested_depth: "normal", loop: "fast" },
    });
    expect(described).toBeTruthy();
    const applied = applyHostAction("publish_brief", {
      symbol: "INFY.NS",
      markdown: "## Infosys — Quick Brief\nProse.",
      sources: [{ url: "https://example.com", title: "t" }],
      execution: { run_id: "run-1", requested_depth: "normal", loop: "fast" },
    });
    expect(applied).toBeTruthy();
    expect(useBriefStore.getState().brief?.backend).toBe("keyless-fallback");
  });

  it("a DIFFERENT run never inherits the prior backend (the 20s clock is dead)", () => {
    useBriefStore.setState({
      brief: {
        query: "infosys",
        symbol: "INFY.NS",
        mode: "FAST",
        depth: "quick",
        markdown: "",
        sources: [],
        sourceCount: 0,
        webAvailable: true,
        backend: "keyless-fallback",
        execution: { runId: "run-1", requestedDepth: "normal", loop: "fast" },
        createdAt: Date.now() - 3_000, // SECONDS old — recency no longer carries
      } as never,
    });
    applyHostAction("publish_brief", {
      symbol: "INFY.NS",
      markdown: "## Infosys\nProse.",
      sources: [{ url: "https://example.com", title: "t" }],
      execution: { run_id: "run-2", requested_depth: "normal", loop: "fast" },
    });
    expect(useBriefStore.getState().brief?.backend).toBeUndefined();
  });

  it("a cross-symbol publish does NOT inherit the prior backend", () => {
    useBriefStore.setState({
      brief: {
        query: "infosys",
        symbol: "INFY.NS",
        mode: "FAST",
        depth: "quick",
        markdown: "",
        sources: [],
        sourceCount: 0,
        webAvailable: true,
        backend: "keyless-fallback",
        createdAt: Date.now() - 60_000,
      } as never,
    });
    applyHostAction("publish_brief", {
      symbol: "MSFT",
      markdown: "## MSFT\nProse.",
      sources: [],
    });
    expect(useBriefStore.getState().brief?.backend).toBeUndefined();
  });
});

describe("briefFromInput backend carry — symbol-less Tier B predecessor", () => {
  it("carries the research-model id across a same-run publish that gains a symbol", () => {
    // Tier B auto-publishes symbol-less; the model's re-publish names the
    // symbol. One side lacking a symbol is compatible — the RUN ID scopes it.
    useBriefStore.setState({
      brief: {
        query: "hdfc bank",
        symbol: "",
        mode: "FAST",
        depth: "quick",
        markdown: "## brief",
        sources: [],
        sourceCount: 0,
        webAvailable: true,
        backend: "research-model:perplexity/sonar",
        execution: { runId: "run-b", requestedDepth: "normal", loop: "research-model" },
        createdAt: Date.now() - 5_000,
      } as never,
    });
    applyHostAction("publish_brief", {
      symbol: "HDFCBANK.NS",
      markdown: "## HDFC Bank\nProse.",
      sources: [],
      execution: { run_id: "run-b", requested_depth: "normal", loop: "research-model" },
    });
    expect(useBriefStore.getState().brief?.backend).toBe("research-model:perplexity/sonar");
  });
});

describe("publish_brief same-run shrink guard (R9 D33, R10 run_id-scoped)", () => {
  it("keeps the engine's richer brief when the model's SAME-RUN re-publish strictly shrinks it", () => {
    const engineBrief = {
      query: "saksoft",
      symbol: "SAKSOFT",
      mode: "DEEP",
      depth: "deep",
      markdown: "## Engine report\n" + "evidence [1] line.\n".repeat(200),
      sources: Array.from({ length: 12 }, (_, i) => ({
        url: `https://example.com/${i}`,
        title: `s${i}`,
        excerpt: "",
      })),
      sourceCount: 12,
      webAvailable: true,
      backend: "native",
      execution: { runId: "run-s", requestedDepth: "deep", loop: "iter" },
      createdAt: Date.now() - 4_000,
    };
    useBriefStore.setState({ brief: engineBrief as never });
    const msg = applyHostAction("publish_brief", {
      symbol: "SAKSOFT",
      markdown: "## Short summary\nA few lines.",
      sources: [{ url: "https://example.com/a", title: "a" }],
      execution: { run_id: "run-s", requested_depth: "deep", loop: "iter" },
    });
    expect(msg).toMatch(/Kept the richer/);
    const kept = useBriefStore.getState().brief;
    expect(kept?.sourceCount).toBe(12);
    expect(kept?.markdown.startsWith("## Engine report")).toBe(true);
  });

  it("a genuinely richer re-publish still replaces (more sources)", () => {
    useBriefStore.setState({
      brief: {
        query: "x",
        symbol: "SAKSOFT",
        mode: "FAST",
        depth: "quick",
        markdown: "## small",
        sources: [],
        sourceCount: 0,
        webAvailable: false,
        createdAt: Date.now() - 4_000,
      } as never,
    });
    const msg = applyHostAction("publish_brief", {
      symbol: "SAKSOFT",
      markdown: "## Bigger report\nWith more.",
      sources: [{ url: "https://example.com/a", title: "a" }],
    });
    expect(msg).toMatch(/Published/);
    expect(useBriefStore.getState().brief?.sourceCount).toBe(1);
  });
});

describe("same-run matching is exchange-suffix-insensitive (R9)", () => {
  it("SAKSOFT.NS re-publish cannot shrink the engine's SAKSOFT brief", () => {
    useBriefStore.setState({
      brief: {
        query: "saksoft",
        symbol: "SAKSOFT",
        mode: "DEEP",
        depth: "deep",
        markdown: "## Engine\n" + "line [1].\n".repeat(100),
        sources: Array.from({ length: 9 }, (_, i) => ({
          url: `https://e.com/${i}`,
          title: `s${i}`,
          excerpt: "",
        })),
        sourceCount: 9,
        webAvailable: true,
        backend: "native",
        execution: { runId: "run-x", requestedDepth: "deep", loop: "iter" },
        createdAt: Date.now() - 60_000,
      } as never,
    });
    const msg = applyHostAction("publish_brief", {
      symbol: "SAKSOFT.NS",
      markdown: "## Summary\nshort.",
      sources: [],
      execution: { run_id: "run-x", requested_depth: "deep", loop: "iter" },
    });
    expect(msg).toMatch(/Kept the richer/);
    expect(useBriefStore.getState().brief?.sourceCount).toBe(9);
  });
});

describe("shrink guard blocks source-less prose re-publishes", () => {
  it("a 0-source long-prose SAME-RUN re-publish never replaces a sourced brief", () => {
    useBriefStore.setState({
      brief: {
        query: "saksoft",
        symbol: "SAKSOFT",
        mode: "DEEP",
        depth: "deep",
        markdown: "## Engine\nshort but cited [1].",
        sources: [{ url: "https://e.com/1", title: "s", excerpt: "" }],
        sourceCount: 1,
        webAvailable: true,
        backend: "native",
        execution: { runId: "run-y", requestedDepth: "deep", loop: "iter" },
        createdAt: Date.now() - 5_000,
      } as never,
    });
    const msg = applyHostAction("publish_brief", {
      symbol: "SAKSOFT.NS",
      markdown: "## Very long prose\n" + "uncited line.\n".repeat(120),
      sources: [],
      execution: { run_id: "run-y", requested_depth: "deep", loop: "iter" },
    });
    expect(msg).toMatch(/Kept the richer/);
    expect(useBriefStore.getState().brief?.sourceCount).toBe(1);
  });
});

// ── R10: execution-derived depth + disambiguation + lifecycle publishes ─────

describe("briefFromInput execution truth (R10 D38/E2)", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
  });

  it("derives mode/depth from the loop that RAN — the wire mode is ignored", () => {
    applyHostAction("publish_brief", {
      query: "reliance",
      symbol: "RELIANCE.NS",
      mode: "fast", // the E2 lie — payload-derived FAST
      markdown: "## Deep report\nCited [1].",
      sources: [{ url: "https://nseindia.com/x", title: "filing" }],
      execution: { run_id: "run-d", requested_depth: "deep", loop: "iter" },
    });
    const brief = useBriefStore.getState().brief;
    expect(brief?.depth).toBe("deep");
    expect(brief?.mode).toBe("DEEP");
    expect(brief?.execution?.runId).toBe("run-d");
  });

  it("research-model lane is stop-based: ultra requested → heavy tier", () => {
    applyHostAction("publish_brief", {
      query: "hdfc",
      markdown: "## Tier B report",
      sources: [],
      execution: { run_id: "run-t", requested_depth: "ultra", loop: "research-model" },
    });
    expect(useBriefStore.getState().brief?.depth).toBe("heavy");
  });

  it("a disambiguation-only publish is accepted and rides the brief", () => {
    const label = applyHostAction("publish_brief", {
      query: "reliance",
      disambiguation: {
        query: "reliance",
        candidates: [
          { symbol: "RELIANCE", name: "Reliance Industries", exchange: "NSE", yahoo_symbol: "RELIANCE.NS" },
          { symbol: "RPOWER", name: "Reliance Power", exchange: "NSE", yahoo_symbol: "RPOWER.NS" },
        ],
      },
      execution: { run_id: "run-dis", requested_depth: "normal", loop: "fast" },
    });
    expect(label).toMatch(/Published/);
    const brief = useBriefStore.getState().brief;
    expect(brief?.disambiguation?.candidates).toHaveLength(2);
    expect(brief?.markdown).toBe("");
  });

  it("a publish from a DIFFERENT run never replaces the run in flight (E3.2)", () => {
    useBriefStore.getState().beginRun({ runId: "run-live", query: "q", depth: "deep" });
    const label = applyHostAction("publish_brief", {
      query: "stale",
      markdown: "## Stale artifact",
      sources: [],
      execution: { run_id: "run-old", requested_depth: "normal", loop: "fast" },
    });
    expect(label).toMatch(/Kept the run in flight/);
    expect(useBriefStore.getState().panel.phase).toBe("in_flight");
  });

  it("publishAckStatus maps the apply label onto the ack vocabulary (D39 §4)", () => {
    expect(publishAckStatus(null)).toBe("failed");
    expect(publishAckStatus("Kept the richer research brief already on screen")).toBe(
      "kept_previous",
    );
    expect(publishAckStatus("Kept the run in flight — this publish belonged to a different run")).toBe(
      "kept_previous",
    );
    expect(publishAckStatus("Published the DEEP research brief")).toBe("applied");
  });
});

// ── R10: data-write / settings host actions (E6, D41/D45) ───────────────────

describe("portfolio host actions (E6 — paper portfolio writes)", () => {
  beforeEach(() => {
    usePortfoliosStore.getState().setAll([], undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => ({}) })) as unknown as typeof fetch,
    );
  });

  afterEach(() => {
    usePortfoliosStore.getState().setAll([], undefined);
    vi.unstubAllGlobals();
  });

  function activeHoldings() {
    const s = usePortfoliosStore.getState();
    return (s.portfolios.find((p) => p.id === s.activeId) ?? s.portfolios[0]).holdings;
  }

  it("describe renders the human diff with kind data-write", () => {
    const diff = describeHostAction("portfolio_add_position", {
      symbol: "RELIANCE",
      quantity: 5,
      cost_basis: 1263,
    });
    expect(diff.kind).toBe("data-write");
    expect(diff.title).toMatch(/Add 5 RELIANCE @ .?1,263 to the paper portfolio/);
    expect(diff.after).toContain("+RELIANCE ×5");
  });

  it("add: POSTs the sidecar ledger and lands the holding in the store", async () => {
    const label = await applyHostActionAsync("portfolio_add_position", {
      symbol: "reliance",
      quantity: 5,
      cost_basis: 1263,
    });
    expect(label).toMatch(/Added 5 RELIANCE/);
    expect(activeHoldings()).toHaveLength(1);
    expect(activeHoldings()[0]).toMatchObject({ symbol: "RELIANCE", quantity: 5, costBasis: 1263 });
    const fetchMock = globalThis.fetch as unknown as { mock: { calls: [string, RequestInit][] } };
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/portfolio/positions");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toMatchObject({
      symbol: "RELIANCE",
      quantity: 5,
      cost_basis: 1263,
    });
  });

  it("update: resolves the holding by id-then-symbol and PUTs the ledger", async () => {
    await applyHostActionAsync("portfolio_add_position", {
      symbol: "RELIANCE",
      quantity: 5,
      cost_basis: 1263,
    });
    const id = activeHoldings()[0].id;
    const label = await applyHostActionAsync("portfolio_update_position", {
      position_id: id,
      symbol: "RELIANCE",
      quantity: 8,
      cost_basis: 1300,
    });
    expect(label).toMatch(/Updated RELIANCE: ×8/);
    expect(activeHoldings()[0]).toMatchObject({ quantity: 8, costBasis: 1300 });
  });

  it("delete: removes the matched holding; an unmatched target is an honest null", async () => {
    await applyHostActionAsync("portfolio_add_position", {
      symbol: "RELIANCE",
      quantity: 5,
      cost_basis: 1263,
    });
    expect(await applyHostActionAsync("portfolio_delete_position", { symbol: "TSLA" })).toBeNull();
    const label = await applyHostActionAsync("portfolio_delete_position", { symbol: "RELIANCE.NS" });
    expect(label).toMatch(/Removed RELIANCE/);
    expect(activeHoldings()).toHaveLength(0);
  });

  it("add with no symbol / non-positive quantity is an honest null", async () => {
    expect(
      await applyHostActionAsync("portfolio_add_position", { quantity: 5, cost_basis: 1 }),
    ).toBeNull();
    expect(
      await applyHostActionAsync("portfolio_add_position", { symbol: "X", quantity: 0 }),
    ).toBeNull();
  });
});

describe("write_note / remove_from_watchlist / set_region / save_screen (R10)", () => {
  afterEach(() => {
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
    resetSettingsStoreForTests();
  });

  it("write_note replaces or appends, scoped to General or a ticker", () => {
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    expect(applyHostAction("write_note", { scope: "general", text: "First take." })).toMatch(
      /Wrote the General note/,
    );
    expect(useNotesStore.getState().general).toBe("First take.");
    applyHostAction("write_note", { scope: "general", text: "Second take.", mode: "append" });
    expect(useNotesStore.getState().general).toBe("First take.\n\nSecond take.");
    applyHostAction("write_note", { scope: "reliance", text: "Q4 beat." });
    expect(useNotesStore.getState().bySymbol.RELIANCE).toBe("Q4 beat.");
    // Empty text is an honest null.
    expect(applyHostAction("write_note", { scope: "general", text: "  " })).toBeNull();
    const diff = describeHostAction("write_note", { scope: "RELIANCE", text: "x", mode: "append" });
    expect(diff.kind).toBe("data-write");
  });

  it("remove_from_watchlist removes a tracked symbol and is idempotent-honest", () => {
    useSymbolsStore.setState({ entries: [] });
    useSymbolsStore.getState().addSymbol("TSLA", "equity");
    const diff = describeHostAction("remove_from_watchlist", { symbol: "TSLA" });
    expect(diff.kind).toBe("watchlist");
    expect(applyHostAction("remove_from_watchlist", { symbol: "tsla" })).toMatch(/Removed TSLA/);
    expect(useSymbolsStore.getState().entries).toHaveLength(0);
    expect(applyHostAction("remove_from_watchlist", { symbol: "TSLA" })).toMatch(
      /was not on your watchlist/,
    );
  });

  it("set_region drives the ONE agent-drivable setting (D45) and rejects junk", () => {
    expect(describeHostAction("set_region", { region: "IN" }).kind).toBe("settings");
    expect(applyHostAction("set_region", { region: "in" })).toBe("Set the region to IN");
    expect(useSettingsStore.getState().region).toBe("IN");
    expect(applyHostAction("set_region", { region: "MARS" })).toBeNull();
    expect(useSettingsStore.getState().region).toBe("IN");
  });

  it("save_screen delegates to the screener store's saveScreen when it ships", () => {
    const saveScreen = vi.fn();
    useScreenerStore.setState({ saveScreen } as never);
    const label = applyHostAction("save_screen", {
      name: "IT value",
      criteria: [{ field: "pe_ratio", operator: "lt", value: 15 }],
      universe: "nse-all",
    });
    expect(label).toBe('Saved the screen as "IT value"');
    expect(saveScreen).toHaveBeenCalledWith("IT value", {
      criteria: [{ field: "pe_ratio", operator: "lt", value: 15 }],
      universe: "nse-all",
    });
    expect(describeHostAction("save_screen", { name: "IT value" }).kind).toBe("data-write");
  });

  it("save_screen is an honest null until the saved-screens API lands", () => {
    useScreenerStore.setState({ saveScreen: undefined } as never);
    expect(applyHostAction("save_screen", { name: "IT value" })).toBeNull();
  });

  it("save_layout is an honest null when the layout has not mounted", async () => {
    useWorkspaceStore.setState({ dockviewApi: null } as never);
    expect(describeHostAction("save_layout", { name: "My desk" }).kind).toBe("data-write");
    expect(await applyHostActionAsync("save_layout", { name: "My desk" })).toBeNull();
  });

  it("write_screener_filters passes formula + run through to applyFilters", () => {
    useScreenerStore.getState().__resetForTests();
    const applyFilters = vi.fn();
    useScreenerStore.setState({ applyFilters } as never);
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    const label = applyHostAction("write_screener_filters", {
      criteria: [{ field: "roe", operator: "gt", value: 0.18 }],
      universe: "india-all",
      formula: "roe > 0.18 and pe_ratio < 30",
      run: true,
    });
    expect(label).toMatch(/running/);
    expect(applyFilters).toHaveBeenCalledWith(
      expect.objectContaining({
        universe: "india-all",
        formula: "roe > 0.18 and pe_ratio < 30",
        run: true,
      }),
    );
    useScreenerStore.getState().__resetForTests();
  });
});
