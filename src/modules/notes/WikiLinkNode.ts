/**
 * `[[SYMBOL]]` wikilink — a Tiptap inline atom node, not escaped text
 * (R15-UI-024 repro c/d). Registered alongside `WikiLinkExtension` (which
 * drives the "[[" suggestion popup); this node is what the popup — and the
 * toolbar "Insert [[wikilink]]" button — actually insert.
 *
 * Clicking the rendered chip fires `loadSymbolIntoChart`, the shared
 * chart-command bus other chip surfaces (research brief, watchlist) already
 * use (CLAUDE.md: "a chip → loadSymbolIntoChart").
 *
 * Markdown round-trip: a custom marked.js inline tokenizer (registered via
 * `markdownTokenizer`) recognizes `[[SYMBOL]]`; `parseMarkdown`/
 * `renderMarkdown` convert it to/from this node so `getMarkdown()` emits
 * `[[SYMBOL]]` literally instead of a decomposed/escaped form.
 */
import { Node, mergeAttributes } from "@tiptap/core";

import { loadSymbolIntoChart } from "@/lib/host-actions";

const WIKILINK_PATTERN = /^\[\[([^\]\n]+)\]\]/;

export const WikiLinkNode = Node.create({
  name: "wikiLinkNode",
  group: "inline",
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      symbol: {
        default: "",
        parseHTML: (element: HTMLElement) => element.getAttribute("data-wikilink") ?? "",
        renderHTML: (attrs: { symbol?: string }) => ({ "data-wikilink": attrs.symbol ?? "" }),
      },
    };
  },

  parseHTML() {
    return [{ tag: "span[data-wikilink]" }];
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      "span",
      mergeAttributes(HTMLAttributes, { class: "notes-wikilink" }),
      `[[${node.attrs.symbol as string}]]`,
    ];
  },

  addNodeView() {
    return ({ node }) => {
      const symbol = String(node.attrs.symbol ?? "");
      const dom = document.createElement("span");
      dom.className = "notes-wikilink";
      dom.dataset.wikilink = symbol;
      dom.setAttribute("role", "link");
      dom.tabIndex = 0;
      dom.textContent = `[[${symbol}]]`;
      dom.addEventListener("click", (event) => {
        event.preventDefault();
        loadSymbolIntoChart(symbol);
      });
      return { dom };
    };
  },

  markdownTokenizer: {
    name: "wikiLinkNode",
    level: "inline",
    start: "[[",
    tokenize(src: string) {
      const match = WIKILINK_PATTERN.exec(src);
      if (!match) return undefined;
      // `type` must be set — @tiptap/markdown's tokenizer wrapper only keeps
      // a match when `result.type` is truthy, otherwise it silently falls
      // through to marked's default tokenizers (which is why an untyped
      // result was previously left as escaped plain text).
      return { type: "wikiLinkNode", raw: match[0], symbol: match[1].trim().toUpperCase() };
    },
  },

  parseMarkdown(token) {
    return { type: "wikiLinkNode", attrs: { symbol: String(token.symbol ?? "") } };
  },

  renderMarkdown(node) {
    const symbol = (node.attrs as { symbol?: string } | undefined)?.symbol ?? "";
    return `[[${symbol}]]`;
  },
});
