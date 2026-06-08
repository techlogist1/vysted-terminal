"use client";

import { cn } from "@/lib/utils";

import type { SlashCommandDef } from "./slash-commands";

/**
 * Inline slash-command picker (FR-100, SC-023) — a presentational list rendered
 * above the chat composer while the user types a command name. Keyboard
 * navigation (arrow keys, enter, escape) and the input wiring live in the
 * lead-owned `ChatSidebar`; this component only renders the rows and highlights
 * the active one. `onPick` fires on a pointer click; arrow/enter selection is
 * the parent's responsibility.
 */
export function SlashCommandPicker({
  matches,
  activeIndex,
  onPick,
}: {
  /** The ranked curated commands to show (from `matchSlash`). */
  matches: SlashCommandDef[];
  /** Index of the highlighted row (the parent drives keyboard nav). */
  activeIndex: number;
  /** Invoked when a row is clicked. */
  onPick: (cmd: SlashCommandDef) => void;
}) {
  if (matches.length === 0) {
    return null;
  }

  return (
    <ul
      role="listbox"
      aria-label="Slash commands"
      className="border-charcoal-700 bg-charcoal-875 rounded-control flex max-h-60 flex-col overflow-y-auto border py-1"
    >
      {matches.map((cmd, index) => {
        const active = index === activeIndex;
        return (
          <li key={cmd.trigger} role="option" aria-selected={active}>
            <button
              type="button"
              // `onMouseDown` (not click) so the composer keeps focus and the
              // pick lands before the input's blur tears the picker down.
              onMouseDown={(event) => {
                event.preventDefault();
                onPick(cmd);
              }}
              className={cn(
                "text-body flex w-full items-baseline gap-2 px-3 py-2 text-left",
                active ? "bg-charcoal-800" : "hover:bg-charcoal-900",
              )}
            >
              <span className={cn("shrink-0", active ? "text-charcoal-300" : "text-charcoal-300")}>
                /{cmd.trigger}
              </span>
              {cmd.argHint && <span className="text-charcoal-500 shrink-0">{cmd.argHint}</span>}
              <span className="text-charcoal-200 truncate">{cmd.title}</span>
              <span className="text-charcoal-500 ml-auto truncate text-right">
                {cmd.description}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
