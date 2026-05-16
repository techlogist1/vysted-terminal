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

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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

  const [draftSymbol, setDraftSymbol] = useState("AAPL");
  const [formFilter, setFormFilter] = useState<FilingFormType | "all">("all");
  const [tab, setTab] = useState<Tab>("filings");

  // Initial load — default symbol = AAPL so populated-state screenshots
  // capture real data on first mount.
  useEffect(() => {
    if (!activeIdentifier) {
      setActiveIdentifier("AAPL");
      void loadFilings("AAPL", undefined);
    }
    // Intentional: run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filings = useMemo(() => {
    void filingsByIdentifier; // subscribe
    return selectFilings(activeIdentifier, formFilter === "all" ? undefined : formFilter);
  }, [filingsByIdentifier, activeIdentifier, formFilter]);

  const submitSymbol = useCallback(
    (event?: React.FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      const symbol = draftSymbol.trim();
      if (!symbol) return;
      setActiveIdentifier(symbol);
      setActiveAccession(null);
      void loadFilings(symbol, formFilter === "all" ? undefined : formFilter);
    },
    [draftSymbol, formFilter, loadFilings, setActiveIdentifier, setActiveAccession],
  );

  const onPickForm = useCallback(
    (value: FilingFormType | "all") => {
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
      className="bg-charcoal-900 text-charcoal-100 flex h-full w-full flex-col text-xs"
    >
      <header className="border-charcoal-700 flex flex-wrap items-end gap-2 border-b px-3 py-2">
        <form onSubmit={submitSymbol} className="flex items-end gap-2">
          <label className="flex flex-col gap-0.5">
            <span className="text-charcoal-400 text-[10px] uppercase">Symbol / CIK</span>
            <input
              type="text"
              value={draftSymbol}
              onChange={(e) => setDraftSymbol(e.target.value)}
              className="bg-charcoal-800 text-charcoal-100 border-charcoal-700 w-32 rounded-md border px-2 py-1 font-mono text-xs uppercase"
              placeholder="AAPL"
              data-testid="sec-symbol-input"
            />
          </label>
          <Button size="xs" variant="outline" type="submit" data-testid="sec-symbol-submit">
            Load
          </Button>
        </form>

        <label className="flex flex-col gap-0.5">
          <span className="text-charcoal-400 text-[10px] uppercase">Form</span>
          <select
            value={formFilter}
            onChange={(e) => onPickForm(e.target.value as FilingFormType | "all")}
            className="bg-charcoal-800 text-charcoal-100 border-charcoal-700 rounded-md border px-2 py-1 text-xs"
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
          <TabButton
            value="filings"
            active={tab === "filings"}
            onClick={() => setTab("filings")}
          >
            Filings
          </TabButton>
          <TabButton
            value="insider"
            active={tab === "insider"}
            onClick={() => setTab("insider")}
          >
            Insider
          </TabButton>
        </nav>

        <span className="text-charcoal-400 ml-2 text-[10px]">
          {filings.company_name || activeIdentifier || ""}
          {filings.filings.length > 0 && (
            <> · {filings.filings.length} filings</>
          )}
        </span>
      </header>

      {filingsError && (
        <p className="px-3 py-2 text-[11px] text-red-400" data-testid="sec-filings-error">
          {filingsError}
        </p>
      )}
      {filingsStatus === "loading" && filings.filings.length === 0 && (
        <p className="text-charcoal-400 px-3 py-2 text-xs">Loading filings…</p>
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
            accession={activeAccession}
            identifier={activeIdentifier}
            onClose={onCloseViewer}
          />
        )}
        {tab === "insider" && (
          <InsiderTradingTable identifier={activeIdentifier} />
        )}
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
        "rounded-md px-2 py-1 text-xs",
        active
          ? "bg-charcoal-700 text-charcoal-50"
          : "text-charcoal-300 hover:bg-charcoal-800",
      )}
    >
      {children}
    </button>
  );
}
