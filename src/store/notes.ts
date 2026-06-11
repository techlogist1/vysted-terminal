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
  /** Append text to the general notes with a blank-line separator (R10 write_note
   * apply path — Team FRONTEND-BRIEF calls this). */
  appendGeneral: (text: string) => void;
  setSymbolNote: (symbol: string, text: string) => void;
  /** Append text to a symbol's note with a blank-line separator (R10). */
  appendSymbolNote: (symbol: string, text: string) => void;
  setFocusSymbol: (symbol: string) => void;
  noteFor: (scope: string) => string;
  /** Scopes (uppercased tickers) that currently hold a non-empty note. */
  symbolsWithNotes: () => string[];
  toBundle: () => NotesBundle;
  fromBundle: (bundle: NotesBundle | null) => void;
}

/** Join an existing note body and new text with a double newline separator.
 *  Avoids leading/trailing blank lines when either part is empty. */
function joinNote(existing: string, text: string): string {
  const trimmed = existing.trim();
  const addendum = text.trim();
  if (!trimmed) return addendum;
  if (!addendum) return trimmed;
  return `${trimmed}\n\n${addendum}`;
}

export const useNotesStore = create<NotesState>((set, get) => ({
  general: "",
  bySymbol: {},
  focusSymbol: "",
  setGeneral: (text) => set({ general: text }),
  appendGeneral: (text) => set((s) => ({ general: joinNote(s.general, text) })),
  setSymbolNote: (symbol, text) => {
    const key = symbol.trim().toUpperCase();
    if (!key) {
      set({ general: text });
      return;
    }
    set((s) => ({ bySymbol: { ...s.bySymbol, [key]: text } }));
  },
  appendSymbolNote: (symbol, text) => {
    const key = symbol.trim().toUpperCase();
    if (!key) {
      set((s) => ({ general: joinNote(s.general, text) }));
      return;
    }
    set((s) => ({
      bySymbol: { ...s.bySymbol, [key]: joinNote(s.bySymbol[key] ?? "", text) },
    }));
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
