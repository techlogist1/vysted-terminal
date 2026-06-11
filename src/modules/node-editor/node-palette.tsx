"use client";

/**
 * Node-editor palette — left rail. Renders every registered node kind —
 * the first-party set (v0.5.0 built-ins, the code node, the v0.6.0
 * sidecar kinds) plus plugin-contributed types — as draggable cards
 * grouped by category, with a search filter (the registry is >12 kinds).
 *
 * The drag-and-drop flow uses the HTML5 native drag API rather than a
 * library so the palette stays SSR-friendly (no zustand or framer-motion
 * required for the gesture) and works regardless of react-flow version.
 * The drop handler lives in `NodeEditorPanel.tsx` and reads the
 * `application/x-vysted-node-type` MIME type set here.
 */

import { useMemo, useState } from "react";

import type { NodeSpec } from "../../../types/plugin";
import { cn } from "@/lib/utils";

import type { RegistryEntry } from "./node-registry";
import { groupByCategory } from "./node-registry";

/** MIME type stamped onto drag payloads so the canvas drop-handler can identify them. */
export const NODE_DRAG_MIME = "application/x-vysted-node-type";

/** Show the search input once the registry outgrows a scannable list. */
const SEARCH_THRESHOLD = 12;

interface NodePaletteProps {
  registry: readonly RegistryEntry[];
}

const CATEGORY_LABELS: Record<NodeSpec["category"], string> = {
  trigger: "Triggers",
  action: "Actions",
  transform: "Transforms",
  condition: "Conditions",
  output: "Outputs",
};

const CATEGORY_ORDER: readonly NodeSpec["category"][] = [
  "trigger",
  "transform",
  "condition",
  "action",
  "output",
];

function matches(entry: RegistryEntry, needle: string): boolean {
  if (needle === "") {
    return true;
  }
  const { spec } = entry;
  return (
    spec.label.toLowerCase().includes(needle) ||
    spec.id.toLowerCase().includes(needle) ||
    (spec.description?.toLowerCase().includes(needle) ?? false)
  );
}

export function NodePalette({ registry }: NodePaletteProps) {
  const [query, setQuery] = useState("");
  const needle = query.trim().toLowerCase();

  const filtered = useMemo(
    () => registry.filter((entry) => matches(entry, needle)),
    [needle, registry],
  );
  const grouped = useMemo(() => groupByCategory(filtered), [filtered]);

  return (
    <aside
      data-testid="node-palette"
      className="border-charcoal-700 bg-charcoal-900 flex h-full w-56 min-w-56 flex-col border-r"
    >
      <header className="border-charcoal-700 flex items-baseline justify-between border-b px-3 py-2">
        <span className="text-charcoal-200 text-caption font-mono uppercase">Nodes</span>
        <span data-testid="node-palette-count" className="text-charcoal-500 text-micro font-mono">
          {needle === "" ? registry.length : `${filtered.length}/${registry.length}`}
        </span>
      </header>
      {registry.length > SEARCH_THRESHOLD && (
        <div className="border-charcoal-800 border-b px-2 py-2">
          <input
            type="search"
            aria-label="Search nodes"
            data-testid="node-palette-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search nodes…"
            spellCheck={false}
            className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-500 rounded-control text-caption focus:ring-charcoal-500 h-7 w-full px-2 font-mono outline-none focus:ring-1"
          />
        </div>
      )}
      <div className="flex-1 overflow-y-auto py-2">
        {filtered.length === 0 ? (
          <p
            data-testid="node-palette-empty"
            className="text-charcoal-500 text-micro px-3 py-2 font-mono"
          >
            No nodes match &ldquo;{query.trim()}&rdquo;
          </p>
        ) : (
          CATEGORY_ORDER.map((category) => {
            const entries = grouped[category];
            if (entries.length === 0) {
              return null;
            }
            return (
              <section
                key={category}
                data-testid={`palette-category-${category}`}
                className="mb-3 px-2"
              >
                <h3 className="text-charcoal-400 text-micro mb-1 flex items-baseline justify-between px-1 font-mono uppercase">
                  <span>{CATEGORY_LABELS[category]}</span>
                  <span className="text-charcoal-600">{entries.length}</span>
                </h3>
                <ul className="flex flex-col gap-1">
                  {entries.map((entry) => (
                    <PaletteCard key={`${entry.source}:${entry.spec.id}`} entry={entry} />
                  ))}
                </ul>
              </section>
            );
          })
        )}
      </div>
    </aside>
  );
}

interface PaletteCardProps {
  entry: RegistryEntry;
}

function PaletteCard({ entry }: PaletteCardProps) {
  const { spec, source } = entry;
  const handleDragStart = (event: React.DragEvent<HTMLLIElement>) => {
    event.dataTransfer.setData(NODE_DRAG_MIME, spec.id);
    event.dataTransfer.setData("text/plain", spec.id);
    event.dataTransfer.effectAllowed = "copy";
  };
  return (
    <li
      draggable
      data-testid={`palette-card-${spec.id}`}
      onDragStart={handleDragStart}
      className={cn(
        "border-charcoal-700 bg-charcoal-850 rounded-control text-caption cursor-grab border px-2 py-1 font-mono select-none",
        "hover:border-charcoal-500 hover:bg-charcoal-700/5 active:cursor-grabbing",
      )}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-charcoal-100">{spec.label}</span>
        {source === "plugin" && (
          <span className="text-micro text-charcoal-300 font-mono uppercase">plugin</span>
        )}
      </div>
      {spec.description !== undefined && (
        <p className="text-charcoal-400 text-micro mt-0.5 truncate">{spec.description}</p>
      )}
    </li>
  );
}
