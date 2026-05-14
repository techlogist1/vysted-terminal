import { create } from "zustand";

interface CommandPaletteState {
  /** Whether the cmd+K command palette modal is open. */
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
}

/** Global UI state for the command palette. Phase 1+ will add the command list here. */
export const useCommandPalette = create<CommandPaletteState>((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
  toggle: () => set((state) => ({ open: !state.open })),
}));
