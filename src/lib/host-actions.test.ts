import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { sidecarGetMock } = vi.hoisted(() => ({ sidecarGetMock: vi.fn() }));

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
  sidecarGet: sidecarGetMock,
}));

import {
  applyHostAction,
  applyHostActionAsync,
  applyIntentAsync,
  describeHostAction,
  describeIntent,
  HOST_ACTION_NAMES,
  hostActionAckDetail,
  isHostActionMutation,
  openCompanyOverview,
  parseHostAction,
} from "@/lib/host-actions";
import { composeBriefMarkdown } from "@/lib/brief-ingest";
import { useBacktestStore } from "@/store/backtest";
import { resetBriefStoreForTests, useBriefStore } from "@/store/brief";
import { useChartCommandStore } from "@/store/chart-command";
import { resetEquityCommandStoreForTests, useEquityCommandStore } from "@/store/equity-command";
import { resetAgentAutonomyStoreForTests } from "@/store/agent-autonomy";
import { useNotesStore } from "@/store/notes";
import { usePortfoliosStore } from "@/store/portfolios";
import {
  resetProposedChangesStoreForTests,
  useProposedChangesStore,
} from "@/store/proposed-changes";
import { useScreenerStore } from "@/store/screener";
import { resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useModulesStore } from "@/store/modules";

// The real layout-only reset; some fixtures below stub store actions.
const realResetLayout = useWorkspaceStore.getState().resetLayout;

