"use client";

/**
 * CommandPalette — cmdk-powered Raycast-grade launcher (FR-120 / SC-031).
 *
 * Five groups in fixed priority order:
 *   1. Ask AI   — always-visible free-text row; routes query to the agent.
 *   2. Agents   — agent roster; selecting opens chat focused on that agent.
 *   3. Actions  — CommandSpec[] from enabled modules.
 *   4. Panels   — PanelSpec[] from enabled modules.
 *   5. Symbols  — watchlist + resolved; query-gated (hidden when empty query) + capped ≤50.
 *
 * Empty-query state: shows "Recent" (last-used commands) + "Suggested" (curated
 * shortcuts) instead of the full corpus dump.
 *
 * Cross-group ranking: a custom `paletteFilter` adds per-group score offsets so
 * agents always outrank actions which outrank panels which outrank symbols,
 * while cmdk fuzzy-ranks within each group normally.
 *
 * Keybinding: `mod+k` via a global `keydown` listener that resolves the
 * `palette.open` binding — falls back to `meta+k` / `ctrl+k` directly if the
 * keybindings store is unavailable.
 *
 * AI-ask routing: selecting the Ask AI row calls
 *   useWorkspaceStore.getState().openPanel("chat")
 * then writes the query to `useChatPendingStore` so `ChatSidebar` auto-submits
 * it on next render.
 */

