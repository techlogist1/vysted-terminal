/**
 * Vysted Terminal — sidecar data-layer types.
 *
 * Hand-maintained TypeScript mirror of the Pydantic models in `sidecar/models/`.
 * When a Pydantic model changes, update the matching interface here in the same
 * commit (see CLAUDE.md Gotchas). Datetimes cross the wire as ISO-8601 strings.
 */

// --- market ---------------------------------------------------------------

/** Calendar-aware staleness label for a served market value (FR-041 / SC-019). */
/** `unknown` = the label could not be computed — still badged, never read as live. */
export type Freshness = "live" | "eod" | "stale" | "unknown";

/** A point-in-time price quote for one instrument. */
export interface Quote {
  symbol: string;
  price: number;
  /** `null` when the lane does not know the day's change — never a fabricated 0. */
  change: number | null;
  change_percent: number | null;
  volume: number | null;
  /** The session's open/high/low and the prior close, where the lane reports them. */
  open?: number | null;
  high?: number | null;
  low?: number | null;
  prev_close?: number | null;
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
 * (WS6 Step 4); absent for a populated series.
 * in_eod_only = BSE/NSE serve end-of-day data only; no intraday/realtime lane exists for this listing
 * unknown_symbol = no bundled equity/ETF master knows the symbol at all (R15-LEAD-026)
 */
export type SeriesReason = "in_eod_only" | "unknown_symbol";

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
  /** True when part of the requested range is missing; complete from `coverage_start` (ISO date). */
  partial?: boolean;
  coverage_start?: string | null;
}

/** One dated observation within a macro series. */
export interface MacroObservation {
  date: string;
  value: number | null;
  /** A forecast, not an outturn (e.g. an IMF WEO year at or after the vintage). */
  is_projection?: boolean;
}

/** An economic/macro time series (FRED-style). */
export interface MacroSeries {
  series_id: string;
  title: string;
  units: string | null;
  observations: MacroObservation[];
  provider: string;
}

/** One listed option contract's end-of-day row in an option chain (R15-DATA-079). */
export interface OptionContract {
  /** ISO date. */
  expiry: string;
  strike: number;
  option_type: "call" | "put";
  /** Exchange-published open interest and its change on the session. */
  open_interest: number | null;
  change_in_oi: number | null;
  last_price: number | null;
  /** Exchange settlement price (NSE F&O); null on the US leg. */
  settle_price: number | null;
  volume: number | null;
  /** The source's implied volatility (US leg); null on the NSE leg. */
  implied_volatility: number | null;
}

/** One expiry of a symbol's listed option chain: EOD research data dated by `as_of`. */
export interface OptionChain {
  symbol: string;
  /** The served expiry (ISO date). */
  expiry: string;
  /** Every listed expiry, nearest first (ISO dates). */
  expiries: string[];
  underlying_price: number | null;
  contracts: OptionContract[];
  /** The session the values describe (ISO date). */
  as_of: string;
  provider: string;
  currency: string;
  freshness: Freshness | null;
}

// --- fundamentals ---------------------------------------------------------

/**
 * Snapshot of valuation, profitability, health, and profile for one symbol.
 * Mirrors `sidecar/models/fundamentals.py` — keep in sync. Fraction fields
 * (`*_margin`, `roe`, `roa`, `*_growth`, `held_percent_*`, `fifty_two_week_change`,
 * `dividend_yield`) are 0.21 = 21%; `debt_to_equity` is a ratio (1.5 = 150%).
 * `currency` is the TRADING currency (prices, `market_cap`, `book_value`, `eps`,
 * `dividend_per_share`); the statement sizes (`revenue_ttm`/`net_income_ttm`/
 * `free_cash_flow`) are in `financial_currency ?? currency`.
 */
