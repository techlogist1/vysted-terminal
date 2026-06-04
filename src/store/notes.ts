import { create } from "zustand";

/**
 * In-app research notes — a free-text scratchpad, scoped per-stock (and a
 * "General" bucket). Rides the workspace blob (like the brief) so notes persist
 * with a saved/named workspace and survive relaunch; never touches localStorage.
 */
export interface NotesBundle {
  general: string;
  /** Per-symbol notes, keyed by uppercased ticker. */
  bySymbol: Record<string, string>;
}

interface NotesState {
  general: string;
  bySymbol: Record<string, string>;
  setGeneral: (text: string) => void;
  setSymbolNote: (symbol: string, text: string) => void;
  noteFor: (scope: string) => string;
  /** Scopes (uppercased tickers) that currently hold a non-empty note. */
  symbolsWithNotes: () => string[];
  toBundle: () => NotesBundle;
  fromBundle: (bundle: NotesBundle | null) => void;
}

export const useNotesStore = create<NotesState>((set, get) => ({
  general: "",
  bySymbol: {},
  setGeneral: (text) => set({ general: text }),
  setSymbolNote: (symbol, text) => {
    const key = symbol.trim().toUpperCase();
    if (!key) {
      set({ general: text });
      return;
    }
    set((s) => ({ bySymbol: { ...s.bySymbol, [key]: text } }));
  },
  noteFor: (scope) => {
    const key = scope.trim().toUpperCase();
    return key ? (get().bySymbol[key] ?? "") : get().general;
  },
  symbolsWithNotes: () =>
    Object.entries(get().bySymbol)
      .filter(([, text]) => text.trim().length > 0)
      .map(([sym]) => sym)
      .sort(),
  toBundle: () => ({ general: get().general, bySymbol: get().bySymbol }),
  fromBundle: (bundle) => set({ general: bundle?.general ?? "", bySymbol: bundle?.bySymbol ?? {} }),
}));