import { Command } from "cmdk";
import {
  Bot,
  Command as CommandIcon,
  LayoutGrid,
  Search,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/EmptyState";
import { executeCommand } from "@/lib/commands";
import { useChatPendingStore } from "@/store/chat-pending";
import {
  buildPaletteCorpus,
  paletteFilter,
  SUGGESTED_ITEMS,
  SYMBOL_CAP,
  useCommandPalette,
  type PaletteItem,
} from "@/store/command-palette";
import { useChartSyncBus } from "@/store/chart-sync";
import { useWorkspaceStore } from "@/store/workspace";

// ---------------------------------------------------------------------------
// Public export
// ---------------------------------------------------------------------------

export function CommandPalette() {
  const { open, setOpen, toggle } = useCommandPalette();

  // Keybinding: resolve `mod+k` from the global keydown listener.
  // We do a direct meta/ctrl check here for reliability — the keybindings store
  // may not have loaded yet at the point this listener fires.
  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
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
        className="border-charcoal-700 bg-charcoal-875 max-w-2xl gap-0 overflow-hidden p-0"
        showCloseButton={false}
      >
        <DialogHeader className="sr-only">
          <DialogTitle>Command Palette</DialogTitle>
          <DialogDescription>
            Search agents, actions, panels, symbols, or ask the AI anything.
          </DialogDescription>
        </DialogHeader>
        {/* Body is its own component so state resets on each open (Radix unmounts
            DialogContent while closed). */}
        <PaletteBody onClose={() => setOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Palette body — owns query state and the cmdk Command tree
// ---------------------------------------------------------------------------

interface PaletteBodyProps {
  onClose: () => void;
}

function PaletteBody({ onClose }: PaletteBodyProps) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const { recordSelection } = useCommandPalette();
  const recents = useCommandPalette((state) => state.recents);

  // Live corpus — rebuilt on each render from live Zustand stores.
  const corpus = useMemo(() => buildPaletteCorpus(), []);

  // Partition by kind.
  const agents = useMemo(() => corpus.filter((i) => i.kind === "agent"), [corpus]);
  const actions = useMemo(() => corpus.filter((i) => i.kind === "action"), [corpus]);
  const panels = useMemo(() => corpus.filter((i) => i.kind === "panel"), [corpus]);
  const symbols = useMemo(() => corpus.filter((i) => i.kind === "symbol"), [corpus]);

  // Recent items resolved to full PaletteItems (most-recent first, up to 5).
  const recentItems = useMemo(() => {
    const byId = new Map(corpus.map((item) => [item.id, item]));
    return recents
      .map((id) => byId.get(id))
      .filter((item): item is PaletteItem => item !== undefined)
      .slice(0, 5);
  }, [corpus, recents]);

  // Whether the symbol group should be visible (only when there's a query).
  const hasQuery = query.trim().length > 0;
  const showSymbols = hasQuery;

  // Auto-focus the input when the body mounts (palette just opened).
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // ---------------------------------------------------------------------------
  // Selection handlers
  // ---------------------------------------------------------------------------

  const openPanel = useWorkspaceStore((state) => state.openPanel);
  const setChartSymbol = useChartSyncBus((state) => state.setSymbol);

  const handleSelectAskAi = useCallback(() => {
    const q = query.trim();
    if (!q) return;
    // Open chat panel then queue the prompt for auto-submit.
    openPanel("chat");
    useChatPendingStore.getState().queuePrompt(q);
    onClose();
  }, [query, openPanel, onClose]);

  const handleSelectItem = useCallback(
    (item: PaletteItem) => {
      recordSelection(item.id);

      switch (item.kind) {
        case "agent":
          // Open chat focused — the panel is already the chat sidebar,
          // so opening it surfaces the correct context.  The agent picker
          // within ChatSidebar is state-local; we just surface the panel.
          openPanel("chat");
          break;
        case "action":
          if (item.commandSpec) {
            executeCommand(item.commandSpec);
          }
          break;
        case "panel":
          if (item.panelSpec) {
            openPanel(item.panelSpec.id);
          }
          break;
        case "symbol":
          if (item.symbolEntry) {
            // Load into the primary chart via the chart sync bus.
            setChartSymbol("palette", item.symbolEntry.symbol);
          }
          break;
      }
      onClose();
    },
    [recordSelection, openPanel, setChartSymbol, onClose],
  );

  // Handler for suggested static items (resolved against the live corpus).
  const handleSelectSuggested = useCallback(
    (suggestion: (typeof SUGGESTED_ITEMS)[number]) => {
      recordSelection(suggestion.id);

      // Try to find the item in the corpus and dispatch normally.
      const found = corpus.find((i) => i.id === suggestion.corpusId);
      if (found) {
        handleSelectItem(found);
        return;
      }

      // Fallback: open by panel id directly.
      if (suggestion.panelId) {
        openPanel(suggestion.panelId);
      }
      onClose();
    },
    [recordSelection, corpus, handleSelectItem, openPanel, onClose],
  );

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Command
      label="Command palette"
      filter={paletteFilter}
      loop
      className="bg-charcoal-875 flex flex-col"
    >
      {/* Search input */}
      <div className="border-charcoal-700 flex items-center gap-3 border-b px-4 py-3">
        <Search className="text-charcoal-400 size-4 shrink-0" aria-hidden />
        <Command.Input
          ref={inputRef}
          value={query}
          onValueChange={setQuery}
          placeholder="Ask anything, search agents, panels, symbols…"
          className="text-charcoal-100 placeholder:text-charcoal-500 text-body min-w-0 flex-1 bg-transparent outline-none"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="text-charcoal-500 hover:text-charcoal-300 text-caption transition-colors"
            aria-label="Clear search"
          >
            esc
          </button>
        )}
      </div>

      {/* Results list */}
      <Command.List className="max-h-96 overflow-y-auto py-2">
        {/* Empty state — shown when query returns no matches */}
        <Command.Empty>
          <EmptyState
            dense
            icon={Search}
            headline="No matches"
            hint="Try a panel, action, agent, or ticker."
          />
        </Command.Empty>

        {/* ── Empty-query state: Recent + Suggested ─────────────────────── */}
        {!hasQuery && (
          <>
            {recentItems.length > 0 && (
              <Command.Group
                heading="Recent"
                className="[&_[cmdk-group-heading]]:group-heading-style"
              >
                {recentItems.map((item) => (
                  <PaletteItemRow
                    key={item.id}
                    item={item}
                    isRecent={false}
                    onSelect={() => handleSelectItem(item)}
                    icon={<KindIcon kind={item.kind} />}
                  />
                ))}
              </Command.Group>
            )}

            <Command.Group
              heading="Suggested"
              className="[&_[cmdk-group-heading]]:group-heading-style"
            >
              {SUGGESTED_ITEMS.map((suggestion) => (
                <Command.Item
                  key={suggestion.id}
                  value={suggestion.id}
                  keywords={[suggestion.label, suggestion.description ?? ""]}
                  onSelect={() => handleSelectSuggested(suggestion)}
                  className="aria-selected:bg-charcoal-800 flex cursor-pointer items-center gap-3 rounded-none px-4 py-2 transition-colors"
                >
                  <suggestion.Icon className="text-charcoal-400 size-4 shrink-0" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <div className="text-charcoal-100 text-body truncate">{suggestion.label}</div>
                    {suggestion.description && (
                      <div className="text-charcoal-500 text-caption truncate">
                        {suggestion.description}
                      </div>
                    )}
                  </div>
                </Command.Item>
              ))}
            </Command.Group>
          </>
        )}

        {/* ── Group 1: Ask AI ───────────────────────────────────────────── */}
        <Command.Group value="ask-ai" forceMount className={hasQuery ? undefined : "hidden"}>
          <AskAiItem query={query} onSelect={handleSelectAskAi} />
        </Command.Group>

        {/* ── Group 2: Agents ───────────────────────────────────────────── */}
        {agents.length > 0 && (
          <Command.Group heading="Agents" className="[&_[cmdk-group-heading]]:group-heading-style">
            {agents.map((item) => (
              <PaletteItemRow
                key={item.id}
                item={item}
                isRecent={recents.includes(item.id)}
                onSelect={() => handleSelectItem(item)}
                icon={<Bot className="size-4 shrink-0 text-amber-400" aria-hidden />}
              />
            ))}
          </Command.Group>
        )}

        {/* ── Group 3: Actions ──────────────────────────────────────────── */}
        {actions.length > 0 && (
          <Command.Group heading="Actions" className="[&_[cmdk-group-heading]]:group-heading-style">
            {actions.map((item) => (
              <PaletteItemRow
                key={item.id}
                item={item}
                isRecent={recents.includes(item.id)}
                onSelect={() => handleSelectItem(item)}
                icon={<CommandIcon className="text-charcoal-400 size-4 shrink-0" aria-hidden />}
              />
            ))}
          </Command.Group>
        )}

        {/* ── Group 4: Panels ───────────────────────────────────────────── */}
        {panels.length > 0 && (
          <Command.Group heading="Panels" className="[&_[cmdk-group-heading]]:group-heading-style">
            {panels.map((item) => (
              <PaletteItemRow
                key={item.id}
                item={item}
                isRecent={recents.includes(item.id)}
                onSelect={() => handleSelectItem(item)}
                icon={<LayoutGrid className="text-charcoal-400 size-4 shrink-0" aria-hidden />}
              />
            ))}
          </Command.Group>
        )}

        {/* ── Group 5: Symbols (query-gated, capped) ────────────────────── */}
        {showSymbols && symbols.length > 0 && (
          <Command.Group
            heading={`Symbols${symbols.length >= SYMBOL_CAP ? ` (top ${SYMBOL_CAP})` : ""}`}
            className="[&_[cmdk-group-heading]]:group-heading-style"
          >
            {symbols.map((item) => (
              <PaletteItemRow
                key={item.id}
                item={item}
                isRecent={recents.includes(item.id)}
                onSelect={() => handleSelectItem(item)}
                icon={<TrendingUp className="text-charcoal-400 size-4 shrink-0" aria-hidden />}
              />
            ))}
          </Command.Group>
        )}
      </Command.List>
    </Command>
  );
}

