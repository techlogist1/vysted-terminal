import type { DockviewApi, Direction } from "dockview";

/**
 * Named dockview layout templates — the "taste" behind the agent's
 * `arrange_layout` host-action (PASS_B_RESEARCH.md §D.2, FR-091). The agent
 * picks a template by query intent (ticker → research-cockpit, "compare X vs Y"
 * → compare, broad market → macro-scan) and the host re-tiles the cockpit into a
 * coherent arrangement instead of dumping every panel into one tile — the fix
 * for the "opened everything in one tile" failure.
 *
 * Two-layer split for testability:
 *   - `planLayout` is a PURE function: template → a declarative `LayoutPlan`
 *     (panel ids + components + relative positions + maximize/focus). No dockview
 *     dependency, so it's exhaustively unit-testable.
 *   - `applyLayoutTemplate` is the imperative applier that drives the live
 *     dockview api from a plan: it reuses any already-open panel (by id) before
 *     adding, so re-running the same template is idempotent (no duplicate-id
 *     crash), then applies focus/maximize.
 */
export type LayoutTemplate = "single-focus" | "research-cockpit" | "compare" | "macro-scan";

/**
 * Every arrangeable panel, by canonical id (matches `default-layout.ts` + the
 * module specs). Broader than the template `PANEL` set below so a CUSTOM arrange
 * ("put the chart here and news there") can place any of them (Track B).
 */
const ARRANGEABLE: Record<string, { id: string; component: string }> = {
  chart: { id: "chart", component: "chart-panel" },
  "equity-overview": { id: "equity-overview", component: "equity-overview-panel" },
  watchlist: { id: "watchlist", component: "watchlist-panel" },
  news: { id: "news", component: "news-panel" },
  portfolio: { id: "portfolio", component: "portfolio-panel" },
  macro: { id: "macro", component: "macro-panel" },
  screener: { id: "screener", component: "screener-panel" },
  brief: { id: "brief", component: "brief-panel" },
  notes: { id: "notes", component: "notes-panel" },
};

/** Loose aliases the agent (or a user) might say, mapped to a canonical id. */
const PANEL_ALIASES: Record<string, string> = {
  equity: "equity-overview",
  overview: "equity-overview",
  "equity-overview-panel": "equity-overview",
  quote: "equity-overview",
  watch: "watchlist",
  "watch-list": "watchlist",
  positions: "portfolio",
  holdings: "portfolio",
  macroeconomics: "macro",
  economy: "macro",
  screen: "screener",
  research: "brief",
};

/** Resolve a free-text panel token to a canonical `{id, component}`, or `null`. */
export function resolvePanelToken(name: string): { id: string; component: string } | null {
  const key = (name || "")
    .trim()
    .toLowerCase()
    .replace(/[_\s]+/g, "-");
  if (key in ARRANGEABLE) {
    return ARRANGEABLE[key];
  }
  const aliased = PANEL_ALIASES[key];
  return aliased ? ARRANGEABLE[aliased] : null;
}

/** One panel in a custom arrange — a name + an optional explicit placement. */
export interface CustomPanelSpec {
  panel: string;
  direction?: "left" | "right" | "above" | "below" | "within";
  reference?: string;
}

/** Relative placement for a planned panel (mirrors dockview's `AddPanelOptions.position`). */
export interface PlannedPanelPosition {
  /** The panel `id` this one is placed relative to (NOT the component id). */
  referencePanel?: string;
  direction?: "left" | "right" | "above" | "below" | "within";
}

/** One panel in a plan: its dockview panel `id` + the React `component` id it renders. */
export interface PlannedPanel {
  /** Stable dockview panel id (e.g. `"chart"`, `"equity-overview"`, `"news"`). */
  id: string;
  /** The registered React component id (e.g. `"chart-panel"`, `"news-panel"`). */
  component: string;
  position?: PlannedPanelPosition;
}

