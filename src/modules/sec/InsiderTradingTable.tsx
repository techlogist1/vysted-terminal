"use client";

/**
 * InsiderTradingTable — Forms 3/4/5 transactions for an issuer.
 *
 * Reads from `useSecStore.insiderByIdentifier`. XBRL-precise numeric
 * fields (shares / price / value) are typed as strings to preserve
 * precision; this table renders them as the strings the wire carries
 * with light grouping for readability.
 */

import { useEffect, useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import { selectInsider, useSecStore } from "@/store/sec";

import type { InsiderTransaction } from "../../../types/sec";

interface InsiderTradingTableProps {
  identifier: string | null;
}

type FormFilter = "all" | "3" | "4" | "5";

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

  return (
    <div className="flex h-full flex-col" data-testid="insider-trading-table">
      <header className="border-charcoal-700 flex items-center gap-3 border-b px-3 py-2">
        <label className="flex items-center gap-1.5 text-[10px] uppercase">
          <span className="text-charcoal-400">Form</span>
          <select
            value={form}
            onChange={(e) => setForm(e.target.value as FormFilter)}
            className="bg-charcoal-800 text-charcoal-100 border-charcoal-700 rounded-md border px-1.5 py-0.5 text-xs"
            data-testid="insider-form-filter"
          >
            <option value="all">All</option>
            <option value="3">3 — ownership</option>
            <option value="4">4 — trade</option>
            <option value="5">5 — deferred</option>
          </select>
        </label>
        <span className="text-charcoal-400 text-[10px]">
          {response.transactions.length} transactions
        </span>
        {status === "loading" && (
          <span className="text-charcoal-400 text-[10px]">Loading…</span>
        )}
      </header>

      <div className="flex-1 overflow-y-auto">
        {error && (
          <p className="px-3 py-2 text-[11px] text-red-400" data-testid="insider-error">
            {error}
          </p>
        )}
        <table className="w-full text-[11px]">
          <thead className="text-charcoal-400 bg-charcoal-900 sticky top-0 text-left text-[10px] uppercase">
            <tr>
              <th className="px-2 py-1">Date</th>
              <th className="px-2 py-1">Reporter</th>
              <th className="px-2 py-1">Title</th>
              <th className="px-2 py-1">Form</th>
              <th className="px-2 py-1">Code</th>
              <th className="px-2 py-1">Direction</th>
              <th className="px-2 py-1 text-right">Shares</th>
              <th className="px-2 py-1 text-right">Price</th>
              <th className="px-2 py-1 text-right">Value</th>
            </tr>
          </thead>
          <tbody>
            {response.transactions.map((txn) => (
              <InsiderRow key={`${txn.accession}-${txn.reporter_cik}-${txn.transaction_date}`} txn={txn} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface InsiderRowProps {
  txn: InsiderTransaction;
}

function InsiderRow({ txn }: InsiderRowProps) {
  const directionColor =
    txn.direction === "disposed" ? "text-rose-300" : "text-emerald-300";
  return (
    <tr
      data-testid={`insider-row-${txn.accession}-${txn.reporter_cik}`}
      className="border-charcoal-800 border-b"
    >
      <td className="text-charcoal-200 px-2 py-1">{txn.transaction_date}</td>
      <td className="text-charcoal-100 px-2 py-1" title={txn.reporter_name}>
        {txn.reporter_name}
      </td>
      <td className="text-charcoal-300 truncate px-2 py-1" title={txn.reporter_title ?? ""}>
        {txn.reporter_title ?? "—"}
      </td>
      <td className="text-charcoal-200 px-2 py-1">{txn.form_type}</td>
      <td className="text-charcoal-400 px-2 py-1 font-mono">{txn.transaction_code || "—"}</td>
      <td className={cn("px-2 py-1 capitalize", directionColor)}>{txn.direction}</td>
      <td className="text-charcoal-100 px-2 py-1 text-right font-mono">
        {formatBigInt(txn.shares)}
      </td>
      <td className="text-charcoal-200 px-2 py-1 text-right font-mono">
        {txn.price_per_share ?? "—"}
      </td>
      <td className="text-charcoal-100 px-2 py-1 text-right font-mono">
        {txn.transaction_value ? formatBigInt(txn.transaction_value) : "—"}
      </td>
    </tr>
  );
}

/** Light-touch big-int formatter — adds thousands separators if safe. */
function formatBigInt(raw: string): string {
  if (!raw) return "—";
  const trimmed = raw.trim();
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) return trimmed;
  const [intPart, frac] = trimmed.split(".");
  const withCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return frac ? `${withCommas}.${frac}` : withCommas;
}
