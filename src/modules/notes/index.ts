import type { VystedModule } from "@/lib/module-registry";

import { NotesPanel } from "./NotesPanel";

/**
 * Notes module — Tiptap/Obsidian-grade markdown editor (FR-121 / SC-032).
 *
 * Singleton panel; markdown is the canonical blob; notes persist via both
 * the workspace blob (sidecar autosave) and atomic `.md` files on disk
 * (`write_text_atomic` Rust command). Sharing: .md export, PNG, PDF print.
 */
export const notesModule: VystedModule = {
  id: "notes",
  title: "Notes",
  panels: [
    {
      id: "notes",
      title: "Notes",
      icon: "pencil",
      component: "notes-panel",
      singleton: true,
      defaultSize: { w: 3, h: 8 },
    },
  ],
  commands: [
    {
      id: "notes.open",
      trigger: "notes",
      title: "Open Notes",
      description: "Markdown notes editor — per-symbol and general",
      icon: "pencil",
      opensPanel: "notes",
    },
  ],
  panelComponents: {
    "notes-panel": NotesPanel,
  },
};
