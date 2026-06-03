/**
 * Host actions — the agent's cockpit-driving mutations, and how the diff/accept
 * gate stages, describes, and applies them (FR-002 act-path, FR-010, FR-011).
 *
 * The catalog tags four capabilities `kind="host_action", read_only=false`:
 * `open_panel`, `set_chart_symbol`, `add_to_watchlist`, `propose_order`. The
 * agent emits them as `tool_use` events; instead of applying immediately, the
 * chat surface stages each as a `ProposedChange` (see `store/proposed-changes`),
 * and these helpers do the work:
 *   - `describeHostAction` — read the live stores to build the old→new diff.
 *   - `applyHostAction`     — apply a non-order mutation on accept.
 *   - `routeOrderProposal`  — route an accepted order through the §6.5
 *                              propose→confirm path (the AI never places).
 */

import {
  applyCustomLayout,
  fitLayoutTemplate,
  type CustomPanelSpec,
  type LayoutTemplate,
} from "@/lib/layout-templates";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useBriefStore } from "@/store/brief";
import { useBrokersStore } from "@/store/brokers";
import { useChartCommandStore } from "@/store/chart-command";
import { useOrdersStore } from "@/store/orders";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";

import type { BrokerId, BrokerOrderProposal } from "../../types/broker";
import type { BriefSource, BriefStep, BriefStructured, ResearchBriefData } from "../../types/brief";
import type { ProposedChangeKind } from "../../types/proposed-change";

/** The catalog host-action tool ids (`kind="host_action"`, `read_only=false`). */
export const HOST_ACTION_NAMES = new Set([
  "open_panel",
  "close_panel",
  "focus_panel",
  "arrange_layout",
  "set_chart_symbol",
  "set_chart_indicators",
  "add_to_watchlist",
  "publish_brief",
  "propose_order",
]);

/** Build a frontend ResearchBriefData from a publish_brief tool input.
 *
 * Normalises the mode to the frontend's uppercase FAST|DEEP (the sidecar
 * research models emit lowercase) and never trusts the agent for the honest web
 * flag — `web_available === false` flows through so the brief shows the honest
 * "structured data only" banner rather than implying web sources exist.
 */
function briefFromInput(input: Record<string, unknown>): ResearchBriefData {
  const rawSources = Array.isArray(input.sources) ? input.sources : [];
  const sources: BriefSource[] = rawSources
    .filter((s): s is Record<string, unknown> => typeof s === "object" && s !== null)
    .map((s) => ({
      url: typeof s.url === "string" ? s.url : "",
      title: typeof s.title === "string" ? s.title : typeof s.url === "string" ? s.url : "",
      excerpt: typeof s.excerpt === "string" ? s.excerpt : "",
      domain: typeof s.domain === "string" ? s.domain : undefined,
    }))
    .filter((s) => s.url);
  const mode = str(input, "mode").toUpperCase() === "DEEP" ? "DEEP" : "FAST";
  const cost =
    typeof input.cost === "object" && input.cost !== null
      ? (input.cost as { tokens?: number; spendUsd?: number; spend_usd?: number })
      : undefined;
  const steps = Array.isArray(input.steps) ? (input.steps as BriefStep[]) : undefined;
  // The provenance-tagged structured bundle (price/fundamentals/news/filings)
  // backs the native metric cards. Passed through verbatim when present — it is
  // non-secret research data, the same shape the sidecar's ResearchBrief emits.
  // Absent on older briefs / structured-only runs → the panel renders no cards.
  const symbol = str(input, "symbol") || undefined;
  let structured =
    typeof input.structured === "object" && input.structured !== null
      ? (input.structured as BriefStructured)
      : undefined;
  // Preserve the structured bundle across a structured-LESS re-publish: the
  // runtime auto-publish seeds the live metric data, and a model-issued
  // publish_brief (which doesn't copy the big structured dict — and often omits
  // the symbol arg) would otherwise wipe it. Carry it over when the symbol
  // matches OR the model omitted the symbol on a brief published moments ago —
  // the auto-publish always seeds the CURRENT symbol first, so a recent prior
  // brief is this same research turn (the recency bound rules out cross-symbol
  // contamination). Keeps the native metric cards populated either way.
  if (!structured) {
    const prev = useBriefStore.getState().brief;
    const sameSymbol =
      !!prev?.symbol && !!symbol && prev.symbol.toUpperCase() === symbol.toUpperCase();
    const recent = typeof prev?.createdAt === "number" && Date.now() - prev.createdAt < 120_000;
    if (prev?.structured && (sameSymbol || (!symbol && recent))) {
      structured = prev.structured;
    }
  }
  return {
    query: str(input, "query"),
    symbol,
    mode,
    markdown: str(input, "markdown"),
    sources,
    sourceCount: sources.length,
    cost: cost ? { tokens: cost.tokens, spendUsd: cost.spendUsd ?? cost.spend_usd } : undefined,
    webAvailable: input.web_available !== false,
    note: str(input, "note") || undefined,
    steps,
    structured,
    createdAt: Date.now(),
  };
}

