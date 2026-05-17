"use client";

import { Trash2, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useScreenerStore } from "@/store/screener";

import type {
  ScreenerCriterion,
  ScreenerNumericField,
  ScreenerStringField,
} from "../../../types/screener";

/**
 * Criterion editor — Phase 6 (Teammate Sc, lead-completed).
 *
 * Discriminated-union editor: the operator pick switches the value input
 * shape — single number / (min, max) / string / comma-list. AND-combined
 * across rows. Add / remove rows from the criteria stack.
 */
const NUMERIC_FIELDS: { value: ScreenerNumericField; label: string }[] = [
  { value: "market_cap", label: "Market cap" },
  { value: "pe_ratio", label: "P/E ratio" },
  { value: "forward_pe", label: "Forward P/E" },
  { value: "peg_ratio", label: "PEG ratio" },
  { value: "price_to_book", label: "Price / Book" },
  { value: "dividend_yield", label: "Dividend yield" },
  { value: "eps", label: "EPS" },
  { value: "beta", label: "Beta" },
  { value: "fifty_two_week_high", label: "52w high" },
  { value: "fifty_two_week_low", label: "52w low" },
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
      className="border-border bg-background/60 grid grid-cols-[8rem,9rem,7rem,1fr,auto] items-center gap-2 rounded-md border p-2"
    >
      <select
        aria-label="criterion category"
        className="border-border bg-background rounded-md border px-2 py-1 text-sm"
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
            className="border-border bg-background rounded-md border px-2 py-1 text-sm"
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
            className="border-border bg-background rounded-md border px-2 py-1 text-sm"
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
                className="border-border bg-background w-full rounded-md border px-2 py-1 text-sm"
                value={criterion.value.min}
                onChange={(e) =>
                  update(index, {
                    ...criterion,
                    value: { min: Number(e.target.value), max: criterion.value.max },
                  })
                }
              />
              <span className="text-muted-foreground text-xs">to</span>
              <input
                aria-label="numeric max"
                type="number"
                className="border-border bg-background w-full rounded-md border px-2 py-1 text-sm"
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
              className="border-border bg-background w-full rounded-md border px-2 py-1 text-sm"
              value={criterion.value}
              onChange={(e) => update(index, { ...criterion, value: Number(e.target.value) })}
            />
          )}
        </>
      ) : isStringEqCriterion(criterion) ? (
        <>
          <select
            aria-label="string field"
            className="border-border bg-background rounded-md border px-2 py-1 text-sm"
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
          <span className="text-muted-foreground text-xs tracking-wide uppercase">equals</span>
          <input
            aria-label="string value"
            type="text"
            className="border-border bg-background w-full rounded-md border px-2 py-1 text-sm"
            value={criterion.value}
            onChange={(e) => update(index, { ...criterion, value: e.target.value })}
          />
        </>
      ) : isInCriterion(criterion) ? (
        <>
          <select
            aria-label="set field"
            className="border-border bg-background rounded-md border px-2 py-1 text-sm"
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
          <span className="text-muted-foreground text-xs tracking-wide uppercase">in</span>
          <input
            aria-label="set values"
            type="text"
            placeholder="comma or space separated"
            className="border-border bg-background w-full rounded-md border px-2 py-1 text-sm"
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

export function ScreenerCriteriaBuilder() {
  const criteria = useScreenerStore((s) => s.criteria);
  const add = useScreenerStore((s) => s.addCriterion);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-muted-foreground text-sm font-semibold tracking-wide uppercase">
          Criteria (AND)
        </h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => add({ field: "pe_ratio", operator: "lt", value: 20 })}
        >
          <Plus className="mr-1 size-3.5" />
          Add criterion
        </Button>
      </div>
      <div className="space-y-1.5">
        {criteria.length === 0 ? (
          <p className="border-border text-muted-foreground rounded-md border border-dashed p-3 text-center text-sm">
            No criteria — every universe member will match.
          </p>
        ) : (
          criteria.map((c, i) => <CriterionRow key={i} index={i} criterion={c} />)
        )}
      </div>
    </div>
  );
}
