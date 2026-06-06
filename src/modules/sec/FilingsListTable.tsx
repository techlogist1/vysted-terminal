"use client";

/**
 * FilingsListTable — sortable table of filings on the shared DataTable.
 *
 * Clicking a row asks the parent to open the FilingViewer (passes the
 * accession + the current identifier). Form-type column is colour-coded
 * by category so the user can scan 10-Ks vs 8-Ks at a glance.
 */

import { useMemo, useState } from "react";
import { FileText } from "lucide-react";

import { DataTable, type DataColumn, type DataTableSort } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { cn } from "@/lib/utils";

import type { Filing } from "../../../types/sec";

type SortKey = "filed_date" | "form_type" | "period_of_report";
type ColumnKey = SortKey | "company_name" | "accession";
type SortDir = "asc" | "desc";

const FORM_COLOR: Record<string, string> = {
  "10-K": "text-charcoal-300",
  "10-Q": "text-charcoal-300",
  "8-K": "text-warning",
  "DEF 14A": "text-charcoal-300",
  "3": "text-charcoal-300",
  "4": "text-charcoal-300",
  "5": "text-charcoal-300",
};

const COLUMNS: DataColumn<Filing, ColumnKey>[] = [
  {
    key: "form_type",
    header: "Form",
    sortable: true,
    width: "10ch",
    cell: (f) => (
      <span className={cn("font-medium", FORM_COLOR[f.form_type] ?? "text-charcoal-100")}>
        {f.form_type}
      </span>
    ),
  },
  {
    key: "filed_date",
    header: "Filed",
    sortable: true,
    tier: "secondary",
    width: "12ch",
    format: (f) => f.filed_date,
  },
  {
    key: "period_of_report",
    header: "Period",
    sortable: true,
    tier: "secondary",
    width: "14ch",
    format: (f) => f.period_of_report ?? null,
  },
  {
    key: "company_name",
    header: "Company",
    truncate: true,
    format: (f) => f.company_name,
  },
  {
    key: "accession",
    header: "Accession",
    tier: "tertiary",
    truncate: true,
    width: "26ch",
    format: (f) => f.accession,
  },
];

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

  // Company / Accession are display-only — a click on them is a no-op.
  function toggleSort(key: ColumnKey) {
    if (key !== "filed_date" && key !== "form_type" && key !== "period_of_report") return;
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const sort: DataTableSort<ColumnKey> = { key: sortKey, direction: sortDir };

  return (
    <div className="h-full overflow-y-auto" data-testid="filings-list-table">
      {sorted.length === 0 ? (
        <EmptyState
          icon={FileText}
          headline="No filings match"
          hint='Try "All forms" or a different symbol to widen the search.'
          dense
        />
      ) : (
        <DataTable
          columns={COLUMNS}
          rows={sorted}
          rowKey={(f) => f.accession}
          sort={sort}
          onSort={toggleSort}
          stickyHeader
          onRowClick={onSelect}
          isRowSelected={(f) => f.accession === selectedAccession}
          rowTestId={(f) => `filings-row-${f.accession}`}
        />
      )}
    </div>
  );
}