/** A declarative, dockview-free description of a cockpit arrangement. */
export interface LayoutPlan {
  panels: PlannedPanel[];
  /** Panel id to activate/focus after placement (e.g. the chart). */
  focus?: string;
  /** Panel id to maximize (single-tile focus mode), if any. */
  maximize?: string;
}

/** Options influencing a plan — symbols are consumed by the chart-command channel,
 *  not the layout itself (the layout is symbol-agnostic; included for parity with
 *  the host-action signature so a caller can pass through without branching). */
export interface LayoutPlanOptions {
  symbol?: string;
  symbols?: string[];
}

// Panel id ↔ component id are NOT interchangeable: the dockview panel `id` is the
// short module name (`"chart"`, `"equity-overview"`, `"news"`, `"macro"`,
// `"screener"`) — matching the default layout (`src/config/default-layout.ts`)
// and the module specs — while the `component` is the registered React component
// id (the `-panel` suffix). Centralised here so the two never drift.
const PANEL = {
  chart: { id: "chart", component: "chart-panel" },
  equityOverview: { id: "equity-overview", component: "equity-overview-panel" },
  news: { id: "news", component: "news-panel" },
  macro: { id: "macro", component: "macro-panel" },
  screener: { id: "screener", component: "screener-panel" },
  brief: { id: "brief", component: "brief-panel" },
  notes: { id: "notes", component: "notes-panel" },
} as const;

/**
 * PURE planner: map a template name to its `LayoutPlan`. No dockview, no side
 * effects — fully unit-testable. `opts` is reserved for the chart-command channel
 * (symbol/symbols); the layout shape itself is symbol-agnostic.
 */
export function planLayout(template: LayoutTemplate, opts?: LayoutPlanOptions): LayoutPlan {
  // `opts` (symbol/symbols) is part of the host-action signature for parity, but
  // the layout SHAPE is symbol-agnostic — symbols ride the chart-command channel,
  // not the tiling. Referenced here so the contract param stays without lint noise.
  void opts;
  switch (template) {
    case "single-focus":
      // Just the chart, maximized — the quick "show me AAPL".
      return {
        panels: [{ id: PANEL.chart.id, component: PANEL.chart.component }],
        focus: PANEL.chart.id,
        maximize: PANEL.chart.id,
      };

    case "research-cockpit":
      // FLAGSHIP ("research NVDA"): chart anchors the left; the right column
      // stacks equity-overview (top), the BriefPanel (the B+A synthesized brief),
      // and news (bottom) — so the cited brief docks BESIDE the chart, never as a
      // tab in the chart group. The agent populates the brief via publish_brief.
      return {
        panels: [
          { id: PANEL.chart.id, component: PANEL.chart.component },
          {
            id: PANEL.equityOverview.id,
            component: PANEL.equityOverview.component,
            position: { referencePanel: PANEL.chart.id, direction: "right" },
          },
          {
            id: PANEL.brief.id,
            component: PANEL.brief.component,
            position: { referencePanel: PANEL.equityOverview.id, direction: "below" },
          },
          {
            id: PANEL.news.id,
            component: PANEL.news.component,
            position: { referencePanel: PANEL.brief.id, direction: "below" },
          },
        ],
        focus: PANEL.brief.id,
      };

    case "compare":
      // "NVDA vs AMD". The DUAL-SYMBOL OVERLAY is driven separately by the
      // lead's host-action via the chart-command channel (it pushes the second
      // symbol as an overlay onto the chart) — this template's ONLY job is the
      // chart-focused layout: a single maximized chart for the comparison to
      // render into. Do NOT add a second chart panel here; the overlay is not a
      // second panel.
      return {
        panels: [{ id: PANEL.chart.id, component: PANEL.chart.component }],
        focus: PANEL.chart.id,
        maximize: PANEL.chart.id,
      };

    case "macro-scan":
      // "what's leading today": macro anchors; chart to its right; screener below.
      //
      // NOTE: §D.2 envisions a sector-heatmap + rotation-quadrant here, but no
      // dedicated heatmap panel id exists yet — the macro panel stands in as the
      // market-overview anchor until one ships. Swap `PANEL.macro` for the
      // heatmap entry when it lands.
      return {
        panels: [
          { id: PANEL.macro.id, component: PANEL.macro.component },
          {
            id: PANEL.chart.id,
            component: PANEL.chart.component,
            position: { referencePanel: PANEL.macro.id, direction: "right" },
          },
          {
            id: PANEL.screener.id,
            component: PANEL.screener.component,
            position: { referencePanel: PANEL.macro.id, direction: "below" },
          },
        ],
        focus: PANEL.macro.id,
      };
  }
}