describe("host-actions", () => {
  beforeEach(() => {
    useChartCommandStore.setState({ command: null, activeSymbol: null });
    resetEquityCommandStoreForTests();
    useSymbolsStore.setState({ entries: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("classifies the catalog host actions as mutations to gate", () => {
    expect([...HOST_ACTION_NAMES].sort()).toEqual(
      [
        "add_chart_drawing",
        "add_to_watchlist",
        "arrange_layout",
        "close_panel",
        "focus_panel",
        "open_company_overview",
        "open_panel",
        "portfolio_add_position",
        "portfolio_delete_position",
        "portfolio_update_position",
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
    expect(isHostActionMutation("propose_order")).toBe(false);
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

  // R15-CODE-FRONTEND-033 (P7 pin): the focus branch of arrange_layout must
  // resolve panel aliases through resolvePanelToken exactly like focus_panel
  // does — "screener" (alias) vs "screener-panel" (registered id) is the case
  // "chart" (alias === id) can never exercise.
  it("arrange_layout pattern=focus resolves a panel ALIAS, matching focus_panel", () => {
    const setActiveSpy = vi.fn();
    const maximizeSpy = vi.fn();
    const screenerPanel = {
      api: { component: "screener-panel", setActive: setActiveSpy, maximize: maximizeSpy },
    };
    useWorkspaceStore.setState({
      dockviewApi: {
        panels: [screenerPanel],
        getPanel: () => undefined,
      } as never,
      openPanel: vi.fn(),
    } as never);
    expect(applyHostAction("arrange_layout", { pattern: "focus", panel: "screener" })).toBe(
      "Focused on Screener",
    );
    expect(setActiveSpy).toHaveBeenCalledTimes(1);
    expect(maximizeSpy).toHaveBeenCalledTimes(1);
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

  it("add_to_watchlist tracks the symbol once it resolves to a listing", async () => {
    // An equity add now resolves through GET /resolve first (R15-AGENT-044).
    sidecarGetMock.mockReset();
    sidecarGetMock.mockResolvedValueOnce({
      resolved: { symbol: "TSLA", name: "Tesla, Inc." },
      needs_disambiguation: false,
      candidates: [{ symbol: "TSLA", name: "Tesla, Inc." }],
    });
    await applyHostActionAsync("add_to_watchlist", { symbol: "tsla", asset_class: "equity" });
    expect(sidecarGetMock).toHaveBeenCalledWith("/resolve", { q: "TSLA" });
    expect(useSymbolsStore.getState().entries.map((e) => e.symbol)).toContain("TSLA");
  });

  it("add_to_watchlist resolves a company name or fails with candidates, never a blank row (R15-AGENT-044)", async () => {
    sidecarGetMock.mockReset();
    // The live /resolve answers for "Mazagon Dock" (bound) and the invented
    // ticker "MAZAGONDOCK" (no listing, no candidate).
    sidecarGetMock.mockResolvedValueOnce({
      resolved: { symbol: "MAZDOCK", name: "Mazagon Dock Shipbuilders Limited" },
      needs_disambiguation: false,
      candidates: [{ symbol: "MAZDOCK", name: "Mazagon Dock Shipbuilders Limited" }],
    });
    expect(await applyHostActionAsync("add_to_watchlist", { symbol: "Mazagon Dock" })).toBe(
      'Added MAZDOCK to your watchlist (resolved from "MAZAGON DOCK")',
    );
    sidecarGetMock.mockResolvedValueOnce({
      resolved: null,
      needs_disambiguation: false,
      candidates: [],
    });
    const invented = await applyIntentAsync(
      parseHostAction("add_to_watchlist", { symbol: "MAZAGONDOCK" }),
    );
    expect(invented).toEqual({
      status: "failed",
      label: null,
      reason: '"MAZAGONDOCK" did not resolve to a listing',
    });
    expect(useSymbolsStore.getState().entries.map((e) => e.symbol)).toEqual(["MAZDOCK"]);
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

  it("write_screener_filters says which malformed criterion it dropped, in label and ack (R15-AGENT-043)", () => {
    useScreenerStore.getState().__resetForTests();
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    const input = {
      criteria: [
        { field: "pe_ratio", operator: "lt", value: 20 },
        { field: "roe", operator: "gt", value: { min: 15, max: 15 } },
        { field: "debt_to_equity", operator: "lt", value: 0.5 },
      ],
    };
    expect(applyHostAction("write_screener_filters", input)).toBe(
      "Wrote 2 of 3 screener criteria; dropped roe: value must be a number — review and Run",
    );
    expect(describeHostAction("write_screener_filters", input).after).toMatch(
      /dropped roe: value must be a number/,
    );
    expect(hostActionAckDetail("write_screener_filters", input).dropped).toEqual([
      "roe: value must be a number",
    ]);
  });

  it("save_screen whose every criterion is malformed refuses instead of saving the current filters (R15-AGENT-043)", () => {
    useScreenerStore.getState().__resetForTests();
    const input = {
      name: "Quality",
      group: { combinator: "and", criteria: [{ field: "roe", operator: "between", value: 15 }] },
    };
    expect(describeHostAction("save_screen", input).after).toMatch(
      /dropped roe: value must be \{min, max\} numbers — can't apply/,
    );
    expect(applyHostAction("save_screen", input)).toBeNull();
    expect(useScreenerStore.getState().savedScreens).toEqual([]);
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

  it("set_chart_indicators applies only known keys and reports the dropped ones", () => {
    const input = { indicators: ["rsi", "bollinger_bands"] };
    expect(describeHostAction("set_chart_indicators", input).after).toBe(
      "Indicators: rsi (dropped unknown: bollinger_bands)",
    );
    expect(applyHostAction("set_chart_indicators", input)).toBe(
      "Set indicators: rsi (dropped unknown: bollinger_bands)",
    );
    expect(useChartCommandStore.getState().indicatorCommand?.indicators).toEqual(["rsi"]);
    expect(hostActionAckDetail("set_chart_indicators", input)).toEqual({
      action: "set_chart_indicators",
      dropped: ["bollinger_bands"],
    });
    // Nothing applicable: an honest null, the chart's selection is left alone.
    expect(applyHostAction("set_chart_indicators", { indicators: ["bogus"] })).toBeNull();
    expect(useChartCommandStore.getState().indicatorCommand?.indicators).toEqual(["rsi"]);
  });

  it("set_chart_indicators keeps a base:param spec like ema:9 — never dropped (R15-UI-091)", () => {
    const input = { indicators: ["ema:9"] };
    expect(hostActionAckDetail("set_chart_indicators", input)).toEqual({
      action: "set_chart_indicators",
    });
    expect(applyHostAction("set_chart_indicators", input)).toBe("Set indicators: ema:9");
    expect(useChartCommandStore.getState().indicatorCommand?.indicators).toEqual(["ema:9"]);
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
    // The diff now reads whether the panel is open; start from no layout
    // rather than the previous test's partial fake api.
    useWorkspaceStore.setState({ dockviewApi: null } as never);
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

  it("openCompanyOverview carries the picked listing's region to the equity command (R15-DATA-002)", () => {
    // AMAL is Amal Ltd on BSE and Amalgamated Financial on NASDAQ: a caller that
    // picked the NASDAQ listing opens THAT company, whatever the session region.
    const openPanel = vi.fn();
    useWorkspaceStore.setState({ dockviewApi: null, openPanel } as never);
    openCompanyOverview("AMAL", undefined, "US");
    expect(useEquityCommandStore.getState().command).toMatchObject({
      symbol: "AMAL",
      region: "US",
    });
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

  it("briefFromInput with only vysted:// + nsearchives rows -> webAvailable false", () => {
    // R15-RESEARCH-041: structured pulls and exchange-filing rows are cited
    // sources but not the web, so the structured-only banner can fire.
    useBriefStore.getState().clearBrief();
    const input = {
      query: "BDL outlook",
      symbol: "BDL",
      mode: "deep",
      markdown: "## Brief\nPrice [1], filing [2].",
      sources: [
        { url: "vysted://price/BDL", title: "Price for BDL", domain: "yfinance" },
        {
          url: "https://nsearchives.nseindia.com/corporate/BDL_18092026111355_BDL_SE_JS_DIP_Cov-1.pdf",
          title: "Appointment of a Non-Executive Director",
          domain: "NSE",
          source_type: "filing",
        },
      ],
      web_available: false,
    };
    applyHostAction("publish_brief", input);
    const brief = useBriefStore.getState().brief;
    expect(brief?.sourceCount).toBe(2);
    expect(brief?.webAvailable).toBe(false);
    // The diff copy agrees: two cited sources, structured-data-only.
    expect(describeHostAction("publish_brief", input).after).toMatch(
      /2 cited sources · structured-data-only/,
    );
  });

  it("publish_brief keeps a source's date and provenance from the wire (R15-RESEARCH-024)", () => {
    useBriefStore.getState().clearBrief();
    applyHostAction("publish_brief", {
      query: "Apple outlook",
      symbol: "AAPL",
      mode: "deep",
      markdown: "## Brief\nText [1].",
      sources: [
        {
          url: "https://www.sec.gov/x",
          title: "10-K",
          domain: "sec.gov",
          published_at: "2026-09-20T10:00:00Z",
          provider: "via Perplexity Sonar",
        },
      ],
    });
    const [source] = useBriefStore.getState().brief?.sources ?? [];
    expect(source?.publishedAt).toBe("2026-09-20T10:00:00Z");
    expect(source?.provider).toBe("via Perplexity Sonar");
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

  it("applyHostAction has no order path (propose_order is not a host action)", () => {
    const label = applyHostAction("propose_order", { symbol: "AAPL", side: "buy", quantity: 1 });
    expect(label).toBeNull();
  });

  it("describeHostAction renders a reviewable old→new diff per kind", () => {
    useChartCommandStore.setState({ activeSymbol: "SPY" });
    const chart = describeHostAction("set_chart_symbol", { symbol: "NVDA", timeframe: "1d" });
    expect(chart.kind).toBe("chart");
    expect(chart.before).toContain("SPY");
    expect(chart.after).toContain("NVDA");
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
          {
            symbol: "RELIANCE",
            name: "Reliance Industries",
            exchange: "NSE",
            yahoo_symbol: "RELIANCE.NS",
          },
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

  it("the apply result carries its ack status (D39 §4) — kept_previous, applied, failed", async () => {
    // The status is set where the outcome is decided, never parsed back out of
    // the label (R15-CODE-FRONTEND-034; publishAckStatus is gone).
    useBriefStore.setState({
      brief: {
        query: "saksoft",
        mode: "DEEP",
        markdown: "## Engine\nshort but cited [1].",
        sources: [{ url: "https://e.com/1", title: "s", excerpt: "" }],
        sourceCount: 1,
        webAvailable: true,
        execution: { runId: "run-y", requestedDepth: "deep", loop: "iter" },
        createdAt: Date.now() - 5_000,
      } as never,
    });
    const shrink = await applyIntentAsync(
      parseHostAction("publish_brief", {
        query: "saksoft",
        markdown: "## Uncited prose",
        sources: [],
        execution: { run_id: "run-y", requested_depth: "deep", loop: "iter" },
      }),
    );
    expect(shrink.status).toBe("kept_previous");
    useBriefStore.getState().beginRun({ runId: "run-live", query: "q", depth: "deep" });
    const stale = await applyIntentAsync(
      parseHostAction("publish_brief", {
        query: "stale",
        markdown: "## Stale artifact",
        sources: [],
        execution: { run_id: "run-old", requested_depth: "normal", loop: "fast" },
      }),
    );
    expect(stale.status).toBe("kept_previous");
    const note = await applyIntentAsync(parseHostAction("write_note", { scope: "", text: "x" }));
    expect(note.status).toBe("applied");
    const empty = await applyIntentAsync(parseHostAction("write_note", { scope: "", text: " " }));
    expect(empty).toMatchObject({ status: "failed", label: null });
  });
});

// ── R10: data-write / settings host actions (E6, D41/D45) ───────────────────

describe("portfolio host actions (E6 — tracked portfolio writes)", () => {
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
    expect(diff.title).toMatch(/Add 5 RELIANCE @ .?1,263 to the portfolio/);
    expect(diff.after).toContain("+RELIANCE ×5");
  });

  it("add: lands the holding in the store", async () => {
    const label = await applyHostActionAsync("portfolio_add_position", {
      symbol: "reliance",
      quantity: 5,
      cost_basis: 1263,
    });
    expect(label).toMatch(/Added 5 RELIANCE/);
    expect(activeHoldings()).toHaveLength(1);
    expect(activeHoldings()[0]).toMatchObject({ symbol: "RELIANCE", quantity: 5, costBasis: 1263 });
  });

  it("add/update/delete write only the store — no sidecar ledger call (R15-CODE-FRONTEND-012)", async () => {
    await applyHostActionAsync("portfolio_add_position", {
      symbol: "TCS",
      quantity: 5,
      cost_basis: 2500,
    });
    const id = activeHoldings()[0].id;
    await applyHostActionAsync("portfolio_update_position", { position_id: id, quantity: 7 });
    expect(activeHoldings()[0].quantity).toBe(7);
    await applyHostActionAsync("portfolio_delete_position", { position_id: id });
    expect(activeHoldings()).toHaveLength(0);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("update: resolves the holding by id-then-symbol", async () => {
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
    const label = await applyHostActionAsync("portfolio_delete_position", {
      symbol: "RELIANCE.NS",
    });
    expect(label).toMatch(/Removed RELIANCE/);
    expect(activeHoldings()).toHaveLength(0);
  });

  it("add with no cost basis writes nothing, and the review card says no price was given", async () => {
    const input = { symbol: "SUMAX.NS", quantity: 40 };
    expect(describeHostAction("portfolio_add_position", input).title).toBe(
      "Add 40 SUMAX.NS to the portfolio — no price given",
    );
    expect(
      describeHostAction("portfolio_add_position", { ...input, cost_basis: 3400 }).after,
    ).toMatch(/\+SUMAX\.NS ×40 @ .?3,400/);
    expect(
      await applyHostActionAsync("portfolio_add_position", { ...input, cost_basis: null }),
    ).toBeNull();
    expect(await applyHostActionAsync("portfolio_add_position", input)).toBeNull();
    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(activeHoldings()).toHaveLength(0);
  });

  it("add with a negative cost basis is an honest null, not a stored holding (R15-DATA-088)", async () => {
    expect(
      await applyHostActionAsync("portfolio_add_position", {
        symbol: "TCS",
        quantity: 5,
        cost_basis: -2500,
      }),
    ).toBeNull();
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

  it("two lots of one symbol: an id picks its lot; the symbol alone refuses, naming both (R15-AGENT-042)", async () => {
    usePortfoliosStore.getState().setAll([
      {
        id: "default",
        name: "Portfolio",
        holdings: [
          { id: "h-1", symbol: "TCS", quantity: 5, costBasis: 2500, assetClass: "equity" },
          { id: "h-2", symbol: "TCS", quantity: 20, costBasis: 3900, assetClass: "equity" },
        ],
      },
    ]);
    const bySymbol = parseHostAction("portfolio_update_position", {
      symbol: "TCS.NS",
      quantity: 25,
    });
    const refused = await applyIntentAsync(bySymbol);
    expect(refused.label).toBeNull();
    expect(refused.reason).toMatch(/TCS\.NS has 2 lots; name one by position_id: h-1 .*, h-2 /);
    expect(describeIntent(bySymbol).after).toMatch(/can't apply/);

    const byId = parseHostAction("portfolio_update_position", { position_id: "h-2", quantity: 25 });
    // The diff names the lot it will change.
    expect(describeIntent(byId).before).toMatch(/^TCS \(lot 2 of 2\): ×20 @/);
    expect((await applyIntentAsync(byId)).label).toMatch(/Updated TCS: ×25/);
    expect(activeHoldings().map((h) => `${h.id}:${h.quantity}`)).toEqual(["h-1:5", "h-2:25"]);
  });
});

describe("write_note / remove_from_watchlist / set_region / save_screen (R10)", () => {
  afterEach(() => {
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
    resetSettingsStoreForTests();
  });

  it("write_note replaces or appends, scoped to General or a ticker", () => {
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    expect(
      applyHostAction("write_note", { scope: "general", text: "First take.", mode: "replace" }),
    ).toMatch(/Wrote the General note/);
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

  it("write_note honours the catalog-documented args: 'global' is General, mode defaults to append", () => {
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    useNotesStore.setState({ general: "My thesis.", bySymbol: { NVDA: "old", AAPL: "keep" } });
    const input = { scope: "global", text: "Agent takeaway." };
    expect(describeHostAction("write_note", input).title).toBe("Append to the General note");
    expect(applyHostAction("write_note", input)).toBe("Appended to the General note");
    expect(useNotesStore.getState().general).toBe("My thesis.\n\nAgent takeaway.");
    expect(useNotesStore.getState().bySymbol.GLOBAL).toBeUndefined();
    // Not the case the fix was written against: an explicit replace on a ticker.
    const replace = { scope: "NVDA", text: "new", mode: "replace" };
    expect(describeHostAction("write_note", replace).title).toBe("Write the NVDA note");
    expect(applyHostAction("write_note", replace)).toBe("Wrote the NVDA note");
    expect(useNotesStore.getState().bySymbol).toEqual({ NVDA: "new", AAPL: "keep" });
    expect(useNotesStore.getState().general).toBe("My thesis.\n\nAgent takeaway.");
  });

  it("write_note append with a trailing-whitespace addendum equals appendSymbolNote", () => {
    // host-actions appends through the notes store seam, so the agent's append
    // and the store's own append can never disagree on trimming (R15-CODE-FRONTEND-035).
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    const seed = { general: "Macro view.\n", bySymbol: { NVDA: "Thesis.  " }, focusSymbol: "" };
    const addendum = "  Q4 beat.\n\n";
    useNotesStore.setState(seed);
    useNotesStore.getState().appendSymbolNote("NVDA", addendum);
    useNotesStore.getState().appendGeneral(addendum);
    const viaSeams = { ...useNotesStore.getState().bySymbol };
    const generalViaSeam = useNotesStore.getState().general;
    useNotesStore.setState(seed);
    applyHostAction("write_note", { scope: "nvda", text: addendum, mode: "append" });
    applyHostAction("write_note", { scope: "general", text: addendum, mode: "append" });
    expect(useNotesStore.getState().bySymbol).toEqual(viaSeams);
    expect(useNotesStore.getState().general).toBe(generalViaSeam);
    expect(viaSeams.NVDA).toBe("Thesis.  \n\nQ4 beat.");
  });

  it("save_layout without a name updates the active saved layout", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({}) }));
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
    useWorkspaceStore.setState({ name: "My desk", dockviewApi: { toJSON: () => ({}) } } as never);
    try {
      expect(describeHostAction("save_layout", {}).title).toBe('Update the saved layout "My desk"');
      expect(await applyHostActionAsync("save_layout", {})).toBe('Saved the layout as "My desk"');
      const init = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
      expect(JSON.parse(String(init.body)).name).toBe("My desk");
      // With no saved layout active, a new "Agent layout" is created.
      useWorkspaceStore.setState({ name: "default" });
      expect(describeHostAction("save_layout", {}).title).toBe(
        'Save the current layout as "Agent layout"',
      );
    } finally {
      vi.unstubAllGlobals();
      useWorkspaceStore.setState({ name: "default", dockviewApi: null } as never);
    }
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

  it("save_screen saves the agent's recipe, not the on-screen draft, and says when it replaces (R15-CODE-FRONTEND-009)", () => {
    // The real store at its defaults: pe<20 + mcap + sector on screen.
    useScreenerStore.getState().__resetForTests();
    useScreenerStore.getState().setFormula("roe > 0.1");
    const input = {
      name: "IT value",
      criteria: [{ field: "pe_ratio", operator: "lt", value: 15 }],
      universe: "nse-all",
    };
    expect(describeHostAction("save_screen", input).after).toBe(
      'Saved screens: +"IT value" (1 criterion)',
    );
    expect(applyHostAction("save_screen", input)).toBe('Saved the screen as "IT value"');
    expect(useScreenerStore.getState().savedScreens).toEqual([
      {
        name: "IT value",
        universe: "nse-all",
        criteria: [{ field: "pe_ratio", operator: "lt", value: 15 }],
        group: null,
        formula: undefined,
        combinator: "and",
      },
    ]);
    // Same name again: the diff and the label say "replaced"; one screen remains.
    const again = { name: "IT value", criteria: [{ field: "roe", operator: "gt", value: 0.2 }] };
    expect(describeHostAction("save_screen", again).after).toBe(
      'Saved screens: "IT value" replaced (1 criterion)',
    );
    expect(applyHostAction("save_screen", again)).toBe('Replaced the saved screen "IT value"');
    const saved = useScreenerStore.getState().savedScreens;
    expect(saved).toHaveLength(1);
    expect(saved[0].criteria).toEqual([{ field: "roe", operator: "gt", value: 0.2 }]);
    expect(applyHostAction("save_screen", { name: " " })).toBeNull();
    useScreenerStore.getState().__resetForTests();
  });

  it("save_layout is an honest null when the layout has not mounted", async () => {
    useWorkspaceStore.setState({ dockviewApi: null } as never);
    expect(describeHostAction("save_layout", { name: "My desk" }).kind).toBe("data-write");
    expect(await applyHostActionAsync("save_layout", { name: "My desk" })).toBeNull();
  });

  it("write_screener_filters writes the recipe and run:true runs it once (R15-CODE-FRONTEND-010)", () => {
    useScreenerStore.getState().__resetForTests();
    // Only the network-backed run is stubbed; applyFilters is the real store's.
    const runScreener = vi.fn(async () => null);
    useScreenerStore.setState({ runScreener });
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    const input = {
      criteria: [{ field: "roe", operator: "gt", value: 0.18 }],
      universe: "india-all",
      formula: "roe > 0.18 and pe_ratio < 30",
    };
    expect(applyHostAction("write_screener_filters", input)).toMatch(/review and Run$/);
    expect(runScreener).not.toHaveBeenCalled();
    const label = applyHostAction("write_screener_filters", { ...input, run: true });
    expect(label).toMatch(/running$/);
    expect(runScreener).toHaveBeenCalledTimes(1);
    const s = useScreenerStore.getState();
    expect(s.criteria).toEqual([{ field: "roe", operator: "gt", value: 0.18 }]);
    expect(s.universe).toBe("india-all");
    expect(s.formula).toBe("roe > 0.18 and pe_ratio < 30");
    useScreenerStore.getState().__resetForTests();
  });
});

describe("open_panel backtest run_id (R15-AGENT-011)", () => {
  const RESULT = {
    runId: "bt-1",
    strategyId: "sma_cross",
    request: {
      strategyId: "sma_cross",
      params: {},
      symbols: ["SPY"],
      startDate: "2024-01-01",
      endDate: "2024-12-31",
      initialCapital: 100_000,
    },
    metrics: {},
    trades: [],
    equityCurve: [],
    startedAt: 1_710_000_000_000,
    durationMs: 250,
  };

  beforeEach(() => {
    useBacktestStore.getState().__resetForTests();
    useWorkspaceStore.setState({ dockviewApi: null, openPanel: vi.fn() } as never);
    sidecarGetMock.mockReset();
  });

  it("loads the agent's run as complete and makes it the active run", async () => {
    sidecarGetMock.mockResolvedValueOnce(RESULT);
    const label = await applyHostActionAsync("open_panel", { panel: "backtest", run_id: "bt-1" });
    expect(label).toBe("Opened Backtest");
    expect(sidecarGetMock).toHaveBeenCalledWith("/backtest/runs/bt-1");
    const state = useBacktestStore.getState();
    expect(state.activeRunId).toBe("bt-1");
    expect(state.runs["bt-1"]).toMatchObject({ status: "complete", result: RESULT });
    expect(describeHostAction("open_panel", { panel: "backtest", run_id: "bt-1" }).title).toBe(
      "Open Backtest — run bt-1",
    );
  });

  it("a run the sidecar does not hold is an honest failure, not an empty panel", async () => {
    sidecarGetMock.mockRejectedValueOnce(new Error("404 unknown run_id"));
    expect(
      await applyHostActionAsync("open_panel", { panel: "backtest", run_id: "gone" }),
    ).toBeNull();
    expect(useBacktestStore.getState().activeRunId).toBeNull();
  });
});

// ── R15-CODE-FRONTEND-011/007: one parsed intent, targets bound at enqueue ──

describe("describe/apply parity over one parsed intent (R15-CODE-FRONTEND-011)", () => {
  const screenerPanel = {
    api: { component: "screener-panel", close: vi.fn(), setActive: vi.fn() },
  };
  const chartPanel = {
    id: "chart",
    api: { component: "chart-panel", close: vi.fn(), setActive: vi.fn() },
  };

  function setup() {
    resetSettingsStoreForTests();
    useChartDrawingsStore.setState({
      byPanel: {},
      views: { chart: { symbol: "TCS", timeframe: "1d", indicators: [], compare: null } },
    });
    resetBriefStoreForTests();
    useScreenerStore.getState().__resetForTests();
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
    useSymbolsStore.setState({ entries: [{ symbol: "TSLA", assetClass: "equity" }] });
    usePortfoliosStore.getState().setAll([
      {
        id: "A",
        name: "A",
        holdings: [
          { id: "h-a", symbol: "TCS", quantity: 10, costBasis: 2500, assetClass: "equity" },
        ],
      },
    ]);
    const panels = [screenerPanel, chartPanel];
    useWorkspaceStore.setState({
      name: "My desk",
      openPanel: vi.fn(),
      resetLayout: vi.fn(),
      dockviewApi: {
        panels,
        getPanel: (id: string) => panels.find((p) => p.api.component === `${id}-panel`),
        toJSON: () => ({}),
      },
    } as never);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => ({}) })) as unknown as typeof fetch,
    );
  }

  afterEach(() => {
    vi.unstubAllGlobals();
    useWorkspaceStore.setState({ name: "default", dockviewApi: null } as never);
    usePortfoliosStore.getState().setAll([], undefined);
  });

  // [name, input, what the diff promises (after), what apply reports (label)]
  const ROWS: [string, Record<string, unknown>, RegExp, RegExp | null][] = [
    ["set_chart_symbol", { symbol: "NVDA" }, /Chart symbol: NVDA/, /Loaded NVDA/],
    [
      "set_chart_indicators",
      { indicators: ["rsi", "bogus"] },
      /rsi \(dropped unknown: bogus\)/,
      /rsi \(dropped unknown: bogus\)/,
    ],
    ["open_panel", { panel: "chart", symbol: "NVDA" }, /open — NVDA loaded/, /Chart — NVDA/],
    // P7b: the alias resolves for the diff exactly as for the apply.
    ["close_panel", { panel: "screener" }, /Screener panel: closed/, /^Closed Screener$/],
    ["focus_panel", { panel: "chart" }, /Foreground: Chart/, /^Focused Chart$/],
    [
      "arrange_layout",
      { pattern: "default" },
      /default panel arrangement \(chart drawings and modules kept\)/,
      /panel arrangement to the default \(drawings and modules kept\)/,
    ],
    ["open_company_overview", { symbol: "AAPL" }, /Equity Overview: AAPL/, /AAPL's overview/],
    [
      "publish_brief",
      { markdown: "## x", mode: "fast", sources: [{ url: "https://a.example", title: "a" }] },
      /1 cited source/,
      /Published the FAST research brief/,
    ],
    ["add_to_watchlist", { symbol: "tsla" }, /TSLA already tracked/, /TSLA is already on/],
    ["remove_from_watchlist", { symbol: "tsla" }, /−TSLA \(0 total\)/, /Removed TSLA/],
    [
      "write_screener_filters",
      { criteria: [{ field: "roe", operator: "gt", value: 0.18 }] },
      /1 criterion — review then Run/,
      /1 screener criterion — review and Run/,
    ],
    ["save_screen", { name: "IT value" }, /\+"IT value"/, /"IT value"/],
    [
      "portfolio_add_position",
      { symbol: "INFY", quantity: 2, cost_basis: 1500 },
      /\+INFY ×2 @ .1,500/,
      /Added 2 INFY @ .1,500/,
    ],
    // P6: a cost-only update keeps the lot's quantity in the diff AND the apply.
    [
      "portfolio_update_position",
      { position_id: "h-a", cost_basis: 3100 },
      /^TCS: ×10 @ .3,100$/,
      /^Updated TCS: ×10 @ .3,100$/,
    ],
    ["portfolio_delete_position", { position_id: "h-a" }, /TCS: removed/, /Removed TCS/],
    [
      "write_note",
      { scope: "NVDA", text: "hello", mode: "replace" },
      /NVDA note: replaced \(5 chars\)/,
      /Wrote the NVDA note/,
    ],
    ["save_layout", { name: "My desk" }, /"My desk" updated/, /Saved the layout as "My desk"/],
    ["set_region", { region: "in" }, /Region: IN/, /Set the region to IN/],
    [
      "add_chart_drawing",
      { kind: "horizontal-line", points: [{ price: 3400 }] },
      /^Drawings on TCS 1d: 1 \(\+a horizontal line at 3400\)$/,
      /^Drew a horizontal line at 3400 on TCS 1d$/,
    ],
    // Refusals: the diff says it can't apply exactly when the apply fails.
    ["set_region", { region: "MARS" }, /"MARS" is not a region — can't apply/, null],
    ["close_panel", { panel: "flux-capacitor" }, /unknown panel — can't apply/, null],
    ["portfolio_update_position", { position_id: "h-a", quantity: 0 }, /can't apply/, null],
    ["write_note", { scope: "NVDA", text: "  " }, /nothing to write — can't apply/, null],
    [
      "add_chart_drawing",
      { kind: "trendline", points: [{ time: "2026-07-01", price: 3400 }] },
      /a trendline takes 2 point\(s\)/,
      null,
    ],
  ];

  it("the table covers every host action", () => {
    expect(new Set(ROWS.map(([name]) => name))).toEqual(HOST_ACTION_NAMES);
  });

  it.each(ROWS)("%s %j: the diff promises what apply does", async (name, input, said, did) => {
    setup();
    const intent = parseHostAction(name, input);
    const { after } = describeIntent(intent);
    const { label } = await applyIntentAsync(intent);
    expect(after).toMatch(said);
    if (did === null) {
      expect(label).toBeNull();
    } else {
      expect(label).toMatch(did);
    }
    expect(/can't apply/.test(after)).toBe(label === null);
  });

  function twoPortfolios() {
    usePortfoliosStore.getState().setAll(
      [
        {
          id: "A",
          name: "A",
          holdings: [
            { id: "h-a", symbol: "TCS", quantity: 10, costBasis: 2500, assetClass: "equity" },
          ],
        },
        {
          id: "B",
          name: "B",
          holdings: [
            { id: "h-b", symbol: "TCS", quantity: 99, costBasis: 3900, assetClass: "equity" },
          ],
        },
      ],
      "A",
    );
  }

  function lots(portfolioId: string): string[] {
    return usePortfoliosStore
      .getState()
      .portfolios.find((p) => p.id === portfolioId)!
      .holdings.map((h) => `${h.symbol}:${h.quantity}`);
  }

  it("P5: accept changes the lot the diff showed in portfolio A, not portfolio B's", async () => {
    setup();
    resetProposedChangesStoreForTests();
    resetAgentAutonomyStoreForTests();
    twoPortfolios();
    const gate = useProposedChangesStore.getState();
    const { id: update } = gate.enqueue({
      toolCallId: "tc-up",
      name: "portfolio_update_position",
      input: { position_id: "h-a", symbol: "TCS", quantity: 12 },
      batchId: "b",
    });
    const { id: add } = gate.enqueue({
      toolCallId: "tc-add",
      name: "portfolio_add_position",
      input: { symbol: "INFY", quantity: 1, cost_basis: 1500 },
      batchId: "b",
    });
    // The user switches the active portfolio before accepting.
    usePortfoliosStore.getState().setActive("B");
    await gate.accept(update);
    await gate.accept(add);
    expect(lots("A")).toEqual(["TCS:12", "INFY:1"]);
    expect(lots("B")).toEqual(["TCS:99"]);
    expect(useProposedChangesStore.getState().pending()).toHaveLength(0);
  });

  it("a bound lot that is gone by accept fails honestly instead of hitting another lot", async () => {
    setup();
    resetProposedChangesStoreForTests();
    resetAgentAutonomyStoreForTests();
    const gate = useProposedChangesStore.getState();
    const { id } = gate.enqueue({
      toolCallId: "tc-del",
      name: "portfolio_delete_position",
      input: { position_id: "h-a" },
      batchId: "b",
    });
    usePortfoliosStore.getState().removeHolding("A", "h-a");
    usePortfoliosStore
      .getState()
      .addHolding("A", { symbol: "TCS", quantity: 3, costBasis: 1, assetClass: "equity" });
    await gate.accept(id);
    const change = useProposedChangesStore.getState().changes[0];
    expect(change.status).toBe("pending");
    expect(change.detail).toMatch(/no longer in the portfolio/);
    expect(lots("A")).toEqual(["TCS:3"]);
  });

  it("an applied holding delete can be undone: the holding is back with its id (R15-AGENT-041)", async () => {
    setup();
    resetProposedChangesStoreForTests();
    resetAgentAutonomyStoreForTests();
    const gate = useProposedChangesStore.getState();
    const { id } = gate.enqueue({
      toolCallId: "tc-del",
      name: "portfolio_delete_position",
      input: { position_id: "h-a" },
      batchId: "b",
    });
    await gate.accept(id);
    expect(lots("A")).toEqual([]);
    expect(useProposedChangesStore.getState().changes[0].preImage).toBeDefined();
    await new Promise((resolve) => setTimeout(resolve, 0)); // let the accept ack land
    const fetchCalls = vi.mocked(fetch).mock.calls.length;
    gate.undo(id);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(vi.mocked(fetch).mock.calls.length).toBe(fetchCalls); // Undo acks nothing new
    const holdings = usePortfoliosStore.getState().portfolios.find((p) => p.id === "A")!.holdings;
    expect(holdings).toEqual([
      { id: "h-a", symbol: "TCS", quantity: 10, costBasis: 2500, assetClass: "equity" },
    ]);
    expect(useProposedChangesStore.getState().changes[0].status).toBe("undone");
  });

  it("an applied note replace can be undone: the prior text is restored (R15-AGENT-041)", async () => {
    setup();
    resetProposedChangesStoreForTests();
    resetAgentAutonomyStoreForTests();
    useNotesStore.getState().setSymbolNote("NVDA", "my own thesis");
    const gate = useProposedChangesStore.getState();
    const { id } = gate.enqueue({
      toolCallId: "tc-note",
      name: "write_note",
      input: { scope: "NVDA", text: "agent text", mode: "replace" },
      batchId: "b",
    });
    await gate.accept(id);
    expect(useNotesStore.getState().noteFor("NVDA")).toBe("agent text");
    gate.undo(id);
    expect(useNotesStore.getState().noteFor("NVDA")).toBe("my own thesis");
  });
});

describe("arrange_layout's default is a layout-only reset (R15-AGENT-056)", () => {
  afterEach(() => {
    useWorkspaceStore.setState({ dockviewApi: null } as never);
    useModulesStore.getState().setEnabledMap({});
    useChartDrawingsStore.getState().replaceAll({ byPanel: {} });
  });

  it.each([{}, { pattern: "bogus" }])("keeps drawings and module choices for %o", (input) => {
    const clear = vi.fn();
    const addPanel = vi.fn(() => ({ api: { setSize: vi.fn() } }));
    useWorkspaceStore.setState({
      resetLayout: realResetLayout,
      dockviewApi: { clear, addPanel, width: 0, height: 0 },
    } as never);
    useModulesStore.getState().setEnabledMap({ news: false });
    useChartDrawingsStore
      .getState()
      .replaceAll({ byPanel: { chart: [{ id: "d1", kind: "hline" }] } } as never);

    expect(describeHostAction("arrange_layout", input).after).toMatch(/drawings and modules kept/);
    expect(applyHostAction("arrange_layout", input)).toMatch(/drawings and modules kept/);
    expect(clear).toHaveBeenCalledTimes(1);
    expect(useModulesStore.getState().enabled).toEqual({ news: false });
    expect(useChartDrawingsStore.getState().byPanel.chart).toHaveLength(1);
  });
});

describe("open_company_overview's highlight is truthful (R15-AGENT-081)", () => {
  beforeEach(() => {
    resetEquityCommandStoreForTests();
    useWorkspaceStore.setState({ dockviewApi: null, openPanel: vi.fn() } as never);
  });

  it("a metric the panel shows is spotlit and named by its row label", () => {
    const input = { symbol: "TATASTEEL", highlight: "pe_ratio" };
    expect(describeHostAction("open_company_overview", input).after).toBe(
      "Equity Overview: TATASTEEL — spotlighting P/E",
    );
    expect(applyHostAction("open_company_overview", input)).toBe(
      "Opened TATASTEEL's overview — spotlighting P/E",
    );
    expect(useEquityCommandStore.getState().command?.highlightMetric).toBe("pe_ratio");
  });

  it("a metric the panel does not show is reported as absent, and not sent", () => {
    const input = { symbol: "TATASTEEL", highlight: "rocket_fuel" };
    expect(applyHostAction("open_company_overview", input)).toBe(
      'Opened TATASTEEL\'s overview — "rocket_fuel" is not a metric on that panel, so nothing is spotlit',
    );
    expect(describeHostAction("open_company_overview", input).after).toContain(
      "is not a metric on that panel",
    );
    expect(useEquityCommandStore.getState().command?.highlightMetric).toBeUndefined();
  });
});
