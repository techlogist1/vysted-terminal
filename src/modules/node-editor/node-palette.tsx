"use client";

/**
 * Node-editor palette — left rail. Renders the built-in node types and
 * plugin-contributed node types as draggable cards grouped by category.
 *
 * The drag-and-drop flow uses the HTML5 native drag API rather than a
 * library so the palette stays SSR-friendly (no zustand or framer-motion
 * required for the gesture) and works regardless of react-flow version.
 * The drop handler lives in `NodeEditorPanel.tsx` and reads the
 * `application/x-vysted-node-type` MIME type set here.
 */

import type { NodeSpec } from "../../../types/plugin";
import { cn } from "@/lib/utils";

import type { RegistryEntry } from "./node-registry";
import { groupByCategory } from "./node-registry";

/** MIME type stamped onto drag payloads so the canvas drop-handler can identify them. */
export const NODE_DRAG_MIME = "application/x-vysted-node-type";

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

export function NodePalette({ registry }: NodePaletteProps) {
  const grouped = groupByCategory(registry);
  const pluginEntries = registry.filter((entry) => entry.source === "plugin");

  return (
    <aside
      data-testid="node-palette"
      className="border-charcoal-700 bg-charcoal-900 flex h-full w-56 min-w-56 flex-col border-r"
    >
      <header className="border-charcoal-700 flex items-baseline justify-between border-b px-3 py-2">
        <span className="text-charcoal-200 font-mono text-xs uppercase">Nodes</span>
        <span className="text-charcoal-500 font-mono text-[10px] uppercase">{registry.length}</span>
      </header>
      <div className="flex-1 overflow-y-auto py-2">
        {CATEGORY_ORDER.map((category) => {
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
              <h3 className="text-charcoal-400 mb-1 px-1 font-mono text-[10px] uppercase">
                {CATEGORY_LABELS[category]}
              </h3>
              <ul className="flex flex-col gap-1">
                {entries.map((entry) => (
                  <PaletteCard key={`${entry.source}:${entry.spec.id}`} entry={entry} />
                ))}
              </ul>
            </section>
          );
        })}
        {pluginEntries.length > 0 && (
          <section data-testid="palette-section-plugin" className="px-2">
            <h3 className="text-charcoal-400 mb-1 px-1 font-mono text-[10px] uppercase">
              Plugin Nodes
            </h3>
            <ul className="flex flex-col gap-1">
              {pluginEntries.map((entry) => (
                <li key={`plugin-flat:${entry.spec.id}`}>
                  <span className="text-charcoal-500 px-2 font-mono text-[9px]">
                    {entry.pluginId ?? "plugin"}
                  </span>
                </li>
              ))}
            </ul>
          </section>
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
        "border-charcoal-700 bg-charcoal-850 cursor-grab rounded-md border px-2 py-1.5 font-mono text-xs select-none",
        "hover:border-amber-500 hover:bg-amber-500/5 active:cursor-grabbing",
      )}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-charcoal-100">{spec.label}</span>
        {source === "plugin" && (
          <span className="font-mono text-[9px] text-amber-400 uppercase">plugin</span>
        )}
      </div>
      {spec.description !== undefined && (
        <p className="text-charcoal-400 mt-0.5 truncate text-[10px]">{spec.description}</p>
      )}
    </li>
  );
}
