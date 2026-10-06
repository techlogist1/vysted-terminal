"use client";

import { cn } from "@/lib/utils";

import type { MentionDef, MentionKind } from "./mentions";

/** Per-layer badge label + tint (token-driven dark palette). */
const KIND_BADGE: Record<MentionKind, { label: string; className: string }> = {
  surface: { label: "surface", className: "text-charcoal-400" },
  scope: { label: "scope", className: "text-charcoal-400" },
  agent: { label: "agent", className: "text-charcoal-300/80" },
  instrument: { label: "ticker", className: "text-charcoal-300" },
};

/**
 * Inline `@`-mention picker (FR-101, SC-023) — a presentational list rendered
 * above the chat composer while the user types a mention token. Keyboard
 * navigation (arrow keys, enter, escape) and the input wiring live in the
 * lead-owned `ChatSidebar`; this component only renders the rows and highlights
 * the active one. `onPick` fires on a pointer click; arrow/enter selection is
 * the parent's responsibility.
 */
export function MentionPicker({
  matches,
  activeIndex,
  onPick,
}: {
  /** The ranked mentions to show (from `resolveMention`). */
  matches: MentionDef[];
  /** Index of the highlighted row (the parent drives keyboard nav). */
  activeIndex: number;
  /** Invoked when a row is clicked. */
  onPick: (mention: MentionDef) => void;
}) {
  if (matches.length === 0) {
    return null;
  }

  return (
    <ul
      role="listbox"
      aria-label="Mentions"
      className={cn(
        "border-charcoal-700 bg-charcoal-875 rounded-control flex flex-col overflow-y-auto border py-1",
        "max-h-60" /* tokens-ok: picker scroll cap — layout, not rhythm */,
      )}
    >
      {matches.map((mention, index) => {
        const active = index === activeIndex;
        const badge = KIND_BADGE[mention.kind];
        return (
          <li key={`${mention.kind}:${mention.token}`} role="option" aria-selected={active}>
            <button
              type="button"
              // `onMouseDown` (not click) so the composer keeps focus and the
              // pick lands before the input's blur tears the picker down.
              onMouseDown={(event) => {
                event.preventDefault();
                onPick(mention);
              }}
              className={cn(
                "text-body flex w-full items-baseline gap-2 px-3 py-2 text-left",
                active ? "bg-charcoal-800" : "hover:bg-charcoal-900",
              )}
            >
              <span className={cn("shrink-0", active ? "text-charcoal-300" : "text-charcoal-300")}>
                {mention.token}
              </span>
              <span className="text-charcoal-200 truncate">{mention.label}</span>
              {mention.description && (
                <span className="text-charcoal-500 truncate">{mention.description}</span>
              )}
              <span className={cn("text-caption ml-auto shrink-0 text-right", badge.className)}>
                {badge.label}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
