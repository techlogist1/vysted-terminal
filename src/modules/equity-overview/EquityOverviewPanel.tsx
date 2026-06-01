"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Building2, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SidecarError } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { usePanelContextBus } from "@/store/panel-context";
import type { FinancialStatement, Fundamentals } from "../../../types/data";
import { loadEquityOverview, type EquityOverview } from "./api";

function formatNumber(value: number | null, fractionDigits = 2): string {
  if (value === null) {
    return "—";
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

function formatLargeNumber(value: number | null): string {
  if (value === null) {
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
  return value === null ? "—" : `${(value * 100).toFixed(2)}%`;
}

const RATIO_FIELDS: Array<{ label: string; key: keyof Fundamentals; kind: "num" | "pct" }> = [
  { label: "Market cap", key: "market_cap", kind: "num" },
  { label: "P/E", key: "pe_ratio", kind: "num" },
  { label: "Forward P/E", key: "forward_pe", kind: "num" },
  { label: "PEG", key: "peg_ratio", kind: "num" },
  { label: "Price/Book", key: "price_to_book", kind: "num" },
  { label: "Dividend yield", key: "dividend_yield", kind: "pct" },
  { label: "EPS", key: "eps", kind: "num" },
  { label: "Beta", key: "beta", kind: "num" },
  { label: "52w high", key: "fifty_two_week_high", kind: "num" },
  { label: "52w low", key: "fifty_two_week_low", kind: "num" },
];

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
          {/* Explicit column widths via <colgroup> — LINE gets 45 %, the period
              columns share the remaining 55 % evenly so the table always fits
              the panel width regardless of how long a line label is.
              `table-fixed` plus these widths means the line text wraps inside
              its cell rather than pushing the whole table past the container. */}
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
 * Equity Overview panel — a symbol input that, on submit, fetches and lays out
 * fundamentals, the three financial statements, analyst ratings, and a live
 * quote in one view. Sections that fail to load degrade individually; an error
 * banner shows only when every section fails.
 */
export function EquityOverviewPanel() {
  const [draft, setDraft] = useState("");
  const [data, setData] = useState<EquityOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Tracks the last successfully submitted symbol so Retry can replay it.
  const submittedSymbolRef = useRef<string | null>(null);

  // --- panel-context bus: publish symbol + which sections loaded ----------
  const publishPanelContext = usePanelContextBus((s) => s.publish);
  const unregisterPanelContext = usePanelContextBus((s) => s.unregisterSource);

  // The publisher's payload describes which sections of the overview
  // currently have data — the chat sidebar can use this to phrase questions
  // like "fundamentals + income statement loaded for AAPL". Computed
  // synchronously from `data` so the effect deps stay primitive-ish.
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
      payload: {
        ticker: currentTicker,
        loadedSections,
      },
      emittedAt: Date.now(),
    });
    // Depend on the primitive key (loadedKey) rather than the array so a
    // re-render that produces the same loaded section set is a no-op.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [publishPanelContext, currentTicker, loadedKey]);

  useEffect(() => {
    return () => {
      unregisterPanelContext("equity");
    };
  }, [unregisterPanelContext]);

  const doLoad = async (symbol: string) => {
    submittedSymbolRef.current = symbol;
    setLoading(true);
    setError(null);
    // Clear immediately so stale data from a previous symbol does not linger.
    setData(null);
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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const symbol = draft.trim().toUpperCase();
    if (symbol === "") {
      return;
    }
    await doLoad(symbol);
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

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <form
        onSubmit={handleSubmit}
        className="border-charcoal-700 flex items-center gap-2 border-b p-3"
      >
        <input
          aria-label="Symbol"
          placeholder="Symbol (e.g. AAPL)"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-400 h-8 flex-1 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
        />
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
            {/* Header skeleton */}
            <div className="flex flex-wrap gap-3">
              <div className="bg-charcoal-800 h-7 w-20 rounded" />
              <div className="bg-charcoal-800 h-5 w-32 self-end rounded" />
              <div className="bg-charcoal-800 h-6 w-24 self-end rounded" />
            </div>
            {/* Valuation ratios skeleton */}
            <div className="border-charcoal-700 rounded-md border">
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
            {/* Analyst ratings skeleton */}
            <div className="border-charcoal-700 rounded-md border">
              <div className="border-charcoal-700 border-b px-3 py-2">
                <div className="bg-charcoal-800 h-3 w-24 rounded" />
              </div>
              <div className="flex flex-wrap gap-x-6 gap-y-2 px-3 py-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="bg-charcoal-800 h-3 w-24 rounded" />
                ))}
              </div>
            </div>
          </div>
        ) : data === null ? (
          <div className="flex flex-col items-center gap-4 pt-12 text-center">
            <Building2 className="text-charcoal-600 size-8" />
            <p className="text-charcoal-300 font-mono text-sm">
              Fundamental data, statements, and analyst ratings for any ticker.
            </p>
            <div className="flex gap-2">
              {["AAPL", "MSFT", "NVDA"].map((t) => (
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
              {fundamentals?.sector != null && (
                <span className="text-charcoal-400 font-mono text-xs">
                  {fundamentals.sector}
                  {fundamentals.industry != null ? ` · ${fundamentals.industry}` : ""}
                </span>
              )}
            </header>

            <section className="border-charcoal-700 @container rounded-md border">
              <h3 className="text-charcoal-200 border-charcoal-700 border-b px-3 py-2 font-mono text-xs uppercase">
                Valuation ratios
              </h3>
              {fundamentals === null ? (
                <p className="text-charcoal-400 px-3 py-2 font-mono text-xs">Unavailable.</p>
              ) : (
                <dl className="grid grid-cols-2 gap-x-6 gap-y-1 px-3 py-2 @[420px]:grid-cols-3">
                  {RATIO_FIELDS.map(({ label, key, kind }) => {
                    const raw = fundamentals[key];
                    const value = typeof raw === "number" ? raw : null;
                    return (
                      <div
                        key={label}
                        className="flex min-w-0 justify-between gap-2 font-mono text-xs"
                      >
                        <dt className="text-charcoal-400 truncate">{label}</dt>
                        <dd className="text-charcoal-100 flex-shrink-0">
                          {kind === "pct"
                            ? formatPercent(value)
                            : key === "market_cap"
                              ? formatLargeNumber(value)
                              : formatNumber(value)}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
              )}
            </section>

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
