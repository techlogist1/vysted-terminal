"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Building2, FileSpreadsheet, Loader2, Search, Sparkles, Star } from "lucide-react";

import { ProvenanceBadge, StalenessBadge } from "@/components/DataBadges";
import { cn, DataTable, type DataColumn, type DataSection } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import {
  formatCompactMoney,
  formatPercent as formatPercentRaw,
  formatPrice,
  formatUnit,
} from "@/lib/format";
import { SidecarError } from "@/lib/sidecar-client";
import { FIELD_GROUPS, type FieldKind, resolveMetric } from "@/modules/equity-overview/metrics";
import { useEquityCommandStore } from "@/store/equity-command";
import { usePanelContextBus } from "@/store/panel-context";
import type {
  CompanyNarrative,
  FieldMeta,
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

/** A currency magnitude (market cap, revenue, FCF) — compact, always suffixed
 *  (the missing-B fix), and denominated in the INSTRUMENT's currency (R8 §6 —
 *  the live D10 defect put ₹ on AAPL's market cap). */
function fmtMoney(value: number | null, currency: string | null): string | null {
  return value === null || Number.isNaN(value) ? null : formatCompactMoney(value, currency);
}

/** A bare large count (shares outstanding) — always K/M/B/T-suffixed. */
function fmtCount(value: number | null): string | null {
  return value === null || Number.isNaN(value) ? null : formatUnit(value);
}

/** How long a spotlit metric row keeps its accent ring. */
const SPOTLIGHT_MS = 2_400;

function fieldValue(fundamentals: Fundamentals, key: keyof Fundamentals): number | null {
  const raw = fundamentals[key];
  return typeof raw === "number" ? raw : null;
}

/** Format a fundamentals field by its kind — every path goes through format.ts.
 *  `currency` is the currency the field is denominated in (money fields only). */
function formatField(
  value: number | null,
  kind: FieldKind,
  currency: string | null,
): string | null {
  switch (kind) {
    case "fraction":
      return fmtFraction(value);
    case "money":
      return fmtMoney(value, currency);
    case "count":
      return fmtCount(value);
    case "price":
      return fmtPriceField(value);
    default:
      return fmtRatio(value);
  }
}

/** One fundamentals row — a curated label + its formatted value + the field's
 *  provenance/coverage record (R13), when the provider shipped one. */
interface FundamentalRow {
  /** The Fundamentals field key (the metric id a host action can spotlight). */
  key: string;
  label: string;
  value: string | null;
  headline: boolean;
  meta?: FieldMeta;
  /** Spotlighted by an `open_company_overview` highlight (R15-AGENT-081). */
  highlighted: boolean;
}

/**
 * The always-visible reason a NULL field carries (R13 — never a silent blank):
 * `withheld` reads as "withheld — implausible" (every current withhold reason is
 * a plausibility-gate rejection); `unavailable` reads as "not published" when the
 * sidecar's reason says so, else the plain "unavailable". Absent `field_meta`
 * (older providers, or a field the gate never touched) → `null`, so the cell
 * falls back to the table's own quiet "—" glyph with no chip.
 */
function fieldReasonChip(meta: FieldMeta | undefined): string | null {
  if (!meta) {
    return null;
  }
  if (meta.status === "withheld") {
    return "withheld — implausible";
  }
  if (meta.status === "unavailable") {
    const reason = (meta.reason ?? "").toLowerCase();
    return reason.includes("not published") ? "not published" : "unavailable";
  }
  return null;
}

/** The field-level hover tooltip (R13): a served ("ok") field states its
 *  provider + as-of date; a withheld/flagged field states its recorded reason
 *  instead (the reason wins). No `field_meta` → no tooltip (the table's default
 *  applies). */
function fieldTitle(meta: FieldMeta | undefined): string | undefined {
  if (!meta) {
    return undefined;
  }
  if (meta.reason) {
    return meta.reason;
  }
  if (meta.status === "ok") {
    const bits = [meta.provider, meta.as_of].filter((b): b is string => Boolean(b));
    return bits.length > 0 ? bits.join(" · ") : undefined;
  }
  return undefined;
}

/** The fundamentals "Value" column cell — a served value (headline/secondary
 *  tier per {@link FundamentalRow.headline}), or an honest absence: an em-dash
 *  plus its reason chip, never a bare hidden row (R13). */
function FundamentalValueCell({ row }: { row: FundamentalRow }) {
  if (row.value !== null) {
    const value = (
      <span className={row.headline ? undefined : "text-charcoal-400"}>{row.value}</span>
    );
    if (row.meta?.status !== "flagged") {
      return value;
    }
    // C1: the value is kept but a cross-check disagrees — a visible chip beside
    // it (the disagreement and the witness figure ride the cell's tooltip).
    return (
      <span className="inline-flex items-center justify-end gap-1">
        {value}
        <span className="text-micro text-warning border-warning/40 rounded-control border px-1 py-px tracking-wide uppercase">
          flagged
        </span>
      </span>
    );
  }
  const chip = fieldReasonChip(row.meta);
  return (
    <span className="inline-flex items-center justify-end gap-1">
      <span className="text-charcoal-500">—</span>
      {chip !== null && (
        <span className="text-micro text-charcoal-500 border-charcoal-800 rounded-control border px-1 py-px tracking-wide uppercase">
          {chip}
        </span>
      )}
    </span>
  );
}

const FUNDAMENTAL_COLUMNS: DataColumn<FundamentalRow>[] = [
  {
    key: "label",
    header: "Metric",
    tier: "secondary",
    truncate: true,
    width: "55%",
    cell: (r) => <span data-highlighted={r.highlighted ? "true" : undefined}>{r.label}</span>,
    title: (r) => r.label,
  },
  {
    key: "value",
    header: "Value",
    numeric: true,
    width: "45%",
    // Headline metrics keep the primary tier; supporting ratios drop to secondary;
    // a null value never returns bare null (that was the SILENT BLANK the design
    // gate would flag) — it always renders the honest cell above.
    cell: (r) => <FundamentalValueCell row={r} />,
    title: (r) => fieldTitle(r.meta),
  },
];

/** The fundamentals snapshot's as-of date (R13): every field a provider actually
 *  SERVED shares one fetch timestamp (the sidecar stamps the whole snapshot at
 *  once), so the first `status: "ok"` entry's `as_of` names the whole payload's
 *  freshness. `null` when the provider shipped no per-field provenance at all. */
function fundamentalsAsOf(fundamentals: Fundamentals | null): string | null {
  const meta = fundamentals?.field_meta;
  if (!meta) {
    return null;
  }
  for (const entry of Object.values(meta)) {
    if (entry?.as_of) {
      return entry.as_of;
    }
  }
  return null;
}

/** A listing whose exchange listing date is under 52 weeks old (R15-DATA-055):
 *  its "52w" range only spans the time since listing and it has no 1Y change. */
function listedUnderAYear(fundamentals: Fundamentals | null): boolean {
  const listed = fundamentals?.listing_date;
  return listed != null && Date.now() - Date.parse(listed) < 364 * 24 * 60 * 60 * 1000;
}

/** Provenance + freshness chips via the shared data-trust badges — which source
 *  served the data, and how fresh. A quote's `freshness` leads; when there is
 *  none (a fundamentals-only load, or a quote leg that failed) the fundamentals
 *  snapshot's own as-of date (R13) fills in as an end-of-day read, so the chip
 *  never goes silent on staleness just because there was no quote to ask. */
function SourceBadges({
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
  const snapshotAsOf = freshness === null ? fundamentalsAsOf(fundamentals) : null;
  return (
    <span className="inline-flex items-center gap-1">
      <ProvenanceBadge provider={provider} />
      {freshness !== null && quote !== null ? (
        <StalenessBadge freshness={freshness} asOf={Date.parse(quote.timestamp)} />
      ) : snapshotAsOf !== null ? (
        <StalenessBadge freshness="eod" asOf={Date.parse(snapshotAsOf)} />
      ) : null}
    </span>
  );
}

/** One analyst-ratings metric cell — a micro label over a body-size value
 *  (tabular when numeric); null renders the table's quiet glyph. */
function RatingMetric({
  label,
  value,
  numeric = false,
}: {
  label: string;
  value: string | null;
  numeric?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1 px-3 py-2">
      <span className="text-charcoal-500 text-micro">{label}</span>
      <span
        className={cn(
          "text-body",
          value === null ? "text-charcoal-500" : "text-charcoal-100",
          numeric && "tabular-nums",
        )}
      >
        {value ?? "—"}
      </span>
    </div>
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
            className="text-charcoal-500 border-charcoal-700 rounded-control mx-1 border border-dashed px-1 align-baseline"
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

/** One FR-124 narrative block — a micro heading over verified prose or bullets;
 *  renders nothing when the model left the section empty. */
function NarrativeBlock({
  label,
  text = null,
  items = [],
}: {
  label: string;
  text?: string | null;
  items?: string[];
}) {
  if (!text && items.length === 0) {
    return null;
  }
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <h4 className="text-charcoal-500 text-micro">{label}</h4>
      {text ? (
        <p className="text-charcoal-200 text-caption leading-relaxed">
          <VerifiedProse text={text} />
        </p>
      ) : null}
      {items.length > 0 ? (
        <ul className="flex flex-col gap-1">
          {items.map((item, i) => (
            <li key={i} className="text-charcoal-300 text-caption flex gap-2 leading-relaxed">
              <span className="text-charcoal-500 mt-px select-none">—</span>
              <span className="min-w-0">
                <VerifiedProse text={item} />
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
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
    <section className="border-charcoal-700 rounded-none border">
      <div className="border-charcoal-700 flex items-center justify-between gap-2 border-b px-3 py-2">
        <h3 className="text-charcoal-200 text-micro">Overview</h3>
        {headerLabel}
      </div>

      {loading ? (
        // Designed skeleton — three prose lines + two insight rows.
        <div className="flex animate-pulse flex-col gap-3 px-3 py-3">
          <div className="bg-charcoal-800 h-3 w-full rounded-none" />
          <div className="bg-charcoal-800 h-3 w-11/12 rounded-none" />
          <div className="bg-charcoal-800 h-3 w-3/4 rounded-none" />
          <div className="mt-1 flex flex-col gap-2">
            <div className="bg-charcoal-800 h-3 w-2/3 rounded-none" />
            <div className="bg-charcoal-800 h-3 w-1/2 rounded-none" />
          </div>
        </div>
      ) : narrative?.summary != null ? (
        <div className="flex flex-col gap-3 px-3 py-3">
          {/* Primary tier — the narrative prose. */}
          <p className="text-charcoal-100 text-prose leading-relaxed">
            <VerifiedProse text={narrative.summary} />
          </p>

          {/* Secondary tier — FR-124's typed sections, each verified like the take. */}
          <NarrativeBlock label="Business" text={narrative.business} />
          <NarrativeBlock label="Storyline" text={narrative.storyline} />
          {narrative.bull_case.length + narrative.bear_case.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <NarrativeBlock label="Bull case" items={narrative.bull_case} />
              <NarrativeBlock label="Bear case" items={narrative.bear_case} />
            </div>
          )}
          <NarrativeBlock label="Risks" items={narrative.risks} />

          {/* Tertiary tier — key insights. */}
          {narrative.insights.length > 0 && (
            <ul className="flex flex-col gap-2">
              {narrative.insights.map((insight, i) => (
                <li key={i} className="text-charcoal-300 text-caption flex gap-2 leading-relaxed">
                  <span className="text-charcoal-500 mt-px select-none">—</span>
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
        // Quiet unavailable state — the composed shared EmptyState, never blank.
        <EmptyState
          icon={Sparkles}
          dense
          headline="AI overview unavailable"
          hint={narrative?.reason ?? undefined}
          className="pt-4"
        />
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
    <section className="border-charcoal-700 rounded-none border">
      <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
        {title}
      </h3>
      {statement === null ? (
        <EmptyState
          icon={FileSpreadsheet}
          dense
          headline={`${title} unavailable`}
          hint="The provider returned no data for this statement."
          className="pt-4"
        />
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
export function EquityOverviewPanel(props: { api?: { id?: string } } = {}) {
  // The panel-context bus key is the dockview panel id PanelHost focuses
  // (R15-AGENT-052); the module's singleton id when rendered outside dockview.
  const busSource = props.api?.id ?? "equity-overview";
  const [draft, setDraft] = useState("");
  const [data, setData] = useState<EquityOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadSeqRef = useRef(0);
  // The last load, with the region of the listing it was for — so Retry
  // reloads the SAME company, not whatever the bare ticker means in the session.
  const submittedRef = useRef<{ symbol: string; region?: string } | null>(null);
  // Exact-ticker listings in more than one region for a typed ticker (SMR:
  // NuScale on NYSE, SMR Jewels on BSE): the user picks, nothing loads until then.
  const [chooser, setChooser] = useState<SymbolCandidate[] | null>(null);

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
  // The symbol input element — the dropdown may only (re)open while the input
  // owns focus, so a debounced response landing AFTER blur can never leave the
  // list stuck open over content (the live D10 defect).
  const inputRef = useRef<HTMLInputElement | null>(null);
  // Set when `draft` is written programmatically (selection, quick-load, the
  // external open-company command): the next debounce pass for that exact
  // value skips the fetch entirely instead of re-opening the list.
  const programmaticDraftRef = useRef<string | null>(null);

  // --- panel-context bus ----------------------------------------------------
  const publishPanelContext = usePanelContextBus((s) => s.publish);
  const unregisterPanelContext = usePanelContextBus((s) => s.unregisterSource);

  // --- external "open this company" command channel -------------------------
  // The always-consumed seam (mirror of chart-command): a screener row, a
  // watchlist entry, a brief ticker chip, or a ⌘K result issues
  // `equity-command.loadSymbol(symbol)` and this panel loads it — so "click any
  // company anywhere → the full overview" works without reaching into local state.
  const equityCommand = useEquityCommandStore((s) => s.command);
  // The metric row an `open_company_overview` highlight spotlights: scrolled into
  // view with a transient accent ring once its row renders (R15-AGENT-081).
  const [spotlight, setSpotlight] = useState<string | null>(null);
  const fundamentalsRef = useRef<HTMLDivElement | null>(null);

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
      source: busSource,
      kind: "symbol",
      payload: { ticker: currentTicker, loadedSections },
      emittedAt: Date.now(),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [publishPanelContext, busSource, currentTicker, loadedKey]);

  useEffect(() => {
    return () => {
      unregisterPanelContext(busSource);
    };
  }, [busSource, unregisterPanelContext]);

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
      // A programmatic draft write (candidate pick, quick-load, external
      // command) must not re-query and re-open the list it just closed.
      if (programmaticDraftRef.current !== null && q === programmaticDraftRef.current.trim()) {
        programmaticDraftRef.current = null;
        return;
      }
      void autocompleteSymbols(q).then((rows) => {
        if (seq !== acSeqRef.current) {
          return;
        }
        setCandidates(rows);
        setAcIndex(-1);
        // Only (re)open while the input owns focus — a slow response landing
        // after blur would otherwise pin the dropdown open over content.
        setAcOpen(rows.length > 0 && document.activeElement === inputRef.current);
      });
    }, 140);
    return () => clearTimeout(handle);
  }, [draft]);

  // Fetch the AI narrative for a freshly-loaded symbol. Sequence-guarded so a
  // slow narrative for a previous symbol never lands on the current one. Any
  // transport failure resolves to a quiet "unavailable" narrative rather than a
  // thrown error — the section degrades, the rest of the panel is unaffected.
  // `useCallback([])`: every dependency (the seq ref, the state setters) is
  // referentially stable, so this is a permanently-stable function — which lets
  // `doLoad` below (and, through it, the external-command effect) depend on it
  // without an eslint-disable or a re-subscribing effect.
  const fetchNarrative = useCallback(async (symbol: string, region?: string) => {
    const seq = ++narrativeSeqRef.current;
    setNarrativeLoading(true);
    try {
      const result = await loadCompanyNarrative(symbol, region);
      if (seq === narrativeSeqRef.current) {
        setNarrative(result);
      }
    } catch {
      if (seq === narrativeSeqRef.current) {
        setNarrative({
          symbol,
          summary: null,
          insights: [],
          business: null,
          storyline: null,
          bull_case: [],
          bear_case: [],
          risks: [],
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
  }, []);

  // `useCallback([fetchNarrative])`: stable across renders (fetchNarrative is
  // itself stable) so the external-command effect below can list it as a real
  // dependency instead of carrying the R10-era `react-hooks/exhaustive-deps`
  // warning — the honest fix, not a suppressed one.
  // `region` is the picked listing's region (a candidate or a host command);
  // every leg, the narrative included, sends it so the whole panel is ONE company.
  const doLoad = useCallback(
    async (symbol: string, region?: string) => {
      // Any caller that loads a symbol has (or will) put it in the draft —
      // suppress the autocomplete pass for that exact value.
      programmaticDraftRef.current = symbol;
      submittedRef.current = { symbol, region };
      setChooser(null);
      setLoading(true);
      setError(null);
      setData(null);
      setNarrative(null);
      setNarrativeLoading(false);
      setAcOpen(false);
      // Only the newest load commits: an older response settling later (a
      // host command opened another company mid-load) is dropped, and its
      // `finally` leaves the newer load's spinner alone (R15-UI-031).
      const seq = ++loadSeqRef.current;
      try {
        const overview = await loadEquityOverview(symbol, region);
        if (seq !== loadSeqRef.current) return;
        if (overview.allFailed) {
          setData(null);
          setError(`No data available for ${symbol}`);
        } else {
          setData(overview);
          void fetchNarrative(symbol, region);
        }
      } catch (err) {
        if (seq !== loadSeqRef.current) return;
        setData(null);
        setError(err instanceof SidecarError ? err.message : `Failed to load ${symbol}`);
      } finally {
        if (seq === loadSeqRef.current) setLoading(false);
      }
    },
    [fetchNarrative],
  );

  const selectCandidate = async (candidate: SymbolCandidate) => {
    setDraft(candidate.symbol);
    setAcOpen(false);
    await doLoad(candidate.symbol, candidate.region);
  };

  // A typed ticker is checked against the exact-ticker listings first: one that
  // names companies in more than one region (SMR, AMAL) opens a chooser instead
  // of silently binding the session region's company; otherwise the load
  // carries the one region its exact listings share.
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
    const exact = (await autocompleteSymbols(symbol)).filter(
      (c) => c.symbol.toUpperCase() === symbol,
    );
    const regions = [...new Set(exact.map((c) => c.region))];
    if (regions.length > 1) {
      setAcOpen(false);
      setChooser(exact);
      return;
    }
    await doLoad(symbol, regions[0]);
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
    if (submittedRef.current) {
      await doLoad(submittedRef.current.symbol, submittedRef.current.region);
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
    const { symbol, region, highlightMetric } = equityCommand;
    const handle = setTimeout(() => {
      setDraft(symbol);
      setSpotlight(resolveMetric(highlightMetric));
      void doLoad(symbol, region);
    }, 0);
    return () => clearTimeout(handle);
  }, [equityCommand, doLoad]);

  const quote = data?.quote ?? null;
  const fundamentals = data?.fundamentals ?? null;
  const ratings = data?.ratings ?? null;
  // The INSTRUMENT's currency (R8 §6) — money fields format in it, never the
  // region/locale default. Fundamentals state the trading currency; the quote
  // currency is the fallback. Statement sizes use the statement currency (C2).
  const instrumentCurrency = fundamentals?.currency ?? quote?.currency ?? null;
  const statementCurrency = fundamentals?.financial_currency ?? instrumentCurrency;

  // EVERY group, EVERY field, ALWAYS (R13) — a null field is never a hidden row;
  // it carries its `field_meta` so the cell can render an honest absence instead
  // of silently vanishing. Projected to DataTable sections with each value
  // pre-formatted through format.ts.
  const fundamentalSections = useMemo<DataSection<FundamentalRow>[]>(() => {
    if (fundamentals === null) {
      return [];
    }
    const young = listedUnderAYear(fundamentals);
    return FIELD_GROUPS.map((group) => {
      const fields = young
        ? group.fields.filter((f) => f.key !== "fifty_two_week_change")
        : group.fields;
      const rows: FundamentalRow[] = fields.map((f) => ({
        key: f.key,
        label: f.label,
        value: formatField(
          fieldValue(fundamentals, f.key),
          f.kind,
          f.statementSize ? statementCurrency : instrumentCurrency,
        ),
        headline: f.headline ?? false,
        meta: fundamentals.field_meta?.[f.key],
        highlighted: f.key === spotlight,
      }));
      return { label: group.title, rows };
    });
  }, [fundamentals, instrumentCurrency, statementCurrency, spotlight]);

  // Bring the spotlit row into view once it renders, then let the ring fade.
  useEffect(() => {
    const row = spotlight ? fundamentalsRef.current?.querySelector("[data-highlighted]") : null;
    if (!row) {
      return;
    }
    row.scrollIntoView?.({ block: "center", behavior: "smooth" });
    const handle = setTimeout(() => setSpotlight(null), SPOTLIGHT_MS);
    return () => clearTimeout(handle);
  }, [spotlight, fundamentalSections]);

  return (
    <div className="bg-charcoal-900 @container flex h-full w-full flex-col">
      <form
        onSubmit={handleSubmit}
        className="border-charcoal-700 relative flex items-center gap-2 border-b p-3"
      >
        <div className="relative flex-1">
          <input
            ref={inputRef}
            aria-label="Symbol"
            placeholder="Search a company or ticker (AAPL, Route Mobile, RELIANCE)…"
            value={draft}
            onChange={(event) => {
              // A keystroke is a USER edit — lift the programmatic suppression
              // so the autocomplete works normally again, and drop a stale chooser.
              programmaticDraftRef.current = null;
              setChooser(null);
              setDraft(event.target.value);
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => candidates.length > 0 && setAcOpen(true)}
            onBlur={() => setTimeout(() => setAcOpen(false), 120)}
            autoComplete="off"
            className="bg-charcoal-850 border-charcoal-700 text-charcoal-100 placeholder:text-charcoal-500 text-body rounded-control focus:border-charcoal-500 h-8 w-full truncate border px-3 outline-none"
          />
          {acOpen && candidates.length > 0 && (
            <ul
              className={
                "border-charcoal-700 bg-charcoal-875 absolute top-full right-0 left-0 z-20 mt-1 max-h-64 overflow-y-auto rounded-none border py-1" /* tokens-ok: dropdown scroll cap */
              }
            >
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
                      "flex w-full items-center justify-between gap-2 px-3 py-2 text-left",
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
          {loading ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
          {loading ? "Loading" : "Load"}
        </Button>
      </form>

      {chooser !== null && (
        <div className="border-charcoal-700 border-b px-3 py-2" data-testid="listing-chooser">
          <p className="text-charcoal-400 text-caption">
            {chooser[0].symbol} is listed in more than one market. Choose the company:
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {chooser.map((candidate) => (
              <button
                key={`${candidate.symbol}:${candidate.exchange}`}
                type="button"
                onClick={() => void selectCandidate(candidate)}
                className="border-charcoal-700 text-charcoal-300 text-caption rounded-control hover:border-charcoal-500 hover:text-charcoal-100 flex h-6 items-center gap-2 border px-3 transition-colors"
              >
                <span>{candidate.name}</span>
                <span className="text-charcoal-500 text-micro">{candidate.exchange}</span>
              </button>
            ))}
          </div>
        </div>
      )}

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
              <div className="bg-charcoal-800 h-7 w-20 rounded-none" />
              <div className="bg-charcoal-800 h-5 w-32 self-end rounded-none" />
              <div className="bg-charcoal-800 h-6 w-24 self-end rounded-none" />
            </div>
            {Array.from({ length: 2 }).map((_, s) => (
              <div key={s} className="border-charcoal-700 rounded-none border">
                <div className="border-charcoal-700 border-b px-3 py-2">
                  <div className="bg-charcoal-800 h-3 w-28 rounded-none" />
                </div>
                <div className="flex flex-col gap-2 px-3 py-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="flex justify-between gap-2">
                      <div className="bg-charcoal-800 h-3 w-20 rounded-none" />
                      <div className="bg-charcoal-800 h-3 w-12 rounded-none" />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : data === null ? (
          // Composed empty state — never instructional copy styled as primary
          // content. The quick-load chips sit on the 24px compact-control ladder.
          <div className="flex flex-col items-center">
            <EmptyState
              icon={Building2}
              headline="Equity overview"
              hint="Screener-grade fundamentals, statements, and ratings for any ticker — US, NSE, or BSE."
              className="pb-3"
            />
            <div className="flex gap-2" data-testid="quick-load-chips">
              {["AAPL", "RELIANCE", "NVDA"].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => void quickLoad(t)}
                  className="border-charcoal-700 text-charcoal-300 text-caption rounded-control hover:border-charcoal-500 hover:text-charcoal-100 flex h-6 items-center border px-3 transition-colors"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Identity row + quote row share ONE baseline; the caption meta
                (sector · 52w · provenance) drops to a second line — no more
                mixed-size text floating mid-row. */}
            <header className="flex flex-col gap-2" data-testid="equity-header">
              <div className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-1">
                <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
                  <h2 className="text-charcoal-100 text-overview">{data.symbol}</h2>
                  {fundamentals?.name != null && (
                    <span className="text-charcoal-400 text-body truncate">
                      {fundamentals.name}
                    </span>
                  )}
                </div>
                {quote !== null && (
                  <div className="flex items-baseline gap-3">
                    <span className="text-charcoal-100 text-overview tabular-nums">
                      {formatPrice(quote.price)} {quote.currency}
                    </span>
                    {quote.change !== null && quote.change_percent !== null && (
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
                  </div>
                )}
              </div>
              <div className="text-caption flex flex-wrap items-center gap-x-4 gap-y-1">
                {fundamentals?.sector != null && (
                  <span className="text-charcoal-400">
                    {fundamentals.sector}
                    {fundamentals.industry != null ? ` · ${fundamentals.industry}` : ""}
                  </span>
                )}
                {fundamentals?.basis != null && (
                  <span
                    className="text-micro text-charcoal-400 border-charcoal-700 rounded-control border px-1 py-px tracking-wide uppercase"
                    title="Accounting basis of the company's exchange-filed results"
                    data-testid="basis-chip"
                  >
                    {fundamentals.basis}
                  </span>
                )}
                {fundamentals != null &&
                  (fundamentals.fifty_two_week_low != null ||
                    fundamentals.fifty_two_week_high != null) && (
                    <span className="text-charcoal-500 tabular-nums">
                      {listedUnderAYear(fundamentals) ? "since listing" : "52w"}{" "}
                      {fmtPriceField(fundamentals.fifty_two_week_low) ?? "—"} –{" "}
                      {fmtPriceField(fundamentals.fifty_two_week_high) ?? "—"}
                    </span>
                  )}
                <SourceBadges quote={quote} fundamentals={fundamentals} />
              </div>
            </header>

            <NarrativeSection loading={narrativeLoading} narrative={narrative} />

            {fundamentals === null ? (
              <section className="border-charcoal-700 rounded-none border">
                <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
                  Fundamentals
                </h3>
                <EmptyState
                  icon={Building2}
                  dense
                  headline="Fundamentals unavailable"
                  hint={
                    data.fundamentalsError ??
                    "The provider returned no fundamentals for this symbol."
                  }
                  className="pt-4"
                />
              </section>
            ) : (
              <section className="border-charcoal-700 rounded-none border">
                <h3 className="text-charcoal-200 border-charcoal-700 text-micro border-b px-3 py-2">
                  Fundamentals
                </h3>
                <div ref={fundamentalsRef}>
                  <DataTable
                    columns={FUNDAMENTAL_COLUMNS}
                    sections={fundamentalSections}
                    rowKey={(row) => row.label}
                    rowClassName={(row) =>
                      row.highlighted ? "ring-1 ring-inset ring-amber-400/70" : undefined
                    }
                    data-testid="fundamentals-table"
                  />
                </div>
              </section>
            )}

            <section className="border-charcoal-700 rounded-none border">
              <h3 className="text-charcoal-200 border-charcoal-700 text-micro flex items-baseline justify-between border-b px-3 py-2">
                Analyst ratings
                {ratings?.as_of != null && (
                  <span
                    className="text-charcoal-500 text-caption"
                    title={new Date(ratings.as_of).toLocaleString()}
                    data-testid="equity-ratings-as-of"
                  >
                    As of {new Date(ratings.as_of).toLocaleString()}
                  </span>
                )}
              </h3>
              {ratings === null ? (
                <EmptyState
                  icon={Star}
                  dense
                  headline="Ratings unavailable"
                  hint="The provider returned no analyst coverage for this symbol."
                  className="pt-4"
                />
              ) : (
                // Metric strip on the table rhythm — micro label over a tabular
                // value per cell, never an inline key:value run-on.
                <div
                  className="divide-charcoal-800 grid grid-cols-2 gap-px @[40rem]:grid-cols-4 @[40rem]:divide-x"
                  data-testid="ratings-strip"
                >
                  <RatingMetric label="Consensus" value={ratings.consensus ?? null} />
                  <RatingMetric
                    label="Target mean"
                    value={fmtPriceField(ratings.target_mean)}
                    numeric
                  />
                  <RatingMetric
                    label="Target range"
                    value={
                      ratings.target_low === null && ratings.target_high === null
                        ? null
                        : `${fmtPriceField(ratings.target_low) ?? "—"} – ${fmtPriceField(ratings.target_high) ?? "—"}`
                    }
                    numeric
                  />
                  <RatingMetric
                    label="SB · B · H · S · SS"
                    value={`${ratings.strong_buy} · ${ratings.buy} · ${ratings.hold} · ${ratings.sell} · ${ratings.strong_sell}`}
                    numeric
                  />
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
