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

import type { Fundamentals, Quote } from "./data";

/**
 * One leg of the research bundle's `structured` map — a provenance-tagged data
 * pull (price / fundamentals / news / filings). Uniform shape so a consumer reads
 * provenance the same way for every leg: `ok` + `provider` always, `data` when
 * `ok`, `error` when not. `data`'s concrete shape depends on the leg.
 */
export interface BriefStructuredLeg<T = unknown> {
  /** Whether this leg's pull succeeded. */
  ok: boolean;
  /** The serving provider (e.g. `yfinance`), for the FR-041 provenance badge. */
  provider?: string | null;
  /** The payload when `ok` (a `Quote` for price, `Fundamentals` for fundamentals, …). */
  data?: T;
  /** A short human reason when the leg failed. */
  error?: string;
}

/**
 * The research bundle's `structured` map — the real, provenance-tagged numbers
 * behind the brief (price/fundamentals/news/filings), used to render native
 * metric cards rather than re-parse them out of prose. Optional + every leg
 * optional: a DEEP run may carry only `resolved`, a structured-only run may have
 * empty legs. NEVER fabricated — an absent/`ok:false` leg renders nothing.
 */
export interface BriefStructured {
  /** The symbol-resolution result (instrument identity). */
  resolved?: unknown;
  /** Latest quote leg. */
  price?: BriefStructuredLeg<Quote>;
  /** Valuation-ratios leg. */
  fundamentals?: BriefStructuredLeg<Fundamentals>;
  /** Recent-news leg. */
  news?: BriefStructuredLeg;
  /** Filings-index leg. */
  filings?: BriefStructuredLeg;
  /**
   * The metric-semantics leg (R10, D37/E8): values COMPUTED sidecar-side from
   * the raw legs with explicit labels and bases, plus cross-source conflicts.
   * `provider` is always `"derived"`. Absent on older briefs.
   */
  derived?: BriefStructuredLeg<BriefDerivedMetrics>;
}

/**
 * One semantically-disciplined metric value (R10 semantics layer). Every number
 * the brief states carries its label, basis, and (when computed) formula — so
 * drawdown-from-high can never wear 52-week-change's label and a growth figure
 * always names its base.
 */
export interface BriefDerivedValue {
  /** The numeric value, or null when inputs were missing (never fabricated). */
  value: number | null;
  /** The exact display label (e.g. "Below 52-week high"). */
  label: string;
  /** The measurement basis (e.g. "TTM", "FY/FY", "vs 52w high", "of face value"). */
  basis?: string;
  /** The computation, when derived (e.g. "(52w high − price) / 52w high"). */
  formula?: string;
  /** How to render the value. */
  unit?: "percent" | "currency" | "ratio";
}

/** A cross-source numeric disagreement the pipeline flagged instead of silently picking. */
export interface BriefMetricConflict {
  /** The metric in conflict (e.g. "dividend_yield", "market_cap"). */
  field: string;
  /**
   * The disagreeing values with their provenance. `basis` names each side's
   * measurement basis when the conflict is basis-bearing (R12 / D66 growth
   * cross-check: provider-claimed mrq_yoy vs statement-computed quarterly YoY).
   */
  sources: { provider: string; value: number | string; basis?: string }[];
  /** One human line on why this is flagged and what would reconcile it. */
  note: string;
  /**
   * The quarter-end pair (ISO dates) a statement-computed figure compared
   * (R12 / D66) — present only on the growth cross-check conflicts.
   */
  quarters?: { mrq: string; prior: string };
  /** Conflict class discriminator (R12 / D67) — e.g. "identity_conflict". */
  kind?: string;
  /** Token-set similarity behind an identity conflict (R12 / D67). */
  similarity?: number;
  /** The instrument the conflict names, when symbol-specific (R12 / D67). */
  symbol?: string;
}

/** The semantics leg's payload — derived, labeled metrics + flagged conflicts. */
export interface BriefDerivedMetrics {
  /** (52w high − price) / 52w high — the true "off the high" figure. */
  drawdown_from_high?: BriefDerivedValue;
  /** Yahoo's 52-week price change — explicitly NOT drawdown. */
  fifty_two_week_change?: BriefDerivedValue;
  /** Reconciled dividend yield (fraction of price). */
  dividend_yield?: BriefDerivedValue;
  /** Dividend in listing currency per share. */
  dividend_per_share?: BriefDerivedValue;
  /** Revenue growth with its basis named. */
  revenue_growth?: BriefDerivedValue;
  /** Earnings growth with its basis named. */
  earnings_growth?: BriefDerivedValue;
  /**
   * Growth computed from the provider's own quarterly income statements
   * (R12 / D66) — present ONLY when it diverges from the provider scalar
   * beyond tolerance (an agreeing figure emits no extra card). The provider
   * values above are never replaced.
   */
  revenue_growth_computed?: BriefDerivedValue;
  earnings_growth_computed?: BriefDerivedValue;
  /** Cross-source disagreements — flagged, never silently resolved. */
  conflicts?: BriefMetricConflict[];
}

/**
 * The execution record of the research run that produced a brief (R10, D38).
 * Stamped at the tool boundary from the loop that ACTUALLY RAN — the brief's
 * mode/depth badges derive from this and only this, never from request or UI
 * state. Wire shape from the sidecar is snake_case; `briefFromInput` maps it.
 */
