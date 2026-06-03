"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Building2, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SidecarError } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { usePanelContextBus } from "@/store/panel-context";
import type { FinancialStatement, Fundamentals, Quote } from "../../../types/data";
import {
  autocompleteSymbols,
  loadEquityOverview,
  type EquityOverview,
  type SymbolCandidate,
} from "./api";

function formatNumber(value: number | null, fractionDigits = 2): string {
  if (value === null || Number.isNaN(value)) {
    return "—";
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

function formatLargeNumber(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return "—";
  }
  const abs = Math.abs(value);
  if (abs >= 1e12) {
    return `${(value / 1e12).toFixed(2)}T`;
  }
  if (abs >= 1e9) {
    return `${(value / 1e9).toFixed(2)}B`;
  }
  if (abs >= 1e6) {
    return `${(value / 1e6).toFixed(2)}M`;
  }
  return formatNumber(value, 0);
}

function formatPercent(value: number | null): string {
  return value === null || Number.isNaN(value) ? "—" : `${(value * 100).toFixed(2)}%`;
}

function formatMoney(value: number | null, currency: string | null): string {
  if (value === null || Number.isNaN(value)) {
    return "—";
  }
  const n = formatLargeNumber(value);
  return currency ? `${n} ${currency}` : n;
}

type FieldKind = "num" | "pct" | "money" | "large";

interface FieldGroup {
  title: string;
  fields: Array<{ label: string; key: keyof Fundamentals; kind: FieldKind }>;
}

// Screener-grade fundamentals, grouped the way a trader reads a stock page.
// A whole group is hidden when every field in it is null (e.g. ownership for an
// index fund) so the page never shows a wall of dashes.
const FIELD_GROUPS: FieldGroup[] = [
  {
    title: "Valuation",
    fields: [
      { label: "Market cap", key: "market_cap", kind: "money" },
      { label: "P/E", key: "pe_ratio", kind: "num" },
      { label: "Fwd P/E", key: "forward_pe", kind: "num" },
      { label: "PEG", key: "peg_ratio", kind: "num" },
      { label: "P/B", key: "price_to_book", kind: "num" },
      { label: "P/S", key: "price_to_sales", kind: "num" },
      { label: "EV/EBITDA", key: "ev_to_ebitda", kind: "num" },
      { label: "Book value", key: "book_value", kind: "num" },
    ],
  },
  {
    title: "Profitability",
    fields: [
      { label: "ROE", key: "roe", kind: "pct" },
      { label: "ROA", key: "roa", kind: "pct" },
      { label: "Gross margin", key: "gross_margin", kind: "pct" },
      { label: "Oper. margin", key: "operating_margin", kind: "pct" },
      { label: "Net margin", key: "profit_margin", kind: "pct" },
    ],
  },
  {
    title: "Financial health",
    fields: [
      { label: "Debt/Equity", key: "debt_to_equity", kind: "num" },
      { label: "Current ratio", key: "current_ratio", kind: "num" },
      { label: "Quick ratio", key: "quick_ratio", kind: "num" },
      { label: "Free cash flow", key: "free_cash_flow", kind: "money" },
    ],
  },
  {
    title: "Growth & size",
    fields: [
      { label: "Revenue (TTM)", key: "revenue_ttm", kind: "money" },
      { label: "Net income", key: "net_income_ttm", kind: "money" },
      { label: "Revenue growth", key: "revenue_growth", kind: "pct" },
      { label: "Earnings growth", key: "earnings_growth", kind: "pct" },
      { label: "Shares out.", key: "shares_outstanding", kind: "large" },
    ],
  },
  {
    title: "Per share & dividend",
    fields: [
      { label: "EPS", key: "eps", kind: "num" },
      { label: "Div / share", key: "dividend_per_share", kind: "num" },
      { label: "Dividend yield", key: "dividend_yield", kind: "pct" },
      { label: "Beta", key: "beta", kind: "num" },
      { label: "1Y change", key: "fifty_two_week_change", kind: "pct" },
    ],
  },
  {
    title: "Ownership",
    fields: [
      { label: "Insiders", key: "held_percent_insiders", kind: "pct" },
      { label: "Institutions", key: "held_percent_institutions", kind: "pct" },
    ],
  },
];

function fieldValue(fundamentals: Fundamentals, key: keyof Fundamentals): number | null {
  const raw = fundamentals[key];
  return typeof raw === "number" ? raw : null;
}

function formatField(value: number | null, kind: FieldKind, currency: string | null): string {
  switch (kind) {
    case "pct":
      return formatPercent(value);
    case "money":
      return formatMoney(value, currency);
    case "large":
      return formatLargeNumber(value);
    default:
      return formatNumber(value);
  }
}

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
        "border-charcoal-700 text-charcoal-400 inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px] tracking-wide uppercase",
        stale && "border-warning/40 text-warning",
      )}
      title={`Source: ${provider}${freshness ? ` · ${freshness}` : ""}`}
    >
      <span>{provider}</span>
      {freshness && <span className="text-charcoal-500">· {freshness}</span>}
    </span>
  );
}