export interface Fundamentals {
  symbol: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  /**
   * Which source served `sector`/`industry` (R15-DATA-052): `"resolver"` when
   * the bundled India sector map overrode an absent/empty Yahoo value (a bare
   * Yahoo `""` never counts as served), `"yfinance"` when Yahoo's own value
   * was used, `null` when neither had one.
   */
  sector_source?: string | null;
  currency: string | null;
  /**
   * Currency of the statement sizes (`revenue_ttm`/`net_income_ttm`/
   * `free_cash_flow`) when it differs from the trading `currency` (Yahoo
   * `financialCurrency`, e.g. an INR-reporting USD ADR). `null`/absent when equal.
   * No FX conversion — format those sizes in `financial_currency ?? currency`.
   */
  financial_currency?: string | null;
  /**
   * The price the provider's ratios and `market_cap` were computed at (same
   * snapshot); its `field_meta` `as_of` is that price's trade time.
   */
  ratio_price?: number | null;
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
  /** ISO date the 52-week high/low each actually traded at (R15-DATA-055). */
  fifty_two_week_high_date?: string | null;
  fifty_two_week_low_date?: string | null;
  /**
   * ISO exchange listing date (R15-DATA-055): the NSE master's DATE OF LISTING
   * for an NSE listing, else `null`. A listing younger than 52 weeks still
   * reports a `fifty_two_week_*` pair (Yahoo backfills from the shorter
   * history it has) — the panel labels that range "since listing" instead of
   * "52w" and hides the "1Y change".
   */
  listing_date?: string | null;
  /** ISO date of the first bar Yahoo holds — the start of its data, not the listing. */
  first_trade_date?: string | null;
  /**
   * ISO date of the fiscal year end `forward_pe` targets (Yahoo
   * `nextFiscalYearEnd`). `null`/absent when Yahoo names no forward estimate
   * or fiscal-year-end date for it.
   */
  forward_pe_fiscal_year?: string | null;
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
  /**
   * Return on capital employed — EBIT / (total assets - current liabilities),
   * a fraction. Yahoo's `info` carries no ROCE field at all, so this is
   * ALWAYS derived from the statements when they carry the ingredients
   * (R15-DATA-048); `null` when they don't.
   */
  roce?: number | null;
  /**
   * Accounting basis the company files its results on (R15-DATA-054), derived
   * from the exchange filings: `"consolidated"` when it files a consolidated
   * result, else `"standalone"`. `null` for a non-Indian listing or when no
   * filing could be read — never a default.
   */
  basis?: "consolidated" | "standalone" | null;
  // Size & growth
  revenue_ttm: number | null;
  net_income_ttm: number | null;
  free_cash_flow: number | null;
  shares_outstanding: number | null;
  revenue_growth: number | null;
  earnings_growth: number | null;
  /**
   * Basis of the growth fields above (R11 / D55): "mrq_yoy" (MOST-RECENT-QUARTER
   * vs the same quarter a year ago — yfinance's growth figures, the exchange-filed
   * overlay) or "annual_yoy". Stated by the producer of a growth value; `null`
   * means no basis was stated, never an inherited default (R15-DATA-102). Every
   * surface rendering growth must disclose this.
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
 *   (`as_of` records when).
 * - `status: "flagged"` — the value is kept but a cross-check disagrees; `reason`
 *   names the disagreement and the witness figure. Never a substitution.
 * - `status: "withheld"` — a value existed but the correctness gate nulled it as
 *   implausible; `reason` says why and the field on the payload is `null`.
 * - `status: "unavailable"` — the source carried no value.
 */
export interface FieldMeta {
  status: "ok" | "flagged" | "withheld" | "unavailable";
  provider?: string | null;
  as_of?: string | null;
  reason?: string | null;
  label?: string | null;
  /**
   * Set alongside `provider === "derived"` (R15-DATA-048/054/055): the
   * formula the value was computed with, e.g. "EBIT / (total assets -
   * current liabilities)".
   */
  basis_note?: string | null;
}

/** One labelled row of a financial statement, keyed by period label. */
export interface StatementLine {
  label: string;
  values: Record<string, number | null>;
}

/** Shared shape for the three financial statements. */
export interface FinancialStatement {
  symbol: string;
  /** ISO period-end dates, newest first (annual and quarterly alike). */
  periods: string[];
  lines: StatementLine[];
  provider: string;
  /** Expected periods the provider did not serve: listed in `periods`, null in every line. */
  gaps?: string[];
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
  /** FR-124 "The Take": 2-4 sentence headline, unverified numbers redacted; null when none. */
  summary: string | null;
  /** Legacy key-insight bullets (an older completion), verified the same way. */
  insights: string[];
  /** FR-124 business: what the company does and how it earns. */
  business: string | null;
  /** FR-124 storyline: the trajectory the served numbers show. */
  storyline: string | null;
  /** FR-124 balanced bull points. */
  bull_case: string[];
  /** FR-124 balanced bear points. */
  bear_case: string[];
  /** FR-124 key risks. */
  risks: string[];
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
  /** When this envelope was fetched upstream (a cache hit keeps the fetch time). */
  as_of?: string | null;
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
  /** The source's publication time; `null` when the feed carried no parseable date. */
  published_at: string | null;
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

/**
 * Whether a disclosure feed covers the instrument: "venue_not_covered" is an
 * Indian listing on a venue with no such feed, "not_applicable" a non-NSE/BSE
 * instrument. Out-of-coverage is answered (200, empty list + `note`), never a 502.
 */
export type DisclosureCoverage = "covered" | "venue_not_covered" | "not_applicable";

/** The date range one exchange lane's items in a response are complete for. */
export interface AnnouncementWindow {
  /** Oldest IST day covered (ISO date); null when nothing older was cut (full history). */
  window_start: string | null;
  /** Newest IST day covered (ISO date, the day of the fetch). */
  window_end: string;
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
  /** Per serving exchange, the date range its items are complete for. */
  windows: Record<string, AnnouncementWindow>;
  coverage: DisclosureCoverage;
  /** Why nothing is served when `coverage` is not "covered". */
  note: string | null;
}

/** One results-calendar / board-meeting event (NSE event calendar, BSE board meetings). */
export interface ResultsEvent {
  symbol: string;
  company: string | null;
  /** Event purpose, e.g. "Financial Results", "Dividend", "Demerger". */
  purpose: string;
  /** The board-meeting description text accompanying the event. */
  description: string | null;
  /** Meeting/event date (ISO date); null when the feed row had none. */
  date: string | null;
  /** "NSE", "BSE", or "NSE+BSE" when a dual listing's feeds carry one meeting. */
  exchange: string | null;
}

/** `GET /disclosures/results` — results/board-meeting events, newest first. */
export interface ResultsCalendarResponse {
  symbol: string;
  count: number;
  events: ResultsEvent[];
  /** Exchanges that served this response. */
  sources: string[];
  /** Exchanges attempted but failed, with the reason (partial merge served). */
  errors: Record<string, string>;
  coverage: DisclosureCoverage;
  note: string | null;
}

/**
 * One quarterly shareholding-pattern row. Percentages are 0-100 as published.
 * `fii_percent`/`dii_percent` are null on the NSE master lane (which does not
 * carry the split); for a dual-listed name they are MERGED in from the BSE SEBI
 * XBRL (`split_source`/`split_as_of` record the provenance). Never fabricated.
 */
export interface ShareholdingPattern {
  symbol: string;
  /**
   * The quarter-end date this pattern reports (ISO date, e.g. "2026-03-31").
   * BSE dates a listing-time (IPO) pattern to the day ("2026-06-04").
   */
  quarter_end: string;
  /**
   * What `quarter_end` is when it is NOT the filed period (the filing date of a
   * pattern whose exchange period label could not be parsed); null otherwise.
   */
  quarter_basis: string | null;
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
  /**
   * How the FII/DII legs were obtained: "filed" (read from the filing) or
   * "derived" (a leg the filing omits = the filed institutions total minus the
   * other leg, or 0 from a 0 total). Null when no leg is known.
   */
  split_basis: "filed" | "derived" | null;
  /**
   * Promoter + promoter-group shares pledged or otherwise encumbered, percent of
   * the promoter holding (SEBI SHP XBRL). 0 when the filing declares none; null
   * when the filing declares nothing (never inferred as 0).
   */
  promoter_pledged_percent: number | null;
  /** "filed" when the filing states the pledge (including an explicit 0); else null. */
  promoter_pledge_basis: "filed" | null;
}

/**
 * One bulk deal, block deal or SAST (SEBI Reg 29) disclosure of an Indian
 * listing. Fields a feed does not carry are null (bulk/block carry no holding
 * after; SAST carries no price).
 */
export interface ExchangeDeal {
  symbol: string;
  kind: "bulk" | "block" | "sast";
  /** ISO date: the deal date, or the SAST acquisition/sale date. */
  date: string | null;
  party: string | null;
  side: "buy" | "sell" | null;
  quantity: number | null;
  /** Weighted average trade price (bulk/block). */
  price: number | null;
  /** quantity x price (bulk/block). */
  value: number | null;
  /** The party's holding after the transaction, percent of shares (SAST). */
  percent_after: number | null;
  exchange: string;
  /** The filed disclosure (SAST attachment). */
  source_url: string | null;
}

/** `GET /disclosures/deals` — bulk/block deals and SAST, newest first. */
export interface ExchangeDealsResponse {
  symbol: string;
  /** The kind filter applied, or null for every kind. */
  kind: string | null;
  count: number;
  deals: ExchangeDeal[];
  /** Lanes that served ("NSE bulk", "NSE sast", "BSE block", ...). */
  sources: string[];
  /** Lanes attempted but failed, with the reason (partial result served). */
  errors: Record<string, string>;
  coverage: DisclosureCoverage;
  note: string | null;
}

/**
 * One corporate action of an Indian listing: a dividend, bonus, split, rights
 * issue or buyback. `purpose` is the exchange's verbatim line; `ratio` and
 * `amount_per_share` are parsed from it (null when absent). `exchange` is
 * "NSE", "BSE" or "NSE+BSE" when both feeds carry the action.
 */
export interface CorporateAction {
  symbol: string;
  kind: "dividend" | "bonus" | "split" | "rights" | "buyback" | "other";
  purpose: string;
  /** e.g. "7:24" for a bonus or rights issue. */
  ratio: string | null;
  amount_per_share: number | null;
  /** ISO dates; null when the feed carried none. */
  ex_date: string | null;
  record_date: string | null;
  payment_date: string | null;
  exchange: string;
}

/** `GET /disclosures/corporate-actions` — NSE+BSE actions, newest ex-date first. */
export interface CorporateActionsResponse {
  symbol: string;
  count: number;
  actions: CorporateAction[];
  /** Exchanges that served this response. */
  sources: string[];
  /** Exchanges attempted but failed, with the reason (partial merge served). */
  errors: Record<string, string>;
  coverage: DisclosureCoverage;
  note: string | null;
}

/** One 5%-or-more holder from a foreign issuer's 20-F (Item 7.A). */
export interface MajorShareholder {
  holder: string;
  /** Percent of the class (0-100), newest column; null when the filing shows a dash. */
  percent: number | null;
  /** ISO date the filing states the holdings as of. */
  as_of: string | null;
}

/**
 * `GET /disclosures/shareholding` — quarterly patterns, newest first. A US-listed
 * ADR's major holders ride `major_shareholders` from its latest 20-F
 * (`provider` "sec-20f"), never merged into `patterns`.
 */
export interface ShareholdingResponse {
  symbol: string;
  count: number;
  patterns: ShareholdingPattern[];
  coverage: DisclosureCoverage;
  note: string | null;
  provider: string | null;
  major_shareholders: MajorShareholder[];
  source_url: string | null;
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
