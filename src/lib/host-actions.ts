/**
 * Host actions — the agent's cockpit-driving mutations, and how the diff/accept
 * gate stages, describes, and applies them (FR-002 act-path, FR-010).
 *
 * The catalog tags these capabilities `kind="host_action", read_only=false`
 * (e.g. `open_panel`, `set_chart_symbol`, `add_to_watchlist`,
 * `portfolio_add_position`). The agent emits them as `tool_use` events; instead
 * of applying immediately, the chat surface stages each as a `ProposedChange`
 * (see `store/proposed-changes`), and these helpers do the work:
 *   - `parseHostAction` — parse the args ONCE into a bound {@link HostIntent}.
 *   - `describeIntent`  — read the live stores to build the old→new diff.
 *   - `applyIntent`     — apply exactly that intent on accept.
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
import { recordBriefClaims } from "@/lib/brief-claims";
import {
  applyContentAwareLayout,
  applyCustomLayout,
  fitLayoutTemplate,
  LAYOUT_TEMPLATE_IDS,
  resolvePanelToken,
  type CustomPanelSpec,
  type LayoutTemplate,
} from "@/lib/layout-templates";
import { regionConfig, isRegion, type Region } from "@/lib/region";
import { METRIC_LABELS, resolveMetric } from "@/modules/equity-overview/metrics";
import { getSidecarBaseUrl, sidecarGet } from "@/lib/sidecar-client";
import { saveWorkspace } from "@/lib/workspace";
import { indicatorByKey } from "@/modules/chart/indicators";
import { DEFAULT_DRAWING_STYLE, pointsRequired } from "@/modules/chart/drawings/factory";
import { useBacktestStore } from "@/store/backtest";
import { useBriefStore } from "@/store/brief";
import { useNotesStore } from "@/store/notes";
import { useChartCommandStore } from "@/store/chart-command";
import { drawingsFor, newDrawingId, useChartDrawingsStore } from "@/store/chart-drawings";
import { useEquityCommandStore } from "@/store/equity-command";
import {
  usePortfoliosStore,
  type AssetClass,
  type Holding,
  type Portfolio,
} from "@/store/portfolios";
import { useScreenerStore, type SavedScreen } from "@/store/screener";
import { useSettingsStore } from "@/store/settings";
import { entryKey, useSymbolsStore, type SymbolEntry } from "@/store/symbols";
import { isReservedLayoutName, useWorkspaceStore } from "@/store/workspace";

import type {
  BriefDepth,
  BriefSource,
  BriefSourceType,
  BriefStep,
  BriefStructured,
  ResearchBriefData,
} from "../../types/brief";
import type { ChartView, DrawingPoint } from "../../types/drawings";
import type { ProposedChangeKind } from "../../types/proposed-change";
import type { CriterionGroup, ScreenerCriterion, ScreenerUniverseId } from "../../types/screener";

/** The catalog host-action tool ids (`kind="host_action"`, `read_only=false`).
 *  R10 (D41/E6) adds the data-write family (portfolio positions, notes,
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
  "add_chart_drawing",
  "add_to_watchlist",
  "remove_from_watchlist",
  "publish_brief",
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

/**
 * Every cockpit action a user can take by hand, mapped to the host action that
 * lets the agent do it too, or to why the agent deliberately cannot
 * (R15-AGENT-084). `hand-action-inventory.test.ts` holds it two-way against
 * {@link HOST_ACTION_NAMES}: a new host action needs a row here, and a row
 * must name a real host action or carry its exclusion reason.
 */
export const HAND_ACTION_INVENTORY: Record<string, string | { excluded: string }> = {
  "Load a symbol into the chart": "set_chart_symbol",
  "Change the chart's indicators": "set_chart_indicators",
  "Draw a horizontal line or trendline": "add_chart_drawing",
  "Draw a ray, rectangle, ellipse, fib, channel, vertical line or text": {
    excluded: "click-placed shapes with no agent use yet; the two price-level kinds cover it",
  },
  "Move or delete a chart drawing": {
    excluded: "the agent adds, never edits or erases the user's own marks",
  },
  "Open a panel": "open_panel",
  "Close a panel": "close_panel",
  "Focus a panel": "focus_panel",
  "Rearrange the layout": "arrange_layout",
  "Save the layout": "save_layout",
  "Open a company's overview": "open_company_overview",
  "Show a research brief": "publish_brief",
  "Add a symbol to the watchlist": "add_to_watchlist",
  "Remove a symbol from the watchlist": "remove_from_watchlist",
  "Set screener filters": "write_screener_filters",
  "Save a screen": "save_screen",
  "Add a portfolio position": "portfolio_add_position",
  "Edit a portfolio position": "portfolio_update_position",
  "Remove a portfolio position": "portfolio_delete_position",
  "Write a note": "write_note",
  "Change the region": "set_region",
  "Enter or remove an API key": {
    excluded: "BYOK secrets live in the OS keychain and only the user types them",
  },
  "Change the model provider or research engine": {
    excluded: "set_region is the one Settings action the agent may drive (D45)",
  },
  "Switch between review and auto-apply": {
    excluded: "the agent never loosens its own review gate",
  },
  "Accept or reject a proposed change": {
    excluded: "the review gate is the user's; self-accepting would bypass it",
  },
};

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
        // Wire snake_case (web rows, ResearchSource.to_dict) → the camelCase
        // contract the sources rail reads (R15-RESEARCH-024, R15-UI-038).
        publishedAt: typeof s.published_at === "string" ? s.published_at : undefined,
        provider: typeof s.provider === "string" ? s.provider : undefined,
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
  const depth: BriefDepth = execution
    ? depthFromExecution(execution)
    : carryBriefDepth(input, symbol);
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
 * `region` (optional) is the region of the listing the caller picked, so a
 * ticker shared across markets (AMAL: BSE and NASDAQ) charts the picked
 * company (R15-DATA-002).
 */
export function loadSymbolIntoChart(symbol: string, timeframe?: string, region?: string): void {
  if (!symbol) {
    return;
  }
  ensureChartOpen();
  useChartCommandStore.getState().loadSymbol(symbol, timeframe || undefined, region);
}

/**
 * Open the Equity Overview for a company via the always-consumed equity-command
 * channel — the shared "click any company anywhere → the full overview" path
 * behind a screener row, a watchlist entry, a brief ticker chip, and a ⌘K symbol
 * pick. Opens the (singleton) panel first so the command has a consumer, then
 * commands it. Reuses the keyless yfinance overview endpoints — no key required.
 * `region` (optional) is the region of the listing the caller picked, so a
 * ticker shared across markets (AMAL: BSE and NASDAQ) opens the picked company.
 */
export function openCompanyOverview(
  symbol: string,
  highlightMetric?: string,
  region?: string,
): void {
  if (!symbol) {
    return;
  }
  const ws = useWorkspaceStore.getState();
  const api = ws.dockviewApi;
  const hasPanel = api?.panels.some((p) => p.api.component === "equity-overview-panel") ?? false;
  if (!hasPanel) {
    ws.openPanel("equity-overview");
  }
  useEquityCommandStore.getState().loadSymbol(symbol, highlightMetric, region);
}

/** The label of the overview row a highlight names, or `null` when it names none. */
function spotlightLabel(highlight: string): string | null {
  const key = resolveMetric(highlight);
  return key ? (METRIC_LABELS.get(key) ?? null) : null;
}

/** What an `open_company_overview` highlight did, composed from the panel's own
 *  metric list — never from the raw input (R15-AGENT-081): a known metric is
 *  spotlit; an unknown one is said to be absent. */
function spotlightNote(highlight: string): string {
  if (!highlight) {
    return "";
  }
  const label = spotlightLabel(highlight);
  return label
    ? ` — spotlighting ${label}`
    : ` — "${highlight}" is not a metric on that panel, so nothing is spotlit`;
}

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
 * a string[] for in). A malformed leaf returns WHY it was dropped
 * ("roe: value must be a number") so the label and the ack can say so — a
 * sloppy arg never crashes the apply, and never vanishes silently either.
 */