function StatementTable({
  title,
  statement,
}: {
  title: string;
  statement: FinancialStatement | null;
}) {
  return (
    <section className="border-charcoal-700 rounded-md border">
      <h3 className="text-charcoal-200 border-charcoal-700 border-b px-3 py-2 font-mono text-xs uppercase">
        {title}
      </h3>
      {statement === null ? (
        <p className="text-charcoal-400 px-3 py-2 font-mono text-xs">Unavailable.</p>
      ) : (
        <table className="w-full table-fixed border-collapse">
          <colgroup>
            <col style={{ width: "45%" }} />
            {statement.periods.map((period) => (
              <col key={period} style={{ width: `${55 / statement.periods.length}%` }} />
            ))}
          </colgroup>
          <thead>
            <tr className="text-charcoal-400 border-charcoal-800 border-b text-left font-mono text-[0.6rem] uppercase">
              <th className="px-3 py-1.5 font-medium">Line</th>
              {statement.periods.map((period) => (
                <th key={period} className="px-3 py-1.5 text-right font-medium">
                  {period}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {statement.lines.map((line) => (
              <tr key={line.label} className="border-charcoal-800 border-b font-mono text-xs">
                <td
                  className="text-charcoal-200 px-3 py-1.5 leading-tight break-words"
                  title={line.label}
                >
                  {line.label}
                </td>
                {statement.periods.map((period) => {
                  const raw = line.values[period] ?? null;
                  const formatted = formatLargeNumber(raw);
                  return (
                    <td
                      key={period}
                      className="text-charcoal-100 overflow-hidden px-3 py-1.5 text-right"
                      title={raw === null ? formatted : `${formatted} (${raw})`}
                    >
                      <span className="block truncate">{formatted}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
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

  // --- autocomplete ---------------------------------------------------------
  const [candidates, setCandidates] = useState<SymbolCandidate[]>([]);
  const [acOpen, setAcOpen] = useState(false);
  const [acIndex, setAcIndex] = useState(-1);
  const acSeqRef = useRef(0);

  // --- panel-context bus ----------------------------------------------------
  const publishPanelContext = usePanelContextBus((s) => s.publish);
  const unregisterPanelContext = usePanelContextBus((s) => s.unregisterSource);

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
    setAcOpen(false);
    try {
      const overview = await loadEquityOverview(symbol);
      if (overview.allFailed) {
        setData(null);
        setError(`No data available for ${symbol}`);
      } else {
        setData(overview);
      }
    } catch (err) {
      setData(null);
      setError(err instanceof SidecarError ? err.message : `Failed to load ${symbol}`);
    } finally {
      setLoading(false);
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

  const quote = data?.quote ?? null;
  const fundamentals = data?.fundamentals ?? null;
  const ratings = data?.ratings ?? null;
  const currency = fundamentals?.currency ?? quote?.currency ?? null;

  // Which grouped sections have at least one populated field (hide empty groups).
  const populatedGroups = useMemo(() => {
    if (fundamentals === null) {
      return [];
    }
    return FIELD_GROUPS.map((group) => ({
      group,
      fields: group.fields.filter((f) => fieldValue(fundamentals, f.key) !== null),
    })).filter((g) => g.fields.length > 0);
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
            className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-500 h-8 w-full rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
          />
          {acOpen && candidates.length > 0 && (
            <ul className="border-charcoal-700 bg-charcoal-875 absolute top-full right-0 left-0 z-20 mt-1 max-h-64 overflow-y-auto rounded-md border py-1 shadow-lg">
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
                      "flex w-full items-center justify-between gap-2 px-2.5 py-1.5 text-left font-mono",
                      idx === acIndex ? "bg-charcoal-800" : "hover:bg-charcoal-800/60",
                    )}
                  >
                    <span className="flex min-w-0 items-baseline gap-2">
                      <span className="text-charcoal-100 shrink-0 text-xs font-semibold">
                        {candidate.symbol}
                      </span>
                      <span className="text-charcoal-400 truncate text-[11px]">
                        {candidate.name}
                      </span>
                    </span>
                    <span className="text-charcoal-500 shrink-0 text-[10px] tracking-wide uppercase">
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
          <p className="text-negative font-mono text-xs">{error}</p>
          <Button type="button" size="sm" variant="ghost" onClick={() => void handleRetry()}>
            Retry
          </Button>
        </div>
      )}

      <div className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto p-3">
        {loading ? (
          <div className="flex animate-pulse flex-col gap-4">
            <div className="flex flex-wrap gap-3">
              <div className="bg-charcoal-800 h-7 w-20 rounded" />
              <div className="bg-charcoal-800 h-5 w-32 self-end rounded" />
              <div className="bg-charcoal-800 h-6 w-24 self-end rounded" />
            </div>
            {Array.from({ length: 2 }).map((_, s) => (
              <div key={s} className="border-charcoal-700 rounded-md border">
                <div className="border-charcoal-700 border-b px-3 py-2">
                  <div className="bg-charcoal-800 h-3 w-28 rounded" />
                </div>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 px-3 py-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="flex justify-between gap-2">
                      <div className="bg-charcoal-800 h-3 w-20 rounded" />
                      <div className="bg-charcoal-800 h-3 w-12 rounded" />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : data === null ? (
          <div className="flex flex-col items-center gap-4 pt-12 text-center">
            <Building2 className="text-charcoal-600 size-8" />
            <p className="text-charcoal-300 font-mono text-sm">
              Screener-grade fundamentals, statements, and ratings for any ticker — US, NSE, or BSE.
            </p>
            <div className="flex gap-2">
              {["AAPL", "RELIANCE", "NVDA"].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => void quickLoad(t)}
                  className="border-charcoal-700 bg-charcoal-800 text-charcoal-300 rounded-md border px-3 py-1.5 font-mono text-xs transition-colors hover:border-amber-500 hover:text-amber-300"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <h2 className="text-charcoal-100 font-serif text-2xl">{data.symbol}</h2>
              {fundamentals?.name != null && (
                <span className="text-charcoal-400 font-mono text-sm">{fundamentals.name}</span>
              )}
              {quote !== null && (
                <span className="text-charcoal-100 font-mono text-lg">
                  {formatNumber(quote.price)} {quote.currency}
                </span>
              )}
              {quote !== null && (
                <span
                  className={cn(
                    "font-mono text-sm whitespace-nowrap",
                    quote.change_percent >= 0 ? "text-positive" : "text-negative",
                  )}
                >
                  {quote.change >= 0 ? "+" : ""}
                  {formatNumber(quote.change)} ({quote.change_percent >= 0 ? "+" : ""}
                  {quote.change_percent.toFixed(2)}%)
                </span>
              )}
              <ProvenanceBadge quote={quote} fundamentals={fundamentals} />
              {fundamentals?.sector != null && (
                <span className="text-charcoal-400 font-mono text-xs">
                  {fundamentals.sector}
                  {fundamentals.industry != null ? ` · ${fundamentals.industry}` : ""}
                </span>
              )}
              {fundamentals != null &&
                (fundamentals.fifty_two_week_low != null ||
                  fundamentals.fifty_two_week_high != null) && (
                  <span className="text-charcoal-500 font-mono text-xs">
                    52w {formatNumber(fundamentals.fifty_two_week_low)} –{" "}
                    {formatNumber(fundamentals.fifty_two_week_high)}
                  </span>
                )}
            </header>

            {fundamentals === null ? (
              <section className="border-charcoal-700 rounded-md border">
                <h3 className="text-charcoal-200 border-charcoal-700 border-b px-3 py-2 font-mono text-xs uppercase">
                  Fundamentals
                </h3>
                <p className="text-charcoal-400 px-3 py-2 font-mono text-xs">Unavailable.</p>
              </section>
            ) : populatedGroups.length === 0 ? (
              <section className="border-charcoal-700 rounded-md border">
                <h3 className="text-charcoal-200 border-charcoal-700 border-b px-3 py-2 font-mono text-xs uppercase">
                  Fundamentals
                </h3>
                <p className="text-charcoal-400 px-3 py-2 font-mono text-xs">
                  Limited fundamentals from the keyless source for this symbol. Add an EODHD key in
                  Settings → AI Providers for full NSE/BSE depth.
                </p>
              </section>
            ) : (
              populatedGroups.map(({ group, fields }) => (
                <section
                  key={group.title}
                  className="border-charcoal-700 @container rounded-md border"
                >
                  <h3 className="text-charcoal-200 border-charcoal-700 border-b px-3 py-2 font-mono text-xs uppercase">
                    {group.title}
                  </h3>
                  <dl className="grid grid-cols-2 gap-x-6 gap-y-1 px-3 py-2 @[420px]:grid-cols-3">
                    {fields.map(({ label, key, kind }) => (
                      <div
                        key={label}
                        className="flex min-w-0 justify-between gap-2 font-mono text-xs"
                      >
                        <dt className="text-charcoal-400 truncate">{label}</dt>
                        <dd className="text-charcoal-100 flex-shrink-0">
                          {formatField(fieldValue(fundamentals, key), kind, currency)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ))
            )}

            <section className="border-charcoal-700 rounded-md border">
              <h3 className="text-charcoal-200 border-charcoal-700 border-b px-3 py-2 font-mono text-xs uppercase">
                Analyst ratings
              </h3>
              {ratings === null ? (
                <p className="text-charcoal-400 px-3 py-2 font-mono text-xs">Unavailable.</p>
              ) : (
                <div className="flex flex-wrap gap-x-6 gap-y-1 px-3 py-2 font-mono text-xs">
                  <span className="text-charcoal-200">
                    Consensus: <span className="text-amber-400">{ratings.consensus ?? "—"}</span>
                  </span>
                  <span className="text-charcoal-200">
                    Target mean:{" "}
                    <span className="text-charcoal-100">{formatNumber(ratings.target_mean)}</span>
                  </span>
                  <span className="text-charcoal-200">
                    Range:{" "}
                    <span className="text-charcoal-100">
                      {formatNumber(ratings.target_low)} – {formatNumber(ratings.target_high)}
                    </span>
                  </span>
                  <span className="text-charcoal-400 flex flex-wrap gap-x-1.5">
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