/**
 * PURE planner for a CUSTOM arrange (Track B — "one panel here, one there"):
 * turn an ordered list of panel specs into a `LayoutPlan` the same generic
 * `applyPlan` lands. Unknown panel tokens are dropped (never crash). The first
 * panel anchors; each later panel honours an explicit `direction`/`reference`
 * when given, else falls back to a coherent default — the 2nd panel beside the
 * anchor (right), the rest stacking below the previous — so a bare list still
 * produces a sensible side-by-side / column arrangement rather than one tile.
 */
export function planCustom(specs: CustomPanelSpec[], opts?: LayoutPlanOptions): LayoutPlan {
  void opts; // symbols ride the chart-command channel, not the tiling (parity).
  const panels: PlannedPanel[] = [];
  const placedIds = new Set<string>();
  let prevId: string | undefined;

  for (const spec of specs) {
    const resolved = resolvePanelToken(spec.panel);
    if (!resolved || placedIds.has(resolved.id)) {
      continue; // unknown or duplicate — skip, don't crash
    }
    let position: PlannedPanelPosition | undefined;
    if (prevId !== undefined) {
      const ref = spec.reference ? resolvePanelToken(spec.reference)?.id : undefined;
      const direction = spec.direction ?? (panels.length === 1 ? "right" : "below");
      position = { referencePanel: ref ?? prevId, direction };
    }
    panels.push({ id: resolved.id, component: resolved.component, position });
    placedIds.add(resolved.id);
    prevId = resolved.id;
  }

  return { panels, focus: panels[0]?.id };
}

/**
 * IMPERATIVE applier for a custom arrange — mirrors `applyLayoutTemplate`'s
 * rAF-batched apply but from a `planCustom` plan. Idempotent via the shared
 * `applyPlan` (reuses already-open panels by id).
 */
export function applyCustomLayout(
  api: DockviewApi,
  specs: CustomPanelSpec[],
  opts?: LayoutPlanOptions,
): void {
  const plan = planCustom(specs, opts);
  if (plan.panels.length === 0) {
    return;
  }
  const run = () => applyPlan(api, plan);
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(run);
  } else {
    run();
  }
}

/**
 * IMPERATIVE applier: drive the live dockview api from a template's plan.
 *
 * Idempotent — re-running the same template reuses already-open panels (looked
 * up by `id` via `api.getPanel`) instead of re-adding them, so dockview's
 * id-uniqueness invariant never trips. A planned position's `referencePanel` is
 * honoured only when that reference is actually present at add time (already open
 * or placed earlier in this same pass); otherwise the panel is added with no
 * position so it still lands (mirrors `applyDefaultLayout`'s placement guard).
 *
 * Per-panel minimum-size constraints are applied automatically by `PanelHost`'s
 * `onDidAddPanel` subscription, so we never call `setConstraints` here.
 *
 * The whole re-tile is wrapped in a single `requestAnimationFrame` (when
 * available) so dockview batches the add/move/maximize work into one layout
 * pass; in a non-browser/test environment (no rAF) it runs synchronously.
 */
