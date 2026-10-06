/**
 * Tiptap extension — `[[wikilink]]` symbol linking.
 *
 * Typing `[[` opens a suggestion popup that filters symbols-with-notes and
 * all watchlist symbols. Selecting an item inserts a `wikiLinkNode` (see
 * `WikiLinkNode.ts`) — a real inline node, not escaped text — that, when
 * clicked, fires `loadSymbolIntoChart` (the shared chart-command bus).
 *
 * The suggestion triggers on `[[` (two chars) — Tiptap suggestion supports
 * multi-character `char` values.
 *
 * ArrowUp/ArrowDown/Enter navigate and pick a row (R15-UI-024 repro b) via
 * the shared `createKeyboardNav` helper.
 *
 * Like the slash-command extension, rendering is done by the parent React
 * component via a `notes:wikilink-menu` DOM custom event.
 */
import { Extension } from "@tiptap/core";
import { PluginKey } from "@tiptap/pm/state";
import { Suggestion } from "@tiptap/suggestion";

import { createKeyboardNav } from "./suggestion-keyboard-nav";

export interface WikiLinkItem {
  symbol: string;
  hasNote: boolean;
}

export interface WikiLinkMenuDetail {
  items: WikiLinkItem[];
  rect: DOMRect | null;
  query: string;
  activeIndex: number;
  setActiveIndex: (index: number) => void;
  command: (item: WikiLinkItem) => void;
}

function dispatch(detail: WikiLinkMenuDetail | null): void {
  document.dispatchEvent(
    new CustomEvent<WikiLinkMenuDetail | null>("notes:wikilink-menu", {
      detail,
    }),
  );
}

export const WikiLinkExtension = Extension.create<{
  getSymbols: () => WikiLinkItem[];
}>({
  name: "wikiLink",

  addOptions() {
    return {
      getSymbols: () => [],
    };
  },

  addProseMirrorPlugins() {
    const { getSymbols } = this.options;

    return [
      Suggestion({
        // Distinct plugin key — must differ from the slash-command Suggestion or
        // the two collide on the shared default key and crash editor init.
        pluginKey: new PluginKey("notesWikiLink"),
        editor: this.editor,
        char: "[[",
        command: ({ editor, range, props }) => {
          const symbol = (props as WikiLinkItem).symbol;
          editor
            .chain()
            .focus()
            .deleteRange(range)
            .insertContent({ type: "wikiLinkNode", attrs: { symbol } })
            .run();
        },
        items: ({ query }: { query: string }) => {
          const q = query.toUpperCase().trim();
          const all = getSymbols();
          if (!q) return all;
          return all.filter((s) => s.symbol.includes(q));
        },
        render: () => {
          const nav = createKeyboardNav<WikiLinkItem>();
          let currentCommand: ((props: WikiLinkItem) => void) | null = null;
          // `onKeyDown`'s props (SuggestionKeyDownProps) carry only
          // {view, event, range} — no clientRect/query — so the last-seen
          // rect/query from onStart/onUpdate is cached here for re-emitting
          // after an arrow-key move.
          let latestRect: DOMRect | null = null;
          let latestQuery = "";

          const emit = () => {
            dispatch({
              items: nav.getItems(),
              rect: latestRect,
              query: latestQuery,
              activeIndex: nav.activeIndex,
              setActiveIndex: (i: number) => {
                nav.setActiveIndex(i);
                emit();
              },
              command: (item: WikiLinkItem) => {
                currentCommand?.(item);
              },
            });
          };

          return {
            onStart(props) {
              currentCommand = props.command;
              latestRect = props.clientRect ? props.clientRect() : null;
              latestQuery = props.query;
              nav.reset();
              nav.setItems(props.items as WikiLinkItem[]);
              emit();
            },
            onUpdate(props) {
              currentCommand = props.command;
              latestRect = props.clientRect ? props.clientRect() : null;
              latestQuery = props.query;
              nav.setItems(props.items as WikiLinkItem[]);
              emit();
            },
            onKeyDown(props) {
              if (props.event.key === "Escape") {
                dispatch(null);
                return true;
              }
              const handled = nav.handleKey(props.event.key, (item) => {
                currentCommand?.(item);
              });
              if (handled) {
                if (props.event.key !== "Enter") {
                  emit();
                }
                return true;
              }
              return false;
            },
            onExit() {
              dispatch(null);
            },
          };
        },
      }),
    ];
  },
});
