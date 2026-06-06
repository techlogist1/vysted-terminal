"use client";

import { Trash2, Plus, FolderPlus } from "lucide-react";

import { Button } from "@/components/ui/button";

import type {
  CriterionGroup,
  ScreenerCriterion,
  ScreenerNumericField,
  ScreenerStringField,
} from "../../../types/screener";

/**
 * Recursive nested AND/OR group editor (FR-122 / SC-033).
 *
 * Each group owns its own AND/OR combinator, an "Add criterion" (a leaf) and an
 * "Add group" (a nested sub-group, nestable to any depth). The shape it edits is
 * the EXISTING recursive `CriterionGroup` wire contract — the backend already
 * evaluates arbitrary nesting (`_evaluate_group`), so this is purely a frontend
 * surface over a tree the server understands. Controlled: it takes a value +
 * `onChange` and never reaches into a store, so it composes at any depth.
 */

const NUMERIC_FIELDS: { value: ScreenerNumericField; label: string }[] = [
  { value: "market_cap", label: "Market cap" },
  { value: "pe_ratio", label: "P/E ratio" },
  { value: "forward_pe", label: "Forward P/E" },
  { value: "peg_ratio", label: "PEG ratio" },
  { value: "price_to_book", label: "Price / Book" },
  { value: "price_to_sales", label: "Price / Sales" },
  { value: "ev_to_ebitda", label: "EV / EBITDA" },
  { value: "book_value", label: "Book value" },
  { value: "dividend_yield", label: "Dividend yield (frac, 0.02 = 2%)" },
  { value: "eps", label: "EPS" },
  { value: "beta", label: "Beta" },
  { value: "roe", label: "ROE (frac, 0.2 = 20%)" },
  { value: "roa", label: "ROA (frac)" },
  { value: "gross_margin", label: "Gross margin (frac)" },
  { value: "operating_margin", label: "Operating margin (frac)" },
  { value: "profit_margin", label: "Net margin (frac)" },
  { value: "debt_to_equity", label: "Debt / Equity (ratio)" },
  { value: "current_ratio", label: "Current ratio" },
  { value: "quick_ratio", label: "Quick ratio" },
  { value: "revenue_growth", label: "Revenue growth (frac)" },
  { value: "earnings_growth", label: "Earnings growth (frac)" },
  { value: "fifty_two_week_high", label: "52w high" },
  { value: "fifty_two_week_low", label: "52w low" },
  { value: "fifty_two_week_change", label: "1y change (frac)" },
  { value: "held_percent_insiders", label: "Insider/promoter holding (frac)" },
  { value: "held_percent_institutions", label: "Institutional holding (frac)" },
  { value: "price", label: "Price" },
  { value: "change_percent_1d", label: "1-day %" },
  { value: "volume", label: "Volume" },
];

const STRING_FIELDS: { value: ScreenerStringField; label: string }[] = [
  { value: "sector", label: "Sector" },
  { value: "industry", label: "Industry" },
  { value: "currency", label: "Currency" },
];

const NUMERIC_OPERATORS: { value: "gt" | "lt" | "gte" | "lte" | "between"; label: string }[] = [
  { value: "gt", label: ">" },
  { value: "lt", label: "<" },
  { value: "gte", label: "≥" },
  { value: "lte", label: "≤" },
  { value: "between", label: "between" },
];

function isGroup(node: ScreenerCriterion | CriterionGroup): node is CriterionGroup {
  return "combinator" in node;
}

function isNumericCriterion(
  c: ScreenerCriterion,
): c is Extract<ScreenerCriterion, { operator: "gt" | "lt" | "gte" | "lte" | "between" }> {
  return (
    c.operator === "gt" ||
    c.operator === "lt" ||
    c.operator === "gte" ||
    c.operator === "lte" ||
    c.operator === "between"
  );
}

function isStringEqCriterion(
  c: ScreenerCriterion,
): c is Extract<ScreenerCriterion, { operator: "eq" }> {
  return c.operator === "eq";
}

function isInCriterion(c: ScreenerCriterion): c is Extract<ScreenerCriterion, { operator: "in" }> {
  return c.operator === "in";
}

/** A default leaf for "Add criterion". */
export function defaultLeaf(): ScreenerCriterion {
  return { field: "pe_ratio", operator: "lt", value: 20 };
}

/** A default empty sub-group for "Add group". */
export function defaultGroup(): CriterionGroup {
  return { combinator: "and", criteria: [defaultLeaf()] };
}

interface LeafEditorProps {
  index: number;
  criterion: ScreenerCriterion;
  onChange: (next: ScreenerCriterion) => void;
  onRemove: () => void;
}

