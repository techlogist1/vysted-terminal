"use client";

/**
 * FilingsListTable — sortable table of filings.
 *
 * Clicking a row asks the parent to open the FilingViewer (passes the
 * accession + the current identifier). Form-type column is colour-coded
 * by category so the user can scan 10-Ks vs 8-Ks at a glance.
 */

import { useMemo, useState } from "react";

import { cn } from "@/lib/utils";

import type { Filing } from "../../../types/sec";

type SortKey = "filed_date" | "form_type" | "period_of_report";
type SortDir = "asc" | "desc";

const FORM_COLOR: Record<string, string> = {
  "10-K": "text-emerald-300",
  "10-Q": "text-sky-300",
  "8-K": "text-amber-300",
  "DEF 14A": "text-violet-300",
  "3": "text-slate-300",
  "4": "text-rose-300",
  "5": "text-orange-300",
};

interface FilingsListTableProps {
  filings: ReadonlyArray<Filing>;
  selectedAccession: string | null;
  onSelect: (filing: Filing) => void;
}

export function FilingsListTable({ filings, selectedAccession, onSelect }: FilingsListTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("filed_date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    const copy = [...filings];
    copy.sort((a, b) => {
      const av = (a[sortKey] ?? "") as string;
      const bv = (b[sortKey] ?? "") as string;
      if (av === bv) return 0;
      const cmp = av < bv ? -1 : 1;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [filings, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  return (
    <div className="flex-1 overflow-y-auto" data-testid="filings-list-table">
      <table className="w-full table-fixed text-[11px]">
        <colgroup>
          <col className="w-[10ch]" />
          <col className="w-[12ch]" />
          <col className="w-[14ch]" />
          <col />
          <col className="w-[26ch]" />
        </colgroup>
        <thead className="text-charcoal-400 bg-charcoal-900 sticky top-0 text-left text-[10px] uppercase">
          <tr>
            <th className="px-2 py-1">
              <SortableHeader
                label="Form"
                active={sortKey === "form_type"}
                dir={sortDir}
                onClick={() => toggleSort("form_type")}
              />
            </th>
            <th className="px-2 py-1">
              <SortableHeader
                label="Filed"
                active={sortKey === "filed_date"}
                dir={sortDir}
                onClick={() => toggleSort("filed_date")}
              />
            </th>
            <th className="px-2 py-1">
              <SortableHeader
                label="Period"
                active={sortKey === "period_of_report"}
                dir={sortDir}
                onClick={() => toggleSort("period_of_report")}
              />
            </th>
            <th className="px-2 py-1">Company</th>
            <th className="px-2 py-1">Accession</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((filing) => (
            <tr
              key={filing.accession}
              data-testid={`filings-row-${filing.accession}`}
              className={cn(
                "border-charcoal-800 hover:bg-charcoal-800 cursor-pointer border-b",
                selectedAccession === filing.accession && "bg-charcoal-800",
              )}
              onClick={() => onSelect(filing)}
            >
              <td
                className={cn(
                  "px-2 py-1 font-semibold",
                  FORM_COLOR[filing.form_type] ?? "text-charcoal-100",
                )}
              >
                {filing.form_type}
              </td>
              <td className="text-charcoal-200 px-2 py-1">{filing.filed_date}</td>
              <td className="text-charcoal-300 px-2 py-1">{filing.period_of_report ?? "—"}</td>
              <td className="text-charcoal-100 truncate px-2 py-1" title={filing.company_name}>
                {filing.company_name}
              </td>
              <td
                className="text-charcoal-500 truncate px-2 py-1 font-mono"
                title={filing.accession}
              >
                {filing.accession}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface SortableHeaderProps {
  label: string;
  active: boolean;
  dir: SortDir;
  onClick: () => void;
}

function SortableHeader({ label, active, dir, onClick }: SortableHeaderProps) {
  return (
    <button
      type="button"
      className={cn(
        "hover:text-charcoal-200 flex items-center gap-1",
        active ? "text-charcoal-200" : "text-charcoal-400",
      )}
      onClick={onClick}
    >
      <span>{label}</span>
      {active && <span aria-hidden>{dir === "asc" ? "▲" : "▼"}</span>}
    </button>
  );
}