// ---------------------------------------------------------------------------
// Kind icon helper (used in Recent rows where kind is dynamic)
// ---------------------------------------------------------------------------

function KindIcon({ kind }: { kind: PaletteItem["kind"] }) {
  switch (kind) {
    case "agent":
      return <Bot className="size-4 shrink-0 text-amber-400" aria-hidden />;
    case "action":
      return <CommandIcon className="text-charcoal-400 size-4 shrink-0" aria-hidden />;
    case "panel":
      return <LayoutGrid className="text-charcoal-400 size-4 shrink-0" aria-hidden />;
    case "symbol":
      return <TrendingUp className="text-charcoal-400 size-4 shrink-0" aria-hidden />;
  }
}

// ---------------------------------------------------------------------------
// Ask AI row
// ---------------------------------------------------------------------------

interface AskAiItemProps {
  query: string;
  onSelect: () => void;
}

function AskAiItem({ query, onSelect }: AskAiItemProps) {
  const trimmed = query.trim();
  if (!trimmed) return null;

  return (
    <Command.Item
      value={`ask-ai:${trimmed}`}
      keywords={["ask", "ai", "agent", "query", trimmed]}
      onSelect={onSelect}
      forceMount
      className="aria-selected:bg-charcoal-800 flex cursor-pointer items-center gap-3 rounded-none px-4 py-2 transition-colors"
    >
      <Sparkles className="size-4 shrink-0 text-amber-400" aria-hidden />
      <div className="min-w-0 flex-1">
        <span className="text-charcoal-300 text-caption">Ask agent: </span>
        <span className="text-charcoal-100 text-body font-medium">&ldquo;{trimmed}&rdquo;</span>
      </div>
      <kbd className="border-charcoal-700 text-charcoal-500 text-micro rounded-control border px-1.5 py-0.5">
        Enter
      </kbd>
    </Command.Item>
  );
}

// ---------------------------------------------------------------------------
// Generic palette item row
// ---------------------------------------------------------------------------

interface PaletteItemRowProps {
  item: PaletteItem;
  isRecent: boolean;
  onSelect: () => void;
  icon: React.ReactNode;
}

function PaletteItemRow({ item, isRecent, onSelect, icon }: PaletteItemRowProps) {
  return (
    <Command.Item
      value={item.id}
      keywords={[item.label, item.description ?? ""].filter(Boolean)}
      onSelect={onSelect}
      className="aria-selected:bg-charcoal-800 flex cursor-pointer items-center gap-3 rounded-none px-4 py-2 transition-colors"
    >
      {icon}
      <div className="min-w-0 flex-1">
        <div className="text-charcoal-100 text-body truncate">{item.label}</div>
        {item.description && (
          <div className="text-charcoal-500 text-caption truncate">{item.description}</div>
        )}
      </div>
      {isRecent && <span className="text-charcoal-600 text-caption shrink-0">recent</span>}
    </Command.Item>
  );
}
