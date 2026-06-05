/**
 * Research-spaces store — per-space durable agent memory.
 *
 * A research space is a saved workspace dedicated to one symbol (detected via
 * the typed `SerializedWorkspace.researchSymbol` field, prefix as fall-back —
 * see `src/lib/workspace.ts`). This store keeps a `byName` map of each space's
 * agent memory: the chat transcript plus a short prior-research summary. The
 * map mirrors `WorkspaceResearchSpaces.byName` exactly so the workspace
 * serializer round-trips it without re-shaping — persisted in the `.vysted-
 * workspace` blob, NEVER localStorage (the CLAUDE.md rule).
 *
 * Chat history (`src/store/chat-history.ts`) is the LIVE conversation; it is
 * session-scoped and shared. This store is the DURABLE per-space archive: on
 * leaving a research space we `saveSpace` the live transcript into the map; on
 * entering one we `restoreSpace` its saved transcript back into the live chat
 * history. `switchSpace` does both atomically — the single entry point the
 * workspace serializer + loader call on a research-space transition.
 */

import { create } from "zustand";

import { type ChatMessage, useChatHistoryStore } from "@/store/chat-history";
import {
  RESEARCH_SPACE_TRANSCRIPT_CAP,
  type ResearchSpaceMemory,
  type ResearchSpaceTurn,
  type WorkspaceResearchSpaces,
} from "../../types/research-space";

/** Build a terse prior-research summary from a transcript (most recent first). */
export function summarizeTranscript(transcript: ResearchSpaceTurn[], symbol: string): string {
  const userTurns = transcript.filter((t) => t.role === "user");
  if (userTurns.length === 0) {
    return `New research space for ${symbol}; no prior questions yet.`;
  }
  const recent = userTurns
    .slice(-3)
    .map((t) => t.content.replace(/\s+/g, " ").trim().slice(0, 120))
    .filter(Boolean);
  const count = userTurns.length;
  const noun = count === 1 ? "question" : "questions";
  return `Prior research on ${symbol} (${count} ${noun}). Recent: ${recent.join(" | ")}`;
}

/** Snapshot the live chat history into persistable transcript turns (capped). */
function captureLiveTranscript(): ResearchSpaceTurn[] {
  return useChatHistoryStore
    .getState()
    .messages.filter(
      (m): m is ChatMessage & { role: "user" | "assistant" } =>
        (m.role === "user" || m.role === "assistant") && m.content.trim().length > 0,
    )
    .slice(-RESEARCH_SPACE_TRANSCRIPT_CAP)
    .map((m) => ({ role: m.role, content: m.content, createdAt: m.createdAt }));
}

/** Rebuild finalized `ChatMessage`s from a saved transcript (none left pending). */
function turnsToMessages(transcript: ResearchSpaceTurn[]): ChatMessage[] {
  return transcript.map((t, i) => ({
    id: `rs-${t.createdAt}-${i}`,
    role: t.role,
    content: t.content,
    createdAt: t.createdAt,
  }));
}

interface ResearchSpacesState {
  /** Durable memory per research-space workspace name. */
  byName: Record<string, ResearchSpaceMemory>;
  /** Replace the entire map — used by workspace load. */
  replaceAll: (spaces: WorkspaceResearchSpaces) => void;
  /** Snapshot the map in `WorkspaceResearchSpaces` shape — used by workspace save. */
  snapshot: () => WorkspaceResearchSpaces;
  /** The saved memory for a space, or `null` if none exists. */
  getMemory: (name: string) => ResearchSpaceMemory | null;
  /**
   * Capture the LIVE chat history into the named space's memory (with a fresh
   * derived summary). No-op when `name` is empty. Use on leaving / saving a
   * space. Returns the memory it wrote (for callers that want the summary).
   */
  saveSpace: (name: string, symbol: string) => ResearchSpaceMemory | null;
  /**
   * Restore the named space's saved transcript into the LIVE chat history,
   * replacing whatever is there. When the space has no saved memory, the live
   * history is cleared (a fresh space starts empty). Use on entering a space.
   */
  restoreSpace: (name: string) => void;
  /**
   * Leave `prev` (saving its live transcript) and enter `next` (restoring its
   * saved transcript). Either may be null — entering from / leaving to a non-
   * research space. The single entry point on a space transition.
   */
  switchSpace: (
    prev: { name: string; symbol: string } | null,
    next: { name: string; symbol: string } | null,
  ) => void;
}

export const useResearchSpacesStore = create<ResearchSpacesState>((set, get) => ({
  byName: {},
  replaceAll: (spaces) => {
    // Defensive copy so subscribers notice changes even if a caller hands back
    // the same object reference (Zustand uses shallow equality).
    const next: Record<string, ResearchSpaceMemory> = {};
    for (const [name, memory] of Object.entries(spaces.byName ?? {})) {
      next[name] = { ...memory, transcript: [...(memory.transcript ?? [])] };
    }
    set({ byName: next });
  },
  snapshot: () => {
    const out: Record<string, ResearchSpaceMemory> = {};
    for (const [name, memory] of Object.entries(get().byName)) {
      out[name] = { ...memory, transcript: [...memory.transcript] };
    }
    return { byName: out };
  },
  getMemory: (name) => get().byName[name] ?? null,
  saveSpace: (name, symbol) => {
    if (!name) {
      return null;
    }
    const transcript = captureLiveTranscript();
    const memory: ResearchSpaceMemory = {
      symbol,
      transcript,
      summary: summarizeTranscript(transcript, symbol),
      updatedAt: Date.now(),
    };
    set((state) => ({ byName: { ...state.byName, [name]: memory } }));
    return memory;
  },
  restoreSpace: (name) => {
    const memory = get().byName[name] ?? null;
    const chat = useChatHistoryStore.getState();
    if (!memory) {
      chat.clear();
      return;
    }
    chat.loadMessages(turnsToMessages(memory.transcript));
  },
  switchSpace: (prev, next) => {
    if (prev?.name) {
      get().saveSpace(prev.name, prev.symbol);
    }
    if (next?.name) {
      get().restoreSpace(next.name);
    } else if (prev?.name) {
      // Leaving a research space for a non-research space — start the ambient
      // copilot fresh rather than carrying the space's transcript over.
      useChatHistoryStore.getState().clear();
    }
  },
}));
