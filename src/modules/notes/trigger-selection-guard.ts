/**
 * Prevents the "/" (slash command) and "[" (wikilink) suggestion-trigger
 * characters from silently deleting a non-empty selection before the
 * suggestion menu opens (R15-UI-024 repro e: selecting text, then triggering
 * a slash/wikilink command lost the selected text — ProseMirror's default
 * typing behaviour replaces a selection with the typed character).
 *
 * Collapses the selection to its end — keeping the text — and appends the
 * trigger character there instead, so a block-level slash command (heading,
 * list, blockquote…) still applies over the preserved text and a `[[`
 * wikilink trigger no longer eats what was selected. The same class of bug
 * hit both SlashCommandExtension and WikiLinkExtension, so this is the one
 * shared fix for both trigger characters (registered once, in
 * SlashCommandExtension's addProseMirrorPlugins).
 */
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { TextSelection } from "@tiptap/pm/state";

const TRIGGER_KEYS = new Set(["/", "["]);

export function createTriggerSelectionGuard(): Plugin {
  return new Plugin({
    key: new PluginKey("notesTriggerSelectionGuard"),
    props: {
      handleKeyDown(view, event) {
        if (!TRIGGER_KEYS.has(event.key)) return false;
        const { state } = view;
        const { selection } = state;
        if (selection.empty) return false;
        const { to } = selection;
        const tr = state.tr
          .setSelection(TextSelection.create(state.doc, to))
          .insertText(event.key, to, to);
        view.dispatch(tr);
        event.preventDefault();
        return true;
      },
    },
  });
}