/** A single leaf criterion editor — the discriminated-union value-shape picker.
 * Self-contained (value + onChange) so it works at any nesting depth. */
function LeafEditor({ index, criterion, onChange, onRemove }: LeafEditorProps) {
  function onCategoryChange(category: "numeric" | "string" | "in") {
    if (category === "numeric") {
      onChange({ field: "pe_ratio", operator: "lt", value: 20 });
    } else if (category === "string") {
      onChange({ field: "sector", operator: "eq", value: "Technology" });
    } else {
      onChange({ field: "sector", operator: "in", value: ["Technology"] });
    }
  }

  const category: "numeric" | "string" | "in" = isNumericCriterion(criterion)
    ? "numeric"
    : isInCriterion(criterion)
      ? "in"
      : "string";

  return (
    <div
      data-testid={`leaf-row-${index}`}
      className="border-border bg-charcoal-900 grid grid-cols-[7rem_9rem_6rem_1fr_auto] items-center gap-2 rounded-none border p-2"
    >
      <select
        aria-label="criterion category"
        className="border-border bg-charcoal-850 rounded-control text-body h-8 min-w-0 truncate border px-2"
        value={category}
        onChange={(e) => onCategoryChange(e.target.value as "numeric" | "string" | "in")}
      >
        <option value="numeric">Numeric</option>
        <option value="string">String</option>
        <option value="in">Set</option>
      </select>

      {isNumericCriterion(criterion) ? (
        <>
          <select
            aria-label="numeric field"
            className="border-border bg-charcoal-850 rounded-control text-body h-8 min-w-0 truncate border px-2"
            value={criterion.field}
            onChange={(e) =>
              onChange({ ...criterion, field: e.target.value as ScreenerNumericField })
            }
          >
            {NUMERIC_FIELDS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
          <select
            aria-label="numeric operator"
            className="border-border bg-charcoal-850 rounded-control text-body h-8 min-w-0 truncate border px-2"
            value={criterion.operator}
            onChange={(e) => {
              const op = e.target.value as "gt" | "lt" | "gte" | "lte" | "between";
              if (op === "between") {
                onChange({
                  field: criterion.field,
                  operator: "between",
                  value: { min: 0, max: 100 },
                });
              } else {
                onChange({ field: criterion.field, operator: op, value: 20 });
              }
            }}
          >
            {NUMERIC_OPERATORS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          {criterion.operator === "between" ? (
            <div className="flex items-center gap-1">
              <input
                aria-label="numeric min"
                type="number"
                className="border-border bg-charcoal-850 rounded-control text-body h-8 w-full border px-2"
                value={criterion.value.min}
                onChange={(e) =>
                  onChange({
                    ...criterion,
                    value: { min: Number(e.target.value), max: criterion.value.max },
                  })
                }
              />
              <span className="text-muted-foreground text-caption">to</span>
              <input
                aria-label="numeric max"
                type="number"
                className="border-border bg-charcoal-850 rounded-control text-body h-8 w-full border px-2"
                value={criterion.value.max}
                onChange={(e) =>
                  onChange({
                    ...criterion,
                    value: { min: criterion.value.min, max: Number(e.target.value) },
                  })
                }
              />
            </div>
          ) : (
            <input
              aria-label="numeric value"
              type="number"
              className="border-border bg-charcoal-850 rounded-control text-body h-8 w-full border px-2"
              value={criterion.value}
              onChange={(e) => onChange({ ...criterion, value: Number(e.target.value) })}
            />
          )}
        </>
      ) : isStringEqCriterion(criterion) ? (
        <>
          <select
            aria-label="string field"
            className="border-border bg-charcoal-850 rounded-control text-body h-8 min-w-0 truncate border px-2"
            value={criterion.field}
            onChange={(e) =>
              onChange({
                field: e.target.value as ScreenerStringField,
                operator: "eq",
                value: criterion.value,
              })
            }
          >
            {STRING_FIELDS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
          <span className="text-muted-foreground text-micro tracking-wide uppercase">equals</span>
          <input
            aria-label="string value"
            type="text"
            className="border-border bg-charcoal-850 rounded-control text-body h-8 w-full border px-2"
            value={criterion.value}
            onChange={(e) => onChange({ ...criterion, value: e.target.value })}
          />
        </>
      ) : isInCriterion(criterion) ? (
        <>
          <select
            aria-label="set field"
            className="border-border bg-charcoal-850 rounded-control text-body h-8 min-w-0 truncate border px-2"
            value={criterion.field}
            onChange={(e) =>
              onChange({
                field: e.target.value as "symbol" | "sector" | "industry",
                operator: "in",
                value: criterion.value,
              })
            }
          >
            <option value="symbol">Symbol</option>
            <option value="sector">Sector</option>
            <option value="industry">Industry</option>
          </select>
          <span className="text-muted-foreground text-micro tracking-wide uppercase">in</span>
          <input
            aria-label="set values"
            type="text"
            placeholder="comma or space separated"
            className="border-border bg-charcoal-850 rounded-control text-body h-8 w-full border px-2"
            value={criterion.value.join(", ")}
            onChange={(e) =>
              onChange({
                ...criterion,
                value: e.target.value
                  .split(/[,\s]+/)
                  .map((v) => v.trim())
                  .filter(Boolean),
              })
            }
          />
        </>
      ) : null}

      <Button size="icon" variant="ghost" aria-label="remove criterion" onClick={onRemove}>
        <Trash2 className="size-4" />
      </Button>
    </div>
  );
}

export interface CriterionGroupEditorProps {
  group: CriterionGroup;
  onChange: (next: CriterionGroup) => void;
  /** Remove this whole group from its parent. Absent at the root. */
  onRemove?: () => void;
  /** Nesting depth (0 = root) — bounds the visual indent + caps deep nesting. */
  depth?: number;
}

/** Cap recursion so a runaway tree can't blow the editor up. */
const MAX_DEPTH = 6;

/**
 * Recursive AND/OR group editor. Renders the combinator toggle, each child (leaf
 * or sub-group), the inter-child "AND/OR" separators, and the add-controls.
 */
export function CriterionGroupEditor({
  group,
  onChange,
  onRemove,
  depth = 0,
}: CriterionGroupEditorProps) {
  const setCombinator = (combinator: "and" | "or") => onChange({ ...group, combinator });

  const updateChild = (index: number, next: ScreenerCriterion | CriterionGroup) =>
    onChange({ ...group, criteria: group.criteria.map((c, i) => (i === index ? next : c)) });

  const removeChild = (index: number) =>
    onChange({ ...group, criteria: group.criteria.filter((_, i) => i !== index) });

  const addLeaf = () => onChange({ ...group, criteria: [...group.criteria, defaultLeaf()] });
  const addGroup = () => onChange({ ...group, criteria: [...group.criteria, defaultGroup()] });

  return (
    <div
      data-testid={`group-editor-${depth}`}
      className={
        depth > 0
          ? "border-border/80 bg-charcoal-875 space-y-1.5 rounded-none border border-dashed p-2"
          : "space-y-1.5"
      }
    >
      <div className="flex items-center justify-between gap-2">
        <div
          role="radiogroup"
          aria-label="group combinator"
          className="border-border bg-charcoal-850 rounded-control text-caption flex items-center border p-0.5"
        >
          {(
            [
              { value: "and", label: "Match ALL" },
              { value: "or", label: "Match ANY" },
            ] as const
          ).map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={group.combinator === opt.value}
              aria-label={opt.label}
              onClick={() => setCombinator(opt.value)}
              className={
                group.combinator === opt.value
                  ? "text-background bg-foreground rounded-control px-2 py-0.5 font-medium transition-colors"
                  : "text-muted-foreground hover:text-foreground rounded-control px-2 py-0.5 transition-colors"
              }
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <Button size="sm" variant="outline" onClick={addLeaf} aria-label="add criterion">
            <Plus className="mr-1 size-3.5" />
            Criterion
          </Button>
          {depth < MAX_DEPTH ? (
            <Button size="sm" variant="outline" onClick={addGroup} aria-label="add group">
              <FolderPlus className="mr-1 size-3.5" />
              Group
            </Button>
          ) : null}
          {onRemove ? (
            <Button size="icon" variant="ghost" aria-label="remove group" onClick={onRemove}>
              <Trash2 className="size-4" />
            </Button>
          ) : null}
        </div>
      </div>

      {group.criteria.length === 0 ? (
        <p className="border-border text-muted-foreground text-body rounded-none border border-dashed p-3 text-center">
          Empty group — every universe member will match. Add a criterion or group.
        </p>
      ) : (
        <div className="space-y-1.5">
          {group.criteria.map((child, i) => (
            <div key={i} className="space-y-1.5">
              {i > 0 ? (
                <div className="text-muted-foreground text-micro pl-2 tracking-widest uppercase">
                  {group.combinator}
                </div>
              ) : null}
              {isGroup(child) ? (
                <CriterionGroupEditor
                  group={child}
                  depth={depth + 1}
                  onChange={(next) => updateChild(i, next)}
                  onRemove={() => removeChild(i)}
                />
              ) : (
                <LeafEditor
                  index={i}
                  criterion={child}
                  onChange={(next) => updateChild(i, next)}
                  onRemove={() => removeChild(i)}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