function parseScreenerCriterion(raw: unknown): ScreenerCriterion | string {
  if (!raw || typeof raw !== "object") {
    return "a criterion that is not an object";
  }
  const o = raw as Record<string, unknown>;
  const field = typeof o.field === "string" ? o.field : "";
  const operator = typeof o.operator === "string" ? o.operator : "";
  if (!field || !operator) {
    return `${field || "a criterion"}: needs both a field and an operator`;
  }
  if (operator === "gt" || operator === "lt" || operator === "gte" || operator === "lte") {
    if (typeof o.value !== "number") {
      return `${field}: value must be a number`;
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
    return `${field}: value must be {min, max} numbers`;
  }
  if (operator === "eq") {
    if (typeof o.value !== "string") {
      return `${field}: value must be a string`;
    }
    return { field, operator: "eq", value: o.value } as ScreenerCriterion;
  }
  if (operator === "in") {
    const arr = Array.isArray(o.value)
      ? o.value.filter((x): x is string => typeof x === "string")
      : [];
    if (arr.length === 0) {
      return `${field}: value must be a list of strings`;
    }
    return { field, operator: "in", value: arr } as ScreenerCriterion;
  }
  return `${field}: unknown operator "${operator}"`;
}

/** Keep a parsed leaf, or record why it was dropped. */
function keepLeaf(
  raw: unknown,
  into: (ScreenerCriterion | CriterionGroup)[],
  dropped: string[],
): void {
  const leaf = parseScreenerCriterion(raw);
  if (typeof leaf === "string") {
    dropped.push(leaf);
  } else {
    into.push(leaf);
  }
}

/** Parse a flat `criteria` array arg into well-formed leaves; each malformed
 *  leaf's reason goes onto `dropped`. */
function parseScreenerCriteria(
  input: Record<string, unknown>,
  dropped: string[],
): ScreenerCriterion[] {
  const criteria: ScreenerCriterion[] = [];
  for (const item of Array.isArray(input.criteria) ? input.criteria : []) {
    keepLeaf(item, criteria, dropped);
  }
  return criteria;
}

/**
 * Parse a loosely-typed nested AND/OR `group` tree (the agent's JSON) into a
 * `CriterionGroup`, dropping malformed children (their reasons go onto
 * `dropped`). Recurses on sub-groups. Returns null when absent or it collapses
 * to nothing.
 */
function parseScreenerGroup(raw: unknown, dropped: string[]): CriterionGroup | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  const combinator = o.combinator === "or" ? "or" : "and";
  const rawChildren = Array.isArray(o.criteria) ? o.criteria : [];
  const criteria: (ScreenerCriterion | CriterionGroup)[] = [];
  for (const child of rawChildren) {
    if (child && typeof child === "object" && "combinator" in (child as object)) {
      const sub = parseScreenerGroup(child, dropped);
      if (sub) {
        criteria.push(sub);
      }
    } else {
      keepLeaf(child, criteria, dropped);
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

/** Split set_chart_indicators keys into the ones the chart's indicator catalog
 *  knows (the keys the sidecar computes) and the unknown ones, which are dropped
 *  and reported. */
function splitIndicatorKeys(input: Record<string, unknown>): {
  known: string[];
  dropped: string[];
} {
  const known: string[] = [];
  const dropped: string[] = [];
  for (const raw of strArray(input, "indicators")) {
    const def = indicatorByKey(raw.trim().toLowerCase());
    if (def) {
      known.push(def.key);
    } else {
      dropped.push(raw);
    }
  }
  return { known, dropped };
}

function droppedNote(dropped: readonly string[]): string {
  return dropped.length ? ` (dropped unknown: ${dropped.join(", ")})` : "";
}

/** The per-share cost basis the agent gave, or null when it gave none. */
function costBasisOf(input: Record<string, unknown>): number | null {
  const v = input.cost_basis;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
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

/**
 * The backtest run an `open_panel` should display: `run_id` when the target is
 * the backtest panel (the agent's `run_custom_backtest` result), else "".
 */
function backtestRunTarget(input: Record<string, unknown>): string {
  const runId = str(input, "run_id");
  return runId && resolvePanelToken(str(input, "panel"))?.id === "backtest" ? runId : "";
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

/** The ACTIVE portfolio (the panel's truth — frontend store). */
function activePortfolio() {
  const s = usePortfoliosStore.getState();
  return s.portfolios.find((p) => p.id === s.activeId) ?? s.portfolios[0];
}

/** A portfolio by id (the one a proposal bound at enqueue). */
function portfolioById(id: string) {
  return usePortfoliosStore.getState().portfolios.find((p) => p.id === id);
}

/**
 * Resolve the holding a portfolio update/delete targets in `portfolio`: an
 * exact holding-id match first (the agent echoes the snapshot's `id` back as
 * `position_id`), else the ONE same-symbol holding. Null with the reason when
 * nothing matches, or when the symbol has several lots and no id picks one —
 * the refusal names each lot so the model can retry with its id. Never a
 * guessed mutation.
 */
function resolveHolding(
  portfolio: Portfolio | undefined,
  input: Record<string, unknown>,
): { target: Holding | null; problem: string } {
  const id = input.position_id != null ? String(input.position_id) : "";
  const symbol = str(input, "symbol");
  const byId = id ? portfolio?.holdings.find((h) => h.id === id) : undefined;
  if (byId) {
    return { target: byId, problem: "" };
  }
  const lots = symbol
    ? (portfolio?.holdings.filter((h) => baseSymbol(h.symbol) === baseSymbol(symbol)) ?? [])
    : [];
  if (lots.length === 1) {
    return { target: lots[0], problem: "" };
  }
  if (lots.length > 1) {
    const choices = lots.map((h) => `${h.id} (${lotText(h)})`).join(", ");
    return {
      target: null,
      problem: `${symbol} has ${lots.length} lots; name one by position_id: ${choices}`,
    };
  }
  return {
    target: null,
    problem: `${symbol || id || "position"} is not in the active portfolio`,
  };
}

/** " (lot 2 of 3)" when the holding's symbol has several lots, else "". */
function lotOrdinal(portfolioId: string, holding: Holding): string {
  const lots = (portfolioById(portfolioId)?.holdings ?? []).filter(
    (h) => baseSymbol(h.symbol) === baseSymbol(holding.symbol),
  );
  const at = lots.findIndex((h) => h.id === holding.id);
  return lots.length > 1 && at >= 0 ? ` (lot ${at + 1} of ${lots.length})` : "";
}

/** The holding fields an agent portfolio write carries, merged over the
 *  targeted holding for an update. An absent or non-finite cost basis is null
 *  (an update keeps the holding's own cost) — never a fabricated 0. */
function holdingFields(input: Record<string, unknown>, fallback?: Holding | null): HoldingDraft {
  const symbol = (str(input, "symbol") || fallback?.symbol || "").toUpperCase();
  const quantity =
    typeof input.quantity === "number" ? input.quantity : (fallback?.quantity ?? Number.NaN);
  const costBasis = costBasisOf(input) ?? fallback?.costBasis ?? null;
  const assetClass: AssetClass =
    (input.asset_class ?? fallback?.assetClass) === "crypto" ? "crypto" : "equity";
  const note = str(input, "note") || fallback?.note;
  return { symbol, quantity, costBasis, assetClass, note };
}

/** Why a holding draft cannot be written (the panel form's rules), or "". */
function holdingProblem(h: HoldingDraft): string {
  if (!h.symbol) {
    return "no symbol given";
  }
  if (!(h.quantity > 0)) {
    return "quantity must be greater than 0";
  }
  if (h.costBasis === null) {
    return "no price given";
  }
  return h.costBasis < 0 ? "cost basis cannot be negative" : "";
}

/** "×5 @ ₹2,500" — one holding's size and price for diff copy. */
function lotText(h: { quantity: number; costBasis: number | null }): string {
  return `×${h.quantity}${h.costBasis === null ? "" : ` @ ${formatPrice(h.costBasis)}`}`;
}

/** The note-scope key: "" = the General bucket, else an uppercased ticker. The
 *  catalog tells the model 'global'; 'general' and an empty scope mean it too. */
function noteScope(input: Record<string, unknown>): string {
  const scope = str(input, "scope").trim();
  const lower = scope.toLowerCase();
  return lower === "global" || lower === "general" || lower === "" ? "" : scope.toUpperCase();
}

/** The write_note mode: the catalog default is 'append', so only an explicit
 *  'replace' overwrites the note. */
function noteMode(input: Record<string, unknown>): "append" | "replace" {
  return str(input, "mode") === "replace" ? "replace" : "append";
}

/** The layout save_layout writes: the named one, else the active saved layout
 *  (the catalog: "omit name to update the active saved layout"); a new
 *  "Agent layout" only when no saved layout is active ("default" is the
 *  store's name for the unsaved cockpit, "__…" names are internal slots). */
function saveLayoutName(input: Record<string, unknown>): string {
  const named = str(input, "name").trim();
  if (named) {
    return named;
  }
  const active = useWorkspaceStore.getState().name;
  return active && active !== "default" && !isReservedLayoutName(active) ? active : "Agent layout";
}

/** A short human label for a note scope. */
function noteScopeLabel(scope: string): string {
  return scope === "" ? "General" : scope;
}

/** A holding an agent portfolio write proposes (cost may be missing). */
interface HoldingDraft {
  symbol: string;
  quantity: number;
  costBasis: number | null;
  assetClass: AssetClass;
  note?: string;
}

/** A resolved dockview panel target. */
type PanelTarget = { id: string; component: string };

/** A screener recipe from the agent's args: flat criteria and/or a nested group. */
interface ScreenRecipe {
  criteria: ScreenerCriterion[];
  group: CriterionGroup | null;
  universe?: ScreenerUniverseId;
  formula: string;
  /** Why each malformed criterion the agent sent was dropped. */
  dropped: string[];
}

/**
 * A host action parsed ONCE (at enqueue) from the agent's loose JSON. The
 * review diff ({@link describeIntent}) and the apply ({@link applyIntent}) both
 * read this one value, so the diff promises exactly what apply does; targets
 * (panel, portfolio + holding, layout name) are bound here and never
 * re-resolved against whatever is active at accept time.
 */
export type HostIntent =
  | { name: "set_chart_symbol"; symbol: string; timeframe: string }
  | { name: "set_chart_indicators"; symbol: string; known: string[]; dropped: string[] }
  | {
      name: "add_chart_drawing";
      kind: ChartDrawingKind | null;
      panelId: string;
      view: ChartView | null;
      points: DrawingPoint[];
      problem: string;
    }
  | {
      name: "open_panel";
      panel: string;
      target: PanelTarget | null;
      symbolTarget: "equity" | "chart" | null;
      symbol: string;
      runId: string;
    }
  | { name: "close_panel" | "focus_panel"; panel: string; target: PanelTarget | null }
  | {
      name: "arrange_layout";
      pattern: string;
      panel: string;
      target: PanelTarget | null;
      customPanels: CustomPanelSpec[];
      symbol: string;
      symbols: string[];
    }
  | { name: "open_company_overview"; symbol: string; highlight: string }
  | {
      name: "publish_brief";
      input: Record<string, unknown>;
      mode: string;
      sourceCount: number;
      webOff: boolean;
    }
  | { name: "add_to_watchlist" | "remove_from_watchlist"; symbol: string; assetClass: AssetClass }
  | { name: "write_screener_filters"; recipe: ScreenRecipe; count: number; run: boolean }
  | { name: "save_screen"; screenName: string; recipe: ScreenRecipe; count: number }
  | { name: "portfolio_add_position"; portfolioId: string; holding: HoldingDraft; problem: string }
  | {
      name: "portfolio_update_position";
      portfolioId: string;
      label: string;
      target: Holding | null;
      holding: HoldingDraft;
      problem: string;
    }
  | {
      name: "portfolio_delete_position";
      portfolioId: string;
      label: string;
      target: Holding | null;
      problem: string;
    }
  | { name: "write_note"; scope: string; text: string; append: boolean }
  | { name: "save_layout"; layoutName: string; updatesActive: boolean }
  | { name: "set_region"; region: Region | null; raw: string }
  | { name: "unknown"; raw: string };

/**
 * What an applied data write replaced, typed so {@link undoPreImage} can put it
 * back (the review's session Undo). Only writes that changed something carry
 * one; an idempotent no-op ("already on your watchlist") has nothing to undo.
 */
export type PreImage =
  | { kind: "holding-added"; portfolioId: string; holdingId: string; symbol: string }
  | { kind: "holding"; portfolioId: string; holding: Holding; index: number }
  | { kind: "note"; scope: string; text: string }
  | { kind: "screen"; name: string; screen: SavedScreen | null }
  | { kind: "watchlist-added"; symbol: string; region?: string }
  | { kind: "watchlist-removed"; entry: SymbolEntry; index: number }
  | { kind: "region"; region: Region };

/** How an apply resolved: a truthful label, or null with why it did not land. */
export interface ApplyResult {
  label: string | null;
  reason?: string;
  /** The state the write replaced, when it is a data write that can be undone. */
  preImage?: PreImage;
}

const done = (label: string, preImage?: PreImage): ApplyResult =>
  preImage ? { label, preImage } : { label };
const fail = (reason?: string): ApplyResult => ({ label: null, reason });

/** Parse a screener recipe (flat criteria + optional nested group) from args. */
function parseScreenRecipe(input: Record<string, unknown>): {
  recipe: ScreenRecipe;
  count: number;
} {
  const flatDropped: string[] = [];
  const groupDropped: string[] = [];
  const criteria = parseScreenerCriteria(input, flatDropped);
  const group = parseScreenerGroup(input.group, groupDropped);
  const universe =
    typeof input.universe === "string" && _SCREENER_UNIVERSES.has(input.universe)
      ? (input.universe as ScreenerUniverseId)
      : undefined;
  // When the agent gives only a nested group, mirror its leaves into the flat
  // `criteria` too so older readers + the match-index column resolve.
  const flat = criteria.length ? criteria : group ? flattenLeaves(group) : [];
  return {
    recipe: {
      criteria: flat,
      group,
      universe,
      formula: str(input, "formula").trim(),
      // A surviving group is what applies (and is counted); else the flat list.
      dropped: group ? groupDropped : [...flatDropped, ...groupDropped],
    },
    count: group ? countLeaves(group) : criteria.length,
  };
}

/** "; dropped roe: value must be a number" — the criteria the agent sent that
 *  did not parse, or "" when none were dropped. */
function droppedCriteriaNote(recipe: ScreenRecipe): string {
  return recipe.dropped.length ? `; dropped ${recipe.dropped.join("; ")}` : "";
}

/** "3 screener criteria" / "2 of 3 screener criteria" when some were dropped. */
function wroteCriteriaText(count: number, recipe: ScreenRecipe): string {
  const total = count + recipe.dropped.length;
  const noun = `screener ${total === 1 ? "criterion" : "criteria"}`;
  return recipe.dropped.length ? `${count} of ${total} ${noun}` : `${count} ${noun}`;
}

/**
 * Parse a host action's loose JSON args once into a {@link HostIntent}. Reads
 * the live stores only to BIND targets (the active portfolio and the holding it
 * names, the layout a nameless save updates); everything else is pure.
 */
export function parseHostAction(name: string, input: Record<string, unknown>): HostIntent {
  const symbol = str(input, "symbol");
  switch (name) {
    case "set_chart_symbol":
      return { name, symbol, timeframe: str(input, "timeframe") };
    case "set_chart_indicators":
      return { name, symbol, ...splitIndicatorKeys(input) };
    case "add_chart_drawing":
      return parseChartDrawing(input);
    case "open_panel": {
      const panel = str(input, "panel");
      const symbolTarget = symbolAwarePanelTarget(panel);
      return {
        name,
        panel,
        target: resolvePanelToken(panel) ?? null,
        symbolTarget,
        // A stray `symbol` on a panel with no symbol input is ignored.
        symbol: symbolTarget ? symbol : "",
        runId: backtestRunTarget(input),
      };
    }
    case "close_panel":
    case "focus_panel": {
      const panel = str(input, "panel");
      return { name, panel, target: resolvePanelToken(panel) ?? null };
    }
    case "arrange_layout": {
      const panel = str(input, "panel");
      return {
        name,
        pattern: str(input, "pattern") || "default",
        panel,
        target: resolvePanelToken(panel) ?? null,
        customPanels: parseCustomPanels(input),
        symbol,
        symbols: strArray(input, "symbols"),
      };
    }
    case "open_company_overview":
      return { name, symbol, highlight: str(input, "highlight") };
    case "publish_brief": {
      const sources = Array.isArray(input.sources) ? input.sources : [];
      const execution = executionFromWire(input.execution);
      const depth = execution
        ? depthFromExecution(execution)
        : normalizeBriefDepth(str(input, "depth"), str(input, "mode"));
      return {
        name,
        input,
        mode: normalizeBriefMode(depth === "quick" ? "fast" : "deep"),
        sourceCount: sources.length,
        // structured-data-only is honest ONLY with zero cited sources: a sourced
        // brief is never tagged structured-only even if the model omitted/zeroed
        // the web flag (WS3 — no contradictory "N sources · structured-data-only").
        webOff: input.web_available === false && sources.length === 0,
      };
    }
    case "add_to_watchlist":
    case "remove_from_watchlist":
      return {
        name,
        symbol: symbol.trim().toUpperCase(),
        assetClass: input.asset_class === "crypto" ? "crypto" : "equity",
      };
    case "write_screener_filters":
      return { name, ...parseScreenRecipe(input), run: input.run === true };
    case "save_screen":
      return { name, screenName: str(input, "name").trim(), ...parseScreenRecipe(input) };
    case "portfolio_add_position": {
      const holding = holdingFields(input);
      return {
        name,
        portfolioId: activePortfolio()?.id ?? "",
        holding,
        problem: holdingProblem(holding),
      };
    }
    case "portfolio_update_position":
    case "portfolio_delete_position": {
      const portfolio = activePortfolio();
      const { target, problem } = resolveHolding(portfolio, input);
      const portfolioId = portfolio?.id ?? "";
      const label = target?.symbol || symbol || "position";
      if (name === "portfolio_delete_position") {
        return { name, portfolioId, label, target, problem };
      }
      const holding = holdingFields(input, target);
      return {
        name,
        portfolioId,
        label,
        target,
        holding,
        problem: problem || holdingProblem(holding),
      };
    }
    case "write_note":
      return {
        name,
        scope: noteScope(input),
        text: str(input, "text"),
        append: noteMode(input) === "append",
      };
    case "save_layout": {
      const layoutName = saveLayoutName(input);
      return {
        name,
        layoutName,
        updatesActive: layoutName === useWorkspaceStore.getState().name,
      };
    }
    case "set_region": {
      const raw = str(input, "region").trim().toUpperCase();
      return { name, raw, region: isRegion(raw) ? (raw as Region) : null };
    }
    default:
      return { name: "unknown", raw: name };
  }
}

const CANT_APPLY = "can't apply";

/** The drawing kinds the agent may add (`add_chart_drawing`); every other kind
 *  stays a hand gesture (see {@link HAND_ACTION_INVENTORY}). */
type ChartDrawingKind = "horizontal-line" | "trendline";
const AGENT_DRAWING_KINDS: readonly string[] = ["horizontal-line", "trendline"];

/** Bar time in UTC seconds, as the chart keys its bars (`toChartTime`). */
function drawingTime(raw: unknown): number | null {
  const ms = typeof raw === "string" ? Date.parse(raw) : NaN;
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : null;
}

/**
 * Bind an `add_chart_drawing` to the open chart panel and the view it shows at
 * enqueue, so the drawing lands on the symbol/timeframe the diff named. A
 * horizontal-line is one price (its time is ignored); a trendline is two
 * timed points.
 */
function parseChartDrawing(input: Record<string, unknown>): HostIntent {
  const rawKind = str(input, "kind");
  const kind = AGENT_DRAWING_KINDS.includes(rawKind) ? (rawKind as ChartDrawingKind) : null;
  const panelId =
    str(input, "panelId") || findOpenPanel({ id: "chart", component: "chart-panel" })?.id || "";
  const view = (panelId && useChartDrawingsStore.getState().views[panelId]) || null;
  const raw = Array.isArray(input.points) ? input.points : [];
  const points: DrawingPoint[] = raw.map((p) => {
    const point = typeof p === "object" && p !== null ? (p as Record<string, unknown>) : {};
    const price =
      typeof point.price === "number" && Number.isFinite(point.price) ? point.price : null;
    return { time: kind === "horizontal-line" ? null : drawingTime(point.time), price };
  });
  const problem = !kind
    ? `"${rawKind}" is not a drawing the agent can add`
    : !view
      ? "no chart is open"
      : points.length !== pointsRequired(kind)
        ? `a ${kind} takes ${pointsRequired(kind)} point(s)`
        : points.some((p) => p.price === null)
          ? "every point needs a price"
          : kind === "trendline" && points.some((p) => p.time === null)
            ? "every trendline point needs a bar time"
            : "";
  return { name: "add_chart_drawing", kind, panelId, view, points, problem };
}

/** "a horizontal line at ₹1,450" / "a trendline". */
function chartDrawingLabel(intent: Extract<HostIntent, { name: "add_chart_drawing" }>): string {
  const price = intent.points[0]?.price;
  if (intent.kind === "horizontal-line") {
    // The chart's symbol may quote in another currency than the region's, so no sign.
    return typeof price === "number" ? `a horizontal line at ${price}` : "a horizontal line";
  }
  return intent.kind === "trendline" ? "a trendline" : "a drawing";
}

/** Drawings a panel already shows for its current view. */
function chartDrawingCount(panelId: string, view: ChartView): number {
  const list = useChartDrawingsStore.getState().getDrawings(panelId);
  return drawingsFor(list, view.symbol, view.timeframe).length;
}

/** "1 criterion" / "3 criteria". */
function criteriaText(count: number): string {
  return `${count} criteri${count === 1 ? "on" : "a"}`;
}

/**
 * Describe a parsed host action as a reviewable old→new diff. Reads the live
 * stores so the "before" reflects the real current cockpit state; the "after"
 * is exactly what {@link applyIntent} will do with the same intent.
 */
export function describeIntent(intent: HostIntent): {
  kind: ProposedChangeKind;
  title: string;
  before: string;
  after: string;
} {
  switch (intent.name) {
    case "set_chart_symbol": {
      const current = useChartCommandStore.getState().activeSymbol ?? "—";
      return {
        kind: "chart",
        title: `Load ${intent.symbol || "symbol"} into the chart`,
        before: `Chart symbol: ${current}`,
        after: intent.symbol
          ? `Chart symbol: ${intent.symbol}${intent.timeframe ? ` · ${intent.timeframe}` : ""}`
          : `Chart symbol: no symbol given — ${CANT_APPLY}`,
      };
    }
    case "set_chart_indicators": {
      const current = useChartCommandStore.getState().activeIndicators;
      const { known, dropped } = intent;
      return {
        kind: "chart",
        title: `Set chart indicators${intent.symbol ? ` on ${intent.symbol}` : ""}`,
        before: `Indicators: ${current.length ? current.join(", ") : "none"}`,
        after:
          known.length === 0 && dropped.length > 0
            ? `Indicators: unchanged — ${CANT_APPLY}${droppedNote(dropped)}`
            : `Indicators: ${known.length ? known.join(", ") : "none"}${droppedNote(dropped)}`,
      };
    }
    case "add_chart_drawing": {
      const { view, problem } = intent;
      const onChart = view ? ` on ${view.symbol} ${view.timeframe}` : "";
      const count = view ? chartDrawingCount(intent.panelId, view) : 0;
      return {
        kind: "chart",
        title: `Draw ${chartDrawingLabel(intent)}${onChart}`,
        before: `Drawings${onChart}: ${count}`,
        after: problem
          ? `Drawings: unchanged — ${CANT_APPLY} — ${problem}`
          : `Drawings${onChart}: ${count + 1} (+${chartDrawingLabel(intent)})`,
      };
    }
    case "open_panel": {
      const { panel, target, symbol, runId } = intent;
      const detail = symbol ? ` — ${symbol}` : runId ? ` — run ${runId}` : "";
      const isOpen = target !== null && findOpenPanel(target) !== null;
      return {
        kind: "panel",
        title: `Open ${panelLabel(panel)}${detail}`,
        before: `${panelLabel(panel)} panel: ${isOpen ? "open" : "not open"}`,
        after: target
          ? `${panelLabel(panel)} panel: open${detail ? `${detail} loaded` : ""}`
          : `${panelLabel(panel)}: unknown panel — ${CANT_APPLY}`,
      };
    }
    case "close_panel": {
      const { panel, target } = intent;
      const isOpen = target !== null && findOpenPanel(target) !== null;
      return {
        kind: "panel",
        title: `Close the ${panelLabel(panel)} panel`,
        before: `${panelLabel(panel)} panel: ${isOpen ? "open" : "not open"}`,
        after: target
          ? `${panelLabel(panel)} panel: ${isOpen ? "closed" : "already closed"}`
          : `${panelLabel(panel)}: unknown panel — ${CANT_APPLY}`,
      };
    }
    case "focus_panel": {
      const { panel, target } = intent;
      return {
        kind: "panel",
        title: `Focus the ${panelLabel(panel)} panel`,
        before: `Foreground: the current panel`,
        after: target
          ? `Foreground: ${panelLabel(panel)}`
          : `${panelLabel(panel)}: unknown panel — ${CANT_APPLY}`,
      };
    }
    case "arrange_layout": {
      const { pattern, panel, customPanels, symbol, symbols } = intent;
      const before = "Layout: the current cockpit";
      if (pattern === "auto") {
        return {
          kind: "panel",
          title: "Arrange your windows around the content",
          before,
          after: "Layout: content-aware (dominant reading panel, wide chart, side rail)",
        };
      }
      if (pattern === "focus") {
        return {
          kind: "panel",
          title: `Focus on ${panel ? panelLabel(panel) : "one panel"}`,
          before,
          after: intent.target
            ? `Layout: ${panelLabel(panel)} maximised`
            : `Layout: unchanged — no panel "${panel}" to maximise`,
        };
      }
      if (pattern === "custom" || customPanels.length > 0) {
        const names = customPanels.map((p) => p.panel).join(" + ");
        return {
          kind: "panel",
          title: names ? `Arrange ${names}` : "Arrange your panels",
          before,
          after: names ? `Layout: ${names}` : "Layout: a custom arrangement",
        };
      }
      if (LAYOUT_TEMPLATE_IDS.has(pattern)) {
        const label =
          pattern === "research-cockpit" ? "research cockpit" : pattern.replace("-", " ");
        const scope =
          pattern === "compare" && symbols.length >= 2
            ? ` (${symbols.slice(0, 2).join(" vs ")})`
            : symbol
              ? ` · ${symbol}`
              : symbols[0]
                ? ` · ${symbols[0]}`
                : "";
        return {
          kind: "panel",
          title: `Arrange the ${label} layout`,
          before,
          after: `Layout: ${label}${scope}`,
        };
      }
      return {
        kind: "panel",
        title: "Reset the panel arrangement (drawings and modules kept)",
        before,
        after: "Layout: the default panel arrangement (chart drawings and modules kept)",
      };
    }
    case "open_company_overview": {
      const sym = intent.symbol || "the company";
      const metric = spotlightLabel(intent.highlight);
      return {
        kind: "panel",
        title: metric ? `Show ${sym}'s ${metric} in the overview` : `Open ${sym}'s overview`,
        before: "Equity Overview: previous company (if any)",
        after: intent.symbol
          ? `Equity Overview: ${sym}${spotlightNote(intent.highlight)}`
          : `Equity Overview: no symbol given — ${CANT_APPLY}`,
      };
    }
    case "publish_brief": {
      const symbol = str(intent.input, "symbol");
      const n = intent.sourceCount;
      return {
        kind: "panel",
        title: `Publish the ${intent.mode} research brief${symbol ? ` on ${symbol}` : ""}`,
        before: "Brief panel: previous brief (if any)",
        after: `Brief: ${n} cited source${n === 1 ? "" : "s"}${intent.webOff ? " · structured-data-only" : ""}`,
      };
    }
    case "add_to_watchlist":
    case "remove_from_watchlist": {
      const { symbol } = intent;
      const entries = useSymbolsStore.getState().entries;
      const tracked = entries.some((e) => e.symbol.toUpperCase() === symbol);
      const before = `Watchlist: ${entries.length} symbol${entries.length === 1 ? "" : "s"}`;
      if (intent.name === "add_to_watchlist") {
        return {
          kind: "watchlist",
          title: `Add ${symbol} to your watchlist`,
          before,
          after: !symbol
            ? `Watchlist: no symbol given — ${CANT_APPLY}`
            : tracked
              ? `Watchlist: ${symbol} already tracked`
              : intent.assetClass === "equity"
                ? `Watchlist: +${symbol} once it resolves to one listing (${entries.length + 1} total)`
                : `Watchlist: +${symbol} (${entries.length + 1} total)`,
        };
      }
      return {
        kind: "watchlist",
        title: `Remove ${symbol} from your watchlist`,
        before,
        after: !symbol
          ? `Watchlist: no symbol given — ${CANT_APPLY}`
          : tracked
            ? `Watchlist: −${symbol} (${entries.length - 1} total)`
            : `Watchlist: ${symbol} is not tracked`,
      };
    }
    case "write_screener_filters": {
      const { recipe, count, run } = intent;
      const s = useScreenerStore.getState();
      const currentCount = s.advanced && s.group ? countLeaves(s.group) : s.criteria.length;
      const nested = recipe.group?.criteria.some((c) => "combinator" in c)
        ? " (nested AND/OR)"
        : "";
      const writes = count > 0 || recipe.formula !== "";
      return {
        kind: "panel",
        title: "Write screener filters",
        before: `Screener: ${criteriaText(currentCount)}`,
        after: writes
          ? `Screener: ${criteriaText(count)}${nested}${recipe.universe ? ` · ${recipe.universe}` : ""}${
              recipe.formula ? " · formula" : ""
            }${droppedCriteriaNote(recipe)} — ${run ? "runs on apply" : "review then Run"}`
          : `Screener: no well-formed criteria${droppedCriteriaNote(recipe)} — ${CANT_APPLY}`,
      };
    }
    case "save_screen": {
      const { screenName, recipe, count } = intent;
      const replaces = useScreenerStore.getState().savedScreens.some((s) => s.name === screenName);
      const what = count
        ? criteriaText(count)
        : recipe.formula
          ? "a formula"
          : "the current filters";
      return {
        kind: "data-write",
        title: `Save the screen as "${screenName || "?"}"`,
        before: replaces ? `Saved screens: "${screenName}" exists` : "Saved screens: unchanged",
        after: !screenName
          ? `Saved screens: no name given — ${CANT_APPLY}`
          : count === 0 && !recipe.formula && recipe.dropped.length > 0
            ? `Saved screens: no well-formed criteria${droppedCriteriaNote(recipe)} — ${CANT_APPLY}`
            : `Saved screens: ${replaces ? `"${screenName}" replaced` : `+"${screenName}"`} (${what})${droppedCriteriaNote(recipe)}`,
      };
    }
    case "portfolio_add_position": {
      const { holding, problem } = intent;
      const count = portfolioById(intent.portfolioId)?.holdings.length ?? 0;
      const price =
        holding.costBasis === null ? "no price given" : `@ ${formatPrice(holding.costBasis)}`;
      const qty = Number.isNaN(holding.quantity) ? "" : holding.quantity;
      return {
        kind: "data-write",
        title: (holding.costBasis === null
          ? `Add ${qty} ${holding.symbol} to the portfolio — no price given`
          : `Add ${qty} ${holding.symbol} ${price} to the portfolio`
        )
          .replace(/\s+/g, " ")
          .trim(),
        before: `Portfolio: ${count} position${count === 1 ? "" : "s"}`,
        after: problem
          ? `Portfolio: unchanged — ${problem}`
          : `Portfolio: +${holding.symbol} ×${holding.quantity} ${price} (${count + 1} total)`,
      };
    }
    case "portfolio_update_position":
    case "portfolio_delete_position": {
      const { target, problem, label } = intent;
      const update = intent.name === "portfolio_update_position";
      return {
        kind: "data-write",
        title: `${update ? "Update" : "Remove"} ${label} ${update ? "in" : "from"} the portfolio`,
        before: target
          ? `${target.symbol}${lotOrdinal(intent.portfolioId, target)}: ${lotText(target)}`
          : "Portfolio: unchanged",
        after: problem
          ? `${CANT_APPLY} — ${problem}`
          : update
            ? `${intent.holding.symbol}: ${lotText(intent.holding)}`
            : `${label}: removed`,
      };
    }
    case "write_note": {
      const { scope, text, append } = intent;
      const current = useNotesStore.getState().noteFor(scope);
      const n = text.trim().length;
      return {
        kind: "data-write",
        title: `${append ? "Append to" : "Write"} the ${noteScopeLabel(scope)} note`,
        before: `${noteScopeLabel(scope)} note: ${current.trim() ? `${current.trim().length} chars` : "empty"}`,
        after: !n
          ? `${noteScopeLabel(scope)} note: nothing to write — ${CANT_APPLY}`
          : append
            ? `${noteScopeLabel(scope)} note: +${n} chars appended`
            : `${noteScopeLabel(scope)} note: replaced (${n} chars)`,
      };
    }
    case "save_layout": {
      const { layoutName, updatesActive } = intent;
      return {
        kind: "data-write",
        title: updatesActive
          ? `Update the saved layout "${layoutName}"`
          : `Save the current layout as "${layoutName}"`,
        before: "Saved workspaces: unchanged",
        after: updatesActive
          ? `Saved workspaces: "${layoutName}" updated (current cockpit)`
          : `Saved workspaces: +"${layoutName}" (current cockpit)`,
      };
    }
    case "set_region": {
      const current = useSettingsStore.getState().region;
      return {
        kind: "settings",
        title: `Set the region to ${intent.region ?? (intent.raw || "?")}`,
        before: `Region: ${current}`,
        after: intent.region
          ? `Region: ${intent.region}`
          : `Region: "${intent.raw}" is not a region — ${CANT_APPLY}`,
      };
    }
    case "unknown":
      return {
        kind: "panel",
        title: intent.raw.replace(/_/g, " "),
        before: "—",
        after: `Unknown action — ${CANT_APPLY}`,
      };
  }
}

/** Describe a host action from its raw args (parses, then {@link describeIntent}). */
export function describeHostAction(name: string, input: Record<string, unknown>) {
  return describeIntent(parseHostAction(name, input));
}

/**
 * Apply a parsed host action to the live stores. Returns a short TRUTHFUL
 * label describing what actually happened, or a null label (with the reason
 * when there is one) if it could not apply — the proposed-changes gate
 * re-pends it and surfaces the failure, so chat/proposal narration never
 * claims an action that did not land (grounded narration, R8 seams
 * deliverable 5). No branch may return a success label without having done (or
 * verified) the work: an unknown panel id, a panel that failed to open, or
 * incomplete arguments all fail.
 */
export function applyIntent(intent: HostIntent): ApplyResult {
  switch (intent.name) {
    case "set_chart_symbol":
      if (!intent.symbol) {
        return fail("no symbol given");
      }
      // Command the chart DIRECTLY (always-consumed channel), not the opt-in
      // sync bus — the BUG-6 fix. The shared helper opens a chart first if the
      // cockpit is empty (the AUTO-mode "no panels open yet" failure).
      loadSymbolIntoChart(intent.symbol, intent.timeframe);
      return done(`Loaded ${intent.symbol} into the chart`);
    case "set_chart_indicators": {
      // Only keys the chart knows reach the fetch: one unknown key made the
      // sidecar reject the whole request, so every indicator failed.
      const { known, dropped, symbol } = intent;
      if (known.length === 0 && dropped.length > 0) {
        // nothing applicable — never clear the chart over bad keys
        return fail(`unknown indicators: ${dropped.join(", ")}`);
      }
      ensureChartOpen();
      const cc = useChartCommandStore.getState();
      // If a symbol was named, load it first so the indicators apply to the
      // intended chart; then set the selection (unscoped → the active chart).
      if (symbol) {
        cc.loadSymbol(symbol);
      }
      cc.setIndicators(known);
      return done(
        `Set indicators: ${known.length ? known.join(", ") : "none"}${droppedNote(dropped)}`,
      );
    }
    case "add_chart_drawing": {
      const { kind, panelId, view, points, problem } = intent;
      if (problem || !kind || !view) {
        return fail(problem);
      }
      useChartDrawingsStore.getState().addDrawing(panelId, {
        id: newDrawingId(),
        panelId,
        symbol: view.symbol,
        timeframe: view.timeframe,
        kind,
        points,
        style: { ...DEFAULT_DRAWING_STYLE },
        createdAt: Date.now(),
      });
      return done(`Drew ${chartDrawingLabel(intent)} on ${view.symbol} ${view.timeframe}`);
    }
    case "open_panel": {
      const { panel, target, symbolTarget, symbol } = intent;
      // Resolved through the alias-tolerant token map (the same one arrange
      // uses) so "screener" opens the registered "screener-panel" instead of
      // silently no-opping. An UNRESOLVABLE token fails: an honest "could not
      // apply" beats a fake "Opened X" (grounded narration).
      if (!target) {
        return fail(`unknown panel "${panel}"`);
      }
      // Symbol-aware open: a symbol for a panel that consumes one rides the
      // always-consumed command channels (equity-command for the overview,
      // chart-command for the chart). Both helpers open the panel first; the
      // stores RETAIN the last command, so a panel that mounts later still gets it.
      if (symbol && symbolTarget === "equity") {
        openCompanyOverview(symbol);
        return done(`Opened ${panelLabel(panel)} — ${symbol}`);
      }
      if (symbol && symbolTarget === "chart") {
        loadSymbolIntoChart(symbol);
        return done(`Opened ${panelLabel(panel)} — ${symbol}`);
      }
      const ws = useWorkspaceStore.getState();
      ws.openPanel(target.id);
      // Verify the open actually landed when a live layout is on screen — a
      // disabled module (findPanel miss) used to no-op while this still
      // claimed "Opened". With no api yet (pre-mount) the claim is left
      // optimistic; a mounted cockpit is the only place proposals apply.
      if (ws.dockviewApi && !findOpenPanel(target)) {
        return fail(`the ${panelLabel(panel)} panel did not open`);
      }
      return done(`Opened ${panelLabel(panel)}`);
    }
    case "close_panel": {
      const { panel, target } = intent;
      if (!target) {
        return fail(`unknown panel "${panel}"`); // never narrate a fake "Closed"
      }
      const open = findOpenPanel(target);
      if (!open) {
        // Truthful idempotent no-op: the desired end state already holds.
        return done(`${panelLabel(panel)} was already closed`);
      }
      open.api.close();
      return done(`Closed ${panelLabel(panel)}`);
    }
    case "focus_panel": {
      const { panel, target } = intent;
      if (!target) {
        return fail(`unknown panel "${panel}"`);
      }
      const open = findOpenPanel(target);
      if (open) {
        open.api.setActive();
        return done(`Focused ${panelLabel(panel)}`);
      }
      // Not open yet — opening a singleton focuses it. Verify it landed so a
      // disabled module never narrates a focus that did not happen.
      const ws = useWorkspaceStore.getState();
      ws.openPanel(target.id);
      if (ws.dockviewApi && !findOpenPanel(target)) {
        return fail(`the ${panelLabel(panel)} panel did not open`);
      }
      return done(`Opened and focused ${panelLabel(panel)}`);
    }
    case "arrange_layout": {
      const ws = useWorkspaceStore.getState();
      const { pattern, customPanels, symbol, symbols } = intent;
      // CONTENT-AWARE (R9, gate 11): arrange the OPEN panels the way a person
      // would — the planner ranks live content (a published brief dominates,
      // the chart gets width, the watchlist parks in a rail). Deterministic;
      // never opens or closes a panel.
      if (pattern === "auto") {
        const api = ws.dockviewApi;
        if (!api) {
          return fail("the layout has not mounted");
        }
        const signals = {
          briefChars: useBriefStore.getState().brief?.markdown?.length ?? 0,
          notesChars: useNotesStore.getState().general.length,
          watchlistRows: useSymbolsStore.getState().entries.length,
        };
        const result = applyContentAwareLayout(api, signals);
        if (result.count === 0) {
          return fail("no panels are open");
        }
        return done(
          result.count === 1
            ? `Focused ${panelLabel(result.anchor ?? "")} — it's the only panel open`
            : `Arranged ${result.count} windows around ${panelLabel(result.anchor ?? "")}`,
        );
      }
      if (pattern === "focus") {
        const open = intent.target ? findOpenPanel(intent.target) : null;
        if (!open) {
          return fail(`no open panel "${intent.panel}" to maximise`);
        }
        open.api.setActive();
        open.api.maximize();
        return done(`Focused on ${panelLabel(intent.panel)}`);
      }
      // CUSTOM arrange (Track B): "put the chart here and news there". Triggered
      // by pattern="custom" OR a `panels` arg on any pattern. The host lays the
      // named panels out coherently (or honours explicit per-panel directions) —
      // the dockview engine already supports arbitrary placement.
      if (pattern === "custom" || customPanels.length > 0) {
        const api = ws.dockviewApi;
        if (!api) {
          return fail("the layout has not mounted");
        }
        applyCustomLayout(api, customPanels, { symbol: symbol || undefined });
        if (symbol) {
          useChartCommandStore.getState().loadSymbol(symbol);
        }
        const names = customPanels.map((p) => p.panel).join(" + ");
        return done(names ? `Arranged ${names}` : "Arranged your panels");
      }
      if (LAYOUT_TEMPLATE_IDS.has(pattern)) {
        const api = ws.dockviewApi;
        if (!api) {
          return fail("the layout has not mounted");
        }
        // Fit-aware (Track 4): on a narrow display a panel-heavy template is
        // downgraded to a layout that actually fits (research → chart + brief).
        const fit = fitLayoutTemplate(api, pattern as LayoutTemplate, {
          symbol: symbol || undefined,
          symbols: symbols.length ? symbols : undefined,
        });
        // The layout is symbol-agnostic — push symbols to the chart via the
        // chart-command channel (compare = symbol A loaded + symbol B overlaid).
        const cc = useChartCommandStore.getState();
        if (pattern === "compare" && symbols.length >= 2) {
          cc.loadSymbol(symbols[0]);
          cc.setComparison(symbols[1]);
        } else if (symbol) {
          cc.loadSymbol(symbol);
        } else if (symbols[0]) {
          cc.loadSymbol(symbols[0]);
        }
        if (fit.downgraded) {
          return done(
            fit.applied === "essentials-research"
              ? "Arranged the essentials (chart + brief) to fit your screen — click any ticker to go deeper"
              : "Arranged a single-focus layout to fit your screen",
          );
        }
        const label =
          pattern === "research-cockpit" ? "research cockpit" : pattern.replace("-", " ");
        return done(`Arranged the ${label} layout`);
      }
      // The agent's default/unknown arrange is layout-only: a cosmetic tool must
      // never delete drawings or re-enable modules (R15-AGENT-056); the factory
      // reset stays the explicit Settings/menu action.
      ws.resetLayout();
      return done("Reset the panel arrangement to the default (drawings and modules kept)");
    }
    case "open_company_overview": {
      const { symbol, highlight } = intent;
      if (!symbol) {
        return fail("no symbol given");
      }
      openCompanyOverview(symbol, resolveMetric(highlight) ?? undefined);
      return done(`Opened ${symbol}'s overview${spotlightNote(highlight)}`);
    }
    case "publish_brief": {
      const brief = briefFromInput(intent.input);
      // Allow a structured-only seed (the FAST auto-publish carries live metrics
      // before the model writes the prose) and a disambiguation-only publish
      // (the chooser renders instead of a body); reject only a truly empty brief.
      if (!brief.markdown.trim() && !brief.structured && !brief.disambiguation) {
        return fail("the brief is empty");
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
        return done("Kept the richer research brief already on screen");
      }
      // Open the brief panel so the output is on screen, then publish through
      // the lifecycle machine — a publish whose run_id mismatches the run in
      // flight is ignored as stale (E3.2) and reports kept_previous.
      useWorkspaceStore.getState().openPanel("brief");
      const result = useBriefStore.getState().publish(brief);
      if (result === "stale_run") {
        return done("Kept the run in flight — this publish belonged to a different run");
      }
      // Record the brief's stated figures into the research-space claims ledger
      // (R13 JARVIS 3a) — deterministic, no-op outside a research space — so a
      // later contradicting figure can be reconciled openly, never silently.
      recordBriefClaims(brief);
      return done(`Published the ${brief.mode} research brief`);
    }
    case "add_to_watchlist": {
      const { symbol } = intent;
      if (!symbol) {
        return fail("no symbol given");
      }
      const symbols = useSymbolsStore.getState();
      if (tracksRegionless(symbol)) {
        // Truthful idempotent no-op: the desired end state already holds.
        return done(`${symbol} is already on your watchlist`);
      }
      if (intent.assetClass === "equity") {
        // A model-supplied equity goes through the one resolution policy first
        // (GET /resolve) — never a verbatim, possibly invented ticker.
        return fail("adding an equity needs the async apply (it resolves the name first)");
      }
      symbols.addSymbol(symbol, intent.assetClass);
      return done(`Added ${symbol} to your watchlist`, { kind: "watchlist-added", symbol });
    }
    case "remove_from_watchlist": {
      const { symbol } = intent;
      if (!symbol) {
        return fail("no symbol given");
      }
      const symbols = useSymbolsStore.getState();
      const index = symbols.entries.findIndex((e) => e.symbol.toUpperCase() === symbol);
      if (index < 0) {
        // Truthful idempotent no-op: the desired end state already holds.
        return done(`${symbol} was not on your watchlist`);
      }
      const entry = symbols.entries[index];
      // Only the found listing, so the single-entry undo is an exact inverse.
      symbols.removeSymbol(symbol, entry.region ?? null);
      return done(`Removed ${symbol} from your watchlist`, {
        kind: "watchlist-removed",
        entry,
        index,
      });
    }
    case "write_screener_filters": {
      const { recipe, count, run } = intent;
      // Need at least one well-formed criterion (flat OR nested) or a formula.
      if (count === 0 && !recipe.formula) {
        return fail(`no well-formed screener criteria${droppedCriteriaNote(recipe)}`);
      }
      // A formula-less write keeps the user's own formula (applyFilters' rule).
      useScreenerStore.getState().applyFilters({
        criteria: recipe.criteria,
        group: recipe.group,
        universe: recipe.universe,
        ...(recipe.formula ? { formula: recipe.formula } : {}),
      });
      if (run) {
        void useScreenerStore.getState().runScreener();
      }
      // Stage the panel so the proposed filters are on screen (running, or for
      // the user to Run). The screener module REGISTERS id "screener-panel" —
      // the bare "screener" id silently no-opped (same drift class as arrange).
      useWorkspaceStore.getState().openPanel("screener-panel");
      const what = count
        ? `${wroteCriteriaText(count, recipe)}${recipe.formula ? " + a formula" : ""}`
        : "a screener formula";
      return done(
        `Wrote ${what}${droppedCriteriaNote(recipe)} — ${run ? "running" : "review and Run"}`,
      );
    }
    case "write_note": {
      const { scope, text, append } = intent;
      if (!text.trim()) {
        return fail("the note text is empty");
      }
      const notes = useNotesStore.getState();
      const current = notes.noteFor(scope);
      const next = append && current.trim() ? `${current.replace(/\s+$/, "")}\n\n${text}` : text;
      if (scope === "") {
        notes.setGeneral(next);
      } else {
        notes.setSymbolNote(scope, next);
      }
      useWorkspaceStore.getState().openPanel("notes");
      return done(`${append ? "Appended to" : "Wrote"} the ${noteScopeLabel(scope)} note`, {
        kind: "note",
        scope,
        text: current,
      });
    }
    case "save_screen": {
      const { screenName, recipe } = intent;
      if (!screenName) {
        return fail("no screen name given");
      }
      // Every criterion the agent sent was malformed: saving would file the
      // user's CURRENT filters under the agent's name — refuse and say why.
      if (intent.count === 0 && !recipe.formula && recipe.dropped.length > 0) {
        return fail(`no well-formed screener criteria${droppedCriteriaNote(recipe)}`);
      }
      // The store saves its current draft, so the agent's recipe is written
      // into the draft first — the saved screen is the recipe, formula and all
      // (none given = none). No recipe saves the current filters, as the diff says.
      const screener = useScreenerStore.getState();
      if (intent.count > 0 || recipe.formula) {
        screener.applyFilters({
          criteria: recipe.criteria,
          group: recipe.group,
          universe: recipe.universe,
          formula: recipe.formula,
        });
      } else if (recipe.universe) {
        screener.setUniverse(recipe.universe);
      }
      const previous = screener.savedScreens.find((s) => s.name === screenName) ?? null;
      useScreenerStore.getState().saveScreen(screenName);
      return done(
        `${previous ? `Replaced the saved screen "${screenName}"` : `Saved the screen as "${screenName}"`}${droppedCriteriaNote(recipe)}`,
        { kind: "screen", name: screenName, screen: previous },
      );
    }
    case "set_region":
      if (!intent.region) {
        return fail(`"${intent.raw}" is not a region`);
      }
      const previousRegion = useSettingsStore.getState().region;
      useSettingsStore.getState().setRegion(intent.region);
      return done(`Set the region to ${intent.region}`, { kind: "region", region: previousRegion });
    case "portfolio_add_position": {
      const { holding, problem } = intent;
      // No price given → incomplete arguments (re-pends), never a ₹0 holding.
      if (problem || holding.costBasis === null) {
        return fail(problem);
      }
      const portfolio = portfolioById(intent.portfolioId);
      if (!portfolio) {
        return fail("the portfolio it was proposed for no longer exists");
      }
      const added = usePortfoliosStore.getState().addHolding(portfolio.id, {
        ...holding,
        costBasis: holding.costBasis,
      });
      if (added === null) {
        return fail("the portfolio refused the holding"); // the store's holding rules
      }
      useWorkspaceStore.getState().openPanel("portfolio");
      return done(
        `Added ${holding.quantity} ${holding.symbol} @ ${formatPrice(holding.costBasis)} to the portfolio`,
        {
          kind: "holding-added",
          portfolioId: portfolio.id,
          holdingId: added,
          symbol: holding.symbol,
        },
      );
    }
    case "portfolio_update_position":
    case "portfolio_delete_position": {
      const { target, problem } = intent;
      if (problem || !target) {
        return fail(problem); // never guess which position to mutate
      }
      // Apply to exactly the lot the diff showed, in the portfolio it was
      // proposed against — gone means an honest failure, never another lot.
      const portfolio = portfolioById(intent.portfolioId);
      const index = portfolio?.holdings.findIndex((h) => h.id === target.id) ?? -1;
      if (!portfolio || index < 0) {
        return fail(`that ${target.symbol} lot is no longer in the portfolio`);
      }
      // The lot as it stands now (not as staged), so Undo restores exactly it.
      const preImage: PreImage = {
        kind: "holding",
        portfolioId: portfolio.id,
        holding: portfolio.holdings[index],
        index,
      };
      const store = usePortfoliosStore.getState();
      if (intent.name === "portfolio_delete_position") {
        store.removeHolding(portfolio.id, target.id);
        useWorkspaceStore.getState().openPanel("portfolio");
        return done(`Removed ${target.symbol} from the portfolio`, preImage);
      }
      const { holding } = intent;
      if (holding.costBasis === null) {
        return fail("no price given");
      }
      const costBasis = holding.costBasis;
      if (!store.updateHolding(portfolio.id, target.id, { ...holding, costBasis })) {
        return fail("the portfolio refused the update");
      }
      useWorkspaceStore.getState().openPanel("portfolio");
      return done(`Updated ${holding.symbol}: ${lotText(holding)}`, preImage);
    }
    case "save_layout":
      // Awaits the workspace save — only the async seam can apply it.
      return fail("saving a layout needs the async apply");
    case "unknown":
      return fail(`unknown action "${intent.raw}"`);
  }
}

/**
 * Put back what an applied data write replaced (the review's session Undo).
 * Restores the pre-image only; a target the user has since removed (the
 * portfolio, or the holding an add created) fails honestly instead of guessing.
 */
export function undoPreImage(preImage: PreImage): ApplyResult {
  switch (preImage.kind) {
    case "holding-added": {
      const portfolio = portfolioById(preImage.portfolioId);
      if (!portfolio?.holdings.some((h) => h.id === preImage.holdingId)) {
        return fail(`the added ${preImage.symbol} holding is no longer in the portfolio`);
      }
      usePortfoliosStore.getState().removeHolding(portfolio.id, preImage.holdingId);
      return done(`Removed the added ${preImage.symbol} holding`);
    }
    case "holding": {
      const store = usePortfoliosStore.getState();
      const portfolio = portfolioById(preImage.portfolioId);
      if (!portfolio) {
        return fail("the portfolio no longer exists");
      }
      const { holding, index } = preImage;
      const holdings = portfolio.holdings.some((h) => h.id === holding.id)
        ? portfolio.holdings.map((h) => (h.id === holding.id ? holding : h))
        : [...portfolio.holdings.slice(0, index), holding, ...portfolio.holdings.slice(index)];
      store.setAll(
        store.portfolios.map((p) => (p.id === portfolio.id ? { ...p, holdings } : p)),
        store.activeId,
      );
      return done(`Restored ${holding.symbol} ${lotText(holding)}`);
    }
    case "note": {
      const notes = useNotesStore.getState();
      if (preImage.scope === "") {
        notes.setGeneral(preImage.text);
      } else {
        notes.setSymbolNote(preImage.scope, preImage.text);
      }
      return done(`Restored the ${noteScopeLabel(preImage.scope)} note`);
    }
    case "screen": {
      const screener = useScreenerStore.getState();
      const { name, screen } = preImage;
      if (!screen) {
        screener.deleteScreen(name);
        return done(`Removed the saved screen "${name}"`);
      }
      screener.setSavedScreens([...screener.savedScreens.filter((s) => s.name !== name), screen]);
      return done(`Restored the saved screen "${name}"`);
    }
    case "watchlist-added":
      useSymbolsStore.getState().removeSymbol(preImage.symbol, preImage.region ?? null);
      return done(`Removed ${preImage.symbol} from your watchlist`);
    case "watchlist-removed": {
      const symbols = useSymbolsStore.getState();
      const { entry, index } = preImage;
      if (!symbols.entries.some((e) => entryKey(e) === entryKey(entry))) {
        symbols.setEntries([
          ...symbols.entries.slice(0, index),
          entry,
          ...symbols.entries.slice(index),
        ]);
      }
      return done(`Restored ${entry.symbol} to your watchlist`);
    }
    case "region":
      useSettingsStore.getState().setRegion(preImage.region);
      return done(`Set the region back to ${preImage.region}`);
  }
}

/** Apply a host action from its raw args — the label, or null when it did not land. */
export function applyHostAction(name: string, input: Record<string, unknown>): string | null {
  return applyIntent(parseHostAction(name, input)).label;
}

// ---------------------------------------------------------------------------
// Async apply seam + publish ack (R10 §3/§4)
// ---------------------------------------------------------------------------

/**
 * Apply a parsed host action, including the cases the synchronous path cannot
 * finish: `save_layout` (awaits the workspace save) and a backtest
 * `open_panel` (awaits its run). Everything else delegates to
 * {@link applyIntent}. Portfolio writes land in the portfolios store only —
 * the workspace blob owns holdings; nothing writes the sidecar positions
 * ledger, which is only read once as the legacy-import source. Same truth
 * contract: a label means the work landed; null re-pends with an honest failure.
 */
export async function applyIntentAsync(intent: HostIntent): Promise<ApplyResult> {
  if (intent.name === "open_panel" && intent.runId) {
    // An agent-started backtest: load its run into the backtest store (made
    // active) before opening the panel; a run the sidecar no longer holds
    // is an honest failure, never an empty panel narrated as opened.
    try {
      await useBacktestStore.getState().loadRun(intent.runId);
    } catch {
      return fail(`the backtest run ${intent.runId} is no longer available`);
    }
  }
  if (intent.name === "save_layout") {
    try {
      await saveWorkspace(intent.layoutName);
    } catch {
      return fail("the layout could not be saved"); // not mounted / sidecar down
    }
    return done(`Saved the layout as "${intent.layoutName}"`);
  }
  if (
    intent.name === "add_to_watchlist" &&
    intent.assetClass === "equity" &&
    intent.symbol &&
    !tracksRegionless(intent.symbol)
  ) {
    return addResolvedEquity(intent.symbol);
  }
  return applyIntent(intent);
}

/** The slice of the `GET /resolve` reply (`sidecar/routers/resolve.py`) the
 *  watchlist add reads. */
interface ResolveReply {
  resolved: { symbol: string; name: string; region?: string } | null;
  needs_disambiguation: boolean;
  candidates: { symbol: string; name: string }[];
}

/**
 * Add a model-supplied equity to the watchlist through the ONE resolution
 * policy (`GET /resolve`, the same decision the mention picker and every agent
 * tool honour): a bound listing is added under its resolved symbol and the
 * label says so; an ambiguous or unresolved name fails with the candidates —
 * never a verbatim invented ticker that sits on the watchlist as a blank row.
 */
async function addResolvedEquity(raw: string): Promise<ApplyResult> {
  let reply: ResolveReply;
  try {
    reply = await sidecarGet<ResolveReply>("/resolve", { q: raw });
  } catch {
    return fail(`could not resolve "${raw}" — the sidecar did not answer`);
  }
  const choices = (reply.candidates ?? [])
    .slice(0, 4)
    .map((c) => `${c.symbol} (${c.name})`)
    .join(", ");
  if (!reply.resolved) {
    return fail(
      reply.needs_disambiguation
        ? `"${raw}" matches more than one listing — did you mean: ${choices}?`
        : `"${raw}" did not resolve to a listing${choices ? ` — did you mean: ${choices}?` : ""}`,
    );
  }
  const symbol = reply.resolved.symbol.toUpperCase();
  const { region } = reply.resolved;
  const from = symbol === raw ? "" : ` (resolved from "${raw}")`;
  // Idempotence is on the listing, not the ticker (R15-DATA-002): "Amalgamated
  // Financial" is AMAL · US, which a region-less AMAL (Amal Ltd in an IN
  // session) is not. A region-less entry is whatever the bare ticker binds to
  // under the session region, so ask the one resolution policy for that.
  let tracked = useSymbolsStore
    .getState()
    .entries.some((e) => e.symbol.toUpperCase() === symbol && e.region === region);
  if (!tracked && tracksRegionless(symbol)) {
    try {
      const bare = await sidecarGet<ResolveReply>("/resolve", { q: symbol });
      tracked = bare.resolved?.region === region;
    } catch {
      return fail(`could not resolve "${symbol}" — the sidecar did not answer`);
    }
  }
  if (tracked) {
    return done(`${symbol} is already on your watchlist${from}`);
  }
  useSymbolsStore.getState().addSymbol(symbol, "equity", region);
  return done(`Added ${symbol} to your watchlist${from}`, {
    kind: "watchlist-added",
    symbol,
    region,
  });
}

/** A region-less (session-following) entry of `symbol` is tracked: the listing
 *  a bare ticker names, the only one the sync path can judge without /resolve. */
function tracksRegionless(symbol: string): boolean {
  return useSymbolsStore
    .getState()
    .entries.some((e) => e.symbol.toUpperCase() === symbol && e.region === undefined);
}

/** {@link applyIntentAsync} from raw args — the label, or null when it did not land. */
export async function applyHostActionAsync(
  name: string,
  input: Record<string, unknown>,
): Promise<string | null> {
  return (await applyIntentAsync(parseHostAction(name, input))).label;
}

/** How a host-action apply resolved — the ack vocabulary (D39 §4). `staged` is
 *  non-terminal: an AUTO-session change that is not auto-applicable is waiting
 *  for the user's review; a later applied/failed ack replaces it. */
export type PublishAckStatus = "applied" | "kept_previous" | "failed" | "staged";

/** Map a host-action apply label onto the ack status: null → failed, a "Kept …"
 *  arbitration (shrink guard / stale run) → kept_previous, else applied. Generic
 *  across every host action (R13 JARVIS): only publish_brief ever labels "Kept",
 *  so this reduces to null→failed / else→applied for the rest. */
export function publishAckStatus(label: string | null): PublishAckStatus {
  if (label === null) {
    return "failed";
  }
  return label.startsWith("Kept") ? "kept_previous" : "applied";
}

/** The generic host-action descriptor threaded on the ack (R13 JARVIS 1a) so
 *  the runtime's grounded tool-result can NAME what resolved (action +
 *  symbol/panel). Additive to the publish_brief brief-identity payload. */
export interface HostActionAckDetail {
  action: string;
  symbol?: string;
  panel?: string;
  /** set_chart_indicators keys the chart did not know and did not apply, or the
   *  screener criteria (write_screener_filters / save_screen) that did not parse,
   *  each with its reason ("roe: value must be a number"). */
  dropped?: string[];
}

/** Build the light ack descriptor from a host action's name + input — the
 *  symbol or panel it targets, when the input carries one. */
export function hostActionAckDetail(
  name: string,
  input: Record<string, unknown>,
): HostActionAckDetail {
  const symbol = str(input, "symbol");
  const panel = str(input, "panel");
  const dropped =
    name === "set_chart_indicators"
      ? splitIndicatorKeys(input).dropped
      : name === "write_screener_filters" || name === "save_screen"
        ? parseScreenRecipe(input).recipe.dropped
        : [];
  return {
    action: name,
    ...(symbol ? { symbol } : {}),
    ...(panel ? { panel } : {}),
    ...(dropped.length ? { dropped } : {}),
  };
}

/**
 * Read back a host-action outcome to the sidecar's action ledger
 * (`POST /agents/actions/ack`, Team RUNTIME) so the runtime can ground its
 * synthesized "dispatched to the panel" narration in the panel's reality
 * (E3.3, generalized to EVERY host action in R13 JARVIS 1a — was publish-only).
 * The publish_brief brief-identity payload is preserved; other actions carry a
 * light `detail` ({action, symbol/panel}). Fire-and-forget: an unreachable
 * sidecar must never block the apply path — a missing ack reads as "the panel
 * did not confirm" on the runtime side, which is the honest state.
 */
export function ackHostAction(
  toolCallId: string,
  status: PublishAckStatus,
  detail?: HostActionAckDetail,
): void {
  if (!toolCallId) {
    return;
  }
  const isPublish = detail?.action === "publish_brief";
  const brief = isPublish ? useBriefStore.getState().brief : null;
  void (async () => {
    const base = await getSidecarBaseUrl();
    await fetch(new URL("/agents/actions/ack", base).toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_call_id: toolCallId,
        status,
        ...(detail ? { detail } : {}),
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
