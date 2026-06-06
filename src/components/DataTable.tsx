"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * The ONE table primitive (PRODUCT_DESIGN_DECISIONS §11). Every tabular / numeric
 * surface — equity-overview statements, screener, analyst, earnings, SEC,
 * portfolio, watchlist — renders through this instead of hand-rolling a `<table>`.
 *
 * It is generic and data-agnostic: a caller supplies column definitions plus rows
 * of arbitrary shape and a per-column `cell` renderer (or a `format` function that
 * derives the display string). The component owns the design law:
 *
 *  - Header cells: `text-micro` (11px) · weight-510 · `charcoal-400` · uppercase ·
 *    `px-3 py-1.5`. Numeric headers are right-aligned to their column.
 *  - Body cells: `text-body` (13px) · `px-3 py-1.5` (one rhythm for every dense
 *    table). Numeric cells are `text-right whitespace-nowrap tabular-nums`.
 *  - Three text tiers via the `tier` prop, never via colour-as-emphasis:
 *    primary `charcoal-100` · secondary `charcoal-400` · tertiary `charcoal-500`.
 *  - Null / missing values render `—` in `charcoal-600`.
 *  - Optional sortable header — `aria-sort` + a quiet caret that is amber **only**
 *    on the active sort key (the table's one accent).
 *  - Optional sticky header (`sticky top-0`).
 *  - Optional grouped section-header rows.
 *  - An `action` column (icons, buttons) sits outside truncation.
 *
 * The component never formats numbers itself — that is the caller's `format`
 * (which must route through `@/lib/format`). It only owns alignment, tiers, and
 * the null fallback.
 */

/** The three foreground tiers (design §4). Maps to a `charcoal-*` text token. */
export type CellTier = "primary" | "secondary" | "tertiary";

const TIER_CLASS: Record<CellTier, string> = {
  primary: "text-charcoal-100",
  secondary: "text-charcoal-400",
  tertiary: "text-charcoal-500",
};

/** What a cell renders when its derived value is null/undefined. */
const NULL_GLYPH = "—";

/** A single column definition. `R` is the row shape. */
export interface DataColumn<R, K extends string = string> {
  /** Stable column id — also the sort key when the column is sortable. */
  key: K;
  /** Header label (uppercased by the header cell). Omit for an action column. */
  header?: React.ReactNode;
  /** Right-align the header + cells and apply `tabular-nums` (numeric column). */
  numeric?: boolean;
  /** This column is sortable — clicking its header cycles the sort. */
  sortable?: boolean;
  /** Default text tier for this column's cells (default `primary`). A row may
   *  still override per-cell via {@link cell}'s returned element. */
  tier?: CellTier;
  /** Explicit width (a CSS length or a `<col>` width). */
  width?: string;
  /** When true the cell truncates with an ellipsis (text columns); the title is
   *  the raw string for hover. Numeric columns never truncate. */
  truncate?: boolean;
  /** This is the trailing action column — it sits outside truncation and is not
   *  tinted/aligned as data (used for row edit/delete/remove controls). */
  action?: boolean;
  /**
   * Derive the display STRING for this column from a row. Return `null` for a
   * missing value (renders the null glyph). Mutually exclusive with {@link cell}.
   */
  format?: (row: R) => string | null;
  /**
   * Render a fully-custom cell body (a colour-coded value, a badge, a control).
   * Takes precedence over {@link format}. Return `null` for the null glyph.
   */
  cell?: (row: R) => React.ReactNode;
  /** Per-cell title attribute (hover) — defaults to the formatted string. */
  title?: (row: R) => string | undefined;
}

/** A grouped section header row spanning the full table width. */
export interface DataSection<R> {
  /** Section label (e.g. "Valuation"), `text-micro charcoal-500`. */
  label: string;
  /** The rows under this section. */
  rows: R[];
}

export interface DataTableSort<K extends string = string> {
  key: K;
  direction: "asc" | "desc";
}

interface DataTableProps<R, K extends string> {
  columns: DataColumn<R, K>[];
  /** Flat rows, OR grouped sections (use one, not both). */
  rows?: R[];
  sections?: DataSection<R>[];
  /** Stable React key for a row. */
  rowKey: (row: R, index: number) => string;
  /** Optional row click (whole-row drill-down). */
  onRowClick?: (row: R) => void;
  /** Mark a row selected (a calm luminance step, not colour). */
  isRowSelected?: (row: R) => boolean;
  /** Extra per-row className (tick-flash, hover overrides). */
  rowClassName?: (row: R) => string | undefined;
  /** Current sort + the setter (clicking a sortable header). */
  sort?: DataTableSort<K>;
  onSort?: (key: K) => void;
  /** Pin the header on scroll. */
  stickyHeader?: boolean;
  /** `table-fixed` + a `<colgroup>` from each column's `width`. Default true. */
  fixed?: boolean;
  /** Min-width so a squeezed panel scrolls horizontally rather than crushing. */
  minWidth?: string;
  /** A caption row rendered below the last body row (e.g. a sparse note). */
  footnote?: React.ReactNode;
  className?: string;
  "data-testid"?: string;
}

/**
 * Resolve a column's display string from a row (null → glyph elsewhere). With no
 * `format`, fall back to reading `row[key]` and coercing it to a string — so a
 * plain string/number column needs no boilerplate formatter.
 */
function formatted<R, K extends string>(col: DataColumn<R, K>, row: R): string | null {
  if (col.format) return col.format(row);
  const raw = (row as Record<string, unknown>)[col.key];
  if (raw === null || raw === undefined) return null;
  return typeof raw === "string" || typeof raw === "number" ? String(raw) : null;
}

/** A single body cell — owns alignment, tier, truncation, and the null glyph. */
function BodyCell<R, K extends string>({ col, row }: { col: DataColumn<R, K>; row: R }) {
  // An action column is chrome, not data: no tint, no alignment-as-number.
  if (col.action) {
    return (
      <td className="px-3 py-1.5 text-right whitespace-nowrap">
        {col.cell ? col.cell(row) : null}
      </td>
    );
  }

  const tier = TIER_CLASS[col.tier ?? "primary"];
  const custom = col.cell ? col.cell(row) : undefined;
  const text = custom === undefined ? formatted(col, row) : undefined;
  const isNull = custom === null || (custom === undefined && text === null);
  const title = col.title
    ? col.title(row)
    : !col.numeric && typeof text === "string"
      ? text
      : undefined;

  return (
    <td
      className={cn(
        "text-body px-3 py-1.5",
        isNull ? "text-charcoal-600" : tier,
        col.numeric && "text-right whitespace-nowrap tabular-nums",
        col.truncate && !col.numeric && "max-w-0 truncate",
      )}
      title={title}
    >
      {isNull ? NULL_GLYPH : custom !== undefined ? custom : text}
    </td>
  );
}

/**
 * The shared data-table. See the file header for the design contract.
 */
export function DataTable<R, K extends string = string>({
  columns,
  rows,
  sections,
  rowKey,
  onRowClick,
  isRowSelected,
  rowClassName,
  sort,
  onSort,
  stickyHeader = false,
  fixed = true,
  minWidth,
  footnote,
  className,
  "data-testid": testId,
}: DataTableProps<R, K>) {
  const hasWidths = columns.some((c) => c.width !== undefined);

  const renderRow = (row: R, index: number) => {
    const selected = isRowSelected?.(row) ?? false;
    return (
      <tr
        key={rowKey(row, index)}
        onClick={onRowClick ? () => onRowClick(row) : undefined}
        className={cn(
          "border-charcoal-800 border-b",
          onRowClick && "hover:bg-charcoal-800/50 cursor-pointer",
          selected && "bg-charcoal-800/40",
          rowClassName?.(row),
        )}
      >
        {columns.map((col) => (
          <BodyCell key={col.key} col={col} row={row} />
        ))}
      </tr>
    );
  };

  return (
    <table
      data-testid={testId}
      className={cn("w-full border-collapse", fixed && "table-fixed", minWidth, className)}
    >
      {fixed && hasWidths && (
        <colgroup>
          {columns.map((col) => (
            <col key={col.key} style={col.width ? { width: col.width } : undefined} />
          ))}
        </colgroup>
      )}
      <thead className={cn(stickyHeader && "bg-charcoal-900 sticky top-0 z-10")}>
        <tr className="border-charcoal-800 border-b">
          {columns.map((col) => {
            const active = sort?.key === col.key;
            const sortable = col.sortable && onSort;
            return (
              <th
                key={col.key}
                scope="col"
                title={typeof col.header === "string" ? col.header : undefined}
                aria-sort={
                  col.sortable
                    ? active
                      ? sort?.direction === "asc"
                        ? "ascending"
                        : "descending"
                      : "none"
                    : undefined
                }
                onClick={sortable ? () => onSort?.(col.key) : undefined}
                className={cn(
                  "text-micro text-charcoal-400 px-3 py-1.5",
                  col.numeric ? "text-right" : "text-left",
                  sortable && "hover:text-charcoal-200 cursor-pointer select-none",
                )}
              >
                {col.header}
                {col.sortable && active && (
                  <span aria-hidden className="ml-1 text-amber-400">
                    {sort?.direction === "asc" ? "▲" : "▼"}
                  </span>
                )}
              </th>
            );
          })}
        </tr>
      </thead>
      <tbody>
        {sections
          ? sections.map((section) => (
              <React.Fragment key={section.label}>
                <tr className="border-charcoal-800 border-b">
                  <th
                    scope="colgroup"
                    colSpan={columns.length}
                    className="text-micro text-charcoal-500 bg-charcoal-900/40 px-3 py-1.5 text-left"
                  >
                    {section.label}
                  </th>
                </tr>
                {section.rows.map((row, i) => renderRow(row, i))}
              </React.Fragment>
            ))
          : (rows ?? []).map((row, i) => renderRow(row, i))}
        {footnote && (
          <tr>
            <td colSpan={columns.length} className="text-caption text-charcoal-500 px-3 py-1.5">
              {footnote}
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
