"use client";

import { CommandIcon, Loader2 } from "lucide-react";
import React, { type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { fuzzyScoreWithIndices } from "@/lib/fuzzy";
import { cn } from "@/lib/utils";
import {
  buildPaletteCorpus,
  KIND_WEIGHT,
  useCommandPalette,
  type PaletteItem,
} from "@/store/command-palette";
import { matchesEvent, useKeybindingsStore } from "@/store/keybindings";
import type { CommandSpec } from "../../types/plugin";

/**
 * Wrap characters at `indices` in an amber highlight mark. Used to render
 * the characters the user typed in the matching result titles.
 */
function fuzzyHighlight(text: string, indices: number[]): React.ReactNode[] {
  if (indices.length === 0) {
    return [text];
  }
  const matchSet = new Set(indices);
  const nodes: React.ReactNode[] = [];
  let plain = "";
  for (let i = 0; i < text.length; i++) {
    if (matchSet.has(i)) {
      if (plain) {
        nodes.push(plain);
        plain = "";
      }
      nodes.push(
        <mark key={i} className="bg-transparent text-amber-400">
          {text[i]}
        </mark>,
      );
    } else {
      plain += text[i];
    }
  }
  if (plain) {
    nodes.push(plain);
  }
  return nodes;
}

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
        className="border-charcoal-700 bg-charcoal-900 max-w-xl gap-0 overflow-hidden p-0 shadow-2xl"
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

/** A ranked item with the title match indices for highlighting. */
interface RankedItem {
  item: PaletteItem;
  score: number;
  titleIndices: number[];
  /** Original position in corpus — used as stable tiebreak. */
  corpusIndex: number;
}

/**
 * Rank corpus against `query` using title-primary scoring with:
 *  - Title scored at full weight via `fuzzyScoreWithIndices`.
 *  - Subtitle fallback at 0.5× weight (for discovery) if title doesn't match.
 *  - `KIND_WEIGHT` multiplier so commands/panels float above agents at equal score.
 */
function rankCorpus(query: string, corpus: PaletteItem[]): RankedItem[] {
  const q = query.trim();
  if (q === "") {
    return corpus.map((item, i) => ({ item, score: 0, titleIndices: [], corpusIndex: i }));
  }
  const ranked: RankedItem[] = [];
  corpus.forEach((item, corpusIndex) => {
    const titleResult = fuzzyScoreWithIndices(q, item.title);
    const subtitleResult =
      titleResult === null && item.subtitle ? fuzzyScoreWithIndices(q, item.subtitle) : null;

    let baseScore: number | null = null;
    let titleIndices: number[] = [];

    if (titleResult !== null) {
      baseScore = titleResult.score;
      titleIndices = titleResult.indices;
    } else if (subtitleResult !== null) {
      // Subtitle-only match: half weight, no title highlighting.
      baseScore = subtitleResult.score * 0.5;
    }

    if (baseScore !== null) {
      ranked.push({
        item,
        score: baseScore * KIND_WEIGHT[item.kind],
        titleIndices,
        corpusIndex,
      });
    }
  });
  // Descending score, stable tiebreak by original corpus order.
  ranked.sort((a, b) => (b.score === a.score ? a.corpusIndex - b.corpusIndex : b.score - a.score));
  return ranked;
}

function CommandPaletteBody({ commands, onClose }: CommandPaletteBodyProps) {
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const itemRefs = useRef<HTMLButtonElement[]>([]);
  // Only auto-scroll on keyboard nav; scrolling on hover makes the list jump
  // under the cursor.
  const navSourceRef = useRef<"kbd" | "mouse">("kbd");

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // The full corpus is assembled once per open (commands change rarely while
  // open; symbols/agents are read at build time). Rank it on each query.
  const corpus = useMemo(() => buildPaletteCorpus(commands), [commands]);
  const ranked = useMemo(() => rankCorpus(query, corpus), [corpus, query]);

  // Scroll highlighted item into view on keyboard nav.
  useEffect(() => {
    if (navSourceRef.current !== "kbd") {
      return;
    }
    const el = itemRefs.current[highlight];
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ block: "nearest" });
    }
  }, [highlight]);

  function run(index: number) {
    const entry = ranked[index];
    if (!entry) {
      return;
    }
    entry.item.run();
    onClose();
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      navSourceRef.current = "kbd";
      setHighlight((current) => Math.min(current + 1, ranked.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      navSourceRef.current = "kbd";
      setHighlight((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      run(highlight);
    } else if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    }
  }

  const activeId = ranked[highlight] ? `palette-item-${ranked[highlight].item.id}` : undefined;

  return (
    <div className="w-full min-w-0">
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
        role="combobox"
        aria-expanded="true"
        aria-haspopup="listbox"
        aria-controls="palette-listbox"
        aria-activedescendant={activeId}
        className="text-charcoal-100 placeholder:text-charcoal-400 w-full bg-transparent px-5 py-3 font-mono text-sm outline-none"
      />
      <div
        id="palette-listbox"
        role="listbox"
        aria-label="Palette results"
        className="border-charcoal-700 max-h-80 min-w-0 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto border-t py-1"
      >
        {ranked.length === 0 ? (
          corpus.length === 0 ? (
            <div role="status" className="flex flex-col items-center gap-2 px-5 py-6 text-center">
              <Loader2 className="text-charcoal-600 size-4 animate-spin" aria-hidden="true" />
              <p className="text-charcoal-400 font-mono text-sm">Sidecar is still starting up</p>
              <p className="text-charcoal-500 font-mono text-xs">
                Try again in a moment or check the status bar
              </p>
            </div>
          ) : (
            <div role="status" className="flex flex-col items-center gap-2 px-5 py-6 text-center">
              <p className="text-charcoal-400 font-mono text-sm">No matches.</p>
              <button
                type="button"
                onClick={() => setQuery("")}
                className="text-charcoal-500 hover:text-charcoal-300 font-mono text-xs transition-colors"
              >
                Clear search
              </button>
            </div>
          )
        ) : (
          ranked.map(({ item, titleIndices }, index) => (
            <button
              key={item.id}
              id={`palette-item-${item.id}`}
              ref={(el) => {
                if (el) itemRefs.current[index] = el;
              }}
              type="button"
              role="option"
              aria-selected={index === highlight}
              onClick={() => run(index)}
              onMouseEnter={() => {
                navSourceRef.current = "mouse";
                setHighlight(index);
              }}
              className={cn(
                "flex w-full items-center gap-3 px-5 py-2 text-left font-mono",
                index === highlight && "bg-charcoal-800",
              )}
            >
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="text-charcoal-100 truncate text-sm">
                  {query.trim() ? fuzzyHighlight(item.title, titleIndices) : item.title}
                </span>
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
    </div>
  );
}
