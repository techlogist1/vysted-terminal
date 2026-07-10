/**
 * Vysted Terminal — sidecar data-layer types.
 *
 * Hand-maintained TypeScript mirror of the Pydantic models in `sidecar/models/`.
 * When a Pydantic model changes, update the matching interface here in the same
 * commit (see CLAUDE.md Gotchas). Datetimes cross the wire as ISO-8601 strings.
 */

// --- market ---------------------------------------------------------------

/** Calendar-aware staleness label for a served market value (FR-041 / SC-019). */
export type Freshness = "live" | "eod" | "stale";

/** A point-in-time price quote for one instrument. */
export interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number | null;
  currency: string;
  market_state: string | null;
  timestamp: string;
  provider: string;
  /** Set by the quotes router so the UI never shows a stale value as live. */
  freshness?: Freshness | null;
}

/** A single open/high/low/close/volume bar. */
export interface OHLCVBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * Typed reason for an EMPTY series (no bars). Set by the history router when
 * every provider returned no data so the chart can show a region-aware message
 * (WS6 Step 4). `in_eod_only` = an IN symbol where BSE/NSE serve EOD only and
 * intraday/realtime needs a BYOK broker; absent for a populated series.
 */
export type SeriesReason = "in_eod_only";

/** An ordered series of OHLCV bars for one symbol and timeframe. */
export interface OHLCVSeries {
  symbol: string;
  timeframe: string;
  bars: OHLCVBar[];
  provider: string;
  /** Staleness of the LAST bar, set by the history router (FR-041 / SC-019). */
  freshness?: Freshness | null;
  /** Typed reason for an empty series, set by the history router (WS6 Step 4). */
  reason?: SeriesReason | null;
}

/** One dated observation within a macro series. */
export interface MacroObservation {
  date: string;
  value: number | null;
}

/** An economic/macro time series (FRED-style). */
export interface MacroSeries {
  series_id: string;
  title: string;
  units: string | null;
  observations: MacroObservation[];
  provider: string;
}

// --- fundamentals ---------------------------------------------------------

/**
 * Snapshot of valuation, profitability, health, and profile for one symbol.
 * Mirrors `sidecar/models/fundamentals.py` — keep in sync. Fraction fields
 * (`*_margin`, `roe`, `roa`, `*_growth`, `held_percent_*`, `fifty_two_week_change`,
 * `dividend_yield`) are 0.21 = 21%; `debt_to_equity` is a ratio (1.5 = 150%);
 * currency sizes (`revenue_ttm`/`net_income_ttm`/`free_cash_flow`/
 * `dividend_per_share`) are in `currency`.
 */
