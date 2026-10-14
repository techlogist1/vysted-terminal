"use client";

/**
 * Code-node inspector — the properties-panel editor for `transform.code`.
 *
 * Three zones:
 *   1. Inputs — named bindings; each one is an input port on the canvas
 *      node AND a variable in the expression scope. Rename commits on
 *      blur/Enter (identifier-validated); add proposes the next free
 *      letter; remove prunes the binding (the panel prunes its edges).
 *   2. Expression — a monospaced textarea; the sandboxed mathjs instance
 *      gives an inline "does this parse" hint as you type, but is never
 *      the answer for a real run.
 *   3. Preview — sample values per binding, evaluated by a debounced
 *      (~300ms) POST to the sidecar's `/workflow/run` (a one-node
 *      `transform.code` spec), so the preview matches the SAME server
 *      evaluator every real run uses (R15-CODE-PLATFORM-017) — never a
 *      second, client-side answer that can silently disagree with it.
 */

import { useEffect, useMemo, useRef, useState } from "react";

import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";

import type { WorkflowSpec } from "../../../types/workflow";
import {
  CODE_NODE_ID,
  CODE_NODE_OUTPUT_PORT,
  codeNodeBindings,
  codeNodeExpression,
  compileCodeExpression,
  isValidBindingName,
  nextBindingName,
  type CodeEvalResult,
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

  // Preview runs on the SAME server evaluator as a real run — a debounced
  // POST to `/workflow/run` with a throwaway one-node spec. Local, not the
  // shared `useWorkflowStore` (that store's `runs`/`activeRun` are the
  // real run log; routing every preview keystroke through it would hijack
  // whatever run the run-overlay is showing elsewhere).
  const [preview, setPreview] = useState<CodeEvalResult | null>(null);
  const previewSeq = useRef(0);
  const isBlank = expression.trim() === "";

  useEffect(() => {
    if (isBlank) {
      return;
    }
    const scope: Record<string, unknown> = {};
    for (const name of bindings) {
      const raw = samples[name];
      if (raw !== undefined && raw.trim() !== "") {
        const parsed = Number(raw);
        scope[name] = Number.isFinite(parsed) ? parsed : raw;
      }
    }
    const seq = (previewSeq.current += 1);
    const controller = new AbortController();
    const timer = setTimeout(() => {
      void runCodeNodePreview(expression, bindings, scope, controller.signal).then((result) => {
        if (seq === previewSeq.current) {
          setPreview(result);
        }
      });
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [bindings, expression, samples, isBlank]);

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
          className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption focus:ring-charcoal-500 min-h-20 resize-y p-2 font-mono leading-snug outline-none focus:ring-1"
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
              className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption focus:ring-charcoal-500 h-7 min-w-0 flex-1 px-2 font-mono outline-none focus:ring-1"
            />
          </label>
        ))}
        {!isBlank && preview !== null && (
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

const PREVIEW_NODE_ID = "preview";

/**
 * Run one `transform.code` node on the sidecar and return its result — the
 * inspector's live preview. Talks to `/workflow/run` directly (not
 * `useWorkflowStore.runWorkflow`): that store's `runs`/`activeRun` are the
 * real run log the run-overlay renders, and a debounced preview firing on
 * every keystroke would spam it with throwaway runs and hijack whatever
 * run is currently shown. Reads only the one event this node needs
 * (`node-output`/`node-error` for `PREVIEW_NODE_ID`) and stops.
 */
async function runCodeNodePreview(
  expression: string,
  bindings: readonly string[],
  scope: Record<string, unknown>,
  signal: AbortSignal,
): Promise<CodeEvalResult> {
  const spec: WorkflowSpec = {
    id: "preview",
    name: "preview",
    version: 1,
    nodes: [
      {
        id: PREVIEW_NODE_ID,
        type: CODE_NODE_ID,
        position: { x: 0, y: 0 },
        config: { expression, inputs: [...bindings] },
      },
    ],
    edges: [],
    updatedAt: Date.now(),
  };
  try {
    const base = await getSidecarBaseUrl();
    const url = new URL("/workflow/run", base);
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ spec, inputs: scope }),
      signal,
    });
    if (!response.ok || !response.body) {
      return { ok: false, error: `sidecar returned ${response.status}` };
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let sep = buffer.indexOf("\n\n");
        while (sep !== -1) {
          const frame = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          const result = parsePreviewFrame(frame);
          if (result !== null) {
            return result;
          }
          sep = buffer.indexOf("\n\n");
        }
      }
      const tail = buffer.trim() !== "" ? parsePreviewFrame(buffer) : null;
      return tail ?? { ok: false, error: "preview stream ended with no result" };
    } finally {
      reader.releaseLock();
    }
  } catch (err: unknown) {
    if (signal.aborted) {
      return { ok: false, error: "aborted" };
    }
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

/** Parse one SSE frame, returning the preview node's terminal result or `null`. */
function parsePreviewFrame(frame: string): CodeEvalResult | null {
  const dataLines = frame
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());
  if (dataLines.length === 0) {
    return null;
  }
  try {
    const raw = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
    if (raw.kind === "node-output" && raw.nodeId === PREVIEW_NODE_ID) {
      const outputs = raw.outputs as Record<string, unknown> | undefined;
      return { ok: true, value: outputs?.[CODE_NODE_OUTPUT_PORT] };
    }
    if (raw.kind === "node-error" && raw.nodeId === PREVIEW_NODE_ID) {
      return { ok: false, error: String(raw.message ?? "node error") };
    }
    if (raw.kind === "run-error") {
      return { ok: false, error: String(raw.message ?? "run error") };
    }
  } catch {
    // Malformed frame — keep reading; the next frame may carry the result.
  }
  return null;
}