/**
 * Load a symbol into the chart via the always-consumed chart-command channel —
 * the shared path behind both the agent's `set_chart_symbol` host-action and a
 * user clicking a ticker chip in the brief. Opens a chart first if none is on
 * screen (so the command has a consumer), then commands it directly. Fit-aware:
 * it retargets the EXISTING chart, never spawns a panel per call.
 */
export function loadSymbolIntoChart(symbol: string, timeframe?: string): void {
  if (!symbol) {
    return;
  }
  ensureChartOpen();
  useChartCommandStore.getState().loadSymbol(symbol, timeframe || undefined);
}

/** The named arrange_layout templates (beyond the legacy default/focus patterns). */
const LAYOUT_TEMPLATES: ReadonlySet<string> = new Set([
  "single-focus",
  "research-cockpit",
  "compare",
  "macro-scan",
]);

/** A host-action mutation the diff gate must intercept rather than auto-apply. */
export function isHostActionMutation(name: string): boolean {
  return HOST_ACTION_NAMES.has(name);
}

function str(input: Record<string, unknown>, key: string): string {
  const v = input[key];
  return typeof v === "string" ? v : "";
}

/** Read a string[] arg, dropping non-strings. */
function strArray(input: Record<string, unknown>, key: string): string[] {
  const v = input[key];
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

/**
 * Parse the `panels` arg of a CUSTOM arrange (Track B). Tolerant of both shapes
 * the model might emit: a bare `["chart","news"]` (host picks coherent positions)
 * or `[{panel,direction,reference}, …]` (explicit "one here, one there"). Anything
 * malformed is dropped so a sloppy arg never crashes the arrange.
 */
function parseCustomPanels(input: Record<string, unknown>): CustomPanelSpec[] {
  const raw = input.panels;
  if (!Array.isArray(raw)) {
    return [];
  }
  const specs: CustomPanelSpec[] = [];
  for (const item of raw) {
    if (typeof item === "string") {
      specs.push({ panel: item });
    } else if (item && typeof item === "object") {
      const o = item as Record<string, unknown>;
      if (typeof o.panel === "string") {
        specs.push({
          panel: o.panel,
          direction: typeof o.direction === "string" ? (o.direction as never) : undefined,
          reference: typeof o.reference === "string" ? o.reference : undefined,
        });
      }
    }
  }
  return specs;
}

/**
 * Ensure a chart panel is open so a chart command (symbol / indicators) has a
 * consumer. A bare `set_chart_symbol` on an empty cockpit otherwise lands in the
 * chart-command channel with no chart panel reading it — the symbol "doesn't
 * take" (the AUTO-mode "no panels open yet" failure). Checks by COMPONENT so it
 * is robust to the chart's generated panel ids (`chart-<id>`, singleton:false).
 */
function ensureChartOpen(): void {
  const ws = useWorkspaceStore.getState();
  const api = ws.dockviewApi;
  const hasChart = api?.panels.some((p) => p.api.component === "chart-panel") ?? false;
  if (!hasChart) {
    ws.openPanel("chart");
  }
}

function num(input: Record<string, unknown>, key: string): number {
  const v = input[key];
  return typeof v === "number" ? v : Number(v ?? 0);
}

/** Human-friendly panel label from a panel id. */
function panelLabel(id: string): string {
  return id.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Describe a host-action mutation as a reviewable old→new diff. Reads the live
 * stores so the "before" reflects the real current cockpit state.
 */
export function describeHostAction(
  name: string,
  input: Record<string, unknown>,
): { kind: ProposedChangeKind; title: string; before: string; after: string } {
  const symbol = str(input, "symbol");
  switch (name) {
    case "set_chart_symbol": {
      const current = useChartCommandStore.getState().activeSymbol ?? "—";
      const tf = str(input, "timeframe");
      return {
        kind: "chart",
        title: `Load ${symbol || "symbol"} into the chart`,
        before: `Chart symbol: ${current}`,
        after: `Chart symbol: ${symbol}${tf ? ` · ${tf}` : ""}`,
      };
    }
    case "set_chart_indicators": {
      const indicators = strArray(input, "indicators");
      const current = useChartCommandStore.getState().activeIndicators;
      return {
        kind: "chart",
        title: `Set chart indicators${symbol ? ` on ${symbol}` : ""}`,
        before: `Indicators: ${current.length ? current.join(", ") : "none"}`,
        after: `Indicators: ${indicators.length ? indicators.join(", ") : "none"}`,
      };
    }
    case "open_panel": {
      const panel = str(input, "panel");
      return {
        kind: "panel",
        title: `Open the ${panelLabel(panel)} panel`,
        before: `${panelLabel(panel)} panel: not open`,
        after: `${panelLabel(panel)} panel: open`,
      };
    }
    case "close_panel": {
      const panel = str(input, "panel");
      const isOpen = useWorkspaceStore.getState().dockviewApi?.getPanel(panel) != null;
      return {
        kind: "panel",
        title: `Close the ${panelLabel(panel)} panel`,
        before: `${panelLabel(panel)} panel: ${isOpen ? "open" : "not open"}`,
        after: `${panelLabel(panel)} panel: closed`,
      };
    }
    case "focus_panel": {
      const panel = str(input, "panel");
      return {
        kind: "panel",
        title: `Focus the ${panelLabel(panel)} panel`,
        before: `Foreground: the current panel`,
        after: `Foreground: ${panelLabel(panel)}`,
      };
    }
    case "arrange_layout": {
      const pattern = str(input, "pattern") || "default";
      const panel = str(input, "panel");
      if (pattern === "focus") {
        return {
          kind: "panel",
          title: `Focus on ${panel ? panelLabel(panel) : "one panel"}`,
          before: "Layout: the current cockpit",
          after: `Layout: ${panel ? panelLabel(panel) : "a single panel"} maximised`,
        };
      }
      const customPanels = parseCustomPanels(input);
      if (pattern === "custom" || customPanels.length > 0) {
        const names = customPanels.map((p) => p.panel).join(" + ");
        return {
          kind: "panel",
          title: names ? `Arrange ${names}` : "Arrange your panels",
          before: "Layout: the current cockpit",
          after: names ? `Layout: ${names}` : "Layout: a custom arrangement",
        };
      }
      if (LAYOUT_TEMPLATES.has(pattern)) {
        const label =
          pattern === "research-cockpit" ? "research cockpit" : pattern.replace("-", " ");
        const sym = str(input, "symbol");
        const syms = strArray(input, "symbols");
        const scope =
          pattern === "compare" && syms.length >= 2
            ? ` (${syms.slice(0, 2).join(" vs ")})`
            : sym
              ? ` · ${sym}`
              : syms[0]
                ? ` · ${syms[0]}`
                : "";
        return {
          kind: "panel",
          title: `Arrange the ${label} layout`,
          before: "Layout: the current cockpit",
          after: `Layout: ${label}${scope}`,
        };
      }
      return {
        kind: "panel",
        title: "Reset to the default layout",
        before: "Layout: the current cockpit",
        after: "Layout: the default cockpit (clears layout customisations)",
      };
    }
    case "publish_brief": {
      const sources = Array.isArray(input.sources) ? input.sources : [];
      const mode = str(input, "mode").toUpperCase() === "DEEP" ? "DEEP" : "FAST";
      const webOff = input.web_available === false;
      return {
        kind: "panel",
        title: `Publish the ${mode} research brief${symbol ? ` on ${symbol}` : ""}`,
        before: "Brief panel: previous brief (if any)",
        after: `Brief: ${sources.length} cited source${sources.length === 1 ? "" : "s"}${webOff ? " · structured-data-only" : ""}`,
      };
    }
    case "add_to_watchlist": {
      const entries = useSymbolsStore.getState().entries;
      const already = entries.some((e) => e.symbol.toUpperCase() === symbol.toUpperCase());
      return {
        kind: "watchlist",
        title: `Add ${symbol} to your watchlist`,
        before: `Watchlist: ${entries.length} symbol${entries.length === 1 ? "" : "s"}`,
        after: already
          ? `Watchlist: ${symbol} already tracked`
          : `Watchlist: +${symbol} (${entries.length + 1} total)`,
      };
    }
    case "propose_order": {
      const side = str(input, "side");
      const qty = num(input, "quantity");
      const type = str(input, "order_type") || "market";
      const limit = input.limit_price;
      return {
        kind: "order",
        title: `${side ? side.toUpperCase() : "ORDER"} ${qty || ""} ${symbol}`
          .replace(/\s+/g, " ")
          .trim(),
        before: "No order placed",
        after: `${side} ${qty} ${symbol} (${type}${typeof limit === "number" ? ` @ ${limit}` : ""}) — routes to the confirm-before-place dialog`,
      };
    }
    default:
      return { kind: "panel", title: name.replace(/_/g, " "), before: "—", after: "—" };
  }
}

/**
 * Apply a non-order host-action mutation to the live stores. Returns a short
 * label, or `null` if it couldn't apply. Orders are NOT applied here — they
 * route through `routeOrderProposal` → the §6.5 dialog.
 */
export function applyHostAction(name: string, input: Record<string, unknown>): string | null {
  const symbol = str(input, "symbol");
  switch (name) {
    case "set_chart_symbol":
      if (symbol) {
        // Command the chart DIRECTLY (always-consumed channel), not the opt-in
        // sync bus — the BUG-6 fix. The shared helper opens a chart first if the
        // cockpit is empty (the AUTO-mode "no panels open yet" failure).
        loadSymbolIntoChart(symbol, str(input, "timeframe"));
        return `Loaded ${symbol} into the chart`;
      }
      return null;
    case "set_chart_indicators": {
      const indicators = strArray(input, "indicators");
      ensureChartOpen();
      const cc = useChartCommandStore.getState();
      // If a symbol was named, load it first so the indicators apply to the
      // intended chart; then set the selection (unscoped → the active chart).
      if (symbol) {
        cc.loadSymbol(symbol);
      }
      cc.setIndicators(indicators);
      return `Set indicators: ${indicators.length ? indicators.join(", ") : "none"}`;
    }
    case "open_panel": {
      const panel = str(input, "panel");
      if (panel) {
        useWorkspaceStore.getState().openPanel(panel);
        return `Opened ${panelLabel(panel)}`;
      }
      return null;
    }
    case "close_panel": {
      const panel = str(input, "panel");
      if (panel) {
        useWorkspaceStore.getState().closePanel(panel);
        return `Closed ${panelLabel(panel)}`;
      }
      return null;
    }
    case "focus_panel": {
      const panel = str(input, "panel");
      if (!panel) {
        return null;
      }
      const ws = useWorkspaceStore.getState();
      const target = ws.dockviewApi?.getPanel(panel);
      if (target) {
        target.api.setActive();
      } else {
        // Not open yet — opening a singleton focuses it.
        ws.openPanel(panel);
      }
      return `Focused ${panelLabel(panel)}`;
    }
    case "arrange_layout": {
      const ws = useWorkspaceStore.getState();
      const pattern = str(input, "pattern") || "default";
      if (pattern === "focus") {
        const panel = str(input, "panel");
        const target = panel ? ws.dockviewApi?.getPanel(panel) : null;
        if (!target) {
          return null;
        }
        target.api.setActive();
        target.api.maximize();
        return `Focused on ${panelLabel(panel)}`;
      }
      // CUSTOM arrange (Track B): "put the chart here and news there". Triggered
      // by pattern="custom" OR a `panels` arg on any pattern. The host lays the
      // named panels out coherently (or honours explicit per-panel directions) —
      // the dockview engine already supports arbitrary placement.
      const customPanels = parseCustomPanels(input);
      if (pattern === "custom" || customPanels.length > 0) {
        const api = ws.dockviewApi;
        if (!api) {
          return null;
        }
        const sym = str(input, "symbol");
        applyCustomLayout(api, customPanels, { symbol: sym || undefined });
        if (sym) {
          useChartCommandStore.getState().loadSymbol(sym);
        }
        const names = customPanels.map((p) => p.panel).join(" + ");
        return names ? `Arranged ${names}` : "Arranged your panels";
      }
      if (LAYOUT_TEMPLATES.has(pattern)) {
        const api = ws.dockviewApi;
        if (!api) {
          return null;
        }
        const sym = str(input, "symbol");
        const syms = strArray(input, "symbols");
        // Fit-aware (Track 4): on a narrow display a panel-heavy template is
        // downgraded to a layout that actually fits (research → chart + brief).
        const fit = fitLayoutTemplate(api, pattern as LayoutTemplate, {
          symbol: sym || undefined,
          symbols: syms.length ? syms : undefined,
        });
        // The layout is symbol-agnostic — push symbols to the chart via the
        // chart-command channel (compare = symbol A loaded + symbol B overlaid).
        const cc = useChartCommandStore.getState();
        if (pattern === "compare" && syms.length >= 2) {
          cc.loadSymbol(syms[0]);
          cc.setComparison(syms[1]);
        } else if (sym) {
          cc.loadSymbol(sym);
        } else if (syms[0]) {
          cc.loadSymbol(syms[0]);
        }
        if (fit.downgraded) {
          return fit.applied === "essentials-research"
            ? "Arranged the essentials (chart + brief) to fit your screen — click any ticker to go deeper"
            : "Arranged a single-focus layout to fit your screen";
        }
        const label =
          pattern === "research-cockpit" ? "research cockpit" : pattern.replace("-", " ");
        return `Arranged the ${label} layout`;
      }
      ws.resetToDefaultLayout();
      return "Reset to the default layout";
    }
    case "publish_brief": {
      const brief = briefFromInput(input);
      // Allow a structured-only seed (the FAST auto-publish carries live metrics
      // before the model writes the prose); reject only a truly empty brief.
      if (!brief.markdown.trim() && !brief.structured) {
        return null;
      }
      // Open the brief panel so the B+A output is on screen, then publish.
      useWorkspaceStore.getState().openPanel("brief");
      useBriefStore.getState().setBrief(brief);
      return `Published the ${brief.mode} research brief`;
    }
    case "add_to_watchlist":
      if (symbol) {
        const assetClass = input.asset_class === "crypto" ? "crypto" : "equity";
        useSymbolsStore.getState().addSymbol(symbol, assetClass);
        return `Added ${symbol} to your watchlist`;
      }
      return null;
    default:
      return null;
  }
}

/**
 * Resolve which broker an AI-proposed order targets: an explicit `broker` arg if
 * the model gave one, else the user's currently-connected broker, else `kite`
 * (the reference broker). This avoids blindly routing every order to kite when
 * the user has a different broker connected (the §6.5 dialog still shows the
 * broker and gates placement regardless).
 */
function resolveTargetBroker(input: Record<string, unknown>): BrokerId {
  if (typeof input.broker === "string" && input.broker) {
    return input.broker as BrokerId;
  }
  const connected = useBrokersStore
    .getState()
    .brokers()
    .find((b) => b.status === "connected");
  return (connected?.broker ?? "kite") as BrokerId;
}

/**
 * Route an agent-proposed order through the existing §6.5 propose→confirm path
 * (FR-011). POSTs `/brokers/{broker}/orders` with `source="ai-agent"`, then opens
 * the `OrderConfirmationDialog`. The AI NEVER reaches `confirm_and_place` — the
 * dialog's explicit "I reviewed" + Confirm is the only path to placement.
 */
export async function routeOrderProposal(
  input: Record<string, unknown>,
  meta: { agentId?: string; agentName?: string },
): Promise<{ ok: boolean; error?: string }> {
  const broker = resolveTargetBroker(input);
  const symbol = str(input, "symbol");
  const side = str(input, "side");
  const type = str(input, "order_type") || "market";
  const quantity = num(input, "quantity");
  const limitPrice = typeof input.limit_price === "number" ? input.limit_price : undefined;
  try {
    const base = await getSidecarBaseUrl();
    const response = await fetch(
      new URL(`/brokers/${encodeURIComponent(broker)}/orders`, base).toString(),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          side,
          type,
          quantity,
          limitPrice,
          source: "ai-agent",
          sourceDetails: { agentId: meta.agentId, agentName: meta.agentName },
        }),
      },
    );
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail !== undefined) {
          detail = body.detail;
        }
      } catch {
        // ignore non-JSON body
      }
      return { ok: false, error: detail };
    }
    const proposal = (await response.json()) as BrokerOrderProposal;
    useOrdersStore.getState().addProposal(proposal);
    useOrdersStore.getState().openProposal(proposal.proposalId);
    return { ok: true };
  } catch (err: unknown) {
    return { ok: false, error: err instanceof Error ? err.message : "Order proposal failed" };
  }
}
