"use client";

import { Trash2, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useScreenerStore } from "@/store/screener";

import type {
  CriterionGroup,
  ScreenerCriterion,
  ScreenerNumericField,
  ScreenerStringField,
} from "../../../types/screener";
import { CriterionGroupEditor, defaultGroup } from "./CriterionGroupEditor";
import { ScreenerFormulaLeaf } from "./ScreenerFormulaLeaf";

/**
 * Criterion editor — Phase 6 (Teammate Sc, lead-completed); R4 nested grammar.
 *
 * Two modes:
 *   - SIMPLE (default): the flat discriminated-union editor — one AND/OR
 *     combinator across a flat list of leaf criteria (the original surface).
 *   - ADVANCED: a recursive nested AND/OR group editor (`CriterionGroupEditor`),
 *     editing the existing recursive `CriterionGroup` wire tree the backend
 *     already evaluates. Toggling to advanced seeds the tree from the flat list.
 * Below either mode sits the custom-formula leaf (the shared restricted
 * grammar, evaluated server-side with the criteria). The operator pick switches
 * the leaf's value input shape — single number / (min, max) / string / comma-list.
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

interface CriterionRowProps {
  index: number;
  criterion: ScreenerCriterion;
}

function CriterionRow({ index, criterion }: CriterionRowProps) {
  const update = useScreenerStore((s) => s.updateCriterion);
  const remove = useScreenerStore((s) => s.removeCriterion);

  function onCategoryChange(category: "numeric" | "string" | "in") {
    if (category === "numeric") {
      update(index, { field: "pe_ratio", operator: "lt", value: 20 });
    } else if (category === "string") {
      update(index, { field: "sector", operator: "eq", value: "Technology" });
    } else {
      update(index, { field: "sector", operator: "in", value: ["Technology"] });
    }
  }

  const category: "numeric" | "string" | "in" = isNumericCriterion(criterion)
    ? "numeric"
    : isInCriterion(criterion)
      ? "in"
      : "string";

  return (
    <div
      data-testid={`criterion-row-${index}`}
      className="border-border bg-charcoal-900 grid grid-cols-[8rem_9rem_7rem_1fr_auto] items-center gap-2 rounded-none border p-2"
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
              update(index, { ...criterion, field: e.target.value as ScreenerNumericField })
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
                update(index, {
                  field: criterion.field,
                  operator: "between",
                  value: { min: 0, max: 100 },
                });
              } else {
                update(index, { field: criterion.field, operator: op, value: 20 });
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
                  update(index, {
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
                  update(index, {
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
              onChange={(e) => update(index, { ...criterion, value: Number(e.target.value) })}
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
              update(index, {
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
            onChange={(e) => update(index, { ...criterion, value: e.target.value })}
          />
        </>
      ) : isInCriterion(criterion) ? (
        <>
          <select
            aria-label="set field"
            className="border-border bg-charcoal-850 rounded-control text-body h-8 min-w-0 truncate border px-2"
            value={criterion.field}
            onChange={(e) =>
              update(index, {
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
              update(index, {
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

      <Button
        size="icon"
        variant="ghost"
        aria-label="remove criterion"
        onClick={() => remove(index)}
      >
        <Trash2 className="size-4" />
      </Button>
    </div>
  );
}

/** Seed an advanced nested tree from the flat criteria + combinator (so toggling
 * to advanced never loses the user's current simple criteria). */
function seedGroupFromFlat(
  criteria: ScreenerCriterion[],
  combinator: "and" | "or",
): CriterionGroup {
  return { combinator, criteria: criteria.length ? [...criteria] : [] };
}