export function applyLayoutTemplate(
  api: DockviewApi,
  template: LayoutTemplate,
  opts?: LayoutPlanOptions,
): void {
  const plan = planLayout(template, opts);
  const run = () => applyPlan(api, plan);

  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(run);
  } else {
    run();
  }
}

// --- fit-aware arrangement (Track 4) ----------------------------------------
//
// A multi-panel template crammed onto a small display reads as chaos. The
// `fitLayoutTemplate` wrapper reads the live viewport width and DOWNGRADES a
// panel-heavy template to a layout that genuinely fits — for research that means
// the ESSENTIALS (chart + brief), so the depth is still visible and the agent can
// say "click any ticker to go deeper" rather than vomiting four panels. A wide
// display gets the full template unchanged. This is deterministic + invisible to
// the agent (the bulletproof safety net); the agent is ALSO made viewport-aware
// via the terminal snapshot so it self-selects well, but this guard catches a
// misfit even if the agent ignores the signal.

/** Width (px) the 4-panel research-cockpit needs; below it → chart + brief only. */
const RESEARCH_COCKPIT_MIN_WIDTH = 1180;
/** Width (px) the 3-panel macro-scan needs; below it → a single maximized focus. */
const MACRO_SCAN_MIN_WIDTH = 1080;
/** Assumed width when dockview hasn't measured yet (comfortable default — never
 *  downgrade on an unknown dimension). */
const DEFAULT_FIT_WIDTH = 1440;

/** What `fitLayoutTemplate` actually applied — so a caller can phrase an honest
 *  "showing the essentials on this screen" message when it downgraded. */
export interface FitResult {
  applied: LayoutTemplate | "essentials-research";
  downgraded: boolean;
}

/** The 2-panel ESSENTIALS research layout: chart anchors the left, the brief
 *  docks beside it — the small-screen fallback for the research-cockpit so the
 *  cited brief (the star of a research turn) is never hidden. */
function essentialsResearchPlan(): LayoutPlan {
  return {
    panels: [
      { id: PANEL.chart.id, component: PANEL.chart.component },
      {
        id: PANEL.brief.id,
        component: PANEL.brief.component,
        position: { referencePanel: PANEL.chart.id, direction: "right" },
      },
    ],
    focus: PANEL.brief.id,
  };
}

/**
 * Apply a layout template, fitting it to the current viewport. A panel-heavy
 * template on a narrow display is downgraded to a layout that actually fits
 * (research-cockpit → chart + brief; macro-scan → single focus); a wide display
 * gets the requested template unchanged. Returns what was applied so the caller
 * can phrase an honest message. The fit decision reads `api.width` at apply time
 * (most-recent dimension), guarding the `> 0` not-yet-measured case.
 */
export function fitLayoutTemplate(
  api: DockviewApi,
  template: LayoutTemplate,
  opts?: LayoutPlanOptions,
): FitResult {
  const width = typeof api.width === "number" && api.width > 0 ? api.width : DEFAULT_FIT_WIDTH;

  if (template === "research-cockpit" && width < RESEARCH_COCKPIT_MIN_WIDTH) {
    const plan = essentialsResearchPlan();
    const run = () => applyPlan(api, plan);
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(run);
    } else {
      run();
    }
    return { applied: "essentials-research", downgraded: true };
  }
  if (template === "macro-scan" && width < MACRO_SCAN_MIN_WIDTH) {
    applyLayoutTemplate(api, "single-focus", opts);
    return { applied: "single-focus", downgraded: true };
  }
  applyLayoutTemplate(api, template, opts);
  return { applied: template, downgraded: false };
}

