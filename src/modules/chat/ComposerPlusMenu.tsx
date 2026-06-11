"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Plus } from "lucide-react";

import { cn } from "@/lib/utils";
import { useAgentAutonomyStore, type AgentAutonomy } from "@/store/agent-autonomy";

import { type AgentMode, AGENT_MODES } from "../../../types/agent-modes";
import { type MentionDef, type MentionKind, STATIC_MENTIONS } from "./mentions";

/**
 * The composer's plus-menu (R9 Track C) — the Claude-reference "+" affordance
 * at the field's bottom-left, now the ONE home for every standing composer
 * mode (the R8 five-chip strip below the input is dead):
 *
 *   - **Persona** — the active lens (Buffett / researcher / …) as a drill-in
 *     roster; the row always shows the DISPLAY NAME, never a raw id.
 *   - **Autonomy** — ASK/AUTO as checked rows (a mode, not a per-message
 *     control; orders always confirm regardless — §6.5).
 *   - **Mode** — Agent / Delegate as checked rows.
 *   - **Context / Scope / Route to** — insertable mention tokens SEEDED FROM
 *     the `@`-mention catalog (one source of truth: `STATIC_MENTIONS`).
 *     Selecting a row inserts through the SAME insert path as typing
 *     (`insertMentionToken` — the parent wires it), byte-identical.
 *   - **Slash commands…** — primes the `/` picker.
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

const ROW_CLASS =
  "text-caption flex w-full cursor-pointer items-center gap-2 px-3 py-1 text-left font-mono transition-colors text-charcoal-300 hover:bg-charcoal-850 hover:text-charcoal-100";

function SectionHeader({ children }: { children: string }) {
  return (
    <div className="text-micro text-charcoal-500 px-3 py-1 tracking-wide uppercase">{children}</div>
  );
}

function Divider() {
  return <div aria-hidden className="border-charcoal-700 my-1 border-t" />;
}

/** A checked-row pick (autonomy / mode / persona): check column + label + hint. */
function CheckRow({
  active,
  label,
  hint,
  onPick,
}: {
  active: boolean;
  label: string;
  hint?: string;
  onPick: () => void;
}) {
  return (
    <button
      type="button"
      role="menuitemradio"
      aria-checked={active}
      title={hint}
      // `onMouseDown` (not click) so the composer keeps focus and the pick
      // lands before a blur tears the menu down — the house picker idiom.
      onMouseDown={(event) => {
        event.preventDefault();
        onPick();
      }}
      className={cn(ROW_CLASS, "flex-col items-stretch gap-0", active && "text-charcoal-100")}
    >
      <span className="flex items-center gap-2">
        <span className="w-3 shrink-0" aria-hidden>
          {active ? <Check className="size-3" /> : null}
        </span>
        <span className="min-w-0 truncate">{label}</span>
      </span>
      {hint && (
        <span className="text-micro text-charcoal-500 pl-5 leading-snug tracking-normal normal-case">
          {hint}
        </span>
      )}
    </button>
  );
}

export interface ComposerPlusMenuProps {
  /** Insert the picked mention token through the shared mention-insert path. */
  onInsertMention: (mention: MentionDef) => void;
  /** Prime the `/`-command picker: insert "/" and focus the field. */
  onSlashCommands: () => void;
  /** The active persona's DISPLAY NAME (never a raw id). */
  personaLabel: string;
  firstParty: readonly { id: string; name: string }[];
  custom: readonly { id: string; name: string }[];
  activeAgentId: string;
  onPersonaChange: (id: string) => void;
  mode: AgentMode;
  onModeChange: (mode: AgentMode) => void;
}

