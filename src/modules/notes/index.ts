import type { VystedModule } from "@/lib/module-registry";

import { NotesPanel } from "./NotesPanel";

/**
 * Notes module (003 rebuild) — an in-app research scratchpad, scoped per-stock or
 * General. Notes ride the workspace blob, so they save with a named workspace /
 * per-stock research space. Part of the OS-for-finance surface.
 */
export const notesModule: VystedModule = {
  id: "notes",
  title: "Notes",
  panels: [
    {
      id: "notes",
      title: "Notes",
      icon: "notebook-pen",
      component: "notes-panel",
      singleton: true,
      defaultSize: { w: 4, h: 6 },
    },
  ],
  commands: [
    {
      id: "notes.open",
      trigger: "notes",
      title: "Open Notes",
      description: "Free-text research notes, scoped per-stock or general",
      icon: "notebook-pen",
      opensPanel: "notes",
    },
  ],
  panelComponents: {
    "notes-panel": NotesPanel,
  },
};