// --- macOS Window→Layout MENU modes (the finance cockpits) ------------------
//
// The native menu (`lib.rs` install_layout_menu) labels these Fundamental /
// Technical / Macro / Compare / Reset and emits a payload id the menu-bridge maps
// here. UNLIKE the agent's ADDITIVE `arrange_layout` (which reuses open panels and
// is viewport-fit-downgraded), a menu mode is a DETERMINISTIC "switch to this
// cockpit": it CLEARS the grid first, then tiles exactly the mode's panel set — so
// a click always opens that mode's FULL multi-panel layout regardless of what was
// open before, and never fit-downgrades to a single panel (Bug-4: "Fundamental"
// was showing just the brief). The payload ids are historical fossils
// (research-cockpit / single-focus / macro-scan / compare) — read the role, not
// the literal id.

/** Build a planned panel from an ARRANGEABLE id, optionally placed beside/below a ref. */
function modePanel(key: string, position?: PlannedPanelPosition): PlannedPanel {
  const p = ARRANGEABLE[key];
  return { id: p.id, component: p.component, position };
}

const MODE_PLANS: Record<string, LayoutPlan> = {
  // FUNDAMENTAL ANALYSIS — the single-company deep-dive: chart (price) anchors the
  // left; the equity-overview (the fundamentals / ratios / financials panel) and
  // the synthesised research brief stack on the right.
  "research-cockpit": {
    panels: [
      modePanel("chart"),
      modePanel("equity-overview", { referencePanel: "chart", direction: "right" }),
      modePanel("brief", { referencePanel: "equity-overview", direction: "below" }),
    ],
    focus: "equity-overview",
  },
  // TECHNICAL ANALYSIS — chart-dominant (indicators ride the chart) with a
  // watchlist to flip symbols and news for catalysts.
  "single-focus": {
    panels: [
      modePanel("chart"),
      modePanel("watchlist", { referencePanel: "chart", direction: "right" }),
      modePanel("news", { referencePanel: "watchlist", direction: "below" }),
    ],
    focus: "chart",
  },
  // MACRO SCAN — the macro desk: macro anchor + chart + screener.
  "macro-scan": {
    panels: [
      modePanel("macro"),
      modePanel("chart", { referencePanel: "macro", direction: "right" }),
      modePanel("screener", { referencePanel: "macro", direction: "below" }),
    ],
    focus: "macro",
  },
  // COMPARE — side-by-side: the chart (carrying the dual-symbol overlay pushed via
  // the chart-command channel) beside the equity overview for the focused name.
  compare: {
    panels: [
      modePanel("chart"),
      modePanel("equity-overview", { referencePanel: "chart", direction: "right" }),
    ],
    focus: "chart",
  },
};

/** Menu-mode payload ids `applyLayoutMode` handles (excludes "default", which the
 *  bridge routes to `resetToDefaultLayout`). */
export const LAYOUT_MODE_IDS: ReadonlySet<string> = new Set(Object.keys(MODE_PLANS));

/**
 * Apply a macOS Layout-MENU mode: CLEAR the cockpit, then tile exactly the mode's
 * panel set (deterministic — the mode IS its panels, never layered onto the prior
 * state and never fit-downgraded). Synchronous (no rAF — which throttles to a halt
 * on an occluded WKWebView). Returns true if applied, false for an unknown id
 * (e.g. "default", handled by the caller via `resetToDefaultLayout`).
 */
export function applyLayoutMode(api: DockviewApi, modeId: string): boolean {
  const plan = MODE_PLANS[modeId];
  if (!plan) {
    return false;
  }
  api.clear();
  applyPlan(api, plan);
  return true;
}

// --- per-stock research SPACE (003 workspace OS) ----------------------------
//
// A "research space" is a dedicated, named workspace bundling ONE ticker's
// research surface: the chart (left) + the equity overview & synthesised brief
// (right column) + a notes scratchpad scoped to the ticker. Distinct from the
// agent's `research-cockpit` arrange — this CLEARS the cockpit first (it's a
// space, not an overlay) and includes the Notes panel, and it applies
// SYNCHRONOUSLY so the caller (`createResearchSpace`) can serialise the layout
// into a saved workspace on the very next line without racing an rAF.

