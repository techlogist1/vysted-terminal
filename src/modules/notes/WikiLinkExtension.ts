/**
 * Tiptap extension — `[[wikilink]]` symbol linking.
 *
 * Typing `[[` opens a suggestion popup that filters symbols-with-notes and
 * all watchlist symbols. Selecting an item inserts an inline `[[SYMBOL]]`
 * mark that, when clicked, fires `loadSymbolIntoChart` (the shared
 * chart-command bus) — reusing the same always-consumed channel the research
 * brief uses (CLAUDE.md: "a chip → loadSymbolIntoChart").
 *
 * The suggestion triggers on `[[` (two chars) — Tiptap suggestion supports
 * multi-character `char` values. The closing `]]` is appended automatically.
 *
 * Like the slash-command extension, rendering is done by the parent React
 * component via a `notes:wikilink-menu` DOM custom event.
 */

import { Extension, type Range } from "@tiptap/core";
import { Suggestion } from "@tiptap/suggestion";

export interface WikiLinkItem {
  symbol: string;
  hasNote: boolean;
}

export interface WikiLinkMenuDetail {
  items: WikiLinkItem[];
  rect: DOMRect | null;
  query: string;
  command: (item: WikiLinkItem) => void;
}

function dispatch(detail: WikiLinkMenuDetail | null): void {
  document.dispatchEvent(
    new CustomEvent<WikiLinkMenuDetail | null>("notes:wikilink-menu", {
      detail,
    }),
  );
}

/** Insert `[[SYMBOL]]` at `range` then close the suggestion. */
function insertWikiLink(
  editor: Parameters<typeof Suggestion>[0]["editor"],
  range: Range,
  symbol: string,
): void {
  editor.chain().focus().deleteRange(range).insertContent(`[[${symbol}]]`).run();
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
        editor: this.editor,
        char: "[[",
        command: ({ editor, range, props }) => {
          insertWikiLink(editor, range, (props as WikiLinkItem).symbol);
        },
        items: ({ query }: { query: string }) => {
          const q = query.toUpperCase().trim();
          const all = getSymbols();
          if (!q) return all;
          return all.filter((s) => s.symbol.includes(q));
        },
        render: () => ({
          onStart(props) {
            dispatch({
              items: props.items as WikiLinkItem[],
              rect: props.clientRect ? props.clientRect() : null,
              query: props.query,
              command: (item: WikiLinkItem) => {
                props.command(item);
              },
            });
          },
          onUpdate(props) {
            dispatch({
              items: props.items as WikiLinkItem[],
              rect: props.clientRect ? props.clientRect() : null,
              query: props.query,
              command: (item: WikiLinkItem) => {
                props.command(item);
              },
            });
          },
          onKeyDown(props) {
            if (props.event.key === "Escape") {
              dispatch(null);
              return true;
            }
            return false;
          },
          onExit() {
            dispatch(null);
          },
        }),
      }),
    ];
  },
});