export interface Fundamentals {
  symbol: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  currency: string | null;
  // Valuation
  market_cap: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  peg_ratio: number | null;
  price_to_book: number | null;
  price_to_sales: number | null;
  ev_to_ebitda: number | null;
  book_value: number | null;
  dividend_yield: number | null;
  dividend_per_share: number | null;
  eps: number | null;
  beta: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  fifty_two_week_change: number | null;
  // Profitability (fractions)
  roe: number | null;
  roa: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  profit_margin: number | null;
  // Financial health
  debt_to_equity: number | null;
  current_ratio: number | null;
  quick_ratio: number | null;
  // Size & growth
  revenue_ttm: number | null;
  net_income_ttm: number | null;
  free_cash_flow: number | null;
  shares_outstanding: number | null;
  revenue_growth: number | null;
  earnings_growth: number | null;
  /**
   * Basis of the growth fields above (R11 / D55). yfinance's growth figures
   * are MOST-RECENT-QUARTER vs the same quarter a year ago ("mrq_yoy") — NOT
   * annual/TTM growth. Every surface rendering growth must disclose this.
   */
  growth_basis?: string | null;
  // Ownership (fractions)
  held_percent_insiders: number | null;
  held_percent_institutions: number | null;
  /**
   * Trailing-12-month dividends ACTUALLY PAID per share (summed corporate-action
   * history, in `currency`) — the deterministic cross-check for
   * `dividend_per_share` (R11 / D56). `null` when history was unavailable.
   */
  dividend_per_share_ttm?: number | null;
  /**
   * MRQ-YoY growth deterministically COMPUTED from the provider's own
   * QUARTERLY income statements (R12 / D66) — the cross-check for the opaque
   * `revenue_growth`/`earnings_growth` scalars. Populated only on the research
   * snapshot path; `null`/absent when quarterly statements were unavailable.
   * These NEVER replace the provider values — a divergence surfaces as a
   * conflict, not a substitution.
   */
  revenue_growth_computed?: number | null;
  earnings_growth_computed?: number | null;
  /** The quarter-end pair (ISO dates) the computed growth compared. */
  growth_computed_quarters?: { mrq: string; prior: string } | null;
  /**
   * Per-field provenance / coverage metadata (R13), keyed by data-field name.
   * Additive — absent on providers that do not populate it, and an absent map
   * never changes how the value fields above are read.
   */
  field_meta?: Record<string, FieldMeta> | null;
  provider: string;
  /**
   * R13 ledger #8 (bounded, additive): a plain-language note when the
   * resolver's canonical master name and THIS provider's company name
   * disagree past the identity cross-check threshold (mirrors
   * `sidecar/services/identity_crosscheck.py`) — e.g. an exchange rename the
   * bundled provider has not caught up with yet. `null`/absent when the names
   * agree or the symbol did not resolve. Never a swap — `name` above always
   * stays the provider's own value; this is a disclosure only.
   */
  identity_note?: string | null;
}

/**
 * Per-field provenance / coverage metadata riding a `Fundamentals` payload (R13).
 *
 * - `status: "ok"` — the field carries a real value the named `provider` served
 *   (`as_of` records when). A `reason` may still be present as a soft flag.
 * - `status: "withheld"` — a value existed but the correctness gate nulled it as
 *   implausible; `reason` says why and the field on the payload is `null`.
 * - `status: "unavailable"` — the source carried no value.
 */
export interface FieldMeta {
  status: "ok" | "withheld" | "unavailable";
  provider?: string | null;
  as_of?: string | null;
  reason?: string | null;
  label?: string | null;
}

/** One labelled row of a financial statement, keyed by period label. */
export interface StatementLine {
  label: string;
  values: Record<string, number | null>;
}

/** Shared shape for the three financial statements. */
export interface FinancialStatement {
  symbol: string;
  periods: string[];
  lines: StatementLine[];
  provider: string;
}

/** Income statement excerpt. */
export type IncomeStatement = FinancialStatement;
/** Balance sheet excerpt. */
export type BalanceSheet = FinancialStatement;
/** Cash-flow statement excerpt. */
export type CashFlowStatement = FinancialStatement;

/**
 * One numeric figure in the AI narrative that did NOT match the source data.
 * Mirrors `sidecar/models/fundamentals.UnverifiedClaim`. The narrative service
 * redacts these from the prose so a hallucinated figure never renders as fact.
 */
export interface UnverifiedClaim {
  /** The literal numeric token as the model wrote it (e.g. `"$4.2T"`). */
  text: string;
  /** Why it failed verification. */
  reason: string;
}

/**
 * An LLM-written, numerically-verified company overview for one symbol. Mirrors
 * `sidecar/models/fundamentals.CompanyNarrative` — keep in sync. Every number in
 * `summary`/`insights` has been checked against the real fundamentals + quote;
 * unverified figures are redacted from the prose and listed in
 * `unverified_claims`. When no model/key/data is available the route still
 * returns 200 with `summary === null` + a `reason` for a quiet empty state.
 */
