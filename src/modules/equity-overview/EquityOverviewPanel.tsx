"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Building2, Loader2, Search, Sparkles } from "lucide-react";

import { cn, DataTable, type DataColumn, type DataSection } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import {
  formatCompactMoney,
  formatPercent as formatPercentRaw,
  formatPrice,
  formatUnit,
} from "@/lib/format";
import { SidecarError } from "@/lib/sidecar-client";
import { useEquityCommandStore } from "@/store/equity-command";
import { usePanelContextBus } from "@/store/panel-context";
import type {
  CompanyNarrative,
  FinancialStatement,
  Fundamentals,
  Quote,
} from "../../../types/data";
import {
  autocompleteSymbols,
  loadCompanyNarrative,
  loadEquityOverview,
  type EquityOverview,
  type SymbolCandidate,
} from "./api";

// --- formatters (single source: @/lib/format) -----------------------------
// Every value on this panel runs through these so a bare overflow ("Free cash
// flow 101.098", "Shares out. 14.698") can never render — the unit + sign are
// always applied. The fraction fields the sidecar ships as 0.21 = 21% are scaled
// to whole-percent before formatPercent (which expects 33.33 = 33.33%).

/** A plain ratio / multiple (P/E, beta) — 2dp, no unit, graceful null. */
function fmtRatio(value: number | null): string | null {
  return value === null || Number.isNaN(value) ? null : formatPrice(value, 2);
}

/** A bare price (EPS, dividend/share, 52w bounds) — sig-digit small, 2dp large. */
function fmtPriceField(value: number | null): string | null {
  return value === null || Number.isNaN(value) ? null : formatPrice(value);
}

/** A fraction (0.21) rendered as a signed percent ("+21.00%"). */
function fmtFraction(value: number | null): string | null {
  return value === null || Number.isNaN(value) ? null : formatPercentRaw(value * 100);
}

/** A currency magnitude (market cap, revenue, FCF) — compact, currency-aware,
 *  always suffixed (the missing-B fix). */
function fmtMoney(value: number | null): string | null {
  return value === null || Number.isNaN(value) ? null : formatCompactMoney(value);
}

/** A bare large count (shares outstanding) — always K/M/B/T-suffixed. */
function fmtCount(value: number | null): string | null {
  return value === null || Number.isNaN(value) ? null : formatUnit(value);
}

type FieldKind = "ratio" | "price" | "fraction" | "money" | "count";

interface FieldDef {
  label: string;
  key: keyof Fundamentals;
  kind: FieldKind;
  /** Headline metrics read at the primary tier; supporting ratios at secondary. */
  headline?: boolean;
}

interface FieldGroup {
  title: string;
  fields: FieldDef[];
}