export function ComposerPlusMenu({
  onInsertMention,
  onSlashCommands,
  personaLabel,
  firstParty,
  custom,
  activeAgentId,
  onPersonaChange,
  mode,
  onModeChange,
}: ComposerPlusMenuProps) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<"root" | "persona">("root");
  const rootRef = useRef<HTMLDivElement | null>(null);
  const sections = buildPlusMenuSections();
  const autonomy = useAgentAutonomyStore((state) => state.autonomy);
  const setAutonomy = useAgentAutonomyStore((state) => state.setAutonomy);

  function toggleOpen() {
    setOpen((v) => {
      if (!v) {
        setView("root");
      }
      return !v;
    });
  }

  // Click-outside or Escape dismisses (same idiom as the model popover).
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

  // Persona roster, concierge first (the same ordering the old lens popover used).
  const orderedFirstParty = [...firstParty].sort((a, b) =>
    a.id === "copilot" ? -1 : b.id === "copilot" ? 1 : 0,
  );

  const autonomyHint: Record<AgentAutonomy, string> = {
    ask: "Every change waits for your review",
    auto: "UI changes apply instantly; orders always confirm",
  };

  return (
    <div ref={rootRef} className="relative shrink-0">
      {/* Primary action scale (law §3): 28×28 with a 16px icon — quiet until hover. */}
      <button
        type="button"
        aria-label="Insert context, switch persona, or set modes"
        aria-haspopup="menu"
        aria-expanded={open}
        title="Context, persona, autonomy, mode, commands"
        onClick={toggleOpen}
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
          aria-label="Composer menu"
          className={cn(
            "border-charcoal-700 bg-charcoal-875 rounded-control absolute bottom-full left-0 z-30 mb-1 flex w-64 flex-col overflow-y-auto border py-1",
            "max-h-[min(20rem,50vh)]" /* tokens-ok: viewport scroll cap — layout, not rhythm */,
          )}
        >
          {view === "persona" ? (
            <>
              <button
                type="button"
                role="menuitem"
                onMouseDown={(event) => {
                  event.preventDefault();
                  setView("root");
                }}
                className={ROW_CLASS}
              >
                <ChevronLeft className="size-3 shrink-0" aria-hidden />
                <span className="min-w-0 truncate">Back</span>
              </button>
              {orderedFirstParty.length === 0 && custom.length === 0 && (
                // Empty roster (sidecar not up yet) — say so quietly rather
                // than render a bare section header over nothing.
                <div className="text-caption text-charcoal-500 px-3 py-1 font-mono">
                  No personas available yet
                </div>
              )}
              {orderedFirstParty.length > 0 && <SectionHeader>First-party</SectionHeader>}
              {orderedFirstParty.map((agent) => (
                <CheckRow
                  key={agent.id}
                  active={agent.id === activeAgentId}
                  label={agent.name}
                  onPick={() => {
                    onPersonaChange(agent.id);
                    setOpen(false);
                  }}
                />
              ))}
              {custom.length > 0 && (
                <>
                  <SectionHeader>Custom</SectionHeader>
                  {custom.map((agent) => (
                    <CheckRow
                      key={agent.id}
                      active={agent.id === activeAgentId}
                      label={agent.name}
                      onPick={() => {
                        onPersonaChange(agent.id);
                        setOpen(false);
                      }}
                    />
                  ))}
                </>
              )}
            </>
          ) : (
            <>
              <button
                type="button"
                role="menuitem"
                aria-label={`Persona — ${personaLabel}`}
                title="Switch the active persona (the lens the agent answers through)"
                onMouseDown={(event) => {
                  event.preventDefault();
                  setView("persona");
                }}
                className={ROW_CLASS}
              >
                <span className="text-charcoal-500 shrink-0">Persona</span>
                <span className="text-charcoal-100 min-w-0 flex-1 truncate text-right">
                  {personaLabel}
                </span>
                <ChevronRight className="size-3 shrink-0" aria-hidden />
              </button>
              <Divider />
              <SectionHeader>Autonomy</SectionHeader>
              {(["ask", "auto"] as const).map((level) => (
                <CheckRow
                  key={level}
                  active={autonomy === level}
                  label={level.toUpperCase()}
                  hint={autonomyHint[level]}
                  onPick={() => setAutonomy(level)}
                />
              ))}
              <SectionHeader>Mode</SectionHeader>
              {AGENT_MODES.map((m) => (
                <CheckRow
                  key={m.id}
                  active={m.id === mode}
                  label={`${m.label} (${m.hotkeyLabel})`}
                  hint={m.hint}
                  onPick={() => onModeChange(m.id)}
                />
              ))}
              <Divider />
              {sections.map((section) => (
                <Fragment key={section.title}>
                  <SectionHeader>{section.title}</SectionHeader>
                  {section.items.map((item) => (
                    <button
                      key={item.token}
                      type="button"
                      role="menuitem"
                      title={item.description}
                      onMouseDown={(event) => {
                        event.preventDefault();
                        setOpen(false);
                        onInsertMention(item);
                      }}
                      className={ROW_CLASS}
                    >
                      <span className="text-charcoal-400 shrink-0">{item.token}</span>
                      <span className="min-w-0 truncate">{item.label}</span>
                    </button>
                  ))}
                </Fragment>
              ))}
              <Divider />
              <button
                type="button"
                role="menuitem"
                onMouseDown={(event) => {
                  event.preventDefault();
                  setOpen(false);
                  onSlashCommands();
                }}
                className={ROW_CLASS}
              >
                <span className="text-charcoal-400 shrink-0">/</span>
                <span className="min-w-0 truncate">Slash commands…</span>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