export interface CompanyNarrative {
  symbol: string;
  /** 2-4 sentence narrative with unverified numbers redacted; null when none. */
  summary: string | null;
  /** 2-4 short key-insight bullets, verified the same way as `summary`. */
  insights: string[];
  /** True when a narrative ran AND every numeric claim matched a source value. */
  verified: boolean;
  /** Numeric claims that failed verification and were redacted from the prose. */
  unverified_claims: UnverifiedClaim[];
  /** The data provider the narrative is grounded in (the "verified against" label). */
  source_provider: string | null;
  /** The LLM model id that wrote the narrative, when one ran. */
  model: string | null;
  /** ISO-8601 UTC timestamp of generation, or null when no narrative ran. */
  generated_at: string | null;
  /** Human-readable explanation when `summary` is null (no key, no output, …). */
  reason: string | null;
}

/** Aggregated analyst ratings and price targets for one symbol. */
export interface AnalystRating {
  symbol: string;
  consensus: string | null;
  target_mean: number | null;
  target_high: number | null;
  target_low: number | null;
  strong_buy: number;
  buy: number;
  hold: number;
  sell: number;
  strong_sell: number;
  provider: string;
}

// --- news -----------------------------------------------------------------

/**
 * A single news article. The `sentiment` / `sentiment_label` fields are
 * populated by the news service (Teammate C); the Phase 1.A provider layer
 * leaves them `null`.
 */
export interface NewsItem {
  id: string;
  title: string;
  summary: string | null;
  url: string;
  source: string;
  published_at: string;
  symbols: string[];
  sentiment: number | null;
  sentiment_label: string | null;
  provider: string;
}

// --- corporate disclosures (India) ------------------------------------------
// Mirror of sidecar/models/announcements.py — the NSE+BSE disclosure feeds.

/** One corporate announcement from an Indian exchange feed. */
export interface Announcement {
  symbol: string;
  /** The exchange that disseminated this item: "NSE" | "BSE". */
  exchange: string;
  headline: string;
  /** Exchange category label (e.g. "Updates", "Company Update"). */
  category: string | null;
  /** Direct URL of the filed attachment (usually a PDF). */
  attachment_url: string | null;
  /** Dissemination timestamp (ISO-8601, IST-aware); null when unparseable. */
  ts: string | null;
}

/** `GET /disclosures/announcements` — the merged, deduped feed. */
export interface AnnouncementsResponse {
  symbol: string;
  /** The single-exchange filter applied, or null for the merged NSE+BSE feed. */
  exchange: string | null;
  count: number;
  announcements: Announcement[];
  /** Exchanges that actually served this response (e.g. ["NSE","BSE"]). */
  sources: string[];
  /** Exchanges attempted but failed, with the honest reason (partial merge). */
  errors: Record<string, string>;
}

/** One results-calendar / board-meeting event (NSE event-calendar feed). */
export interface ResultsEvent {
  symbol: string;
  company: string | null;
  /** Event purpose, e.g. "Financial Results", "Dividend", "Demerger". */
  purpose: string;
  /** The board-meeting description text accompanying the event. */
  description: string | null;
  /** Meeting/event date (ISO date); null when the feed row had none. */
  date: string | null;
}

/** `GET /disclosures/results` — results/board-meeting events, newest first. */
export interface ResultsCalendarResponse {
  symbol: string;
  count: number;
  events: ResultsEvent[];
}

/**
 * One quarterly shareholding-pattern row. Percentages are 0-100 as published.
 * `fii_percent`/`dii_percent` are null on the NSE master lane (which does not
 * carry the split); for a dual-listed name they are MERGED in from the BSE SEBI
 * XBRL (`split_source`/`split_as_of` record the provenance). Never fabricated.
 */