/** Width (px) below which a research SPACE drops the equity-overview panel so the
 *  chart + brief + notes still fit cleanly. */
const RESEARCH_SPACE_MIN_WIDTH = 1180;

/**
 * Build a clean per-stock research space layout on `api`. Clears the current
 * cockpit, then tiles chart + (equity overview) + brief + notes. Fit-aware: a
 * narrow viewport drops the overview (chart + brief + notes). Synchronous — no
 * rAF — so a caller can immediately `api.toJSON()` the result. Symbol-agnostic:
 * the caller pushes the ticker via the chart-command channel + the notes scope.
 */
export function applyResearchSpaceLayout(api: DockviewApi): void {
  api.clear();
  const width = typeof api.width === "number" && api.width > 0 ? api.width : DEFAULT_FIT_WIDTH;
  const compact = width < RESEARCH_SPACE_MIN_WIDTH;
  const panels: PlannedPanel[] = [{ id: PANEL.chart.id, component: PANEL.chart.component }];
  let lastRightId: string = PANEL.chart.id;
  if (!compact) {
    panels.push({
      id: PANEL.equityOverview.id,
      component: PANEL.equityOverview.component,
      position: { referencePanel: PANEL.chart.id, direction: "right" },
    });
    lastRightId = PANEL.equityOverview.id;
  }
  panels.push({
    id: PANEL.brief.id,
    component: PANEL.brief.component,
    position: {
      referencePanel: lastRightId,
      direction: compact ? "right" : "below",
    },
  });
  panels.push({
    id: PANEL.notes.id,
    component: PANEL.notes.component,
    position: { referencePanel: PANEL.brief.id, direction: "below" },
  });
  applyPlan(api, { panels, focus: PANEL.brief.id });
}

/** Apply a resolved plan to the dockview api. Extracted so the rAF wrapper above
 *  stays a thin scheduler and the placement logic is testable in isolation. */
function applyPlan(api: DockviewApi, plan: LayoutPlan): void {
  // Track which panel ids are present so a later panel's `referencePanel` only
  // resolves against a panel that actually exists (open before this pass, or
  // added earlier within it).
  const present = new Set<string>(api.panels.map((p) => p.id));

  for (const panel of plan.panels) {
    const existing = api.getPanel(panel.id);
    if (existing) {
      // Reuse — idempotent re-tile. Don't move an already-open panel; dockview
      // re-tiling of live panels is jarring and risks orphaning the user's view.
      present.add(panel.id);
      continue;
    }

    const position = resolvePosition(panel.position, present);
    api.addPanel({
      id: panel.id,
      component: panel.component,
      position,
    });
    present.add(panel.id);
  }

  // Maximize takes precedence over a plain focus (single-tile focus mode). Exit
  // any prior maximized group first so re-tiling from a maximized state is clean.
  if (plan.maximize) {
    const target = api.getPanel(plan.maximize);
    if (target) {
      if (api.hasMaximizedGroup()) {
        api.exitMaximizedGroup();
      }
      api.maximizeGroup(target);
      return;
    }
  }

  // Not a maximize template — make sure we're not stuck maximized from a prior
  // single-focus/compare pass, then activate the focus panel.
  if (api.hasMaximizedGroup()) {
    api.exitMaximizedGroup();
  }
  if (plan.focus) {
    api.getPanel(plan.focus)?.api.setActive();
  }
}

/** Translate a planned position into a dockview `addPanel` position, dropping it
 *  when the reference panel isn't present yet (so the panel still lands). */
function resolvePosition(
  position: PlannedPanelPosition | undefined,
  present: Set<string>,
): { referencePanel: string; direction: Direction } | undefined {
  if (!position?.referencePanel || !present.has(position.referencePanel)) {
    return undefined;
  }
  return {
    referencePanel: position.referencePanel,
    direction: (position.direction ?? "within") as Direction,
  };
}
