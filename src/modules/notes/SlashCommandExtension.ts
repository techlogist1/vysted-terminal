/**
 * Tiptap extension — "/" slash-command menu.
 *
 * Uses @tiptap/suggestion to detect "/" at the start of a word. On match it
 * dispatches a DOM custom event (`notes:slash-menu`) with the filtered items
 * list and the reference rect — the `NotesPanel` React component renders the
 * popup by listening to that event. On selection the item's `action(editor)`
 * fires and the "/" trigger character is deleted.
 */

import { Extension } from "@tiptap/core";
import { PluginKey } from "@tiptap/pm/state";
import { Suggestion } from "@tiptap/suggestion";

import { SLASH_COMMANDS, type SlashCommandItem } from "./slash-commands";

/** Custom event dispatched to the document when the slash menu should update. */
export interface SlashMenuDetail {
  items: SlashCommandItem[];
  /** DOMRect from `clientRect()` for positioning the popup. */
  rect: DOMRect | null;
  query: string;
  command: (item: SlashCommandItem) => void;
}

function dispatch(detail: SlashMenuDetail | null): void {
  document.dispatchEvent(new CustomEvent<SlashMenuDetail | null>("notes:slash-menu", { detail }));
}

export const SlashCommandExtension = Extension.create({
  name: "slashCommand",

  addProseMirrorPlugins() {
    return [
      Suggestion({
        // Distinct plugin key — two Suggestion plugins (slash + wikilink) on one
        // editor collide on the shared default key and crash editor init.
        pluginKey: new PluginKey("notesSlashCommand"),
        editor: this.editor,
        char: "/",
        startOfLine: false,
        command: ({ editor, range, props }) => {
          editor.chain().focus().deleteRange(range).run();
          (props as { action: (e: typeof editor) => void }).action(editor);
        },
        items: ({ query }: { query: string }) => {
          const q = query.toLowerCase().trim();
          if (!q) return SLASH_COMMANDS;
          return SLASH_COMMANDS.filter(
            (item) =>
              item.title.toLowerCase().includes(q) || item.description.toLowerCase().includes(q),
          );
        },
        render: () => ({
          onStart(props) {
            dispatch({
              items: props.items as SlashCommandItem[],
              rect: props.clientRect ? props.clientRect() : null,
              query: props.query,
              command: (item: SlashCommandItem) => {
                props.command({ action: item.action });
              },
            });
          },
          onUpdate(props) {
            dispatch({
              items: props.items as SlashCommandItem[],
              rect: props.clientRect ? props.clientRect() : null,
              query: props.query,
              command: (item: SlashCommandItem) => {
                props.command({ action: item.action });
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
