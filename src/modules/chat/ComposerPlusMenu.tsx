"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { Plus } from "lucide-react";

import { cn } from "@/lib/utils";

import { type MentionDef, type MentionKind, STATIC_MENTIONS } from "./mentions";

/**
 * The composer's plus-menu (R8 Track C) — the Claude-reference "+" affordance
 * at the field's bottom-left. It opens an anchored menu of insertable actions
 * SEEDED FROM the `@`-mention catalog (one source of truth: `STATIC_MENTIONS`),
 * sectioned by layer, plus a "Slash commands…" row that primes the `/` picker.
 * Selecting a row inserts the mention token through the SAME insert path as
 * typing (`insertMentionToken` — the parent wires it), so the result is
 * byte-identical to a hand-typed mention.
 */

export interface PlusMenuSection {
  title: string;
  items: MentionDef[];
}

/** Section title per mention layer — the menu's grouping vocabulary. */
const SECTION_TITLE: Partial<Record<MentionKind, string>> = {
  surface: "Context",
  scope: "Scope",
  agent: "Route to",
};

/** Section order in the menu (instrument mentions are type-time only — never here). */
const SECTION_ORDER: readonly MentionKind[] = ["surface", "scope", "agent"];

/**
 * Group the static mention catalog into the plus-menu's sections: Context
 * (surfaces), Scope (scopes), Route to (agents). Pure — derives entirely from
 * the catalog, so a new static mention appears here without a second edit.
 */
export function buildPlusMenuSections(
  catalog: readonly MentionDef[] = STATIC_MENTIONS,
): PlusMenuSection[] {
  return SECTION_ORDER.map((kind) => ({
    title: SECTION_TITLE[kind] ?? kind,
    items: catalog.filter((m) => m.kind === kind),
  })).filter((section) => section.items.length > 0);
}

export function ComposerPlusMenu({
  onInsertMention,
  onSlashCommands,
}: {
  /** Insert the picked mention token through the shared mention-insert path. */
  onInsertMention: (mention: MentionDef) => void;
  /** Prime the `/`-command picker: insert "/" and focus the field. */
  onSlashCommands: () => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const sections = buildPlusMenuSections();

  // Click-outside or Escape dismisses (same idiom as the meta-row popovers).
  useEffect(() => {
    if (!open) {
      return;
    }
    function onPointerDown(event: PointerEvent) {
      const el = rootRef.current;
      if (el && event.target instanceof Node && !el.contains(event.target)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const rowClass =
    "text-caption flex w-full cursor-pointer items-baseline gap-2 px-3 py-1 text-left font-mono transition-colors text-charcoal-300 hover:bg-charcoal-850 hover:text-charcoal-100";

  return (
    <div ref={rootRef} className="relative shrink-0">
      {/* Primary action scale (law §2): 28×28 with a 16px icon — quiet until hover. */}
      <button
        type="button"
        aria-label="Insert context, scope, or a command"
        aria-haspopup="menu"
        aria-expanded={open}
        title="Add context, scope, or a command"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "rounded-control flex size-7 shrink-0 cursor-pointer items-center justify-center transition-colors",
          open
            ? "bg-charcoal-800 text-charcoal-200"
            : "text-charcoal-500 hover:bg-charcoal-800 hover:text-charcoal-200",
        )}
      >
        <Plus className="size-4" strokeWidth={2} />
      </button>
      {open && (
        <div
          role="menu"
          aria-label="Insert into the composer"
          className="border-charcoal-700 bg-charcoal-875 rounded-control absolute bottom-full left-0 z-30 mb-1 flex max-h-[min(20rem,50vh)] w-60 flex-col overflow-y-auto border py-1"
        >
          {sections.map((section) => (
            <Fragment key={section.title}>
              <div className="text-micro text-charcoal-500 px-3 py-1 tracking-wide uppercase">
                {section.title}
              </div>
              {section.items.map((item) => (
                <button
                  key={item.token}
                  type="button"
                  role="menuitem"
                  title={item.description}
                  // `onMouseDown` (not click) so the composer keeps focus and the
                  // insert lands before a blur tears the menu down — the same
                  // idiom as the inline MentionPicker.
                  onMouseDown={(event) => {
                    event.preventDefault();
                    setOpen(false);
                    onInsertMention(item);
                  }}
                  className={rowClass}
                >
                  <span className="text-charcoal-400 shrink-0">{item.token}</span>
                  <span className="min-w-0 truncate">{item.label}</span>
                </button>
              ))}
            </Fragment>
          ))}
          <div className="border-charcoal-700 mt-1 border-t pt-1">
            <button
              type="button"
              role="menuitem"
              onMouseDown={(event) => {
                event.preventDefault();
                setOpen(false);
                onSlashCommands();
              }}
              className={rowClass}
            >
              <span className="text-charcoal-400 shrink-0">/</span>
              <span className="min-w-0 truncate">Slash commands…</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
