"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  compileScreenerExpr,
  identifierAt,
  NUMERIC_FIELDS,
  suggestFields,
  type FieldSuggestion,
} from "@/lib/screener-expr";
import { cn } from "@/lib/utils";
import { useScreenerStore } from "@/store/screener";

/**
 * Custom-formula editor (R7 hackability Pillar 3).
 *
 * A free-text boolean expression over the screener's numeric fields, parsed
 * against the SAME restricted grammar the sidecar evaluates server-side
 * (`src/lib/screener-expr.ts` ⇄ `sidecar/services/screener_formula.py`). The
 * formula rides the run request and AND-combines with the criteria; a row
 * missing a referenced field is skipped and itemized in the skip ledger (the
 * results table's "evaluated / skipped" summary stays honest).
 *
 * Editor affordances:
 *   - instant inline validation with a monospace caret line (`^` under the
 *     offending column) — recovery-first, never a raw stack;
 *   - a prefix dropdown completing field names (canonical + aliases) at the
 *     caret, keyboard-navigable (up/down · tab/enter accept · esc dismiss);
 *   - three one-click example chips seeding working formulas.
 */

/** One-click starter formulas — each parses under the shared grammar. */
const EXAMPLES: { label: string; formula: string }[] = [
  { label: "value + quality", formula: "pe_ratio < 15 and roe > 0.2" },
  { label: "yield, low debt", formula: "dividend_yield > 0.03 and debt_to_equity < 1" },
  {
    label: "calm compounders",
    formula: "max(roe, roa) > 0.15 and abs(change_percent_1d) < 2",
  },
];

/** Max dropdown rows — enough to disambiguate, never a wall. */
const MAX_SUGGESTIONS = 8;