// Screener-grade fundamentals, grouped the way a trader reads a stock page. Labels
// are curated (never snake_case). A whole group is hidden when every field in it is
// null (e.g. ownership for an index fund) so the page never shows a wall of dashes.
const FIELD_GROUPS: FieldGroup[] = [
  {
    title: "Valuation",
    fields: [
      { label: "Market cap", key: "market_cap", kind: "money", headline: true },
      { label: "P/E", key: "pe_ratio", kind: "ratio", headline: true },
      { label: "Fwd P/E", key: "forward_pe", kind: "ratio" },
      { label: "PEG", key: "peg_ratio", kind: "ratio" },
      { label: "P/B", key: "price_to_book", kind: "ratio" },
      { label: "P/S", key: "price_to_sales", kind: "ratio" },
      { label: "EV/EBITDA", key: "ev_to_ebitda", kind: "ratio" },
      { label: "Book value", key: "book_value", kind: "price" },
    ],
  },
  {
    title: "Profitability",
    fields: [
      { label: "ROE", key: "roe", kind: "fraction", headline: true },
      { label: "ROA", key: "roa", kind: "fraction" },
      { label: "Gross margin", key: "gross_margin", kind: "fraction" },
      { label: "Operating margin", key: "operating_margin", kind: "fraction" },
      { label: "Net margin", key: "profit_margin", kind: "fraction", headline: true },
    ],
  },
  {
    title: "Financial health",
    fields: [
      { label: "Debt / equity", key: "debt_to_equity", kind: "ratio", headline: true },
      { label: "Current ratio", key: "current_ratio", kind: "ratio" },
      { label: "Quick ratio", key: "quick_ratio", kind: "ratio" },
      { label: "Free cash flow", key: "free_cash_flow", kind: "money", headline: true },
    ],
  },
  {
    title: "Growth & size",
    fields: [
      { label: "Revenue (TTM)", key: "revenue_ttm", kind: "money", headline: true },
      { label: "Net income (TTM)", key: "net_income_ttm", kind: "money", headline: true },
      { label: "Revenue growth", key: "revenue_growth", kind: "fraction" },
      { label: "Earnings growth", key: "earnings_growth", kind: "fraction" },
      { label: "Shares outstanding", key: "shares_outstanding", kind: "count" },
    ],
  },
  {
    title: "Per share & dividend",
    fields: [
      { label: "EPS", key: "eps", kind: "price", headline: true },
      { label: "Dividend / share", key: "dividend_per_share", kind: "price" },
      { label: "Dividend yield", key: "dividend_yield", kind: "fraction" },
      { label: "Beta", key: "beta", kind: "ratio" },
      { label: "1Y change", key: "fifty_two_week_change", kind: "fraction" },
    ],
  },
  {
    title: "Ownership",
    fields: [
      { label: "Insiders", key: "held_percent_insiders", kind: "fraction" },
      { label: "Institutions", key: "held_percent_institutions", kind: "fraction" },
    ],
  },
];

function fieldValue(fundamentals: Fundamentals, key: keyof Fundamentals): number | null {
  const raw = fundamentals[key];
  return typeof raw === "number" ? raw : null;
}

/** Format a fundamentals field by its kind — every path goes through format.ts. */
function formatField(value: number | null, kind: FieldKind): string | null {
  switch (kind) {
    case "fraction":
      return fmtFraction(value);
    case "money":
      return fmtMoney(value);
    case "count":
      return fmtCount(value);
    case "price":
      return fmtPriceField(value);
    default:
      return fmtRatio(value);
  }
}

/** One fundamentals row — a curated label + its formatted value. */
interface FundamentalRow {
  label: string;
  value: string | null;
  headline: boolean;
}

const FUNDAMENTAL_COLUMNS: DataColumn<FundamentalRow>[] = [
  { key: "label", header: "Metric", tier: "secondary", truncate: true, width: "55%" },
  {
    key: "value",
    header: "Value",
    numeric: true,
    width: "45%",
    // Headline metrics keep the primary tier; supporting ratios drop to secondary.
    cell: (r) =>
      r.value === null ? null : (
        <span className={r.headline ? undefined : "text-charcoal-400"}>{r.value}</span>
      ),
  },
];

/** Provenance + freshness chip — which source served the data, and how fresh. */
function ProvenanceBadge({
  quote,
  fundamentals,
}: {
  quote: Quote | null;
  fundamentals: Fundamentals | null;
}) {
  const provider = quote?.provider ?? fundamentals?.provider ?? null;
  if (provider === null) {
    return null;
  }
  const freshness = quote?.freshness ?? null;
  const stale = freshness === "stale";
  return (
    <span
      className={cn(
        "border-charcoal-700 text-charcoal-400 text-micro inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5",
        stale && "border-warning/40 text-warning",
      )}
      title={`Source: ${provider}${freshness ? ` · ${freshness}` : ""}`}
    >
      <span>{provider}</span>
      {freshness && <span className="text-charcoal-500">· {freshness}</span>}
    </span>
  );
}

