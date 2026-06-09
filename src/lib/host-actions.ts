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
  briefDepthTier,
  dedupeSources,
  normalizeBriefDepth,
  normalizeBriefMode,
} from "@/lib/brief-ingest";
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
import { useEquityCommandStore } from "@/store/equity-command";
import { useOrdersStore } from "@/store/orders";
import { useScreenerStore } from "@/store/screener";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";

import type { BrokerId, BrokerOrderProposal } from "../../types/broker";
import type {
  BriefDepth,
  BriefSource,
  BriefSourceType,
  BriefStep,
  BriefStructured,
  ResearchBriefData,
} from "../../types/brief";
import type { ProposedChangeKind } from "../../types/proposed-change";
import type { CriterionGroup, ScreenerCriterion, ScreenerUniverseId } from "../../types/screener";

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
  "write_screener_filters",
  "open_company_overview",
]);

/** Tier order for {@link BriefDepth}: quick < deep < heavy. Drives the MAX-tier
 *  pick when a re-publish carries an explicit depth, and the "is there an explicit
 *  signal?" check (a model that only writes prose omits both depth + a deep mode). */
const DEPTH_RANK: Record<BriefDepth, number> = { quick: 0, deep: 1, heavy: 2 };

/**
 * Resolve the brief's depth TIER, carrying the prior run's tier across a
 * depth-less re-publish — the exact mirror of the structured-bundle carry-over
 * below (same 20s/same-symbol recency guard). The bug it fixes (#5): the runtime
 * auto-publish stamps the real tier (e.g. `heavy`), then the model issues its own
 * `publish_brief` carrying only prose — no `depth`, no deep `mode` — which used
 * to normalise back to `quick` and clobber the tier, so the brief's "Go all out"
 * affordance reappeared after a heavy run. Now:
 *   - the model gives an EXPLICIT signal (a `depth` arg or a `deep`/`heavy` mode)
 *     → take the MAX of it and the prior same-symbol tier (an escalation can only
 *     deepen, never shallow, and an explicit re-run at the same tier is a no-op);
 *   - the model OMITS depth (re-publish of the same turn) → keep the prior tier.
 * The recency/same-symbol guard is identical to the structured carry so the two
 * never disagree about whether this is the same research turn.
 */
function carryBriefDepth(input: Record<string, unknown>, symbol: string | undefined): BriefDepth {
  const own = normalizeBriefDepth(str(input, "depth"), str(input, "mode"));
  // An explicit signal is a `depth` arg OR a `deep`/`heavy` mode — anything that
  // resolves above `quick`. (`quick` is also the no-signal default, so a bare
  // re-publish is indistinguishable from an explicit `quick` here — and we never
  // want a re-publish to SHALLOW a deeper prior run regardless, so both branches
  // below treat `quick` as "no escalation" and prefer the carried tier.)
  const prev = useBriefStore.getState().brief;
  // Same tier-derivation rule as the chat control + brief mirror (one source of
  // truth — briefDepthTier reads the explicit `depth` with a mode-badge fallback).
  const prevDepth: BriefDepth | undefined = prev ? briefDepthTier(prev) : undefined;
  if (prevDepth === undefined) {
    return own;
  }
  const sameSymbol =
    !!prev?.symbol && !!symbol && prev.symbol.toUpperCase() === symbol.toUpperCase();
  const recent = typeof prev?.createdAt === "number" && Date.now() - prev.createdAt < 20_000;
  // Same research turn? (Same symbol, or the model omitted the symbol on a brief
  // published moments ago — the auto-publish always seeds the CURRENT symbol.)
  if (!(sameSymbol || (!symbol && recent))) {
    return own;
  }
  // Same turn: never shallow the prior tier — take the deeper of the two.
  return DEPTH_RANK[own] >= DEPTH_RANK[prevDepth] ? own : prevDepth;
}

/** Build a frontend ResearchBriefData from a publish_brief tool input.
 *
 * Normalises the mode to the frontend's uppercase FAST|DEEP (the sidecar
 * research models emit lowercase) and reconciles the honest web flag with the
 * ACTUAL source count (WS3): a brief that cited sources is never marked
 * web-unavailable, an explicit `web_available: false` with zero sources still
 * shows the honest "structured data only" banner, and a model that omits the
 * flag does not default-true a sourceless run into implying web ran.
 */