export interface ShareholdingPattern {
  symbol: string;
  /** The quarter-end date this pattern reports (ISO date, e.g. "2026-03-31"). */
  quarter_end: string;
  /** Promoter + promoter-group holding, percent of equity. */
  promoter_percent: number | null;
  fii_percent: number | null;
  dii_percent: number | null;
  /**
   * Total institutional holding (FII + DII), percent of equity. Null on the
   * NSE master lane alone; populated from the SEBI XBRL (BSE lane, or merged onto
   * a dual-listed NSE pattern). Never fabricated.
   */
  institutions_percent: number | null;
  /**
   * The PUBLIC bucket, percent of equity — INCLUDES institutions on both lanes
   * (the exchange "Public" category), so a large-FII name overstates its true
   * public float here. See `public_basis` and `public_non_institutional_percent`.
   */
  public_percent: number | null;
  /** What `public_percent` counts — "incl. institutions" (the only exchange basis). */
  public_basis: string | null;
  /**
   * The non-institutional public float (SEBI NonInstitutionsMember) — the "true
   * public" carved out of `public_percent`. From the BSE SEBI XBRL only; else null.
   */
  public_non_institutional_percent: number | null;
  employee_trusts_percent: number | null;
  /** Date the pattern was filed with the exchange (ISO date). */
  submission_date: string | null;
  /** The XBRL filing URL carrying the full category-level split. */
  xbrl_url: string | null;
  /** Exchange lane that served this pattern — "NSE" or "BSE". */
  source: string | null;
  /**
   * The lane that supplied the FII/DII/institutions split when MERGED from a
   * different lane than `source` — "BSE" on a dual-listed NSE pattern enriched
   * from the SEBI XBRL; null when the split (if any) is native to `source`.
   */
  split_source: string | null;
  /**
   * The quarter-end the merged split came from (ISO date). Equals `quarter_end`
   * on an exact-quarter merge; differs when the nearest BSE quarter supplied it.
   */
  split_as_of: string | null;
}

/** `GET /disclosures/shareholding` — quarterly patterns, newest first. */
export interface ShareholdingResponse {
  symbol: string;
  count: number;
  patterns: ShareholdingPattern[];
}

// --- portfolio ------------------------------------------------------------

/** A single held position, persisted in the local SQLite database. */
export interface Position {
  id: number | null;
  symbol: string;
  quantity: number;
  cost_basis: number;
  asset_class: string;
  opened_at: string | null;
  note: string | null;
}

/** Payload for creating or updating a position (no server-assigned id). */
export interface PositionInput {
  symbol: string;
  quantity: number;
  cost_basis: number;
  asset_class: string;
  opened_at: string | null;
  note: string | null;
}

// --- indicators -----------------------------------------------------------
// Mirror of sidecar/models/indicators.py — the chart panel's overlay contract.

/** Which chart pane an indicator renders on. */
export type IndicatorPanel = "price" | "separate";

/**
 * A single `(time, value)` sample on an indicator line. `time` is an ISO-8601
 * timestamp mirrored from the source OHLCV bar; a `null` value marks a gap
 * where the indicator is undefined (e.g. a moving average's warm-up window).
 */
export interface IndicatorPoint {
  time: string;
  value: number | null;
}

/** One named line within an indicator (an indicator may plot several). */
export interface IndicatorLine {
  label: string;
  points: IndicatorPoint[];
}

/** The full result of computing one indicator over an OHLCV series. */
export interface IndicatorSeries {
  name: string;
  panel: IndicatorPanel;
  lines: IndicatorLine[];
}

/**
 * One price-bucket of a Volume Profile histogram — `price` is the bucket
 * centre and `volume` is the total traded volume that closed inside it.
 */
export interface VolumeProfileBucket {
  price: number;
  volume: number;
}

/**
 * A horizontal-histogram Volume Profile. Lives on its own contract because
 * its axes are price-keyed rather than time-keyed; the chart panel renders
 * it on the price pane via a custom series primitive.
 */
export interface VolumeProfile {
  buckets: VolumeProfileBucket[];
}

/** The `/indicators/{symbol}` payload — every requested indicator. */
export interface IndicatorResponse {
  symbol: string;
  timeframe: string;
  provider: string;
  indicators: IndicatorSeries[];
  volume_profile: VolumeProfile | null;
}
