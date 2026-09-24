"use client";

/**
 * SecFilingsPanel — top-level panel for the SEC filings reader.
 *
 * Layout: symbol field + form-type filter on the left rail; main pane
 * toggles between a filings list table and the FilingViewer for the
 * selected filing; an "Insider" tab shows the InsiderTradingTable for
 * the same issuer.
 *
 * Owns the local view state (active tab, selected filing) and reads /
 * writes the data through `useSecStore`.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useRetryOnSidecarReady } from "@/lib/use-sidecar-retry";
import { selectFilings, useSecStore } from "@/store/sec";

import type { Filing, FilingFormType } from "../../../types/sec";

import { FilingsListTable } from "./FilingsListTable";
import { FilingViewer } from "./FilingViewer";
import { InsiderTradingTable } from "./InsiderTradingTable";

type Tab = "filings" | "insider";

const FORM_FILTER_OPTIONS: Array<{ value: FilingFormType | "all"; label: string }> = [
  { value: "all", label: "All forms" },
  { value: "10-K", label: "10-K" },
  { value: "10-Q", label: "10-Q" },
  { value: "8-K", label: "8-K" },
  { value: "DEF 14A", label: "DEF 14A" },
];

export function SecFilingsPanel() {
  const activeIdentifier = useSecStore((s) => s.activeIdentifier);
  const filingsByIdentifier = useSecStore((s) => s.filingsByIdentifier);
  const setActiveIdentifier = useSecStore((s) => s.setActiveIdentifier);
  const loadFilings = useSecStore((s) => s.loadFilings);
  const filingsStatus = useSecStore((s) => s.filingsStatus);
  const filingsError = useSecStore((s) => s.filingsError);
  const activeAccession = useSecStore((s) => s.activeAccession);
  const setActiveAccession = useSecStore((s) => s.setActiveAccession);
  const searchResults = useSecStore((s) => s.searchResults);
  const searchCompanies = useSecStore((s) => s.searchCompanies);
  const clearSearch = useSecStore((s) => s.clearSearch);

  const [draftSymbol, setDraftSymbol] = useState("AAPL");
  const [formFilter, setFormFilter] = useState<FilingFormType | "all">("all");
  const [tab, setTab] = useState<Tab>("filings");

  // --- symbol-field autocomplete (R15-UI-032) --------------------------------
  const [acOpen, setAcOpen] = useState(false);
  const acSeqRef = useRef(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Once the user picks a symbol / form, the auto-retry default loader goes
  // inert so it never fights an explicit choice (even on a reconnect re-fire
  // after a failed default load, where `activeIdentifier` may already be set).
  const userInteractedRef = useRef(false);

  // Initial load — default symbol = AAPL so populated-state screenshots
  // capture real data on first mount. Auto-retries on a cold-boot sidecar bind
  // (and re-arms on reconnect) so a panel mounted before the sidecar was ready
  // self-heals. `loadFilings` swallows its error into store state — re-throw the
  // kept original error so the hook retries only a not-ready engine.
  const loadDefault = useCallback(async () => {
    if (userInteractedRef.current) {
      return;
    }
    setActiveIdentifier("AAPL");
    await loadFilings("AAPL", undefined);
    if (useSecStore.getState().filingsStatus === "error") {
      throw useSecStore.getState().filingsCause;
    }
  }, [loadFilings, setActiveIdentifier]);
  useRetryOnSidecarReady(loadDefault, []);

  const filings = useMemo(() => {
    void filingsByIdentifier; // subscribe
    return selectFilings(activeIdentifier, formFilter === "all" ? undefined : formFilter);
  }, [filingsByIdentifier, activeIdentifier, formFilter]);

  const submitSymbol = useCallback(
    (event?: React.FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      const symbol = draftSymbol.trim();
      if (!symbol) return;
      userInteractedRef.current = true;
      setActiveIdentifier(symbol);
      setActiveAccession(null);
      void loadFilings(symbol, formFilter === "all" ? undefined : formFilter);
    },
    [draftSymbol, formFilter, loadFilings, setActiveIdentifier, setActiveAccession],
  );

  // Debounced company-name autocomplete — mirrors the EquityOverviewPanel
  // pattern: a sequence id discards an out-of-order response, and the
  // dropdown only (re)opens while the input still owns focus.
  useEffect(() => {
    const q = draftSymbol.trim();
    const seq = ++acSeqRef.current;
    const handle = setTimeout(() => {
      if (seq !== acSeqRef.current) return;
      if (q.length < 1) {
        clearSearch();
        setAcOpen(false);
        return;
      }
      void searchCompanies(q).then(() => {
        if (seq !== acSeqRef.current) return;
        setAcOpen(document.activeElement === inputRef.current);
      });
    }, 200);
    return () => clearTimeout(handle);
  }, [draftSymbol, searchCompanies, clearSearch]);

  const pickCompany = useCallback(
    (row: { cik: string; name: string; ticker: string | null }) => {
      const symbol = row.ticker ?? row.cik;
      setDraftSymbol(symbol);
      setAcOpen(false);
      clearSearch();
      userInteractedRef.current = true;
      setActiveIdentifier(symbol);
      setActiveAccession(null);
      void loadFilings(symbol, formFilter === "all" ? undefined : formFilter);
    },
    [formFilter, loadFilings, setActiveIdentifier, setActiveAccession, clearSearch],
  );

  const onPickForm = useCallback(
    (value: FilingFormType | "all") => {
      userInteractedRef.current = true;
      setFormFilter(value);
      if (activeIdentifier) {
        void loadFilings(activeIdentifier, value === "all" ? undefined : value);
      }
    },
    [activeIdentifier, loadFilings],
  );

  const onOpenFiling = useCallback(
    (filing: Filing) => {
      setActiveAccession(filing.accession);
      setTab("filings");
    },
    [setActiveAccession],
  );

  const onCloseViewer = useCallback(() => {
    setActiveAccession(null);
  }, [setActiveAccession]);

  const hasOpenFiling = activeAccession !== null;

  return (
    <div
      data-testid="sec-filings-panel"
      className="bg-charcoal-900 text-charcoal-100 text-caption flex h-full w-full flex-col"
    >
      <header className="border-charcoal-700 flex flex-wrap items-end gap-2 border-b px-3 py-2">
        <form onSubmit={submitSymbol} className="flex items-end gap-2">
          <label className="relative flex flex-col gap-1">
            <span className="text-charcoal-500 text-micro">Symbol / CIK</span>
            <input
              ref={inputRef}
              type="text"
              value={draftSymbol}
              onChange={(e) => setDraftSymbol(e.target.value)}
              onFocus={() => setAcOpen(searchResults.length > 0)}
              onBlur={() => setTimeout(() => setAcOpen(false), 120)}
              className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 w-32 border px-3 uppercase outline-none"
              placeholder="AAPL"
              autoComplete="off"
              data-testid="sec-symbol-input"
            />
            {acOpen && searchResults.length > 0 && (
              <ul
                role="listbox"
                data-testid="sec-symbol-suggestions"
                className="border-charcoal-700 bg-charcoal-900 absolute top-full left-0 z-20 mt-1 max-h-56 w-64 overflow-y-auto border shadow-lg"
              >
                {searchResults.map((row) => (
                  <li key={row.cik}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={false}
                      // A blur fires before the click otherwise discards it —
                      // onMouseDown beats onBlur in the event order.
                      onMouseDown={(e) => {
                        e.preventDefault();
                        pickCompany(row);
                      }}
                      className="hover:bg-charcoal-800 text-caption flex w-full flex-col items-start gap-0.5 px-2 py-1.5 text-left normal-case"
                    >
                      <span className="text-charcoal-100">{row.name}</span>
                      <span className="text-charcoal-500 text-micro">{row.ticker ?? row.cik}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </label>
          <Button size="sm" variant="outline" type="submit" data-testid="sec-symbol-submit">
            Load
          </Button>
        </form>

        <label className="flex flex-col gap-1">
          <span className="text-charcoal-500 text-micro">Form</span>
          <select
            value={formFilter}
            onChange={(e) => onPickForm(e.target.value as FilingFormType | "all")}
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 border px-3 outline-none"
            data-testid="sec-form-filter"
          >
            {FORM_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <nav className="ml-auto flex items-center gap-1" role="tablist">
          <TabButton value="filings" active={tab === "filings"} onClick={() => setTab("filings")}>
            Filings
          </TabButton>
          <TabButton value="insider" active={tab === "insider"} onClick={() => setTab("insider")}>
            Insider
          </TabButton>
        </nav>

        <span className="text-charcoal-400 text-micro ml-2">
          {filings.company_name || activeIdentifier || ""}
          {filings.filings.length > 0 && <> · {filings.filings.length} filings</>}
        </span>
      </header>

      {filingsError && (
        <div
          className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2"
          data-testid="sec-filings-error"
        >
          <span className="text-negative text-caption">
            Could not load filings — {filingsError}
          </span>
          <Button
            size="xs"
            variant="ghost"
            className="text-charcoal-300 hover:text-charcoal-100 shrink-0"
            onClick={() =>
              activeIdentifier &&
              void loadFilings(activeIdentifier, formFilter === "all" ? undefined : formFilter)
            }
            disabled={!activeIdentifier}
          >
            Retry
          </Button>
        </div>
      )}
      {filingsStatus === "loading" && filings.filings.length === 0 && (
        // Row-shaped pulse skeleton for the filings fetch window — never a bare
        // prose line standing in for the table.
        <div className="flex animate-pulse flex-col px-3 py-2" data-testid="sec-filings-skeleton">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="border-charcoal-800 flex gap-6 border-b px-3 py-2">
              <div className="bg-charcoal-800 h-3 w-16 rounded-none" />
              <div className="bg-charcoal-800 h-3 w-1/3 rounded-none" />
              <div className="bg-charcoal-800 ml-auto h-3 w-24 rounded-none" />
            </div>
          ))}
        </div>
      )}

      <div className="min-h-0 flex-1">
        {tab === "filings" && !hasOpenFiling && (
          <FilingsListTable
            filings={filings.filings}
            selectedAccession={activeAccession}
            onSelect={onOpenFiling}
          />
        )}
        {tab === "filings" && hasOpenFiling && (
          <FilingViewer
            key={activeAccession ?? "empty"}
            accession={activeAccession}
            identifier={activeIdentifier}
            onClose={onCloseViewer}
          />
        )}
        {tab === "insider" && <InsiderTradingTable identifier={activeIdentifier} />}
      </div>
    </div>
  );
}

interface TabButtonProps {
  value: Tab;
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

function TabButton({ value, active, onClick, children }: TabButtonProps) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      data-testid={`sec-tab-${value}`}
      onClick={onClick}
      className={cn(
        "rounded-control text-caption px-2 py-1",
        active ? "bg-charcoal-700 text-lume" : "text-charcoal-300 hover:bg-charcoal-800",
      )}
    >
      {children}
    </button>
  );
}