function briefFromInput(input: Record<string, unknown>): ResearchBriefData {
  const rawSources = Array.isArray(input.sources) ? input.sources : [];
  const mapped: BriefSource[] = rawSources
    .filter((s): s is Record<string, unknown> => typeof s === "object" && s !== null)
    .map((s): BriefSource => {
      const st: unknown = s.source_type ?? s.sourceType;
      const sourceType: BriefSourceType | undefined =
        st === "news" || st === "research" || st === "filing" || st === "web" ? st : undefined;
      return {
        url: typeof s.url === "string" ? s.url : "",
        title: typeof s.title === "string" ? s.title : typeof s.url === "string" ? s.url : "",
        excerpt: typeof s.excerpt === "string" ? s.excerpt : "",
        domain: typeof s.domain === "string" ? s.domain : undefined,
        sourceType,
      };
    })
    .filter((s) => s.url);
  // De-duplicate by URL at the ingest boundary so a repeated citation never
  // shows twice in the rail (the markdown's [n] markers point at the first).
  const sources = dedupeSources(mapped);
  const symbol = str(input, "symbol") || undefined;
  // The true depth TIER (FR-115): prefer the explicit `depth` the auto-publish
  // sets; else derive it from the mode ("heavy"/"deep" → DEEP tier, else quick).
  // Drives the brief panel's in-place "Go deeper" escalation. The mode BADGE
  // then collapses the three tiers to FAST|DEEP — also fixing the S-6 casing
  // miss where a lowercase "deep"/"heavy" never matched the uppercase badge.
  // `carryBriefDepth` MIRRORS the structured carry-over below: a depth-less
  // model re-publish keeps the prior run's tier (so a heavy run isn't clobbered
  // back to quick — fixing the "Go all out reappears after a deep report" bug),
  // and an explicit re-publish takes the MAX tier for the same symbol.
  const depth: BriefDepth = carryBriefDepth(input, symbol);
  const mode = normalizeBriefMode(depth === "quick" ? "fast" : "deep");
  const cost =
    typeof input.cost === "object" && input.cost !== null
      ? (input.cost as { tokens?: number; spendUsd?: number; spend_usd?: number })
      : undefined;
  const steps = Array.isArray(input.steps) ? (input.steps as BriefStep[]) : undefined;
  // The provenance-tagged structured bundle (price/fundamentals/news/filings)
  // backs the native metric cards. Passed through verbatim when present — it is
  // non-secret research data, the same shape the sidecar's ResearchBrief emits.
  // Absent on older briefs / structured-only runs → the panel renders no cards.
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
    // Tight 20s window (was 120s): the auto-publish → model publish_brief round-trip
    // is a few seconds, so 20s safely covers the same turn while shrinking the
    // cross-symbol contamination window 6x (AAPL then MSFT within seconds).
    const recent = typeof prev?.createdAt === "number" && Date.now() - prev.createdAt < 20_000;
    if (prev?.structured && (sameSymbol || (!symbol && recent))) {
      structured = prev.structured;
    }
  }
  // webAvailable, reconciled with the ACTUAL evidence (WS3 — kills symptom #2,
  // the "N sources" + "web unavailable" banner firing together):
  //  - any cited source (web OR native-search / publish_brief url_citation that
  //    folded into `sources`) ⇒ TRUE. A sourced brief is NEVER false-flagged,
  //    and when WS5 lands a successful native search clears the banner for free.
  //  - explicit `web_available: false` with ZERO sources ⇒ FALSE (a real outage
  //    is honoured — the honest "structured data only" affordance survives).
  //  - the model OMITTING the flag does NOT default-true: with no sources it
  //    derives FALSE from the (lack of) evidence rather than implying web ran.
  // TRUE iff a source was cited (web OR structured/native) OR the pipeline
  // explicitly affirmed web; an omitted flag with zero sources stays FALSE (no
  // default-true), an explicit false with zero sources stays FALSE (real outage).
  const webAvailable = sources.length > 0 || input.web_available === true;
  return {
    query: str(input, "query"),
    symbol,
    mode,
    depth,
    markdown: str(input, "markdown"),
    sources,
    sourceCount: sources.length,
    cost: cost ? { tokens: cost.tokens, spendUsd: cost.spendUsd ?? cost.spend_usd } : undefined,
    webAvailable,
    webReason: str(input, "web_reason") || undefined,
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

/**
 * Open the Equity Overview for a company via the always-consumed equity-command
 * channel — the shared "click any company anywhere → the full overview" path
 * behind a screener row, a watchlist entry, a brief ticker chip, and a ⌘K symbol
 * pick. Opens the (singleton) panel first so the command has a consumer, then
 * commands it. Reuses the keyless yfinance overview endpoints — no key required.
 */
export function openCompanyOverview(symbol: string, highlightMetric?: string): void {
  if (!symbol) {
    return;
  }
  const ws = useWorkspaceStore.getState();
  const api = ws.dockviewApi;
  const hasPanel = api?.panels.some((p) => p.api.component === "equity-overview-panel") ?? false;
  if (!hasPanel) {
    ws.openPanel("equity-overview");
  }
  useEquityCommandStore.getState().loadSymbol(symbol, highlightMetric);
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

const _SCREENER_UNIVERSES: ReadonlySet<string> = new Set([
  "sp500",
  "nifty50",
  "crypto-top50",
  "custom",
]);

/**
 * Coerce one loosely-typed object the agent emitted into a `ScreenerCriterion`.
 * The agent JSON isn't a discriminated union, so we keep only well-formed leaves
 * (a numeric `value` for thresholds / a {min,max} for between / a string for eq /
 * a string[] for in). Returns null for anything malformed so a sloppy arg never
 * crashes the apply.
 */
function parseScreenerCriterion(raw: unknown): ScreenerCriterion | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  const field = typeof o.field === "string" ? o.field : "";
  const operator = typeof o.operator === "string" ? o.operator : "";
  if (!field || !operator) {
    return null;
  }
  if (operator === "gt" || operator === "lt" || operator === "gte" || operator === "lte") {
    if (typeof o.value !== "number") {
      return null;
    }
    return { field, operator, value: o.value } as ScreenerCriterion;
  }
  if (operator === "between") {
    const v = o.value;
    if (v && typeof v === "object") {
      const vo = v as Record<string, unknown>;
      if (typeof vo.min === "number" && typeof vo.max === "number") {
        return {
          field,
          operator: "between",
          value: { min: vo.min, max: vo.max },
        } as ScreenerCriterion;
      }
    }
    return null;
  }
  if (operator === "eq") {
    if (typeof o.value !== "string") {
      return null;
    }
    return { field, operator: "eq", value: o.value } as ScreenerCriterion;
  }
  if (operator === "in") {
    const arr = Array.isArray(o.value)
      ? o.value.filter((x): x is string => typeof x === "string")
      : [];
    if (arr.length === 0) {
      return null;
    }
    return { field, operator: "in", value: arr } as ScreenerCriterion;
  }
  return null;
}

/** Parse a flat `criteria` array arg into well-formed leaves. */
function parseScreenerCriteria(input: Record<string, unknown>): ScreenerCriterion[] {
  const raw = input.criteria;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map(parseScreenerCriterion).filter((c): c is ScreenerCriterion => c !== null);
}

/**
 * Parse a loosely-typed nested AND/OR `group` tree (the agent's JSON) into a
 * `CriterionGroup`, dropping malformed children. Recurses on sub-groups. Returns
 * null when absent or it collapses to nothing.
 */
function parseScreenerGroup(raw: unknown): CriterionGroup | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  const combinator = o.combinator === "or" ? "or" : "and";
  const rawChildren = Array.isArray(o.criteria) ? o.criteria : [];
  const criteria: (ScreenerCriterion | CriterionGroup)[] = [];
  for (const child of rawChildren) {
    if (child && typeof child === "object" && "combinator" in (child as object)) {
      const sub = parseScreenerGroup(child);
      if (sub) {
        criteria.push(sub);
      }
    } else {
      const leaf = parseScreenerCriterion(child);
      if (leaf) {
        criteria.push(leaf);
      }
    }
  }
  if (criteria.length === 0) {
    return null;
  }
  return { combinator, criteria };
}

