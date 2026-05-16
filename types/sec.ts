/**
 * Vysted Terminal — SEC EDGAR filing contracts (Phase 6).
 *
 * Hand-maintained TypeScript mirror of ``sidecar/models/sec.py``. When a
 * Pydantic model changes, update the matching interface here in the same
 * commit (see CLAUDE.md Gotchas).
 *
 * **Numeric precision callout.** sec-edgar-mcp's design philosophy preserves
 * the exact numeric precision as filed with the SEC (no rounding). Large
 * filings emit values whose magnitude exceeds JavaScript's
 * ``Number.MAX_SAFE_INTEGER`` (e.g. AAPL's total assets in cents). Those
 * fields are typed as ``string`` on the wire and parsed lazily by the UI
 * via ``BigInt`` or string-display when precision matters.
 */

// ---------------------------------------------------------------------------
// Filing identity
// ---------------------------------------------------------------------------

/** The form types Vysted's filings reader surfaces in v0.6.0. */
export type FilingFormType = "10-K" | "10-Q" | "8-K" | "DEF 14A" | "3" | "4" | "5";

/**
 * Top-level filing metadata — the row a user sees in the filings list. The
 * filing's full content lives behind ``GET /sec/filings/{accession}``.
 */
export interface Filing {
  /** SEC accession number, e.g. ``"0000320193-24-000123"``. */
  accession: string;
  /** Filer CIK (Central Index Key), zero-padded to 10 digits. */
  cik: string;
  /** Company name as the SEC filing carries it. */
  company_name: string;
  /** Primary ticker, where the filing exposes one (10-K/10-Q/8-K do). */
  symbol: string | null;
  /** Form type — e.g. ``"10-K"``, ``"4"``. */
  form_type: FilingFormType;
  /** ISO-8601 date the filing was accepted by EDGAR. */
  filed_date: string;
  /** ISO-8601 date the filing's reporting period closes (e.g. fiscal-year end). */
  period_of_report: string | null;
  /** Canonical EDGAR URL for the filing landing page. */
  edgar_url: string;
}

// ---------------------------------------------------------------------------
// Filing content
// ---------------------------------------------------------------------------

/**
 * One section of a parsed filing. 10-K / 10-Q split into Item 1 / 1A / 2,
 * etc.; 8-K splits into the numbered Items the filing reports. The
 * FilingViewer panel renders each section as a collapsible block.
 */
export interface FilingSection {
  /** Stable id assigned by sec-edgar-mcp's section parser. */
  id: string;
  /** Section title as printed in the filing — e.g. ``"Item 1A. Risk Factors"``. */
  title: string;
  /** Plain-text body. HTML tags + tables are stripped for the v0.6.0 viewer;
   * the link-out to EDGAR is the path to the formatted original. */
  text: string;
  /** Word count for the section — surfaced in the section index. */
  word_count: number;
}

/** Filing detail payload — what the FilingViewer panel renders. */
export interface FilingDetail {
  filing: Filing;
  sections: FilingSection[];
  /** Raw filing text length in characters (sum across sections). */
  total_chars: number;
}

// ---------------------------------------------------------------------------
// XBRL-precise financial facts
// ---------------------------------------------------------------------------

/**
 * One XBRL-precise financial fact pulled from a filing. Values are kept as
 * strings to preserve precision; the UI parses to ``BigInt`` only when it
 * needs to compute on them.
 */
export interface XbrlFact {
  concept: string;
  value: string;
  units: string;
  /** Period end (ISO-8601). */
  period_end: string;
  /** Period start (ISO-8601) for duration facts; ``null`` for point-in-time facts. */
  period_start: string | null;
  /** SEC accession the fact was extracted from. */
  accession: string;
}

/** The set of XBRL facts for one financial-statement category at a symbol. */
export interface FinancialFacts {
  cik: string;
  symbol: string | null;
  category: "balance-sheet" | "income-statement" | "cash-flow";
  facts: XbrlFact[];
}

// ---------------------------------------------------------------------------
// Insider transactions (Forms 3, 4, 5)
// ---------------------------------------------------------------------------

/** Buy or sell direction on a Form 4 transaction. */
export type InsiderTransactionDirection = "acquired" | "disposed";

/**
 * One insider transaction row from a Form 3 / 4 / 5 filing. v0.6.0 surfaces
 * the unified shape across all three form types in a single tabular view;
 * Form-specific nuances (Form 3 ownership disclosures vs. Form 4 trades vs.
 * Form 5 deferred-reporting) are encoded in the ``form_type`` discriminator.
 */
export interface InsiderTransaction {
  /** SEC accession the transaction was filed under. */
  accession: string;
  /** Insider's name as the filing carries it. */
  reporter_name: string;
  /** CIK of the reporting insider (zero-padded to 10 digits). */
  reporter_cik: string;
  /** Issuer (company) CIK the insider has a relationship with. */
  issuer_cik: string;
  issuer_name: string;
  issuer_symbol: string | null;
  /** Filing form type — one of ``"3" | "4" | "5"``. */
  form_type: "3" | "4" | "5";
  /** ISO-8601 transaction date (NOT the filing date — the trade date). */
  transaction_date: string;
  /** ``"acquired" | "disposed"``. */
  direction: InsiderTransactionDirection;
  /** Number of shares as a string — exact XBRL value (may exceed safe int). */
  shares: string;
  /** Per-share price as a string; ``null`` for gift / inheritance transactions. */
  price_per_share: string | null;
  /** Total transaction value (``shares × price_per_share``) as a string;
   * computed by the sidecar to keep the math precise. */
  transaction_value: string | null;
  /** Form-specific transaction code — e.g. ``"P"`` purchase, ``"S"`` sale. */
  transaction_code: string;
  /** Insider's title at the issuer at filing time. */
  reporter_title: string | null;
}

/** Insider-transactions payload returned by ``/sec/insider/{cik}``. */
export interface InsiderTransactionsResponse {
  cik: string;
  issuer_name: string;
  transactions: InsiderTransaction[];
}

// ---------------------------------------------------------------------------
// Filings list response
// ---------------------------------------------------------------------------

/** Filings-list payload returned by ``/sec/filings?cik=`` or ``?symbol=``. */
export interface FilingsListResponse {
  cik: string;
  company_name: string;
  symbol: string | null;
  filings: Filing[];
}
