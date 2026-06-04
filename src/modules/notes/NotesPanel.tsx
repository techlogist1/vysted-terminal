"use client";

import { NotebookPen } from "lucide-react";

import { cn } from "@/lib/utils";
import { useNotesStore } from "@/store/notes";

/**
 * Notes panel — a free-text research scratchpad, scoped per-stock (type a ticker)
 * or "General". Notes ride the workspace blob, so they persist with a saved/named
 * workspace and a per-stock research space (a layout saved for one ticker keeps
 * its notes). The active scope (`focusSymbol`) is lifted into the store so a
 * per-stock research space can open the panel already scoped to its ticker — and
 * that scope persists across a reload. Quick-switch chips list the tickers that
 * already have notes.
 */
export function NotesPanel() {
  const general = useNotesStore((s) => s.general);
  const bySymbol = useNotesStore((s) => s.bySymbol);
  const scope = useNotesStore((s) => s.focusSymbol);
  const setScope = useNotesStore((s) => s.setFocusSymbol);
  const setGeneral = useNotesStore((s) => s.setGeneral);
  const setSymbolNote = useNotesStore((s) => s.setSymbolNote);

  const key = scope.trim().toUpperCase();
  const value = key ? (bySymbol[key] ?? "") : general;
  const chips = Object.entries(bySymbol)
    .filter(([, text]) => text.trim().length > 0)
    .map(([sym]) => sym)
    .sort();

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <div className="border-charcoal-700 flex items-center gap-2 border-b p-3">
        <NotebookPen className="size-4 shrink-0 text-amber-400" aria-hidden />
        <input
          aria-label="Notes scope"
          value={scope}
          onChange={(e) => setScope(e.target.value.toUpperCase())}
          placeholder="General — type a ticker to scope (e.g. AAPL)"
          className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-500 h-8 flex-1 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
        />
        <span className="text-charcoal-500 shrink-0 font-mono text-[0.65rem] tracking-wide uppercase">
          {key || "General"}
        </span>
      </div>
      {chips.length > 0 && (
        <div className="border-charcoal-700 flex flex-wrap items-center gap-1.5 border-b px-3 py-1.5">
          <button
            type="button"
            onClick={() => setScope("")}
            className={cn(
              "rounded-full border px-2.5 py-0.5 font-mono text-[11px] transition-colors",
              key === ""
                ? "border-amber-500/50 bg-amber-500/15 text-amber-300"
                : "border-charcoal-700 text-charcoal-400 hover:text-lume",
            )}
          >
            General
          </button>
          {chips.map((sym) => (
            <button
              key={sym}
              type="button"
              onClick={() => setScope(sym)}
              className={cn(
                "rounded-full border px-2.5 py-0.5 font-mono text-[11px] transition-colors",
                key === sym
                  ? "border-amber-500/50 bg-amber-500/15 text-amber-300"
                  : "border-charcoal-700 text-charcoal-400 hover:text-lume",
              )}
            >
              {sym}
            </button>
          ))}
        </div>
      )}
      <textarea
        aria-label="Notes"
        value={value}
        onChange={(e) => (key ? setSymbolNote(key, e.target.value) : setGeneral(e.target.value))}
        placeholder={key ? `Research notes on ${key}…` : "General research notes…"}
        spellCheck
        className="text-charcoal-100 placeholder:text-charcoal-500 flex-1 resize-none bg-transparent p-3 font-mono text-sm leading-relaxed outline-none"
      />
      <div className="border-charcoal-700 text-charcoal-500 border-t px-3 py-1 font-mono text-[0.6rem]">
        {key ? `Notes for ${key}` : "General notes"} · saved with your workspace
      </div>
    </div>
  );
}
