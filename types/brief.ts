/**
 * Research-brief contract (FR-074, PASS_B_RESEARCH B.5).
 *
 * The serialisable shape JARVIS' research pipeline emits and the BriefPanel
 * renders. It is the single source of truth for the B+A research output surface:
 * a markdown body with inline `[n]` citation chips, the sources behind those
 * chips, the FAST/DEEP mode + cost metadata, and an honest `webAvailable` flag
 * that lets the panel state "no web-search backend configured" rather than fake
 * an error or an empty result.
 *
 * NO secrets cross this contract — like the rest of the workspace blob it carries
 * only non-secret research output (the BYOK web-search key is keychain-only).
 */

/** One cited source behind an inline `[n]` chip in the brief body. */
export interface BriefSource {
  /** Canonical URL of the source. */
  url: string;
  /** Human-readable title shown in the sources tray. */
  title: string;
  /** A short snippet the brief drew from, shown under the title. */
  excerpt: string;
  /**
   * The source's domain (e.g. `sec.gov`), used for the domain badge + favicon.
   * Optional — when absent the panel derives it from {@link url}.
   */
  domain?: string;
}

/** The kind of a single step in the research pipeline's trace. */
export type BriefStepKind = "plan" | "tool" | "search" | "compress" | "reflect" | "synthesize";

/** The terminal status of a single research step. */
export type BriefStepStatus = "ok" | "error" | "skipped";

/** One entry in the dev-only research step-log (plan → tool/search → synthesize). */
export interface BriefStep {
  /** Which stage of the pipeline this step belongs to. */
  kind: BriefStepKind;
  /** A one-line human description of what the step did. */
  detail: string;
  /** Wall-clock latency of the step in milliseconds, when measured. */
  latencyMs?: number;
  /** How the step resolved. */
  status: BriefStepStatus;
}

/** The two research depths the pipeline runs in. */
export type BriefMode = "FAST" | "DEEP";

/**
 * A complete research brief — the payload the BriefPanel renders and the
 * workspace blob persists (`SerializedWorkspace.brief`).
 */
export interface ResearchBriefData {
  /** The natural-language research question the brief answers. */
  query: string;
  /** The primary ticker the brief is about, when the query resolved to one. */
  symbol?: string;
  /** The depth the pipeline ran in. */
  mode: BriefMode;
  /** The brief body, in markdown, with inline `[n]` citation markers. */
  markdown: string;
  /** The cited sources, indexed 1-based by the `[n]` markers in {@link markdown}. */
  sources: BriefSource[];
  /**
   * The number of sources consulted. Usually `sources.length`, but the pipeline
   * may report a higher count when it consulted more than it cited.
   */
  sourceCount: number;
  /** Token + spend cost of the run, when the pipeline metered it. */
  cost?: {
    /** Total tokens consumed across the run. */
    tokens?: number;
    /** Total spend in USD across the run. */
    spendUsd?: number;
  };
  /**
   * Whether a web-search backend was available for this run. When `false` the
   * brief was built from structured data only — the panel says so honestly
   * (NOT an error, NOT an empty state).
   */
  webAvailable: boolean;
  /**
   * A free-form honest note from the pipeline (e.g. why web search was skipped).
   * Surfaced prominently when {@link webAvailable} is `false`.
   */
  note?: string;
  /** The dev-only research step trace, when the pipeline emitted one. */
  steps?: BriefStep[];
  /** Epoch milliseconds the brief was produced. */
  createdAt: number;
}
