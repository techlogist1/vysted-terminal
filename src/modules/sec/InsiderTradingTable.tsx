"use client";

/**
 * InsiderTradingTable — Forms 3/4/5 transactions for an issuer, on the shared
 * DataTable.
 *
 * Reads from `useSecStore.insiderByIdentifier`. XBRL-precise numeric fields
 * (shares / price / value) are typed as strings to preserve precision; this table
 * groups their digits via `groupDigits` (never parsing to a lossy Number).
 */

import { useEffect, useMemo, useState } from "react";
import { Users2 } from "lucide-react";

import { DataTable, type DataColumn } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { groupDigits } from "@/lib/format";
import { cn } from "@/lib/utils";
import { selectInsider, useSecStore } from "@/store/sec";

import type { InsiderTransaction } from "../../../types/sec";

interface InsiderTradingTableProps {
  identifier: string | null;
}

type FormFilter = "all" | "3" | "4" | "5";

const COLUMNS: DataColumn<InsiderTransaction>[] = [
  {
    key: "transaction_date",
    header: "Date",
    tier: "secondary",
    width: "10ch",
    format: (t) => t.transaction_date,
  },
  {
    key: "reporter_name",
    header: "Reporter",
    truncate: true,
    width: "14ch",
    format: (t) => t.reporter_name,
  },
  {
    key: "reporter_title",
    header: "Title",
    tier: "secondary",
    truncate: true,
    width: "10ch",
    format: (t) => t.reporter_title ?? null,
  },
  { key: "form_type", header: "Form", tier: "secondary", width: "4ch", format: (t) => t.form_type },
  {
    key: "transaction_code",
    header: "Code",
    tier: "secondary",
    width: "4ch",
    format: (t) => t.transaction_code || null,
  },
  {
    key: "direction",
    header: "Direction",
    width: "8ch",
    cell: (t) => (
      <span
        className={cn("capitalize", t.direction === "disposed" ? "text-negative" : "text-positive")}
      >
        {t.direction}
      </span>
    ),
  },
  {
    key: "shares",
    header: "Shares",
    numeric: true,
    width: "10ch",
    format: (t) => groupDigits(t.shares),
  },
  {
    key: "price_per_share",
    header: "Price",
    numeric: true,
    tier: "secondary",
    width: "8ch",
    format: (t) => (t.price_per_share ? groupDigits(t.price_per_share) : null),
  },
  {
    key: "transaction_value",
    header: "Value",
    numeric: true,
    width: "12ch",
    format: (t) => (t.transaction_value ? groupDigits(t.transaction_value) : null),
  },
];

export function InsiderTradingTable({ identifier }: InsiderTradingTableProps) {
  const [form, setForm] = useState<FormFilter>("4");
  const loadInsider = useSecStore((s) => s.loadInsider);
  const status = useSecStore((s) => s.insiderStatus);
  const error = useSecStore((s) => s.insiderError);

  // Subscribe to the per-identifier map so re-renders happen when the
  // loaded payload updates.
  const byIdentifier = useSecStore((s) => s.insiderByIdentifier);
  const response = useMemo(() => {
    void byIdentifier; // hooked above for subscription
    const raw = selectInsider(identifier, form === "all" ? undefined : form);
    // Defend against an upstream that returns a shape without `transactions`
    // (e.g. a mocked sidecarGet that returned a generic FilingsListResponse).
    if (!raw || !Array.isArray(raw.transactions)) {
      return { cik: "", issuer_name: "", transactions: [] };
    }
    return raw;
  }, [byIdentifier, identifier, form]);

  useEffect(() => {
    if (identifier) {
      void loadInsider(identifier, form === "all" ? undefined : form);
    }
  }, [identifier, form, loadInsider]);

  if (!identifier) {
    return (
      <div className="flex h-full flex-col" data-testid="insider-trading-table">
        <EmptyState
          icon={Users2}
          headline="No issuer selected"
          hint="Enter a ticker in the Symbol field above to load insider transactions."
          dense
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col" data-testid="insider-trading-table">
      <header className="border-charcoal-700 flex items-center gap-3 border-b px-3 py-2">
        <label className="text-micro flex items-center gap-1.5">
          <span className="text-charcoal-400">Form</span>
          <select
            value={form}
            onChange={(e) => setForm(e.target.value as FormFilter)}
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 text-caption rounded-control h-6 border px-1.5"
            data-testid="insider-form-filter"
          >
            <option value="all">All</option>
            <option value="3">3 — ownership</option>
            <option value="4">4 — trade</option>
            <option value="5">5 — deferred</option>
          </select>
        </label>
        <span className="text-charcoal-400 text-micro tabular-nums">
          {response.transactions.length} transactions
        </span>
        {status === "loading" && <span className="text-charcoal-400 text-micro">Loading…</span>}
      </header>

      <div
        className={cn(
          "flex-1 overflow-y-auto",
          status === "loading" && response.transactions.length > 0 ? "opacity-50" : "",
        )}
      >
        {error && (
          <div
            className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2"
            data-testid="insider-error"
          >
            <span className="text-negative text-caption">
              Could not load insider data — {error}
            </span>
            <Button
              size="xs"
              variant="ghost"
              className="shrink-0 text-amber-300 hover:text-amber-200"
              onClick={() => void loadInsider(identifier, form === "all" ? undefined : form)}
            >
              Retry
            </Button>
          </div>
        )}
        <DataTable
          columns={COLUMNS}
          rows={response.transactions}
          rowKey={(t) => `${t.accession}-${t.reporter_cik}-${t.transaction_date}`}
          rowTestId={(t) => `insider-row-${t.accession}-${t.reporter_cik}`}
          stickyHeader
        />
      </div>
    </div>
  );
}