/** SIMPLE flat-criteria editor (the original surface, unchanged behaviour). */
function SimpleCriteriaEditor() {
  const criteria = useScreenerStore((s) => s.criteria);
  const add = useScreenerStore((s) => s.addCriterion);
  const combinator = useScreenerStore((s) => s.combinator);
  const setCombinator = useScreenerStore((s) => s.setCombinator);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        {/* Match ALL (AND) / ANY (OR) — drives the `group` boolean tree on run.
            A row of independent thresholds reads as "match ALL"; flip to "ANY"
            for an OR sweep (e.g. cheap-by-P/E OR high-yield). */}
        <div
          role="radiogroup"
          aria-label="criteria combinator"
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
              aria-checked={combinator === opt.value}
              aria-label={opt.label}
              onClick={() => setCombinator(opt.value)}
              // Design-law segmented toggle: the active segment climbs one rung
              // (raised surface, bright text) — never an inverted fill.
              className={
                combinator === opt.value
                  ? "bg-charcoal-700 text-charcoal-100 rounded-control px-2 py-0.5 font-medium transition-colors"
                  : "text-muted-foreground hover:text-foreground rounded-control px-2 py-0.5 transition-colors"
              }
            >
              {opt.label}
            </button>
          ))}
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => add({ field: "pe_ratio", operator: "lt", value: 20 })}
        >
          <Plus className="mr-1" />
          Add criterion
        </Button>
      </div>
      <div className="space-y-2">
        {criteria.length === 0 ? (
          <p className="border-border text-muted-foreground text-body rounded-none border border-dashed p-3 text-center">
            No criteria — every universe member will match.
          </p>
        ) : (
          criteria.map((c, i) => (
            <div key={i} className="space-y-2">
              {i > 0 ? (
                <div className="text-muted-foreground text-micro pl-2 tracking-widest uppercase">
                  {combinator === "or" ? "or" : "and"}
                </div>
              ) : null}
              <CriterionRow index={i} criterion={c} />
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/** ADVANCED nested-group editor bound to the store's `group` tree. */
function AdvancedGroupEditor() {
  const group = useScreenerStore((s) => s.group);
  const setGroup = useScreenerStore((s) => s.setGroup);
  // The store guarantees a group exists in advanced mode (set on toggle); guard
  // anyway so a direct advanced=true via the agent path still renders.
  const tree = group ?? defaultGroup();
  return <CriterionGroupEditor group={tree} onChange={setGroup} />;
}

export function ScreenerCriteriaBuilder() {
  const advanced = useScreenerStore((s) => s.advanced);
  const setAdvanced = useScreenerStore((s) => s.setAdvanced);

  function toggleAdvanced(next: boolean) {
    if (next && !useScreenerStore.getState().group) {
      // Seed the nested tree from the current flat criteria on first switch so
      // nothing the user already typed is lost.
      const { criteria, combinator } = useScreenerStore.getState();
      useScreenerStore.getState().setGroup(seedGroupFromFlat(criteria, combinator));
    }
    setAdvanced(next);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-muted-foreground text-caption font-semibold tracking-wide uppercase">
          Criteria
        </h3>
        <div
          role="radiogroup"
          aria-label="criteria mode"
          className="border-border bg-charcoal-850 rounded-control text-caption flex items-center border p-0.5"
        >
          {(
            [
              { value: false, label: "Simple" },
              { value: true, label: "Nested" },
            ] as const
          ).map((opt) => (
            <button
              key={String(opt.value)}
              type="button"
              role="radio"
              aria-checked={advanced === opt.value}
              aria-label={`${opt.label} mode`}
              onClick={() => toggleAdvanced(opt.value)}
              className={
                advanced === opt.value
                  ? "bg-charcoal-700 text-charcoal-100 rounded-control px-2 py-0.5 font-medium transition-colors"
                  : "text-muted-foreground hover:text-foreground rounded-control px-2 py-0.5 transition-colors"
              }
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {advanced ? <AdvancedGroupEditor /> : <SimpleCriteriaEditor />}

      <div className="border-border border-t pt-2">
        <ScreenerFormulaLeaf />
      </div>
    </div>
  );
}
