"use client";

/**
 * Chart toolbar disclosures — the one-row toolbar's Draw / Indicators /
 * Compare / Sync popovers (R7 chart redesign).
 *
 * The old surface stacked three toolbar rows of terse codes plus an always-on
 * ~50-entry indicator wall under the chart. This module collapses all of that
 * into quiet disclosure triggers on a single row. Each popover is a raised
 * surface (one ladder rung up, `charcoal-875`) with a 1px hairline-strong
 * border — never a shadow — and command-row styling inside. Popovers spell
 * full words ("Fibonacci retracement", "Relative Strength Index"); the
 * toolbar chips stay terse ("Fib Retr", "RSI").
 *
 * Dismissal: Escape (stops propagation so the chart panel's own Escape
 * handler does not also disarm an armed tool) and click-outside.
 */

import { useEffect, useRef, type ReactNode } from "react";

import { cn } from "@/lib/utils";

import { pointsRequired } from "./drawings/factory";
import { indicatorsByCategory, type IndicatorDef } from "./indicators";
import type { DrawingKind } from "../../../types/drawings";

// ---------------------------------------------------------------------------
// Draw tool catalog — full names for the popover, terse labels for chips
// ---------------------------------------------------------------------------

/** One drawing tool: spelled-out popover name + terse chip label. */
export interface DrawToolDef {
  kind: DrawingKind;
  /** Full name shown in the Draw popover ("Fibonacci retracement"). */
  name: string;
  /** Terse label for the armed-tool chip + drawings inspector ("Fib Retr"). */
  chipLabel: string;
}

/** The ten drawing tools, in display order. */
export const DRAW_TOOLS: readonly DrawToolDef[] = [
  { kind: "trendline", name: "Trendline", chipLabel: "Trend" },
  { kind: "horizontal-line", name: "Horizontal line", chipLabel: "H-Line" },
  { kind: "vertical-line", name: "Vertical line", chipLabel: "V-Line" },
  { kind: "ray", name: "Ray", chipLabel: "Ray" },
  { kind: "rectangle", name: "Rectangle", chipLabel: "Rect" },
  { kind: "ellipse", name: "Ellipse", chipLabel: "Ellipse" },
  { kind: "fib-retracement", name: "Fibonacci retracement", chipLabel: "Fib Retr" },
  { kind: "fib-extension", name: "Fibonacci extension", chipLabel: "Fib Ext" },
  { kind: "parallel-channel", name: "Parallel channel", chipLabel: "Channel" },
  { kind: "text", name: "Text label", chipLabel: "Text" },
];

/** kind → terse chip label, so chips read "Fib Retr", not "fib-retracement". */
export const DRAWING_CHIP_LABELS: Record<DrawingKind, string> = Object.fromEntries(
  DRAW_TOOLS.map((tool) => [tool.kind, tool.chipLabel]),
) as Record<DrawingKind, string>;

// ---------------------------------------------------------------------------
// Shared row styling — command-row treatment inside every popover
// ---------------------------------------------------------------------------

function rowClass(active: boolean): string {
  return cn(
    "rounded-control text-body flex h-8 w-full items-center gap-2 px-2 text-left font-mono transition-colors",
    active
      ? "bg-charcoal-850 text-charcoal-100"
      : "text-charcoal-300 hover:bg-charcoal-850 hover:text-charcoal-100",
  );
}

