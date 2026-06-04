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
  /** The scope the Notes panel is focused on ("" = General, else an uppercased
   * ticker). Persisted so a per-stock research space reopens scoped to its
   * ticker. Optional for blobs saved before this shipped. */
  focusSymbol?: string;
}

interface NotesState {
  general: string;
  bySymbol: Record<string, string>;
  /** Active scope of the Notes panel — "" for General, else an uppercased
   * ticker. Lifted into the store (was panel-local) so a per-stock research
   * space can scope it and it persists with the workspace. */
  focusSymbol: string;
  setGeneral: (text: string) => void;
  setSymbolNote: (symbol: string, text: string) => void;
  setFocusSymbol: (symbol: string) => void;
  noteFor: (scope: string) => string;
  /** Scopes (uppercased tickers) that currently hold a non-empty note. */
  symbolsWithNotes: () => string[];
  toBundle: () => NotesBundle;
  fromBundle: (bundle: NotesBundle | null) => void;
}

export const useNotesStore = create<NotesState>((set, get) => ({
  general: "",
  bySymbol: {},
  focusSymbol: "",
  setGeneral: (text) => set({ general: text }),
  setSymbolNote: (symbol, text) => {
    const key = symbol.trim().toUpperCase();
    if (!key) {
      set({ general: text });
      return;
    }
    set((s) => ({ bySymbol: { ...s.bySymbol, [key]: text } }));
  },
  setFocusSymbol: (symbol) => set({ focusSymbol: symbol.trim().toUpperCase() }),
  noteFor: (scope) => {
    const key = scope.trim().toUpperCase();
    return key ? (get().bySymbol[key] ?? "") : get().general;
  },
  symbolsWithNotes: () =>
    Object.entries(get().bySymbol)
      .filter(([, text]) => text.trim().length > 0)
      .map(([sym]) => sym)
      .sort(),
  toBundle: () => ({
    general: get().general,
    bySymbol: get().bySymbol,
    focusSymbol: get().focusSymbol,
  }),
  fromBundle: (bundle) =>
    set({
      general: bundle?.general ?? "",
      bySymbol: bundle?.bySymbol ?? {},
      focusSymbol: (bundle?.focusSymbol ?? "").toUpperCase(),
    }),
}));
