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
  depthFromExecution,
  disambiguationFromWire,
  executionFromWire,
  normalizeBriefDepth,
  normalizeBriefMode,
} from "@/lib/brief-ingest";
import {
  applyContentAwareLayout,
  applyCustomLayout,
  fitLayoutTemplate,
  resolvePanelToken,
  type CustomPanelSpec,
  type LayoutTemplate,
} from "@/lib/layout-templates";
import { regionConfig, isRegion, type Region } from "@/lib/region";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { saveWorkspace } from "@/lib/workspace";
import { useBriefStore } from "@/store/brief";
import { useNotesStore } from "@/store/notes";
import { useBrokersStore } from "@/store/brokers";
import { useChartCommandStore } from "@/store/chart-command";
import { useEquityCommandStore } from "@/store/equity-command";
import { useOrdersStore } from "@/store/orders";
import { usePortfoliosStore, type AssetClass, type Holding } from "@/store/portfolios";
import { useScreenerStore } from "@/store/screener";
import { useSettingsStore } from "@/store/settings";
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

/** The catalog host-action tool ids (`kind="host_action"`, `read_only=false`).
 *  R10 (D41/E6) adds the data-write family (paper-portfolio positions, notes,
 *  saved screens, layout save), the watchlist remove, and the ONE settings
 *  action the agent may drive (`set_region` — D45). Names are EXACT catalog
 *  ids; Team RUNTIME's toolbelt-integrity test asserts set-equality. */
export const HOST_ACTION_NAMES = new Set([
  "open_panel",
  "close_panel",
  "focus_panel",
  "arrange_layout",
  "set_chart_symbol",
  "set_chart_indicators",
  "add_to_watchlist",
  "remove_from_watchlist",
  "publish_brief",
  "propose_order",
  "write_screener_filters",
  "open_company_overview",
  "portfolio_add_position",
  "portfolio_update_position",
  "portfolio_delete_position",
  "write_note",
  "save_layout",
  "save_screen",
  "set_region",
]);

/** Tier order for {@link BriefDepth}: quick < deep < heavy. Drives the MAX-tier
 *  pick when a re-publish carries an explicit depth, and the "is there an explicit
 *  signal?" check (a model that only writes prose omits both depth + a deep mode). */
const DEPTH_RANK: Record<BriefDepth, number> = { quick: 0, deep: 1, heavy: 2 };

/**
 * Resolve a LEGACY (execution-less) brief's depth TIER, carrying the prior
 * run's tier across a depth-less SAME-SYMBOL re-publish. The bug it fixes
 * (#5): the runtime auto-publish stamps the real tier (e.g. `heavy`), then the
 * model issues its own `publish_brief` carrying only prose — no `depth`, no
 * deep `mode` — which used to normalise back to `quick` and clobber the tier,
 * so the brief's "Go all out" affordance reappeared after a heavy run. The
 * R10 rule (D38): a brief WITH an execution record derives its tier from the
 * loop that ran and never reaches this helper; the same-symbol MAX-tier carry
 * survives for legacy inputs only. The 20s wall-clock recency branch is DEAD —
 * a symbol-less artifact can no longer inherit another entity's tier (E3.2).
 */
function carryBriefDepth(input: Record<string, unknown>, symbol: string | undefined): BriefDepth {
  const own = normalizeBriefDepth(str(input, "depth"), str(input, "mode"));
  const prev = useBriefStore.getState().brief;
  // Same tier-derivation rule as the chat control + brief mirror (one source of
  // truth — briefDepthTier reads the explicit `depth` with a mode-badge fallback).
  const prevDepth: BriefDepth | undefined = prev ? briefDepthTier(prev) : undefined;
  if (prevDepth === undefined) {
    return own;
  }
  const sameSymbol = !!prev?.symbol && !!symbol && baseSymbol(prev.symbol) === baseSymbol(symbol);
  if (!sameSymbol) {
    return own;
  }
  // Same symbol: never shallow the prior tier — take the deeper of the two.
  return DEPTH_RANK[own] >= DEPTH_RANK[prevDepth] ? own : prevDepth;
}

