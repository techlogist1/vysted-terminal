"use client";

import { useMemo } from "react";

import { cn } from "@/lib/utils";
import type { BacktestStrategySpec } from "../../../types/backtest";

/**
 * Strategy picker — renders the registered strategies as a vertical
 * radio-list with a one-line description. Selecting a strategy bubbles
 * up the id; the parent panel resolves the spec + renders the params
 * form. Kept presentation-only so the picker is trivial to test.
 */
export interface StrategyPickerProps {
  strategies: readonly BacktestStrategySpec[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** Disable selection while a backtest is streaming. */
  disabled?: boolean;
}

export function StrategyPicker({
  strategies,
  selectedId,
  onSelect,
  disabled,
}: StrategyPickerProps) {
  const empty = strategies.length === 0;

  return (
    <div className="flex flex-col gap-1.5" data-testid="strategy-picker">
      <span className="text-charcoal-500 font-mono text-[10px] tracking-widest uppercase">
        Strategy
      </span>
      {empty ? (
        <p className="text-charcoal-400 font-mono text-xs">
          No strategies registered. The sidecar must be running.
        </p>
      ) : (
        <ul className="flex flex-col gap-1">
          {strategies.map((spec) => {
            const active = selectedId === spec.id;
            return (
              <li key={spec.id}>
                <button
                  type="button"
                  onClick={() => onSelect(spec.id)}
                  disabled={disabled}
                  aria-pressed={active}
                  className={cn(
                    "rounded-control w-full border px-2 py-1.5 text-left transition-colors",
                    active
                      ? "border-amber-500 bg-amber-500/15 text-amber-300"
                      : "border-charcoal-700 text-charcoal-200 hover:border-charcoal-600",
                    disabled && "cursor-not-allowed opacity-50",
                  )}
                >
                  <div className="font-mono text-xs font-medium">{spec.name}</div>
                  <div className="text-charcoal-400 mt-0.5 font-mono text-[10px] leading-snug">
                    {spec.description}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/**
 * Params form — renders one input per ``paramsSchema.properties`` entry.
 * The schema is JSON-Schema-draft-07 subset; we support
 * ``type: "integer"`` / ``type: "number"`` (rendered as ``<input
 * type="number">``) and fall back to plain string inputs. Each input
 * carries the property's default until the user overrides it.
 */
export interface ParamsFormProps {
  schema: Record<string, unknown> | undefined;
  values: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
  disabled?: boolean;
}

interface FieldSpec {
  key: string;
  type: "integer" | "number" | "string";
  defaultValue: unknown;
  description?: string;
}

function pickFields(schema: Record<string, unknown> | undefined): FieldSpec[] {
  if (!schema) {
    return [];
  }
  const props = schema.properties;
  if (!props || typeof props !== "object") {
    return [];
  }
  return Object.entries(props as Record<string, unknown>).map(([key, raw]) => {
    const def = (raw ?? {}) as { type?: string; default?: unknown; description?: string };
    const type = def.type === "integer" ? "integer" : def.type === "number" ? "number" : "string";
    return {
      key,
      type,
      defaultValue: def.default,
      description: def.description,
    };
  });
}

export function ParamsForm({ schema, values, onChange, disabled }: ParamsFormProps) {
  const fields = useMemo(() => pickFields(schema), [schema]);
  if (fields.length === 0) {
    return null;
  }
  return (
    <div className="flex flex-col gap-1.5" data-testid="params-form">
      <span className="text-charcoal-500 font-mono text-[10px] tracking-widest uppercase">
        Params
      </span>
      <div className="grid grid-cols-2 gap-2">
        {fields.map((field) => {
          const current = values[field.key];
          const displayValue =
            current === undefined ? (field.defaultValue ?? "") : (current as string | number);
          return (
            <label key={field.key} className="flex flex-col gap-1">
              <span className="text-charcoal-300 font-mono text-[10px]" title={field.description}>
                {field.key}
              </span>
              <input
                type={field.type === "string" ? "text" : "number"}
                inputMode={field.type === "string" ? "text" : "decimal"}
                aria-label={field.key}
                value={String(displayValue)}
                onChange={(event) => {
                  const raw = event.target.value;
                  let next: unknown = raw;
                  if (field.type === "integer") {
                    const parsed = parseInt(raw, 10);
                    next = Number.isFinite(parsed) ? parsed : raw;
                  } else if (field.type === "number") {
                    const parsed = parseFloat(raw);
                    next = Number.isFinite(parsed) ? parsed : raw;
                  }
                  onChange({ ...values, [field.key]: next });
                }}
                disabled={disabled}
                className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control h-8 border px-2 font-mono text-xs outline-none focus-visible:border-amber-500 disabled:opacity-50"
              />
            </label>
          );
        })}
      </div>
    </div>
  );
}
