"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAnalystRatingsStore } from "@/store/analyst-ratings";

import { IndividualAnalystTable } from "./IndividualAnalystTable";
import { PriceTargetTimeline } from "./PriceTargetTimeline";
import { RatingsHistoryTable } from "./RatingsHistoryTable";

type Tab = "history" | "price-targets" | "individual";

/**
 * Analyst Ratings panel — Phase 6 (Teammate E).
 *
 * Symbol input + three tabs:
 * - History — sortable table of rating-change events.
 * - Price Targets — line chart of consensus targets over time.
 * - Individual — per-firm currently-active forecasts.
 *
 * Each tab fetches via the store; switching tabs is instant on cache hit.
 * A slice failure with cached data keeps the table and shows an inline
 * banner; with NO data it renders the composed error EmptyState (with a
 * Retry CTA) — an error is never disguised as an empty result, and the
 * fetch window is a table-shaped skeleton, never a pulsing prose line.
 */
const DEFAULT_SYMBOL = "AAPL";

/** Table-shaped pulse skeleton for the fetch window. */
function TabSkeleton() {
  return (
    <div className="flex animate-pulse flex-col" data-testid="analyst-tab-skeleton">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="border-charcoal-800 flex gap-6 border-b px-3 py-2">
          <div className="bg-charcoal-800 h-3 w-1/6 rounded-none" />
          <div className="bg-charcoal-800 h-3 w-1/4 rounded-none" />
          <div className="bg-charcoal-800 h-3 w-1/5 rounded-none" />
          <div className="bg-charcoal-800 ml-auto h-3 w-1/6 rounded-none" />
        </div>
      ))}
    </div>
  );
}

export function AnalystRatingsPanel() {
  const [draft, setDraft] = useState(DEFAULT_SYMBOL);
  const [symbol, setSymbol] = useState<string | null>(DEFAULT_SYMBOL);
  const [tab, setTab] = useState<Tab>("history");

  const histories = useAnalystRatingsStore((s) => s.histories);
  const historyErrors = useAnalystRatingsStore((s) => s.historyErrors);
  const priceTargets = useAnalystRatingsStore((s) => s.priceTargets);
  const priceTargetErrors = useAnalystRatingsStore((s) => s.priceTargetErrors);
  const individuals = useAnalystRatingsStore((s) => s.individuals);
  const individualErrors = useAnalystRatingsStore((s) => s.individualErrors);
  const getHistory = useAnalystRatingsStore((s) => s.getHistory);
  const getPriceTargets = useAnalystRatingsStore((s) => s.getPriceTargets);
  const getIndividual = useAnalystRatingsStore((s) => s.getIndividual);

  useEffect(() => {
    if (!symbol) return;
    void getHistory(symbol);
    void getPriceTargets(symbol);
    void getIndividual(symbol);
  }, [symbol, getHistory, getPriceTargets, getIndividual]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const candidate = draft.trim().toUpperCase();
    if (candidate) {
      setSymbol(candidate);
    }
  };

  const history = symbol ? (histories[symbol]?.history ?? null) : null;
  const targets = symbol ? (priceTargets[symbol]?.history ?? null) : null;
  const individual = symbol ? (individuals[symbol]?.analysts ?? null) : null;

  const historyError = symbol ? historyErrors[symbol] : null;
  const priceTargetError = symbol ? priceTargetErrors[symbol] : null;
  const individualError = symbol ? individualErrors[symbol] : null;

  const tabError =
    tab === "history" ? historyError : tab === "price-targets" ? priceTargetError : individualError;
  const tabData = tab === "history" ? history : tab === "price-targets" ? targets : individual;

  // A slice is "loading" while its symbol is set, the data hasn't arrived, and
  // no error has landed — gate the child empty-states behind this so the fetch
  // window isn't mislabelled as an empty result.
  const tabLoading = symbol !== null && tabData === null && !tabError;

  // Re-fire the active tab's fetch (the store re-fetches on a cache miss).
  const retryTab = () => {
    if (!symbol) return;
    if (tab === "history") void getHistory(symbol);
    else if (tab === "price-targets") void getPriceTargets(symbol);
    else void getIndividual(symbol);
  };

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
          className="bg-charcoal-850 text-charcoal-100 placeholder:text-charcoal-500 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 flex-1 border px-3 outline-none"
        />
        <Button type="submit" size="sm" variant="outline">
          <Search />
          Load
        </Button>
      </form>

      {symbol === null ? (
        <EmptyState
          icon={Search}
          headline="No symbol loaded"
          hint="Enter a ticker above to load rating history, price targets, and individual analyst tracks."
        />
      ) : (
        <>
          <nav
            className="border-charcoal-700 flex gap-2 border-b px-3 pt-2"
            aria-label="Analyst ratings tabs"
          >
            <TabButton
              label="History"
              active={tab === "history"}
              onSelect={() => setTab("history")}
            />
            <TabButton
              label="Price Targets"
              active={tab === "price-targets"}
              onSelect={() => setTab("price-targets")}
            />
            <TabButton
              label="Individual"
              active={tab === "individual"}
              onSelect={() => setTab("individual")}
            />
          </nav>

          {/* A failed slice that still has cached data keeps the table below
              and flags the staleness inline; the no-data error case renders
              the composed error state in the body instead. */}
          {tabError && tabData !== null && (
            <div className="border-charcoal-700 flex items-center justify-between gap-3 border-b px-3 py-2">
              <p className="text-negative text-caption min-w-0 truncate" title={tabError}>
                {tabError}
              </p>
              <Button type="button" size="xs" variant="ghost" onClick={retryTab}>
                Retry
              </Button>
            </div>
          )}

          <div className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto p-3">
            <header className="text-charcoal-100 text-body mb-3">
              {symbol}
              <span className="text-charcoal-500 text-caption ml-2">
                {!tabLoading &&
                  tab === "history" &&
                  history !== null &&
                  `${history.length} rating changes`}
                {!tabLoading &&
                  tab === "price-targets" &&
                  targets !== null &&
                  `${targets.length} target updates`}
                {!tabLoading &&
                  tab === "individual" &&
                  individual !== null &&
                  `${individual.length} analysts`}
              </span>
            </header>

            {tabLoading ? (
              <TabSkeleton />
            ) : tabError && tabData === null ? (
              <EmptyState
                icon={Search}
                headline={`Could not load ${symbol}`}
                hint={tabError}
                cta={{ label: "Retry", onClick: retryTab, primary: true }}
              />
            ) : (
              <>
                {tab === "history" && <RatingsHistoryTable history={history ?? []} />}
                {tab === "price-targets" && <PriceTargetTimeline history={targets ?? []} />}
                {tab === "individual" && <IndividualAnalystTable analysts={individual ?? []} />}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function TabButton({
  label,
  active,
  onSelect,
}: {
  label: string;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "text-caption rounded-control flex h-8 items-center px-3",
        active
          ? "bg-charcoal-800 border-charcoal-700 text-charcoal-200 -mb-px border-x border-t"
          : "text-charcoal-400 hover:text-charcoal-200",
      )}
      aria-pressed={active}
    >
      {label}
    </button>
  );
}
