/**
 * Vysted Terminal — per-research-space agent memory contract.
 *
 * A "research space" is a saved workspace dedicated to investigating one symbol.
 * Historically a research space was detected solely by a `"Research: "` name
 * prefix (fragile — a rename or a stray colon broke detection). The workspace
 * blob now carries a typed `researchSymbol` field (see `SerializedWorkspace`);
 * this module is the durable per-space agent memory that rides alongside it so
 * the copilot "remembers" what it researched the last time the user was in that
 * space.
 *
 * The memory is plain serializable data (no React types, no functions) so it
 * round-trips through `.vysted-workspace` JSON exactly like chart drawings do —
 * persisted in the workspace blob, NEVER localStorage (the CLAUDE.md rule:
 * UI/session state lives in the workspace blob the sidecar stores opaquely).
 */

/** One persisted chat turn in a research space's transcript. */
export interface ResearchSpaceTurn {
  /** Conversation role — system turns are dropped on save (they re-derive). */
  role: "user" | "assistant";
  /** The turn's text content. */
  content: string;
  /** Epoch milliseconds when the turn was created. */
  createdAt: number;
}

/** Durable agent memory for a single research space. */
export interface ResearchSpaceMemory {
  /** The symbol this space researches (mirrors `SerializedWorkspace.researchSymbol`). */
  symbol: string;
  /**
   * The space's saved chat transcript — capped to the most recent turns so the
   * blob stays bounded. Restored into the live chat history on space entry.
   */
  transcript: ResearchSpaceTurn[];
  /**
   * A short, human-readable prior-research summary injected into the agent
   * context so the model has an anchor without re-reading the whole transcript.
   * Optional — derived from the transcript when not set explicitly.
   */
  summary?: string;
  /** Epoch milliseconds the memory was last written. */
  updatedAt: number;
}

/**
 * The workspace-persisted map of research-space memories, keyed by the space's
 * workspace name. Mirrors `WorkspaceDrawings.byPanel` in shape so the workspace
 * serializer round-trips it without re-shaping.
 */
export interface WorkspaceResearchSpaces {
  /** Memory per research-space workspace name. */
  byName: Record<string, ResearchSpaceMemory>;
}

/** Hard cap on transcript turns persisted per space (keeps the blob bounded). */
export const RESEARCH_SPACE_TRANSCRIPT_CAP = 40;
