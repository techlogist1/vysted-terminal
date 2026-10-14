/**
 * Slash-command menu items for the notes editor.
 *
 * Each item describes what "/" triggers: a display label, a keyboard shortcut
 * hint, and an `action` callback that calls the Tiptap chain. The suggestion
 * plugin calls `action(editor)` when the user selects an item.
 */

import type { Editor } from "@tiptap/core";

export interface SlashCommandItem {
  title: string;
  description: string;
  action: (editor: Editor) => void;
}

export const SLASH_COMMANDS: SlashCommandItem[] = [
  {
    title: "Heading 1",
    description: "Large section heading",
    action: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run(),
  },
  {
    title: "Heading 2",
    description: "Medium section heading",
    action: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run(),
  },
  {
    title: "Heading 3",
    description: "Small section heading",
    action: (editor) => editor.chain().focus().toggleHeading({ level: 3 }).run(),
  },
  {
    title: "Bullet List",
    description: "Unordered list",
    action: (editor) => editor.chain().focus().toggleBulletList().run(),
  },
  {
    title: "Numbered List",
    description: "Ordered list",
    action: (editor) => editor.chain().focus().toggleOrderedList().run(),
  },
  {
    title: "Task List",
    description: "Checklist with checkboxes",
    action: (editor) => editor.chain().focus().toggleTaskList().run(),
  },
  {
    title: "Blockquote",
    description: "Indented quote block",
    action: (editor) => editor.chain().focus().toggleBlockquote().run(),
  },
  {
    title: "Code Block",
    description: "Monospace code fence",
    action: (editor) => editor.chain().focus().toggleCodeBlock().run(),
  },
  {
    title: "Table",
    description: "3-column table",
    action: (editor) =>
      editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
  },
  {
    title: "Divider",
    description: "Horizontal rule",
    action: (editor) => editor.chain().focus().setHorizontalRule().run(),
  },
];
