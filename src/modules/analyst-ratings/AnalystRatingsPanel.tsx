"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";

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
 * Errors land inline per-tab so a failure on one slice does not blank
 * the others.
 */
export function AnalystRatingsPanel() {
  const [draft, setDraft] = useState("");
  const [symbol, setSymbol] = useState<string | null>(null);
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
        <Button type="submit" size="sm" variant="outline">
          <Search />
          Load
        </Button>
      </form>

      {symbol === null ? (
        <p className="text-charcoal-400 p-3 font-mono text-xs">
          Enter a symbol to load rating history, price targets, and individual analyst tracks.
        </p>
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

          {tabError && (
            <p className="text-negative border-charcoal-700 border-b px-3 py-2 font-mono text-xs">
              {tabError}
            </p>
          )}

          <div className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto p-3">
            <header className="text-charcoal-100 mb-3 font-mono text-sm">
              {symbol}
              <span className="text-charcoal-500 ml-2 text-xs">
                {tab === "history" && history !== null && `${history.length} rating changes`}
                {tab === "price-targets" && targets !== null && `${targets.length} target updates`}
                {tab === "individual" && individual !== null && `${individual.length} analysts`}
              </span>
            </header>

            {tab === "history" && <RatingsHistoryTable history={history ?? []} />}
            {tab === "price-targets" && <PriceTargetTimeline history={targets ?? []} />}
            {tab === "individual" && <IndividualAnalystTable analysts={individual ?? []} />}
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
        "rounded-t-md px-3 py-1 font-mono text-xs",
        active
          ? "bg-charcoal-800 border-charcoal-700 border-x border-t text-amber-400"
          : "text-charcoal-400 hover:text-charcoal-200",
      )}
      aria-pressed={active}
    >
      {label}
    </button>
  );
}
