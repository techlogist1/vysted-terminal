"use client";

import { motion } from "framer-motion";
import { CommandIcon } from "lucide-react";
import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { fuzzyRank } from "@/lib/fuzzy";
import { cn } from "@/lib/utils";
import { buildPaletteCorpus, useCommandPalette, type PaletteItem } from "@/store/command-palette";
import { matchesEvent, useKeybindingsStore } from "@/store/keybindings";
import type { CommandSpec } from "../../types/plugin";

/** Human label per corpus kind, shown as a right-aligned category badge. */
const KIND_LABEL: Record<PaletteItem["kind"], string> = {
  command: "Command",
  panel: "Panel",
  symbol: "Symbol",
  agent: "Agent",
};

export function CommandPalette() {
  const { open, setOpen, toggle, commands } = useCommandPalette();

  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      // The open shortcut is data-driven from the keybindings store (FR-031 /
      // foundation for FR-039) — no hardcoded `key === "k"`.
      const combo = useKeybindingsStore.getState().bindingFor("palette.open");
      if (combo && matchesEvent(combo, event)) {
        event.preventDefault();
        toggle();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggle]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        className="border-charcoal-700 bg-charcoal-900 max-w-xl gap-0 p-0 shadow-2xl"
        showCloseButton={false}
      >
        <DialogHeader className="border-charcoal-700 border-b px-5 py-3">
          <DialogTitle className="text-charcoal-200 flex items-center gap-2 font-mono text-sm font-medium">
            <CommandIcon className="size-3.5 text-amber-400" aria-hidden="true" />
            Command Palette
          </DialogTitle>
          <DialogDescription className="sr-only">
            Search and run commands, open panels, jump to a symbol, or pick an agent.
          </DialogDescription>
        </DialogHeader>
        {/* The body is a child component so its query/highlight state resets
            each time the palette opens — Radix unmounts DialogContent while
            the dialog is closed. Building the corpus here (on each open) keeps
            it in sync with the live watchlist / agent roster. */}
        <CommandPaletteBody commands={commands} onClose={() => setOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}

interface CommandPaletteBodyProps {
  commands: CommandSpec[];
  onClose: () => void;
}

function CommandPaletteBody({ commands, onClose }: CommandPaletteBodyProps) {
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // The full corpus is assembled once per open (commands change rarely while
  // open; symbols/agents are read at build time). Fuzzy-rank it on each query.
  const corpus = useMemo(() => buildPaletteCorpus(commands), [commands]);
  const filtered = useMemo(
    () => fuzzyRank(query, corpus, (item) => `${item.title} ${item.subtitle ?? ""}`),
    [corpus, query],
  );

  function run(index: number) {
    const item = filtered[index];
    if (!item) {
      return;
    }
    item.run();
    onClose();
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlight((current) => Math.min(current + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      run(highlight);
    } else if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
    >
      <input
        ref={inputRef}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setHighlight(0);
        }}
        onKeyDown={handleInputKeyDown}
        placeholder="Search commands, panels, symbols, agents…"
        aria-label="Search the command palette"
        className="text-charcoal-100 placeholder:text-charcoal-400 w-full bg-transparent px-5 py-3 font-mono text-sm outline-none"
      />
      <div
        role="listbox"
        aria-label="Palette results"
        className="border-charcoal-700 max-h-80 overflow-y-auto border-t py-1"
      >
        {filtered.length === 0 ? (
          <p className="text-charcoal-400 px-5 py-6 text-center font-mono text-sm">
            {corpus.length === 0 ? "Nothing to search yet." : "No matches."}
          </p>
        ) : (
          filtered.map((item, index) => (
            <button
              key={item.id}
              type="button"
              role="option"
              aria-selected={index === highlight}
              onClick={() => run(index)}
              onMouseEnter={() => setHighlight(index)}
              className={cn(
                "flex w-full items-center gap-3 px-5 py-2 text-left font-mono",
                index === highlight && "bg-charcoal-800",
              )}
            >
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="text-charcoal-100 truncate text-sm">{item.title}</span>
                {item.subtitle ? (
                  <span className="text-charcoal-400 truncate text-xs">{item.subtitle}</span>
                ) : null}
              </span>
              {item.keybinding ? (
                <kbd className="border-charcoal-700 bg-charcoal-925 text-charcoal-300 shrink-0 rounded border px-1.5 py-0.5 font-mono text-[11px] leading-none">
                  {item.keybinding}
                </kbd>
              ) : null}
              <span className="text-charcoal-500 shrink-0 text-[10px] tracking-wide uppercase">
                {KIND_LABEL[item.kind]}
              </span>
            </button>
          ))
        )}
      </div>
    </motion.div>
  );
}
