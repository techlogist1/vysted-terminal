/**
 * Tiptap extension — "/" slash-command menu.
 *
 * Uses @tiptap/suggestion to detect "/" at the start of a word. On match it
 * dispatches a DOM custom event (`notes:slash-menu`) with the filtered items
 * list and the reference rect — the `NotesPanel` React component renders the
 * popup by listening to that event. On selection the item's `action(editor)`
 * fires and the "/" trigger character is deleted.
 *
 * ArrowUp/ArrowDown/Enter navigate and pick a row (R15-UI-024 repro b) via
 * the shared `createKeyboardNav` helper; a `createTriggerSelectionGuard`
 * plugin keeps "/" from eating an active selection before the menu opens
 * (repro e).
 */
import { Extension, type Editor } from "@tiptap/core";
import { PluginKey } from "@tiptap/pm/state";
import { Suggestion } from "@tiptap/suggestion";

import { SLASH_COMMANDS, type SlashCommandItem } from "./slash-commands";
import { createKeyboardNav } from "./suggestion-keyboard-nav";
import { createTriggerSelectionGuard } from "./trigger-selection-guard";

/** Custom event dispatched to the document when the slash menu should update. */
export interface SlashMenuDetail {
  items: SlashCommandItem[];
  /** DOMRect from `clientRect()` for positioning the popup. */
  rect: DOMRect | null;
  query: string;
  activeIndex: number;
  setActiveIndex: (index: number) => void;
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
        render: () => {
          const nav = createKeyboardNav<SlashCommandItem>();
          let currentCommand: ((props: { action: (editor: Editor) => void }) => void) | null = null;
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
              command: (item: SlashCommandItem) => {
                currentCommand?.({ action: item.action });
              },
            });
          };

          return {
            onStart(props) {
              currentCommand = props.command;
              latestRect = props.clientRect ? props.clientRect() : null;
              latestQuery = props.query;
              nav.reset();
              nav.setItems(props.items as SlashCommandItem[]);
              emit();
            },
            onUpdate(props) {
              currentCommand = props.command;
              latestRect = props.clientRect ? props.clientRect() : null;
              latestQuery = props.query;
              nav.setItems(props.items as SlashCommandItem[]);
              emit();
            },
            onKeyDown(props) {
              if (props.event.key === "Escape") {
                dispatch(null);
                return true;
              }
              const handled = nav.handleKey(props.event.key, (item) => {
                currentCommand?.({ action: item.action });
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
      createTriggerSelectionGuard(),
    ];
  },
});