/** ASCII bracket toggle marker — the design system's iconography. */
function ToggleMarker({ on }: { on: boolean }) {
  return (
    <span aria-hidden className={cn("shrink-0", on ? "text-charcoal-200" : "text-charcoal-500")}>
      {on ? "[x]" : "[ ]"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// ToolbarDisclosure — trigger + raised hairline popover
// ---------------------------------------------------------------------------

interface ToolbarDisclosureProps {
  /** Visible trigger label ("Draw", "Indicators", ...). */
  label: string;
  /** Active-item count rendered after the label when > 0. */
  count?: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Accessible name for the popover region. */
  menuLabel: string;
  /** Tailwind width class for the popover ("w-72", "w-96", ...). */
  widthClass: string;
  children: ReactNode;
}

export function ToolbarDisclosure({
  label,
  count,
  open,
  onOpenChange,
  menuLabel,
  widthClass,
  children,
}: ToolbarDisclosureProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        // Stop here so the chart panel's window-level Escape handler does not
        // also disarm an armed drawing tool / deselect a drawing.
        event.stopPropagation();
        onOpenChange(false);
      }
    };
    const onPointerDown = (event: MouseEvent) => {
      const root = rootRef.current;
      if (root && event.target instanceof Node && !root.contains(event.target)) {
        onOpenChange(false);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, [open, onOpenChange]);

  const hasCount = typeof count === "number" && count > 0;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => onOpenChange(!open)}
        aria-expanded={open}
        aria-haspopup="true"
        className={cn(
          "rounded-control text-caption flex h-6 items-center gap-1 px-2 font-mono transition-colors",
          open
            ? "bg-charcoal-875 text-charcoal-100"
            : hasCount
              ? "text-charcoal-200 hover:bg-charcoal-875 hover:text-charcoal-100"
              : "text-charcoal-400 hover:bg-charcoal-875 hover:text-charcoal-100",
        )}
      >
        {label}
        {hasCount ? <span className="text-charcoal-200">{count}</span> : null}
        <span aria-hidden className="text-charcoal-500">
          ▾
        </span>
      </button>
      {open ? (
        <div
          role="group"
          aria-label={menuLabel}
          className={cn(
            "rounded-control bg-charcoal-875 absolute top-full left-0 z-30 mt-1 border p-1",
            widthClass,
          )}
          style={{ borderColor: "var(--hairline-strong)" }}
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// DrawMenu — ten tools, full names, points-required meta
// ---------------------------------------------------------------------------

interface DrawMenuProps {
  activeTool: DrawingKind | null;
  onArm: (kind: DrawingKind) => void;
}

export function DrawMenu({ activeTool, onArm }: DrawMenuProps) {
  return (
    <div className="flex flex-col">
      {DRAW_TOOLS.map((tool) => {
        const armed = activeTool === tool.kind;
        const points = pointsRequired(tool.kind);
        return (
          <button
            key={tool.kind}
            type="button"
            onClick={() => onArm(tool.kind)}
            aria-pressed={armed}
            className={rowClass(armed)}
          >
            <span className="min-w-0 flex-1 truncate">{tool.name}</span>
            {/* Decoration only — aria-hidden keeps the accessible name = tool name. */}
            <span aria-hidden className="text-micro text-charcoal-500 shrink-0">
              {points} {points === 1 ? "point" : "points"}
            </span>
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// IndicatorsMenu — search + grouped toggle rows over the 50-entry catalog
// ---------------------------------------------------------------------------

interface IndicatorsMenuProps {
  selected: ReadonlySet<string>;
  query: string;
  onQueryChange: (query: string) => void;
  onToggle: (key: string) => void;
  onClearAll: () => void;
}

/** True when every whitespace token of `query` matches the indicator's text. */
function matchesQuery(indicator: IndicatorDef, query: string): boolean {
  const haystack = `${indicator.menuLabel} ${indicator.label} ${indicator.key}`.toLowerCase();
  return query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((token) => haystack.includes(token));
}

export function IndicatorsMenu({
  selected,
  query,
  onQueryChange,
  onToggle,
  onClearAll,
}: IndicatorsMenuProps) {
  const groups = indicatorsByCategory()
    .map((group) => ({
      ...group,
      indicators: group.indicators.filter((indicator) => matchesQuery(indicator, query)),
    }))
    .filter((group) => group.indicators.length > 0);

  return (
    <div className="flex flex-col">
      <input
        // Search is the popover's primary affordance — focus lands here on open.
        autoFocus
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        aria-label="Search indicators"
        placeholder="Search indicators"
        spellCheck={false}
        className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 rounded-control text-body placeholder:text-charcoal-500 focus-visible:border-charcoal-500 mb-1 h-7 w-full border px-2 font-mono outline-none"
      />
      <div className="max-h-80 overflow-y-auto">
        {groups.length === 0 ? (
          <p className="text-charcoal-500 text-caption px-2 py-2 font-mono">
            No indicators match &ldquo;{query}&rdquo;
          </p>
        ) : (
          groups.map((group) => (
            <div key={group.category}>
              <div className="text-charcoal-500 text-micro px-2 pt-2 pb-1 font-mono">
                {group.label}
              </div>
              {group.indicators.map((indicator) => {
                const active = selected.has(indicator.key);
                return (
                  <button
                    key={indicator.key}
                    type="button"
                    onClick={() => onToggle(indicator.key)}
                    aria-pressed={active}
                    className={rowClass(active)}
                  >
                    <ToggleMarker on={active} />
                    <span className="min-w-0 flex-1 truncate">{indicator.menuLabel}</span>
                  </button>
                );
              })}
            </div>
          ))
        )}
      </div>
      {selected.size > 0 ? (
        <button
          type="button"
          onClick={onClearAll}
          aria-label="Clear all indicators"
          className="text-charcoal-400 hover:text-charcoal-100 rounded-control hover:bg-charcoal-850 text-caption mt-1 flex h-6 w-full items-center px-2 text-left font-mono transition-colors"
        >
          Clear all ({selected.size})
        </button>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CompareMenu — second-symbol overlay input
// ---------------------------------------------------------------------------

interface CompareMenuProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function CompareMenu({ value, onChange, onSubmit }: CompareMenuProps) {
  return (
    <form
      className="flex flex-col gap-1 p-1"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <p className="text-charcoal-500 text-caption font-mono">
        Overlay a second symbol on this chart.
      </p>
      <div className="flex items-center gap-1">
        <input
          // The symbol field is the popover's only input — focus lands here.
          autoFocus
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-label="Compare symbol"
          placeholder="Symbol"
          spellCheck={false}
          className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 rounded-control text-body placeholder:text-charcoal-500 focus-visible:border-charcoal-500 h-7 min-w-0 flex-1 border px-2 font-mono uppercase outline-none"
        />
        <button
          type="submit"
          className="rounded-control bg-charcoal-850 text-charcoal-200 hover:bg-charcoal-800 hover:text-charcoal-100 text-caption h-6 shrink-0 px-2 font-mono whitespace-nowrap transition-colors"
        >
          Add
        </button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// SyncMenu — the three opt-in sync flavors, spelled out
// ---------------------------------------------------------------------------

type SyncFlavor = "crosshair" | "visibleRange" | "symbol";

const SYNC_FLAVORS: readonly { flavor: SyncFlavor; name: string }[] = [
  { flavor: "crosshair", name: "Crosshair" },
  { flavor: "visibleRange", name: "Visible range" },
  { flavor: "symbol", name: "Symbol" },
];

interface SyncMenuProps {
  subscriptions: Record<SyncFlavor, boolean>;
  onToggle: (flavor: SyncFlavor) => void;
}

export function SyncMenu({ subscriptions, onToggle }: SyncMenuProps) {
  return (
    <div className="flex flex-col">
      <p className="text-charcoal-500 text-caption px-2 pt-1 pb-2 font-mono">
        Link this chart with other open charts.
      </p>
      {SYNC_FLAVORS.map(({ flavor, name }) => {
        const active = subscriptions[flavor];
        return (
          <button
            key={flavor}
            type="button"
            onClick={() => onToggle(flavor)}
            aria-pressed={active}
            aria-label={`Sync ${flavor}`}
            className={rowClass(active)}
          >
            <ToggleMarker on={active} />
            <span className="min-w-0 flex-1 truncate">{name}</span>
          </button>
        );
      })}
    </div>
  );
}