export function ScreenerFormulaLeaf() {
  const formula = useScreenerStore((s) => s.formula);
  const setFormula = useScreenerStore((s) => s.setFormula);

  const inputRef = useRef<HTMLInputElement>(null);
  const [caret, setCaret] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  // The caret position to restore after an accepted completion re-renders.
  const pendingCaretRef = useRef<number | null>(null);

  // Instant validation against the shared grammar (the server enforces the
  // same one, so a green editor never 422s).
  const compiled = useMemo(() => compileScreenerExpr(formula), [formula]);
  const showError = !compiled.ok && formula.trim().length > 0;

  // Autocomplete context: the identifier being typed at the caret.
  const span = useMemo(
    () => (dismissed ? null : identifierAt(formula, caret)),
    [formula, caret, dismissed],
  );
  const suggestions = useMemo<FieldSuggestion[]>(
    () => (span ? suggestFields(span.prefix, MAX_SUGGESTIONS) : []),
    [span],
  );
  const open = suggestions.length > 0;
  // Clamp at render time (no effect needed) — the list reshapes as the user
  // types, and the highlight must always point at a real row.
  const activeIndex = open ? Math.min(highlighted, suggestions.length - 1) : 0;

  useEffect(() => {
    // Restore the caret after a completion was inserted (React re-render
    // resets the selection to the end otherwise).
    if (pendingCaretRef.current !== null && inputRef.current) {
      inputRef.current.setSelectionRange(pendingCaretRef.current, pendingCaretRef.current);
      pendingCaretRef.current = null;
    }
  }, [formula]);

  function syncCaret() {
    const el = inputRef.current;
    if (el && el.selectionStart !== null) {
      setCaret(el.selectionStart);
    }
  }

  function accept(suggestion: FieldSuggestion) {
    if (!span) {
      return;
    }
    // Replace the WHOLE identifier under the caret (not just the prefix) so
    // completing mid-word never leaves a stray suffix.
    const next = formula.slice(0, span.start) + suggestion.name + formula.slice(span.end);
    pendingCaretRef.current = span.start + suggestion.name.length;
    setFormula(next);
    setCaret(span.start + suggestion.name.length);
    setDismissed(true);
    inputRef.current?.focus();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) {
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((activeIndex + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((activeIndex - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === "Tab" || e.key === "Enter") {
      e.preventDefault();
      accept(suggestions[activeIndex]!);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setDismissed(true);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <h3 className="text-muted-foreground text-caption font-semibold tracking-wide uppercase">
          Custom formula
        </h3>
        <span className="text-muted-foreground text-micro normal-case">
          evaluated server-side with the criteria · rows missing a field are skipped, itemized
        </span>
      </div>

      <div className="relative">
        <input
          ref={inputRef}
          aria-label="custom formula"
          data-testid="screener-formula-input"
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls="screener-formula-suggestions"
          aria-autocomplete="list"
          autoComplete="off"
          spellCheck={false}
          value={formula}
          onChange={(e) => {
            setFormula(e.target.value);
            setDismissed(false);
            setHighlighted(0);
            if (e.target.selectionStart !== null) {
              setCaret(e.target.selectionStart);
            }
          }}
          onKeyDown={onKeyDown}
          onKeyUp={syncCaret}
          onClick={syncCaret}
          onBlur={() => setDismissed(true)}
          placeholder="e.g. pe_ratio < 15 and roe > 0.2   ·   market_cap / volume > 1e6"
          className={cn(
            "border-border bg-charcoal-850 rounded-control text-body h-8 w-full border px-2 font-mono",
            showError && "border-destructive/60",
          )}
        />
        {open && (
          <ul
            id="screener-formula-suggestions"
            data-testid="screener-formula-suggestions"
            role="listbox"
            aria-label="field suggestions"
            className="border-charcoal-600 bg-charcoal-800 rounded-control absolute top-full right-0 left-0 z-20 mt-1 overflow-hidden border"
          >
            {suggestions.map((s, i) => (
              <li
                key={s.name}
                role="option"
                aria-selected={i === activeIndex}
                data-testid={`screener-formula-suggestion-${s.name}`}
                // onMouseDown so the pick lands BEFORE the input's blur dismisses.
                onMouseDown={(e) => {
                  e.preventDefault();
                  accept(s);
                }}
                onMouseEnter={() => setHighlighted(i)}
                className={cn(
                  "text-body flex cursor-pointer items-baseline justify-between gap-3 px-2 py-1 font-mono",
                  i === activeIndex ? "bg-charcoal-700 text-charcoal-100" : "text-charcoal-300",
                )}
              >
                <span>{s.name}</span>
                <span className="text-charcoal-500 text-micro truncate normal-case">{s.hint}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {showError && !compiled.ok ? (
        <div
          data-testid="screener-formula-error"
          className="text-destructive text-micro overflow-x-auto font-mono whitespace-pre normal-case"
        >
          {/* The terminal-native caret line: the formula, `^` under the
              offending column, then the parser's message. */}
          {`${formula}\n${" ".repeat(Math.min(compiled.position, formula.length))}^ ${compiled.error}`}
        </div>
      ) : (
        <p className="text-muted-foreground text-micro normal-case">
          {formula.trim() && compiled.ok && compiled.fields.length > 0
            ? `Fields: ${compiled.fields.join(", ")} — run the screener to apply.`
            : `${NUMERIC_FIELDS.length} fields (pe_ratio, market_cap, roe, …) · abs, min, max · and / or / not, + - * /, comparisons`}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-charcoal-500 text-micro tracking-wide uppercase">Examples</span>
        {EXAMPLES.map((example, i) => (
          <button
            key={example.label}
            type="button"
            data-testid={`screener-formula-example-${i}`}
            title={example.formula}
            onClick={() => {
              setFormula(example.formula);
              setDismissed(true);
              inputRef.current?.focus();
            }}
            className="border-border bg-charcoal-850 text-muted-foreground rounded-control text-micro hover:border-charcoal-500 hover:text-charcoal-100 border px-2 py-0.5 transition-colors"
          >
            {example.label}
          </button>
        ))}
      </div>
    </div>
  );
}
