"use client";

/**
 * Code-node inspector — the properties-panel editor for `transform.code`.
 *
 * Three zones:
 *   1. Inputs — named bindings; each one is an input port on the canvas
 *      node AND a variable in the expression scope. Rename commits on
 *      blur/Enter (identifier-validated); add proposes the next free
 *      letter; remove prunes the binding (the panel prunes its edges).
 *   2. Expression — a monospaced textarea evaluated by the sandboxed
 *      mathjs instance; parse errors render inline as you type.
 *   3. Preview — sample values per binding, evaluated live so the author
 *      sees the output (or the honest eval error) before running.
 */

import { useMemo, useState } from "react";

import { cn } from "@/lib/utils";

import {
  codeNodeBindings,
  codeNodeExpression,
  compileCodeExpression,
  evaluateCodeExpression,
  isValidBindingName,
  nextBindingName,
} from "./code-node";

interface CodeNodeInspectorProps {
  config: Record<string, unknown>;
  /** Patch the node config (merged by the panel's `updateNodeConfig`). */
  onPatch: (patch: Record<string, unknown>) => void;
}

export function CodeNodeInspector({ config, onPatch }: CodeNodeInspectorProps) {
  const bindings = useMemo(() => codeNodeBindings(config), [config]);
  const expression = codeNodeExpression(config);
  const compile = useMemo(() => compileCodeExpression(expression), [expression]);

  // Sample values for the live preview — inspector-local, never persisted.
  const [samples, setSamples] = useState<Record<string, string>>({});

  const preview = useMemo(() => {
    if (!compile.ok) {
      return null;
    }
    const scope: Record<string, unknown> = {};
    for (const name of bindings) {
      const raw = samples[name];
      if (raw !== undefined && raw.trim() !== "") {
        const parsed = Number(raw);
        scope[name] = Number.isFinite(parsed) ? parsed : raw;
      }
    }
    return evaluateCodeExpression(expression, scope);
  }, [bindings, compile.ok, expression, samples]);

  const setBindings = (next: string[]) => {
    onPatch({ inputs: next });
  };

  return (
    <div data-testid="code-node-inspector" className="flex flex-col gap-3">
      {/* Inputs */}
      <div className="flex flex-col gap-1">
        <span className="text-charcoal-400 text-micro font-mono uppercase">Inputs</span>
        <ul className="flex flex-col gap-1">
          {bindings.map((name) => (
            <BindingRow
              key={name}
              name={name}
              taken={bindings}
              onRename={(nextName) => {
                setBindings(bindings.map((b) => (b === name ? nextName : b)));
              }}
              onRemove={() => {
                setBindings(bindings.filter((b) => b !== name));
                setSamples((prev) => {
                  const { [name]: _dropped, ...rest } = prev;
                  return rest;
                });
              }}
            />
          ))}
        </ul>
        <button
          type="button"
          data-testid="code-binding-add"
          onClick={() => setBindings([...bindings, nextBindingName(bindings)])}
          className="border-charcoal-700 hover:border-charcoal-500 text-charcoal-300 rounded-control text-micro mt-0.5 self-start border px-2 py-1 font-mono"
        >
          + Add input
        </button>
      </div>

      {/* Expression */}
      <label className="flex flex-col gap-1">
        <span className="text-charcoal-400 text-micro font-mono uppercase">Expression</span>
        <textarea
          aria-label="Code expression"
          data-testid="code-node-expression"
          value={expression}
          onChange={(event) => onPatch({ expression: event.target.value })}
          rows={5}
          spellCheck={false}
          placeholder="a + b * 2"
          className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption focus:ring-charcoal-500 min-h-[5rem] resize-y p-2 font-mono leading-snug outline-none focus:ring-1"
        />
      </label>
      {!compile.ok && compile.error !== undefined && (
        <p data-testid="code-node-error" className="text-negative text-micro -mt-2 font-mono">
          {compile.error}
        </p>
      )}

      {/* Preview */}
      <div className="border-charcoal-800 flex flex-col gap-1 border-t pt-2">
        <span className="text-charcoal-400 text-micro font-mono uppercase">Preview</span>
        {bindings.map((name) => (
          <label key={name} className="flex items-center gap-2">
            <span className="text-charcoal-300 text-micro w-16 truncate font-mono">{name}</span>
            <input
              aria-label={`Sample value for ${name}`}
              data-testid={`code-binding-sample-${name}`}
              value={samples[name] ?? ""}
              onChange={(event) => setSamples((prev) => ({ ...prev, [name]: event.target.value }))}
              placeholder="0"
              className="bg-charcoal-800 text-charcoal-100 rounded-control text-micro focus:ring-charcoal-500 h-7 min-w-0 flex-1 px-2 font-mono outline-none focus:ring-1"
            />
          </label>
        ))}
        {preview !== null && (
          <p
            data-testid="code-node-preview"
            className={cn(
              "text-micro font-mono break-all",
              preview.ok ? "text-positive" : "text-negative",
            )}
          >
            {preview.ok ? `= ${formatPreview(preview.value)}` : preview.error}
          </p>
        )}
      </div>
    </div>
  );
}

interface BindingRowProps {
  name: string;
  taken: readonly string[];
  onRename: (next: string) => void;
  onRemove: () => void;
}

function BindingRow({ name, taken, onRename, onRemove }: BindingRowProps) {
  const [draft, setDraft] = useState(name);
  const [error, setError] = useState<string | null>(null);

  const commit = () => {
    const next = draft.trim();
    if (next === name) {
      setError(null);
      return;
    }
    if (!isValidBindingName(next)) {
      setError("letters, digits, _ — must not start with a digit");
      return;
    }
    if (taken.includes(next)) {
      setError("name already in use");
      return;
    }
    setError(null);
    onRename(next);
  };

  return (
    <li data-testid={`code-binding-row-${name}`} className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1">
        <input
          aria-label={`Input binding ${name}`}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={commit}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              commit();
            }
          }}
          spellCheck={false}
          className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption focus:ring-charcoal-500 h-7 min-w-0 flex-1 px-2 font-mono outline-none focus:ring-1"
        />
        <button
          type="button"
          aria-label={`Remove input ${name}`}
          data-testid={`code-binding-remove-${name}`}
          onClick={onRemove}
          className="text-charcoal-400 hover:text-charcoal-100 text-body px-1 font-mono"
        >
          ×
        </button>
      </div>
      {error !== null && <span className="text-negative text-micro font-mono">{error}</span>}
    </li>
  );
}

function formatPreview(value: unknown): string {
  try {
    const text = JSON.stringify(value);
    return text === undefined ? String(value) : text.slice(0, 200);
  } catch {
    return String(value);
  }
}
