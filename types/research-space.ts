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

/**
 * One figure the agent STATED this session (R13 JARVIS 3a) — recorded
 * DETERMINISTICALLY from a published brief's structured metric cards (no LLM
 * parsing), so a later turn that contradicts it materially can be reconciled
 * openly instead of silently switched.
 */
export interface ResearchSpaceClaim {
  /** The instrument the figure is about (upper-case ticker). */
  symbol: string;
  /** The metric label as the brief stated it (e.g. "P/E", "Revenue growth"). */
  metric: string;
  /** The stated numeric value. */
  value: number;
  /** Epoch milliseconds the figure was stated. */
  statedAt: number;
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
  /**
   * Prior stated figures for this space (R13 JARVIS 3a) — a bounded,
   * deterministically-recorded ledger of the metrics the agent published here, so
   * the copilot can reconcile a materially-contradicting new figure openly rather
   * than silently switching. Capped to {@link RESEARCH_SPACE_CLAIMS_CAP}. Optional
   * — older blobs omit it.
   */
  claims?: ResearchSpaceClaim[];
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

/** Hard cap on stated-value claims retained per space (keeps the blob bounded). */
export const RESEARCH_SPACE_CLAIMS_CAP = 50;