export interface BriefExecution {
  /** Unique id of the research run (minted when the tool dispatched). */
  runId: string;
  /** The depth requested after the slider-floor/model-escalation merge. */
  requestedDepth: "normal" | "deep" | "ultra";
  /** The loop that actually executed. */
  loop: "fast" | "iter" | "heavy" | "research-model";
  /** The retrieval backend the run rode (mirrors `ResearchBriefData.backend`). */
  backend?: string | null;
  /** Epoch ms the run started/finished, when metered. */
  startedAt?: number;
  finishedAt?: number;
  /** Why the run executed below the requested depth, when it did — never silent. */
  degradedReason?: string | null;
}

/** One instrument candidate in an honest disambiguation (R10, D37). */
export interface BriefCandidate {
  symbol: string;
  name: string;
  exchange?: string | null;
  /** Resolver confidence in [0,1]. */
  score?: number;
  /** The quote-routable form (e.g. "RELIANCE.NS") for one-click re-research. */
  yahooSymbol?: string;
}

/**
 * An explicit "which did you mean?" — rendered INSTEAD of a guessed brief when
 * resolution lands between the reject and accept thresholds. Never co-exists
 * with a researched body for the same run.
 */
export interface BriefDisambiguation {
  query: string;
  candidates: BriefCandidate[];
}

/**
 * The category of a cited source, used for the quiet source-type badge in the
 * sources rail (news / research / filing / web). The pipeline may emit it
 * directly; when absent the panel derives it from the source's domain.
 */
export type BriefSourceType = "news" | "research" | "filing" | "web";

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
  /**
   * The source's category (news / research / filing / web), shown as a small
   * quiet badge in the sources rail. Optional — when absent the panel derives
   * it client-side from {@link domain}/{@link url} (SEC → filing, known news
   * domains → news, etc.).
   */
  sourceType?: BriefSourceType;
}

/**
 * The kind of a single step in the research pipeline's trace. `distill`
 * (IterResearch central-report rewrite) and `engine` (the honest backend /
 * fallback line) are emitted by the sidecar and rendered by ResearchActivity.
 */
export type BriefStepKind =
  | "plan"
  | "tool"
  | "search"
  | "compress"
  | "distill"
  | "reflect"
  | "synthesize"
  | "engine";

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

/** The two research depths the pipeline renders in the mode badge. */
export type BriefMode = "FAST" | "DEEP";

/**
 * The true depth TIER a brief was produced at (FR-115). The ONE research model
 * escalates in place across these three internal tiers; the brief carries the
 * tier it reached so the panel's "Go deeper" affordance knows the NEXT tier (and
 * hides itself at `heavy`). `quick` ≙ FAST mode; `deep`/`heavy` ≙ DEEP mode.
 * Optional — older briefs omit it and the panel derives the tier from `mode`.
 */
export type BriefDepth = "quick" | "deep" | "heavy";

/**
 * A complete research brief — the payload the BriefPanel renders and the
 * workspace blob persists (`SerializedWorkspace.brief`).
 */
export interface ResearchBriefData {
  /** The natural-language research question the brief answers. */
  query: string;
  /** The primary ticker the brief is about, when the query resolved to one. */
  symbol?: string;
  /** The depth the pipeline ran in (the mode badge: FAST | DEEP). */
  mode: BriefMode;
  /**
   * The true depth tier reached (`quick` | `deep` | `heavy`). Drives the in-place
   * "Go deeper" escalation (FR-115). Optional — derived from `mode` when absent.
   */
  depth?: BriefDepth;
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
   * (NOT an error, NOT an empty state). Reconciled with {@link sourceCount}: a
   * brief that cited sources is never marked web-unavailable.
   */
  webAvailable: boolean;
  /**
   * Why the web round did not answer, when it didn't (`webAvailable === false`):
   * `"rate_limited"` ⇒ a TRANSIENT throttle (the backend exists — the banner says
   * "rate-limited, retrying"), anything else / absent ⇒ a genuine no-backend miss
   * (the banner stays "structured data only"). NEVER a "no backend" claim for a
   * transient throttle. Optional — older briefs omit it.
   */
  webReason?: string;
  /**
   * A free-form honest note from the pipeline (e.g. why web search was skipped).
   * Surfaced prominently when {@link webAvailable} is `false`.
   */
  note?: string;
  /**
   * The retrieval backend that served this brief's web round (R9 two-tier
   * model, Team A): `"searxng"`, `"keyless-fallback"`, or
   * `"research-model:<model-id>"`. `keyless-fallback` — SearXNG not ready, the
   * run silently fell back to the keyless engines — drives the brief panel's
   * honest "limited keyless search" nudge banner; it never renders for the
   * searxng / research-model backends. Optional — older briefs omit it.
   */
  backend?: string;
  /** The dev-only research step trace, when the pipeline emitted one. */
  steps?: BriefStep[];
  /**
   * The provenance-tagged structured bundle (price/fundamentals/news/filings)
   * the pipeline gathered, used to render native metric cards. Optional — older
   * briefs and structured-only runs may omit it; an absent leg renders nothing
   * (never fabricated).
   */
  structured?: BriefStructured;
  /**
   * The execution record of the run that produced this brief (R10, D38). The
   * mode/depth badges derive from `execution.loop` when present; structured
   * carry-over between publishes requires a matching `execution.runId`.
   * Optional — pre-R10 briefs omit it and render as archival.
   */
  execution?: BriefExecution;
  /**
   * Set when resolution needed an explicit human choice (R10, D37) — the panel
   * renders the candidate chooser instead of a brief body. Mutually exclusive
   * with a researched `markdown`.
   */
  disambiguation?: BriefDisambiguation;
  /** Epoch milliseconds the brief was produced. */
  createdAt: number;
}
