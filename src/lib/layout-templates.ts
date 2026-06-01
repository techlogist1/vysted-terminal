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
