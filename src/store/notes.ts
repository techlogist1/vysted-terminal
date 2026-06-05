/**
 * Notes store — per-symbol and general markdown notes.
 *
 * Markdown is the canonical format: the Tiptap editor serialises to markdown
 * on every debounced change and stores it here. Restoring a scope deserialises
 * from markdown back into the editor. The workspace blob carries a `notes`
 * field (`NotesBundle`) for cross-session persistence, piggybacking on the
 * existing atomic sidecar workspace-save path.
 *
 * The Rust `write_text_atomic` command additionally writes each note as a real
 * `.md` file under `{appData}/notes/` for Obsidian-grade on-disk durability.
 */

import { create } from "zustand";

/** The serialisable notes bundle stored inside the workspace blob. */
export interface NotesBundle {
  /** General notes (scope = "general"). */
  general: string;
  /** Per-symbol notes, keyed by upper-cased symbol (e.g. "AAPL"). */
  bySymbol: Record<string, string>;
  /** The focused symbol when notes were last saved. Optional back-compat. */
  focusSymbol?: string;
}

interface NotesState {
  /** General notes content (markdown). */
  general: string;
  /** Per-symbol notes, keyed by upper-cased symbol. */
  bySymbol: Record<string, string>;
  /** The symbol currently focused in the notes scope chip. `undefined` = general. */
  focusSymbol: string | undefined;

  /** Replace the general note. */
  setGeneral: (text: string) => void;
  /** Set the note for a specific symbol (upper-cased). */
  setSymbolNote: (symbol: string, text: string) => void;
  /** Change the focused symbol (undefined = general). */
  setFocusSymbol: (symbol: string | undefined) => void;
  /**
   * Return the markdown content for the current scope (general or the focused
   * symbol). Returns an empty string if no note exists yet.
   */
  noteFor: (scope: string | undefined) => string;
  /** Symbols that have at least one non-empty note. */
  symbolsWithNotes: () => string[];
  /** Serialise state to a `NotesBundle` for the workspace blob. */
  toBundle: () => NotesBundle;
  /** Restore state from a `NotesBundle` (e.g. on workspace load). */
  fromBundle: (bundle: NotesBundle) => void;
}

export const useNotesStore = create<NotesState>((set, get) => ({
  general: "",
  bySymbol: {},
  focusSymbol: undefined,

  setGeneral: (text) => set({ general: text }),

  setSymbolNote: (symbol, text) =>
    set((state) => ({
      bySymbol: { ...state.bySymbol, [symbol.toUpperCase()]: text },
    })),

  setFocusSymbol: (symbol) =>
    set({ focusSymbol: symbol !== undefined ? symbol.toUpperCase() : undefined }),

  noteFor: (scope) => {
    const state = get();
    if (!scope) return state.general;
    return state.bySymbol[scope.toUpperCase()] ?? "";
  },

  symbolsWithNotes: () => {
    const { bySymbol } = get();
    return Object.entries(bySymbol)
      .filter(([, text]) => text.trim().length > 0)
      .map(([sym]) => sym);
  },

  toBundle: () => {
    const { general, bySymbol, focusSymbol } = get();
    return { general, bySymbol, focusSymbol };
  },

  fromBundle: (bundle) =>
    set({
      general: bundle.general ?? "",
      bySymbol: bundle.bySymbol ?? {},
      focusSymbol: bundle.focusSymbol,
    }),
}));