/** Exchange-suffix-insensitive symbol identity ("SAKSOFT" ≡ "SAKSOFT.NS" ≡
 *  "SAKSOFT.BO") — the engine binds the bare NSE/BSE name while panels and the
 *  model often carry the suffixed form; same-turn carries must not miss on it. */
function baseSymbol(value: string | undefined | null): string {
  return (value ?? "")
    .trim()
    .toUpperCase()
    .replace(/\.(NS|BO|NSE|BSE)$/, "");
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
  // The execution record of the run that ACTUALLY RAN (R10, D38) — minted at
  // the sidecar tool boundary, injected by the runtime onto the model's own
  // re-publish. Snake_case wire → camelCase contract in brief-ingest. A brief
  // WITHOUT a valid record is a legacy/archival artifact by definition.
  const execution = executionFromWire(input.execution);
  // The honest "which did you mean?" (D37) — ingested verbatim; the panel
  // renders the candidate chooser instead of a brief body.
  const disambiguation = disambiguationFromWire(input.disambiguation);
  // Depth truth (E2 dead): with an execution record the tier derives ONLY from
  // the loop that ran (fast→quick, iter→deep, heavy→heavy, research-model→
  // stop-based) — the wire `mode` is ignored. Legacy inputs keep the explicit
  // depth/mode derivation with the same-symbol MAX-tier carry (#5).
  const depth: BriefDepth = execution ? depthFromExecution(execution) : carryBriefDepth(input, symbol);
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
  // Carry-over is RUN-SCOPED (E3.2 — the 20s wall-clock window is dead): the
  // engine's auto-publish seeds structured/backend, and the model's same-run
  // re-publish (the runtime injects the same execution record) may omit them.
  // Carry ONLY when this publish's run_id matches the previous brief's
  // execution.runId AND the base symbols match-or-one-absent — a reload, a
  // different run, or a different entity can never inherit another artifact's
  // live metrics again.
  const prevBrief = useBriefStore.getState().brief;
  const symbolsCompatible =
    !symbol || !prevBrief?.symbol || baseSymbol(prevBrief.symbol) === baseSymbol(symbol);
  const runCarry =
    !!execution &&
    !!prevBrief?.execution?.runId &&
    prevBrief.execution.runId === execution.runId &&
    symbolsCompatible;
  if (!structured && prevBrief?.structured && runCarry) {
    structured = prevBrief.structured;
  }
  // The engine's honest backend id (R9: "keyless-fallback" drives the nudge,
  // "research-model:<id>" names the Tier B brain). The execution record names
  // it authoritatively; the same-run carry covers a record that omitted it.
  let backend = str(input, "backend") || execution?.backend || undefined;
  if (!backend && prevBrief?.backend && runCarry) {
    backend = prevBrief.backend;
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
    // See the carry block above — verbatim when sent, same-run carry when the
    // model's own publish omits it.
    backend,
    execution,
    disambiguation,
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
  // R10 (D40): the full India universes from the resolver masters.
  "nse-all",
  "bse-all",
  "india-all",
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

/**
 * Find an OPEN dockview panel for a resolved token — by its registered id
 * first, then by component (robust to a legacy generated id like `chart-<id>`
 * from a pre-singleton workspace blob). Null when the panel is not on screen
 * (or the layout has not mounted yet).
 */
function findOpenPanel(resolved: { id: string; component: string }) {
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    return null;
  }
  return (
    api.getPanel(resolved.id) ??
    api.panels.find((p) => p.api.component === resolved.component) ??
    null
  );
}

/**
 * Which symbol-aware command channel an `open_panel` target consumes, if any.
 * Resolved through the same alias-tolerant token map arrange uses, so
 * "overview" / "equity" route like "equity-overview" does. Panels with no
 * symbol input return null — a stray `symbol` arg on them is ignored.
 */
function symbolAwarePanelTarget(panelToken: string): "equity" | "chart" | null {
  const resolved = resolvePanelToken(panelToken);
  if (!resolved) {
    return null;
  }
  if (resolved.id === "equity-overview") {
    return "equity";
  }
  if (resolved.id === "chart") {
    return "chart";
  }
  return null;
}

/** Human-friendly panel label from a panel id. */
function panelLabel(id: string): string {
  return id.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** The active region's currency sign for human diff copy ("@ ₹1,263"). */
function currencySign(): string {
  const currency = regionConfig(useSettingsStore.getState().region).currency;
  return currency === "INR" ? "₹" : "$";
}

/** "₹1,263" — a human price in the active region's locale + sign. */
function formatPrice(value: number): string {
  const locale = regionConfig(useSettingsStore.getState().region).locale;
  return `${currencySign()}${value.toLocaleString(locale, { maximumFractionDigits: 2 })}`;
}

/** The ACTIVE paper portfolio (the panel's truth — frontend store). */
function activePortfolio() {
  const s = usePortfoliosStore.getState();
  return s.portfolios.find((p) => p.id === s.activeId) ?? s.portfolios[0];
}

/**
 * Resolve the holding a portfolio update/delete targets: an exact holding-id
 * match first (the agent echoes the snapshot's `id` back as `position_id`),
 * else the first same-symbol holding (a sidecar-numbered id never matches a
 * frontend holding id, but the action always names the symbol). Null when
 * nothing matches — an honest failure, never a guessed mutation.
 */
function resolveHolding(input: Record<string, unknown>): Holding | null {
  const portfolio = activePortfolio();
  if (!portfolio) {
    return null;
  }
  const id = input.position_id != null ? String(input.position_id) : "";
  const byId = id ? portfolio.holdings.find((h) => h.id === id) : undefined;
  if (byId) {
    return byId;
  }
  const symbol = str(input, "symbol");
  if (!symbol) {
    return null;
  }
  return portfolio.holdings.find((h) => baseSymbol(h.symbol) === baseSymbol(symbol)) ?? null;
}

/** The note-scope key: "" = the General bucket, else an uppercased ticker. */
function noteScope(input: Record<string, unknown>): string {
  const scope = str(input, "scope").trim();
  return scope.toLowerCase() === "general" ? "" : scope.toUpperCase();
}

/** A short human label for a note scope. */
function noteScopeLabel(scope: string): string {
  return scope === "" ? "General" : scope;
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
      // Render the symbol only when the target panel actually consumes one —
      // the diff must promise exactly what the apply will do.
      const sym = symbolAwarePanelTarget(panel) ? symbol : "";
      return {
        kind: "panel",
        title: `Open ${panelLabel(panel)}${sym ? ` — ${sym}` : ""}`,
        before: `${panelLabel(panel)} panel: not open`,
        after: `${panelLabel(panel)} panel: open${sym ? ` — ${sym} loaded` : ""}`,
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
      if (pattern === "auto") {
        return {
          kind: "panel",
          title: "Arrange your windows around the content",
          before: "Layout: the current cockpit",
          after: "Layout: content-aware (dominant reading panel, wide chart, side rail)",
        };
      }
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
      const formula = str(input, "formula").trim();
      const runs = input.run === true;
      return {
        kind: "panel",
        title: "Write screener filters",
        before: `Screener: ${currentCount} criteri${currentCount === 1 ? "on" : "a"}`,
        after: `Screener: ${proposedCount} criteri${proposedCount === 1 ? "on" : "a"}${nested}${
          universe && _SCREENER_UNIVERSES.has(universe) ? ` · ${universe}` : ""
        }${formula ? " · formula" : ""} — ${runs ? "runs on apply" : "review then Run"}`,
      };
    }
    case "portfolio_add_position": {
      const qty = num(input, "quantity");
      const cost = num(input, "cost_basis");
      const count = activePortfolio()?.holdings.length ?? 0;
      return {
        kind: "data-write",
        title: `Add ${qty || ""} ${symbol}${cost ? ` @ ${formatPrice(cost)}` : ""} to the paper portfolio`
          .replace(/\s+/g, " ")
          .trim(),
        before: `Portfolio: ${count} position${count === 1 ? "" : "s"}`,
        after: `Portfolio: +${symbol} ×${qty} (${count + 1} total)`,
      };
    }
    case "portfolio_update_position": {
      const target = resolveHolding(input);
      const qty = num(input, "quantity");
      const cost = num(input, "cost_basis");
      const label = target?.symbol || symbol || "position";
      return {
        kind: "data-write",
        title: `Update ${label} in the paper portfolio`,
        before: target
          ? `${target.symbol}: ×${target.quantity} @ ${formatPrice(target.costBasis)}`
          : `${label}: not found in the active portfolio`,
        after: `${label}: ×${qty}${cost ? ` @ ${formatPrice(cost)}` : ""}`,
      };
    }
    case "portfolio_delete_position": {
      const target = resolveHolding(input);
      const label = target?.symbol || symbol || "position";
      return {
        kind: "data-write",
        title: `Remove ${label} from the paper portfolio`,
        before: target
          ? `${target.symbol}: ×${target.quantity} @ ${formatPrice(target.costBasis)}`
          : `${label}: not found in the active portfolio`,
        after: `${label}: removed`,
      };
    }
    case "write_note": {
      const scope = noteScope(input);
      const text = str(input, "text");
      const append = str(input, "mode") === "append";
      const current = useNotesStore.getState().noteFor(scope);
      return {
        kind: "data-write",
        title: `${append ? "Append to" : "Write"} the ${noteScopeLabel(scope)} note`,
        before: `${noteScopeLabel(scope)} note: ${current.trim() ? `${current.trim().length} chars` : "empty"}`,
        after: append
          ? `${noteScopeLabel(scope)} note: +${text.trim().length} chars appended`
          : `${noteScopeLabel(scope)} note: replaced (${text.trim().length} chars)`,
      };
    }
    case "remove_from_watchlist": {
      const entries = useSymbolsStore.getState().entries;
      const tracked = entries.some((e) => e.symbol.toUpperCase() === symbol.toUpperCase());
      return {
        kind: "watchlist",
        title: `Remove ${symbol} from your watchlist`,
        before: `Watchlist: ${entries.length} symbol${entries.length === 1 ? "" : "s"}`,
        after: tracked
          ? `Watchlist: −${symbol} (${entries.length - 1} total)`
          : `Watchlist: ${symbol} is not tracked`,
      };
    }
    case "save_layout": {
      const layoutName = str(input, "name").trim() || "Agent layout";
      return {
        kind: "data-write",
        title: `Save the current layout as "${layoutName}"`,
        before: "Saved workspaces: unchanged",
        after: `Saved workspaces: +"${layoutName}" (current cockpit)`,
      };
    }
    case "save_screen": {
      const screenName = str(input, "name").trim() || "Agent screen";
      const leafCount = (() => {
        const group = parseScreenerGroup(input.group);
        if (group) {
          return countLeaves(group);
        }
        const criteria = parseScreenerCriteria(input);
        return criteria.length;
      })();
      return {
        kind: "data-write",
        title: `Save the screen as "${screenName}"`,
        before: "Saved screens: unchanged",
        after: `Saved screens: +"${screenName}"${leafCount ? ` (${leafCount} criteri${leafCount === 1 ? "on" : "a"})` : " (current filters)"}`,
      };
    }
    case "set_region": {
      const current = useSettingsStore.getState().region;
      const next = str(input, "region").toUpperCase();
      return {
        kind: "settings",
        title: `Set the region to ${next || "?"}`,
        before: `Region: ${current}`,
        after: `Region: ${next || current}`,
      };
    }
    default:
      return { kind: "panel", title: name.replace(/_/g, " "), before: "—", after: "—" };
  }
}

/**
 * Apply a non-order host-action mutation to the live stores. Returns a short
 * TRUTHFUL label describing what actually happened, or `null` if it could not
 * apply — the proposed-changes gate re-pends a null and surfaces the failure,
 * so chat/proposal narration never claims an action that did not land
 * (grounded narration, R8 seams deliverable 5). No branch may return a
 * success label without having done (or verified) the work: an unknown panel
 * id, a panel that failed to open, or incomplete arguments all return null.
 * Orders are NOT applied here — they route through `routeOrderProposal` →
 * the §6.5 dialog.
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
      if (!panel) {
        return null;
      }
      // Resolve through the alias-tolerant token map (the same one arrange
      // uses) so "screener" opens the registered "screener-panel" instead of
      // silently no-opping — the id-drift class the screener fix documented.
      // An UNRESOLVABLE token returns null: an honest "could not apply" beats
      // a fake "Opened X" (grounded narration).
      const resolved = resolvePanelToken(panel);
      if (!resolved) {
        return null;
      }
      // Symbol-aware open (the "opened equity-overview WITHOUT the requested
      // symbol" fix): when the agent passes `symbol` for a panel that consumes
      // one, route it through the existing always-consumed command channels —
      // the equity-command store for the overview, the chart-command channel
      // for the chart. Both helpers open the panel first so the command has a
      // consumer; the stores RETAIN the last command, so a panel that mounts
      // after the command fired still receives it.
      const target = symbolAwarePanelTarget(panel);
      if (symbol && target === "equity") {
        openCompanyOverview(symbol);
        return `Opened ${panelLabel(panel)} — ${symbol}`;
      }
      if (symbol && target === "chart") {
        loadSymbolIntoChart(symbol);
        return `Opened ${panelLabel(panel)} — ${symbol}`;
      }
      const ws = useWorkspaceStore.getState();
      ws.openPanel(resolved.id);
      // Verify the open actually landed when a live layout is on screen — a
      // disabled module (findPanel miss) used to no-op while this still
      // claimed "Opened". With no api yet (pre-mount) the claim is left
      // optimistic; a mounted cockpit is the only place proposals apply.
      if (ws.dockviewApi && !findOpenPanel(resolved)) {
        return null;
      }
      return `Opened ${panelLabel(panel)}`;
    }
    case "close_panel": {
      const panel = str(input, "panel");
      if (!panel) {
        return null;
      }
      const resolved = resolvePanelToken(panel);
      if (!resolved) {
        return null; // unknown panel id — never narrate a fake "Closed"
      }
      const target = findOpenPanel(resolved);
      if (!target) {
        // Truthful idempotent no-op: the desired end state already holds.
        return `${panelLabel(panel)} was already closed`;
      }
      target.api.close();
      return `Closed ${panelLabel(panel)}`;
    }
    case "focus_panel": {
      const panel = str(input, "panel");
      if (!panel) {
        return null;
      }
      const resolved = resolvePanelToken(panel);
      if (!resolved) {
        return null; // unknown panel id — honest failure
      }
      const target = findOpenPanel(resolved);
      if (target) {
        target.api.setActive();
        return `Focused ${panelLabel(panel)}`;
      }
      // Not open yet — opening a singleton focuses it. Verify it landed so a
      // disabled module never narrates a focus that did not happen.
      const ws = useWorkspaceStore.getState();
      ws.openPanel(resolved.id);
      if (ws.dockviewApi && !findOpenPanel(resolved)) {
        return null;
      }
      return `Opened and focused ${panelLabel(panel)}`;
    }
    case "arrange_layout": {
      const ws = useWorkspaceStore.getState();
      const pattern = str(input, "pattern") || "default";
      // CONTENT-AWARE (R9, gate 11): arrange the OPEN panels the way a person
      // would — the planner ranks live content (a published brief dominates,
      // the chart gets width, the watchlist parks in a rail). Deterministic;
      // never opens or closes a panel.
      if (pattern === "auto") {
        const api = ws.dockviewApi;
        if (!api) {
          return null;
        }
        const signals = {
          briefChars: useBriefStore.getState().brief?.markdown?.length ?? 0,
          notesChars: useNotesStore.getState().general.length,
          watchlistRows: useSymbolsStore.getState().entries.length,
        };
        const result = applyContentAwareLayout(api, signals);
        if (result.count === 0) {
          return null;
        }
        return result.count === 1
          ? `Focused ${panelLabel(result.anchor ?? "")} — it's the only panel open`
          : `Arranged ${result.count} windows around ${panelLabel(result.anchor ?? "")}`;
      }
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
      // before the model writes the prose) and a disambiguation-only publish
      // (the chooser renders instead of a body); reject only a truly empty brief.
      if (!brief.markdown.trim() && !brief.structured && !brief.disambiguation) {
        return null;
      }
      // R9 (D33), R10-scoped: a SAME-RUN re-publish that STRICTLY SHRINKS the
      // brief is a downgrade — the deep engine's cited report must not be
      // replaced by the model's shorter, less-cited summary of the same run.
      // Scope is the execution run_id (the 20s wall-clock window is dead): the
      // runtime injects the run's record onto the model's own publish, so the
      // same-turn pair always shares one run_id. The model's narrative still
      // reads in chat; the panel keeps the richer artifact. Whole-brief
      // decision only (never merge two markdowns — the [n] markers must stay
      // coherent with their sources). The apply path reports kept_previous
      // through the ack (D39 §4) via the "Kept …" label.
      const prev = useBriefStore.getState().brief;
      const sameRun =
        !!prev?.execution?.runId &&
        !!brief.execution?.runId &&
        prev.execution.runId === brief.execution.runId;
      const shrinks =
        !!prev &&
        ((brief.sourceCount < prev.sourceCount &&
          brief.markdown.trim().length < (prev.markdown ?? "").trim().length) ||
          // A source-LESS re-publish over a sourced brief is a downgrade no
          // matter how long its prose runs — citations are the product.
          (brief.sourceCount === 0 && prev.sourceCount > 0));
      if (sameRun && shrinks && !brief.disambiguation) {
        useWorkspaceStore.getState().openPanel("brief");
        return "Kept the richer research brief already on screen";
      }
      // Open the brief panel so the output is on screen, then publish through
      // the lifecycle machine — a publish whose run_id mismatches the run in
      // flight is ignored as stale (E3.2) and reports kept_previous.
      useWorkspaceStore.getState().openPanel("brief");
      const result = useBriefStore.getState().publish(brief);
      if (result === "stale_run") {
        return "Kept the run in flight — this publish belonged to a different run";
      }
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
      const formula = str(input, "formula").trim();
      // Need at least one well-formed criterion (flat OR nested) or a formula.
      if (criteria.length === 0 && !group && !formula) {
        return null;
      }
      const universe =
        typeof input.universe === "string" && _SCREENER_UNIVERSES.has(input.universe)
          ? (input.universe as ScreenerUniverseId)
          : undefined;
      // When the agent gives only a nested group, mirror its leaves into the
      // flat `criteria` too so older readers + the match-index column resolve.
      const flat = criteria.length ? criteria : group ? flattenLeaves(group) : [];
      const screener = useScreenerStore.getState();
      // `formula`/`run` pass through to the store's applyFilters (R10 — Team
      // FRONTEND-DATA extends the input type in the same wave; the cast keeps
      // the two branches integrable without a cross-team type dependency).
      screener.applyFilters({
        criteria: flat,
        group,
        universe,
        ...(formula ? { formula } : {}),
        ...(input.run === true ? { run: true } : {}),
      } as Parameters<typeof screener.applyFilters>[0]);
      // Stage the panel so the proposed filters are on screen for the user to Run.
      // The screener module REGISTERS id "screener-panel" — the bare "screener"
      // id silently no-opped here (same drift class as the arrange map).
      useWorkspaceStore.getState().openPanel("screener-panel");
      const count = group ? countLeaves(group) : criteria.length;
      const what = count
        ? `${count} screener criteri${count === 1 ? "on" : "a"}${formula ? " + a formula" : ""}`
        : "a screener formula";
      return `Wrote ${what} — ${input.run === true ? "running" : "review and Run"}`;
    }
    case "write_note": {
      const scope = noteScope(input);
      const text = str(input, "text");
      if (!text.trim()) {
        return null;
      }
      const notes = useNotesStore.getState();
      const append = str(input, "mode") === "append";
      const current = notes.noteFor(scope);
      const next = append && current.trim() ? `${current.replace(/\s+$/, "")}\n\n${text}` : text;
      if (scope === "") {
        notes.setGeneral(next);
      } else {
        notes.setSymbolNote(scope, next);
      }
      useWorkspaceStore.getState().openPanel("notes");
      return `${append ? "Appended to" : "Wrote"} the ${noteScopeLabel(scope)} note`;
    }
    case "remove_from_watchlist": {
      if (!symbol) {
        return null;
      }
      const symbols = useSymbolsStore.getState();
      const tracked = symbols.entries.some((e) => e.symbol.toUpperCase() === symbol.toUpperCase());
      if (!tracked) {
        // Truthful idempotent no-op: the desired end state already holds.
        return `${symbol.toUpperCase()} was not on your watchlist`;
      }
      symbols.removeSymbol(symbol);
      return `Removed ${symbol.toUpperCase()} from your watchlist`;
    }
    case "save_screen": {
      const screenName = str(input, "name").trim();
      if (!screenName) {
        return null;
      }
      // Delegate to the screener store's saved-screens API (Team FRONTEND-DATA
      // ships `saveScreen` in the same wave). The duck-typed seam keeps the two
      // branches independently green; until the API lands the action returns
      // an honest null (re-pends) instead of narrating a save that never was.
      const screener = useScreenerStore.getState() as unknown as {
        saveScreen?: (name: string, payload: Record<string, unknown>) => unknown;
      };
      if (typeof screener.saveScreen !== "function") {
        return null;
      }
      const group = parseScreenerGroup(input.group);
      const criteria = parseScreenerCriteria(input);
      const formula = str(input, "formula").trim();
      const universe =
        typeof input.universe === "string" && _SCREENER_UNIVERSES.has(input.universe)
          ? input.universe
          : undefined;
      screener.saveScreen(screenName, {
        ...(criteria.length ? { criteria } : {}),
        ...(group ? { group } : {}),
        ...(formula ? { formula } : {}),
        ...(universe ? { universe } : {}),
      });
      return `Saved the screen as "${screenName}"`;
    }
    case "set_region": {
      const next = str(input, "region").toUpperCase();
      if (!isRegion(next)) {
        return null;
      }
      useSettingsStore.getState().setRegion(next as Region);
      return `Set the region to ${next}`;
    }
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Async apply seam + publish ack (R10 §3/§4)
// ---------------------------------------------------------------------------

/** The paper-portfolio positions endpoint (sidecar SQLite ledger). */
async function portfolioUrl(id?: number): Promise<string> {
  const base = await getSidecarBaseUrl();
  const path = id === undefined ? "/portfolio/positions" : `/portfolio/positions/${id}`;
  return new URL(path, base).toString();
}

/** The wire body the sidecar's PositionInput expects (snake_case). */
function positionBody(input: Record<string, unknown>, fallback?: Holding) {
  const symbol = (str(input, "symbol") || fallback?.symbol || "").toUpperCase();
  const quantity = typeof input.quantity === "number" ? input.quantity : (fallback?.quantity ?? 0);
  const costBasis =
    typeof input.cost_basis === "number" ? input.cost_basis : (fallback?.costBasis ?? 0);
  const assetClass: AssetClass = (input.asset_class ?? fallback?.assetClass) === "crypto"
    ? "crypto"
    : "equity";
  const note = str(input, "note") || fallback?.note;
  return { symbol, quantity, costBasis, assetClass, note };
}

/** Best-effort sidecar ledger sync — the frontend store is the panel's truth
 *  (it feeds the panel, the workspace blob, and get_portfolio's snapshot); the
 *  sidecar positions table is a secondary ledger kept in sync per the wire
 *  contract. A sidecar miss is tolerated: the user's visible change must not
 *  fail over a ledger no surface reads (the store mutation IS the apply). */
async function syncPositionToSidecar(
  method: "POST" | "PUT" | "DELETE",
  body: ReturnType<typeof positionBody> | null,
  id?: number,
): Promise<boolean> {
  try {
    const response = await fetch(await portfolioUrl(id), {
      method,
      headers: { "Content-Type": "application/json" },
      ...(body
        ? {
            body: JSON.stringify({
              symbol: body.symbol,
              quantity: body.quantity,
              cost_basis: body.costBasis,
              asset_class: body.assetClass,
              ...(body.note ? { note: body.note } : {}),
            }),
          }
        : {}),
    });
    // A 404 on update/delete means the sidecar ledger never had this row (it
    // is written only through this path) — the frontend store remains the
    // truth, so the miss is tolerated rather than failing the user's change.
    return response.ok || response.status === 404;
  } catch {
    return false;
  }
}

/** A numeric sidecar position id from the agent's `position_id`, when it is one. */
function sidecarPositionId(input: Record<string, unknown>): number | undefined {
  const raw = input.position_id;
  const n = typeof raw === "number" ? raw : Number(raw);
  return Number.isInteger(n) && n >= 0 ? n : undefined;
}

/**
 * Apply a host-action mutation, including the network-backed cases (paper
 * portfolio writes ride POST/PUT/DELETE `/portfolio/positions` and mirror into
 * the portfolios store — the truth every surface reads; `save_layout` awaits
 * the workspace save). Everything else delegates to the synchronous
 * {@link applyHostAction}. Same truth contract: a string label means the work
 * landed; null re-pends with an honest failure.
 */
export async function applyHostActionAsync(
  name: string,
  input: Record<string, unknown>,
): Promise<string | null> {
  switch (name) {
    case "portfolio_add_position": {
      const body = positionBody(input);
      if (!body.symbol || !(body.quantity > 0)) {
        return null;
      }
      await syncPositionToSidecar("POST", body);
      const portfolio = activePortfolio();
      if (!portfolio) {
        return null;
      }
      usePortfoliosStore.getState().addHolding(portfolio.id, {
        symbol: body.symbol,
        quantity: body.quantity,
        costBasis: body.costBasis,
        assetClass: body.assetClass,
        note: body.note,
      });
      useWorkspaceStore.getState().openPanel("portfolio");
      return `Added ${body.quantity} ${body.symbol} @ ${formatPrice(body.costBasis)} to the paper portfolio`;
    }
    case "portfolio_update_position": {
      const target = resolveHolding(input);
      if (!target) {
        return null; // never guess which position to mutate
      }
      const body = positionBody(input, target);
      if (!(body.quantity > 0)) {
        return null;
      }
      await syncPositionToSidecar("PUT", body, sidecarPositionId(input));
      const portfolio = activePortfolio();
      if (!portfolio) {
        return null;
      }
      usePortfoliosStore.getState().updateHolding(portfolio.id, target.id, {
        symbol: body.symbol,
        quantity: body.quantity,
        costBasis: body.costBasis,
        assetClass: body.assetClass,
        note: body.note,
      });
      useWorkspaceStore.getState().openPanel("portfolio");
      return `Updated ${body.symbol}: ×${body.quantity} @ ${formatPrice(body.costBasis)}`;
    }
    case "portfolio_delete_position": {
      const target = resolveHolding(input);
      if (!target) {
        return null;
      }
      await syncPositionToSidecar("DELETE", null, sidecarPositionId(input));
      const portfolio = activePortfolio();
      if (!portfolio) {
        return null;
      }
      usePortfoliosStore.getState().removeHolding(portfolio.id, target.id);
      useWorkspaceStore.getState().openPanel("portfolio");
      return `Removed ${target.symbol} from the paper portfolio`;
    }
    case "save_layout": {
      const layoutName = str(input, "name").trim() || "Agent layout";
      try {
        await saveWorkspace(layoutName);
      } catch {
        return null; // layout not mounted / sidecar down — honest failure
      }
      return `Saved the layout as "${layoutName}"`;
    }
    default:
      return applyHostAction(name, input);
  }
}

/** How a publish_brief apply resolved — the ack vocabulary (D39 §4). */
export type PublishAckStatus = "applied" | "kept_previous" | "failed";

/** Map the publish apply label onto the ack status: null → failed, a "Kept …"
 *  arbitration (shrink guard / stale run) → kept_previous, else applied. */
export function publishAckStatus(label: string | null): PublishAckStatus {
  if (label === null) {
    return "failed";
  }
  return label.startsWith("Kept") ? "kept_previous" : "applied";
}

/**
 * Read back a publish_brief outcome to the sidecar's action ledger
 * (`POST /agents/actions/ack`, Team RUNTIME) so the runtime can surface a
 * divergence notice when its synthesized "dispatched to the panel" narration
 * and the panel's reality disagree (E3.3). Fire-and-forget: an unreachable
 * sidecar must never block the apply path — the missing ack itself reads as
 * "the panel did not confirm" on the runtime side, which is the honest state.
 */
export function ackPublishBrief(toolCallId: string, status: PublishAckStatus): void {
  if (!toolCallId) {
    return;
  }
  const brief = useBriefStore.getState().brief;
  void (async () => {
    const base = await getSidecarBaseUrl();
    await fetch(new URL("/agents/actions/ack", base).toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_call_id: toolCallId,
        status,
        ...(brief
          ? {
              brief: {
                run_id: brief.execution?.runId ?? null,
                created_at: brief.createdAt,
                symbol: brief.symbol ?? null,
                source_count: brief.sourceCount,
              },
            }
          : {}),
      }),
    });
  })().catch(() => {
    // Best-effort read-back; the runtime treats a missing ack honestly.
  });
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