/**
 * Render narrative prose, surfacing the verifier's redaction marker. Any
 * `[unverified]` token the numeric-verification pass left in place of a
 * hallucinated figure is shown as a dimmed inline chip — so the reader sees a
 * number was withheld rather than reading around a silent gap.
 */
function VerifiedProse({ text }: { text: string }) {
  const parts = text.split(/(\[unverified\])/g);
  return (
    <>
      {parts.map((part, i) =>
        part === "[unverified]" ? (
          <span
            key={i}
            className="text-charcoal-500 border-charcoal-700 mx-0.5 rounded-sm border border-dashed px-1 align-baseline"
            title="A figure here was removed because it did not match the source data."
          >
            redacted
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

/**
 * AI narrative section — an LLM-written, numerically-verified company overview
 * rendered above the field groups. Every number in it was checked against the
 * real fundamentals/quote; the "AI · verified against {provider}" label states
 * the grounding source and per-claim verification is surfaced inline (redacted
 * figures) and as a footnote count. Loading is a designed skeleton; an
 * unavailable narrative is a quiet icon + one calm line, never a dead void.
 */
function NarrativeSection({
  loading,
  narrative,
}: {
  loading: boolean;
  narrative: CompanyNarrative | null;
}) {
  const headerLabel =
    narrative?.source_provider != null ? (
      <span className="text-charcoal-500 text-micro inline-flex items-center gap-1">
        <Sparkles className="size-3" />
        AI · {narrative.verified ? "verified against" : "grounded in"} {narrative.source_provider}
      </span>
    ) : (
      <span className="text-charcoal-500 text-micro inline-flex items-center gap-1">
        <Sparkles className="size-3" />
        AI overview
      </span>
    );

  return (
    <section className="border-charcoal-700 rounded-md border">
      <div className="border-charcoal-700 flex items-center justify-between gap-2 border-b px-3 py-2">
        <h3 className="text-charcoal-200 text-micro">Overview</h3>
        {headerLabel}
      </div>

      {loading ? (
        // Designed skeleton — three prose lines + two insight rows.
        <div className="flex animate-pulse flex-col gap-3 px-3 py-3">
          <div className="bg-charcoal-800 h-3 w-full rounded-sm" />
          <div className="bg-charcoal-800 h-3 w-11/12 rounded-sm" />
          <div className="bg-charcoal-800 h-3 w-3/4 rounded-sm" />
          <div className="mt-1 flex flex-col gap-2">
            <div className="bg-charcoal-800 h-3 w-2/3 rounded-sm" />
            <div className="bg-charcoal-800 h-3 w-1/2 rounded-sm" />
          </div>
        </div>
      ) : narrative?.summary != null ? (
        <div className="flex flex-col gap-3 px-3 py-3">
          {/* Primary tier — the narrative prose. */}
          <p className="text-charcoal-100 text-body leading-relaxed">
            <VerifiedProse text={narrative.summary} />
          </p>

          {/* Tertiary tier — key insights. */}
          {narrative.insights.length > 0 && (
            <ul className="flex flex-col gap-2">
              {narrative.insights.map((insight, i) => (
                <li key={i} className="text-charcoal-300 text-caption flex gap-2 leading-relaxed">
                  <span className="text-charcoal-600 mt-px select-none">—</span>
                  <span className="min-w-0">
                    <VerifiedProse text={insight} />
                  </span>
                </li>
              ))}
            </ul>
          )}

          {/* Per-claim verification footnote — only when something was redacted. */}
          {narrative.unverified_claims.length > 0 && (
            <p
              className="text-charcoal-500 text-micro leading-snug"
              title={narrative.unverified_claims.map((c) => `${c.text} — ${c.reason}`).join("\n")}
            >
              {narrative.unverified_claims.length} figure
              {narrative.unverified_claims.length === 1 ? "" : "s"} the model wrote did not match
              the source data and {narrative.unverified_claims.length === 1 ? "was" : "were"}{" "}
              redacted.
            </p>
          )}
        </div>
      ) : (
        // Quiet unavailable state — icon + one calm line (the reason), never blank.
        <div className="flex flex-col items-center gap-2 px-3 py-6 text-center">
          <Sparkles className="text-charcoal-600 size-5" />
          <p className="text-charcoal-500 text-caption max-w-xs leading-snug">
            {narrative?.reason ?? "AI overview unavailable."}
          </p>
        </div>
      )}
    </section>
  );
}

/** Finance acronyms that read wrong in sentence case — uppercased whole. */
const STATEMENT_ACRONYMS = new Set([
  "ebitda",
  "ebit",
  "eps",
  "da",
  "sga",
  "fcf",
  "ppe",
  "roe",
  "roa",
  "rnd",
]);

/**
 * Humanize a raw statement line key (the provider returns snake_case keys like
 * `free_cash_flow` / `repurchase_of_common_equity`) into a clean sentence-case
 * label — "Free cash flow", "Repurchase of common equity", "EBITDA". A label that
 * already contains whitespace is assumed human and passes through untouched.
 * Keeps the statements snake_case-free (no raw DB keys ever surface — checklist #1).
 */
function humanizeLineLabel(raw: string): string {
  if (/\s/.test(raw)) return raw;
  const words = raw.replace(/_/g, " ").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return raw;
  return words
    .map((w, i) =>
      STATEMENT_ACRONYMS.has(w.toLowerCase())
        ? w.toUpperCase()
        : i === 0
          ? w.charAt(0).toUpperCase() + w.slice(1)
          : w,
    )
    .join(" ");
}

/** A statement line, projected to a row whose period values are pre-formatted
 *  through formatUnit so a column never overflows with a bare magnitude. */
interface StatementRow {
  label: string;
  /** period label → formatted display string (null → glyph). */
  values: Record<string, string | null>;
}

/**
 * A real period-column financial statement on the shared DataTable. Each period
 * (TTM / FY2025 / FY2024…) is an explicit right-aligned numeric column; the line
 * label is the left primary column. Every figure runs through formatUnit so the
 * statement reads "14.70B", never a raw "14698000000".
 */
function StatementTable({
  title,
  statement,
}: {
  title: string;
  statement: FinancialStatement | null;
}) {
  const columns = useMemo<DataColumn<StatementRow>[]>(() => {
    if (statement === null) return [];
    const periodCols: DataColumn<StatementRow>[] = statement.periods.map((period) => ({
      key: period,
      header: period,
      numeric: true,
      tier: "primary",
      format: (row: StatementRow) => row.values[period] ?? null,
    }));
    return [
      {
        key: "label",
        header: "Line item",
        tier: "secondary",
        truncate: true,
        width: "40%",
        format: (row: StatementRow) => row.label,
        title: (row: StatementRow) => row.label,
      },
      ...periodCols,
    ];
  }, [statement]);

  const rows = useMemo<StatementRow[]>(() => {
    if (statement === null) return [];
    return statement.lines.map((line) => ({
      label: humanizeLineLabel(line.label),
      values: Object.fromEntries(
        statement.periods.map((period) => {
          const raw = line.values[period] ?? null;
          return [period, raw === null ? null : formatUnit(raw)];
        }),
      ),
    }));
  }, [statement]);

  return (
    <section className="border-charcoal-700 rounded-md border">
      <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
        {title}
      </h3>
      {statement === null ? (
        <p className="text-charcoal-500 text-caption px-3 py-2">Unavailable.</p>
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(row, i) => `${row.label}-${i}`}
          data-testid={`statement-${title}`}
        />
      )}
    </section>
  );
}

/**
 * Equity Overview panel — a symbol input with live autocomplete that, on submit,
 * fetches and lays out screener-grade fundamentals (grouped), the three financial
 * statements, analyst ratings, and a provenance-badged live quote in one view.
 * Sections that fail to load degrade individually; an error banner shows only
 * when every section fails, and a sparse-fundamentals note is shown honestly
 * rather than a wall of dashes.
 */
export function EquityOverviewPanel() {
  const [draft, setDraft] = useState("");
  const [data, setData] = useState<EquityOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submittedSymbolRef = useRef<string | null>(null);

  // --- AI narrative ---------------------------------------------------------
  // Fetched independently of the data fan-out: it depends on the BYOK LLM and is
  // slower, so it must never block the fundamentals render. Keyed to the loaded
  // symbol; a stale-symbol guard drops out-of-order responses.
  const [narrative, setNarrative] = useState<CompanyNarrative | null>(null);
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const narrativeSeqRef = useRef(0);

  // --- autocomplete ---------------------------------------------------------
  const [candidates, setCandidates] = useState<SymbolCandidate[]>([]);
  const [acOpen, setAcOpen] = useState(false);
  const [acIndex, setAcIndex] = useState(-1);
  const acSeqRef = useRef(0);

  // --- panel-context bus ----------------------------------------------------
  const publishPanelContext = usePanelContextBus((s) => s.publish);
  const unregisterPanelContext = usePanelContextBus((s) => s.unregisterSource);

  // --- external "open this company" command channel -------------------------
  // The always-consumed seam (mirror of chart-command): a screener row, a
  // watchlist entry, a brief ticker chip, or a ⌘K result issues
  // `equity-command.loadSymbol(symbol)` and this panel loads it — so "click any
  // company anywhere → the full overview" works without reaching into local state.
  const equityCommand = useEquityCommandStore((s) => s.command);

  const loadedSections = useMemo<string[]>(() => {
    if (data === null) {
      return [];
    }
    const sections: string[] = [];
    if (data.quote !== null) sections.push("quote");
    if (data.fundamentals !== null) sections.push("fundamentals");
    if (data.income !== null) sections.push("income");
    if (data.balance !== null) sections.push("balance");
    if (data.cashFlow !== null) sections.push("cashFlow");
    if (data.ratings !== null) sections.push("ratings");
    return sections;
  }, [data]);

  const loadedKey = loadedSections.join(",");
  const currentTicker = data?.symbol ?? null;

  useEffect(() => {
    publishPanelContext({
      source: "equity",
      kind: "symbol",
      payload: { ticker: currentTicker, loadedSections },
      emittedAt: Date.now(),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [publishPanelContext, currentTicker, loadedKey]);

  useEffect(() => {
    return () => {
      unregisterPanelContext("equity");
    };
  }, [unregisterPanelContext]);

  // Debounced autocomplete fetch — a fresh sequence id guards against
  // out-of-order responses overwriting a newer query's results. All state
  // updates happen inside the timer (never synchronously in the effect body),
  // including the empty-query clear, so there are no cascading renders.
  useEffect(() => {
    const q = draft.trim();
    const seq = ++acSeqRef.current;
    const handle = setTimeout(() => {
      if (seq !== acSeqRef.current) {
        return;
      }
      if (q.length < 1) {
        setCandidates([]);
        setAcOpen(false);
        return;
      }
      void autocompleteSymbols(q).then((rows) => {
        if (seq !== acSeqRef.current) {
          return;
        }
        setCandidates(rows);
        setAcIndex(-1);
        setAcOpen(rows.length > 0);
      });
    }, 140);
    return () => clearTimeout(handle);
  }, [draft]);

  const doLoad = async (symbol: string) => {
    submittedSymbolRef.current = symbol;
    setLoading(true);
    setError(null);
    setData(null);
    setNarrative(null);
    setNarrativeLoading(false);
    setAcOpen(false);
    try {
      const overview = await loadEquityOverview(symbol);
      if (overview.allFailed) {
        setData(null);
        setError(`No data available for ${symbol}`);
      } else {
        setData(overview);
        void fetchNarrative(symbol);
      }
    } catch (err) {
      setData(null);
      setError(err instanceof SidecarError ? err.message : `Failed to load ${symbol}`);
    } finally {
      setLoading(false);
    }
  };

  // Fetch the AI narrative for a freshly-loaded symbol. Sequence-guarded so a
  // slow narrative for a previous symbol never lands on the current one. Any
  // transport failure resolves to a quiet "unavailable" narrative rather than a
  // thrown error — the section degrades, the rest of the panel is unaffected.
  const fetchNarrative = async (symbol: string) => {
    const seq = ++narrativeSeqRef.current;
    setNarrativeLoading(true);
    try {
      const result = await loadCompanyNarrative(symbol);
      if (seq === narrativeSeqRef.current) {
        setNarrative(result);
      }
    } catch {
      if (seq === narrativeSeqRef.current) {
        setNarrative({
          symbol,
          summary: null,
          insights: [],
          verified: false,
          unverified_claims: [],
          source_provider: null,
          model: null,
          generated_at: null,
          reason: "AI overview unavailable — the data engine could not be reached.",
        });
      }
    } finally {
      if (seq === narrativeSeqRef.current) {
        setNarrativeLoading(false);
      }
    }
  };

  const selectCandidate = async (candidate: SymbolCandidate) => {
    setDraft(candidate.symbol);
    setAcOpen(false);
    await doLoad(candidate.symbol);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (acOpen && acIndex >= 0 && candidates[acIndex]) {
      await selectCandidate(candidates[acIndex]);
      return;
    }
    const symbol = draft.trim().toUpperCase();
    if (symbol === "") {
      return;
    }
    await doLoad(symbol);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (!acOpen || candidates.length === 0) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setAcIndex((i) => Math.min(i + 1, candidates.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setAcIndex((i) => Math.max(i - 1, -1));
    } else if (event.key === "Escape") {
      setAcOpen(false);
    }
  };

  const handleRetry = async () => {
    if (submittedSymbolRef.current) {
      await doLoad(submittedSymbolRef.current);
    }
  };

  const quickLoad = async (symbol: string) => {
    setDraft(symbol);
    await doLoad(symbol);
  };

  // Consume the external open-company command. Keyed on the command object (whose
  // `seq` bumps on every issue), so re-opening the SAME symbol still re-loads; a
  // null command (initial) is a no-op. The load is deferred a tick so the state
  // updates never fire synchronously in the effect body (the codebase's
  // no-synchronous-setState-in-effect rule, as the autocomplete effect does).
  useEffect(() => {
    if (!equityCommand) {
      return;
    }
    const symbol = equityCommand.symbol;
    const handle = setTimeout(() => {
      setDraft(symbol);
      void doLoad(symbol);
    }, 0);
    return () => clearTimeout(handle);
  }, [equityCommand]);

  const quote = data?.quote ?? null;
  const fundamentals = data?.fundamentals ?? null;
  const ratings = data?.ratings ?? null;

  // Which grouped sections have at least one populated field (hide empty groups),
  // projected to DataTable sections with each value pre-formatted through format.ts.
  const fundamentalSections = useMemo<DataSection<FundamentalRow>[]>(() => {
    if (fundamentals === null) {
      return [];
    }
    return FIELD_GROUPS.map((group) => {
      const rows: FundamentalRow[] = group.fields
        .map((f) => ({
          label: f.label,
          value: formatField(fieldValue(fundamentals, f.key), f.kind),
          headline: f.headline ?? false,
        }))
        .filter((r) => r.value !== null);
      return { label: group.title, rows };
    }).filter((s) => s.rows.length > 0);
  }, [fundamentals]);

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <form
        onSubmit={handleSubmit}
        className="border-charcoal-700 relative flex items-center gap-2 border-b p-3"
      >
        <div className="relative flex-1">
          <input
            aria-label="Symbol"
            placeholder="Search a company or ticker (AAPL, Route Mobile, RELIANCE)…"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => candidates.length > 0 && setAcOpen(true)}
            onBlur={() => setTimeout(() => setAcOpen(false), 120)}
            autoComplete="off"
            className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-500 text-body h-9 w-full rounded-md px-3 outline-none focus:ring-1 focus:ring-amber-400"
          />
          {acOpen && candidates.length > 0 && (
            <ul className="border-charcoal-700 bg-charcoal-875 absolute top-full right-0 left-0 z-20 mt-1 max-h-64 overflow-y-auto rounded-md border py-1">
              {candidates.map((candidate, idx) => (
                <li key={`${candidate.symbol}:${candidate.exchange}`}>
                  <button
                    type="button"
                    // onMouseDown (not onClick) so it fires before the input's blur closes the list.
                    onMouseDown={(e) => {
                      e.preventDefault();
                      void selectCandidate(candidate);
                    }}
                    onMouseEnter={() => setAcIndex(idx)}
                    className={cn(
                      "flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left",
                      idx === acIndex ? "bg-charcoal-800" : "hover:bg-charcoal-800/60",
                    )}
                  >
                    <span className="flex min-w-0 items-baseline gap-2">
                      <span className="text-charcoal-100 text-caption shrink-0 font-medium">
                        {candidate.symbol}
                      </span>
                      <span className="text-charcoal-400 text-caption truncate">
                        {candidate.name}
                      </span>
                    </span>
                    <span className="text-charcoal-500 text-micro shrink-0">
                      {candidate.exchange}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <Button type="submit" size="sm" variant="outline" disabled={loading}>
          {loading ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Search className="size-3.5" />
          )}
          {loading ? "Loading" : "Load"}
        </Button>
      </form>

      {error !== null && (
        <div className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2">
          <p className="text-negative text-caption">{error}</p>
          <Button type="button" size="sm" variant="ghost" onClick={() => void handleRetry()}>
            Retry
          </Button>
        </div>
      )}

      <div className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto p-3">
        {loading ? (
          <div className="flex animate-pulse flex-col gap-4">
            <div className="flex flex-wrap gap-3">
              <div className="bg-charcoal-800 h-7 w-20 rounded-sm" />
              <div className="bg-charcoal-800 h-5 w-32 self-end rounded-sm" />
              <div className="bg-charcoal-800 h-6 w-24 self-end rounded-sm" />
            </div>
            {Array.from({ length: 2 }).map((_, s) => (
              <div key={s} className="border-charcoal-700 rounded-md border">
                <div className="border-charcoal-700 border-b px-3 py-2">
                  <div className="bg-charcoal-800 h-3 w-28 rounded-sm" />
                </div>
                <div className="flex flex-col gap-2 px-3 py-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="flex justify-between gap-2">
                      <div className="bg-charcoal-800 h-3 w-20 rounded-sm" />
                      <div className="bg-charcoal-800 h-3 w-12 rounded-sm" />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : data === null ? (
          <div className="flex flex-col items-center gap-4 pt-12 text-center">
            <Building2 className="text-charcoal-600 size-8" />
            <p className="text-charcoal-300 text-body max-w-sm">
              Screener-grade fundamentals, statements, and ratings for any ticker — US, NSE, or BSE.
            </p>
            <div className="flex gap-2">
              {["AAPL", "RELIANCE", "NVDA"].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => void quickLoad(t)}
                  className="border-charcoal-700 bg-charcoal-800 text-charcoal-300 text-caption rounded-md border px-3 py-1.5 transition-colors hover:border-amber-500 hover:text-amber-300"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <h2 className="text-charcoal-100 text-overview">{data.symbol}</h2>
              {fundamentals?.name != null && (
                <span className="text-charcoal-400 text-body">{fundamentals.name}</span>
              )}
              {quote !== null && (
                <span className="text-charcoal-100 text-panel-title tabular-nums">
                  {formatPrice(quote.price)} {quote.currency}
                </span>
              )}
              {quote !== null && (
                <span
                  className={cn(
                    "text-body whitespace-nowrap tabular-nums",
                    quote.change_percent >= 0 ? "text-positive" : "text-negative",
                  )}
                >
                  {quote.change >= 0 ? "+" : ""}
                  {formatPrice(quote.change)} ({quote.change_percent >= 0 ? "+" : ""}
                  {quote.change_percent.toFixed(2)}%)
                </span>
              )}
              <ProvenanceBadge quote={quote} fundamentals={fundamentals} />
              {fundamentals?.sector != null && (
                <span className="text-charcoal-400 text-caption">
                  {fundamentals.sector}
                  {fundamentals.industry != null ? ` · ${fundamentals.industry}` : ""}
                </span>
              )}
              {fundamentals != null &&
                (fundamentals.fifty_two_week_low != null ||
                  fundamentals.fifty_two_week_high != null) && (
                  <span className="text-charcoal-500 text-caption tabular-nums">
                    52w {fmtPriceField(fundamentals.fifty_two_week_low) ?? "—"} –{" "}
                    {fmtPriceField(fundamentals.fifty_two_week_high) ?? "—"}
                  </span>
                )}
            </header>

            <NarrativeSection loading={narrativeLoading} narrative={narrative} />

            {fundamentals === null ? (
              <section className="border-charcoal-700 rounded-md border">
                <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
                  Fundamentals
                </h3>
                <p className="text-charcoal-500 text-caption px-3 py-2">Unavailable.</p>
              </section>
            ) : fundamentalSections.length === 0 ? (
              <section className="border-charcoal-700 rounded-md border">
                <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
                  Fundamentals
                </h3>
                <p className="text-charcoal-500 text-caption px-3 py-2">
                  No fundamentals resolved for this symbol — it may be newly listed, renamed, or
                  delisted. Try the search above to pick the exact listing.
                </p>
              </section>
            ) : (
              <section className="border-charcoal-700 rounded-md border">
                <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
                  Fundamentals
                </h3>
                <DataTable
                  columns={FUNDAMENTAL_COLUMNS}
                  sections={fundamentalSections}
                  rowKey={(row) => row.label}
                  data-testid="fundamentals-table"
                />
              </section>
            )}

            <section className="border-charcoal-700 rounded-md border">
              <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
                Analyst ratings
              </h3>
              {ratings === null ? (
                <p className="text-charcoal-500 text-caption px-3 py-2">Unavailable.</p>
              ) : (
                <div className="text-caption flex flex-wrap gap-x-6 gap-y-1 px-3 py-2">
                  <span className="text-charcoal-200">
                    Consensus: <span className="text-amber-400">{ratings.consensus ?? "—"}</span>
                  </span>
                  <span className="text-charcoal-200">
                    Target mean:{" "}
                    <span className="text-charcoal-100 tabular-nums">
                      {fmtPriceField(ratings.target_mean) ?? "—"}
                    </span>
                  </span>
                  <span className="text-charcoal-200">
                    Range:{" "}
                    <span className="text-charcoal-100 tabular-nums">
                      {fmtPriceField(ratings.target_low) ?? "—"} –{" "}
                      {fmtPriceField(ratings.target_high) ?? "—"}
                    </span>
                  </span>
                  <span className="text-charcoal-400 flex flex-wrap gap-x-2 tabular-nums">
                    <span className="whitespace-nowrap">SB {ratings.strong_buy}</span>
                    <span className="whitespace-nowrap">· B {ratings.buy}</span>
                    <span className="whitespace-nowrap">· H {ratings.hold}</span>
                    <span className="whitespace-nowrap">· S {ratings.sell}</span>
                    <span className="whitespace-nowrap">· SS {ratings.strong_sell}</span>
                  </span>
                </div>
              )}
            </section>

            <StatementTable title="Income statement" statement={data.income} />
            <StatementTable title="Balance sheet" statement={data.balance} />
            <StatementTable title="Cash flow" statement={data.cashFlow} />
          </div>
        )}
      </div>
    </div>
  );
}