/** Count leaves in a (possibly nested) group tree — for the diff summary. */
function countLeaves(node: ScreenerCriterion | CriterionGroup): number {
  if ("combinator" in node) {
    return node.criteria.reduce((acc, c) => acc + countLeaves(c), 0);
  }
  return 1;
}

/**
 * Ensure a chart panel is open so a chart command (symbol / indicators) has a
 * consumer. A bare `set_chart_symbol` on an empty cockpit otherwise lands in the
 * chart-command channel with no chart panel reading it — the symbol "doesn't
 * take" (the AUTO-mode "no panels open yet" failure). Checks by COMPONENT, so it
 * detects the chart whether it carries the literal `chart` id (singleton) or a
 * legacy generated `chart-<id>` from a pre-singleton workspace blob.
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
    case "open_company_overview": {
      const sym = str(input, "symbol");
      const metric = str(input, "highlight");
      return {
        kind: "panel",
        title: metric
          ? `Show ${sym || "the company"}'s ${metric.replace(/_/g, " ")} in the overview`
          : `Open ${sym || "the company"}'s overview`,
        before: "Equity Overview: previous company (if any)",
        after: `Equity Overview: ${sym || "the company"}${metric ? ` · ${metric.replace(/_/g, " ")} spotlighted` : ""}`,
      };
    }
    case "publish_brief": {
      const sources = Array.isArray(input.sources) ? input.sources : [];
      const mode = normalizeBriefMode(str(input, "depth") || str(input, "mode"));
      // structured-data-only is honest ONLY with zero cited sources: a sourced
      // brief is never tagged structured-only even if the model omitted/zeroed the
      // web flag (WS3 — no contradictory "N sources · structured-data-only").
      const webOff = input.web_available === false && sources.length === 0;
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
    case "write_screener_filters": {
      const s = useScreenerStore.getState();
      const currentCount = s.advanced && s.group ? countLeaves(s.group) : s.criteria.length;
      const group = parseScreenerGroup(input.group);
      const criteria = parseScreenerCriteria(input);
      const proposedCount = group ? countLeaves(group) : criteria.length;
      const nested =
        group && group.criteria.some((c) => "combinator" in c) ? " (nested AND/OR)" : "";
      const universe = typeof input.universe === "string" ? input.universe : "";
      return {
        kind: "panel",
        title: "Write screener filters",
        before: `Screener: ${currentCount} criteri${currentCount === 1 ? "on" : "a"}`,
        after: `Screener: ${proposedCount} criteri${proposedCount === 1 ? "on" : "a"}${nested}${
          universe && _SCREENER_UNIVERSES.has(universe) ? ` · ${universe}` : ""
        } — review then Run`,
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
    case "open_company_overview": {
      const sym = str(input, "symbol");
      if (!sym) {
        return null;
      }
      const metric = str(input, "highlight");
      openCompanyOverview(sym, metric || undefined);
      return metric
        ? `Opened ${sym}'s overview — spotlighting ${metric.replace(/_/g, " ")}`
        : `Opened ${sym}'s overview`;
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
    case "write_screener_filters": {
      const criteria = parseScreenerCriteria(input);
      const group = parseScreenerGroup(input.group);
      // Need at least one well-formed criterion (flat OR nested) to write.
      if (criteria.length === 0 && !group) {
        return null;
      }
      const universe =
        typeof input.universe === "string" && _SCREENER_UNIVERSES.has(input.universe)
          ? (input.universe as ScreenerUniverseId)
          : undefined;
      // When the agent gives only a nested group, mirror its leaves into the
      // flat `criteria` too so older readers + the match-index column resolve.
      const flat = criteria.length ? criteria : group ? flattenLeaves(group) : [];
      useScreenerStore.getState().applyFilters({ criteria: flat, group, universe });
      // Stage the panel so the proposed filters are on screen for the user to Run.
      // The screener module REGISTERS id "screener-panel" — the bare "screener"
      // id silently no-opped here (same drift class as the arrange map).
      useWorkspaceStore.getState().openPanel("screener-panel");
      const count = group ? countLeaves(group) : criteria.length;
      return `Wrote ${count} screener criteri${count === 1 ? "on" : "a"} — review and Run`;
    }
    default:
      return null;
  }
}

/** Collect every leaf criterion from a (possibly nested) group, in order. */
function flattenLeaves(group: CriterionGroup): ScreenerCriterion[] {
  const out: ScreenerCriterion[] = [];
  for (const child of group.criteria) {
    if ("combinator" in child) {
      out.push(...flattenLeaves(child));
    } else {
      out.push(child);
    }
  }
  return out;
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
