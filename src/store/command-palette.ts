import { create } from "zustand";

import type { CommandSpec } from "../../types/plugin";

interface CommandPaletteState {
  /** Whether the cmd+K command palette modal is open. */
  open: boolean;
  /** Commands shown in the palette — aggregated from enabled modules. */
  commands: CommandSpec[];
  setOpen: (open: boolean) => void;
  toggle: () => void;
  setCommands: (commands: CommandSpec[]) => void;
}

/**
 * Global UI state for the command palette. The command list is populated from
 * the enabled modules at startup (`page.tsx`); Teammate D keeps it in sync as
 * modules are toggled.
 */
export const useCommandPalette = create<CommandPaletteState>((set) => ({
  open: false,
  commands: [],
  setOpen: (open) => set({ open }),
  toggle: () => set((state) => ({ open: !state.open })),
  setCommands: (commands) => set({ commands }),
}));
