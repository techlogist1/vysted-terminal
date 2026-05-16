"use client";

/**
 * AuditLogViewer — BLUEPRINT §6.5 #4 UI surface.
 *
 * Live-tails `GET /safety/audit-log?limit=200` every 2 seconds. Supports
 * filtering by broker + action + time range; export to CSV through
 * `GET /safety/audit-log/export.csv`.
 */

import { useCallback, useEffect, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { defaultAuditFilter, useSafetyStore } from "@/store/safety";

import type { BrokerId } from "../../../types/broker";
import type { AuditLogAction, AuditLogEntry } from "../../../types/safety";

const POLL_INTERVAL_MS = 2_000;
const TAIL_LIMIT = 200;

const KNOWN_BROKERS: Array<BrokerId | "_meta"> = [
  "_meta",
  "dhan",
  "angelone",
  "kite",
  "alpaca",
  "ib",
  "oanda",
  "ccxt-bybit",
  "ccxt-binance",
  "ccxt-kraken",
  "ccxt-coinbase",
];

const KNOWN_ACTIONS: AuditLogAction[] = [
  "order-proposed",
  "order-confirmed",
  "order-declined",
  "order-placed",
  "order-cancelled",
  "order-rejected",
  "kill-switch-fired",
  "kill-switch-reset",
  "mode-changed",
  "read-only-changed",
  "connection",
  "disclaimer-ack",
];

export function AuditLogViewer() {
  const refreshAuditLog = useSafetyStore((s) => s.refreshAuditLog);
  const filter = useSafetyStore((s) => s.auditFilter);
  const setAuditFilter = useSafetyStore((s) => s.setAuditFilter);
  const filteredAuditEntries = useSafetyStore((s) => s.filteredAuditEntries);
  const status = useSafetyStore((s) => s.auditStatus);

  useEffect(() => {
    void refreshAuditLog(TAIL_LIMIT);
    const interval = setInterval(() => {
      void refreshAuditLog(TAIL_LIMIT);
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refreshAuditLog]);

  const entries = filteredAuditEntries();

  const exportCsv = useCallback(async () => {
    const base = await getSidecarBaseUrl();
    const url = new URL("/safety/audit-log/export.csv", base);
    if (filter.startMs !== null && filter.endMs !== null) {
      url.searchParams.set("start_ms", String(filter.startMs));
      url.searchParams.set("end_ms", String(filter.endMs));
    }
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`export failed (${response.status})`);
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = "vysted-audit-log.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(objectUrl);
  }, [filter.endMs, filter.startMs]);

  const resetFilter = useCallback(() => {
    setAuditFilter(defaultAuditFilter);
  }, [setAuditFilter]);

  return (
    <div
      data-testid="audit-log-viewer"
      className="bg-charcoal-900 text-charcoal-100 flex h-full w-full flex-col font-mono text-xs"
    >
      <header className="border-charcoal-700 flex flex-wrap items-end gap-2 border-b px-3 py-2">
        <FilterSelect
          label="Broker"
          value={filter.broker}
          options={[
            { value: "all", label: "All" },
            ...KNOWN_BROKERS.map((b) => ({ value: b, label: b })),
          ]}
          onChange={(value) => setAuditFilter({ broker: value as BrokerId | "_meta" | "all" })}
          dataTestId="audit-filter-broker"
        />
        <FilterSelect
          label="Action"
          value={filter.action}
          options={[
            { value: "all", label: "All" },
            ...KNOWN_ACTIONS.map((a) => ({ value: a, label: a })),
          ]}
          onChange={(value) => setAuditFilter({ action: value as AuditLogAction | "all" })}
          dataTestId="audit-filter-action"
        />
        <DateRangeFilter
          startMs={filter.startMs}
          endMs={filter.endMs}
          onChange={(start, end) => setAuditFilter({ startMs: start, endMs: end })}
        />
        <Button size="xs" variant="ghost" onClick={resetFilter}>
          Reset
        </Button>
        <span className="ml-auto flex items-center gap-2">
          <span className="text-charcoal-400 text-[10px]">{entries.length} entries</span>
          <Button size="xs" variant="outline" onClick={exportCsv} data-testid="audit-export-csv">
            Export CSV
          </Button>
        </span>
      </header>

      <div className="flex-1 overflow-y-auto">
        {status === "loading" && entries.length === 0 && (
          <p className="text-charcoal-400 px-3 py-2">Loading…</p>
        )}
        {status === "ready" && entries.length === 0 && (
          <p className="text-charcoal-400 px-3 py-2">No audit entries match the filter.</p>
        )}
        <table className="w-full table-fixed text-[11px]">
          <colgroup>
            <col className="w-[10ch]" />
            <col className="w-[18ch]" />
            <col className="w-[14ch]" />
            <col className="w-[18ch]" />
            <col />
            <col className="w-[10ch]" />
            <col className="w-[16ch]" />
          </colgroup>
          <thead className="text-charcoal-400 bg-charcoal-900 sticky top-0 text-left text-[10px] uppercase">
            <tr>
              <th className="px-2 py-1">ID</th>
              <th className="px-2 py-1">Time</th>
              <th className="px-2 py-1">Broker</th>
              <th className="px-2 py-1">Action</th>
              <th className="px-2 py-1">Payload</th>
              <th className="px-2 py-1">Source</th>
              <th className="px-2 py-1">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <AuditRow key={entry.id} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface AuditRowProps {
  entry: AuditLogEntry;
}

function AuditRow({ entry }: AuditRowProps) {
  const payloadPreview = useMemo(() => JSON.stringify(entry.payload), [entry.payload]);
  const outcomeColor = entry.outcome.startsWith("rejected")
    ? "text-red-400"
    : entry.outcome === "declined"
      ? "text-amber-300"
      : "text-charcoal-200";
  return (
    <tr data-testid={`audit-row-${entry.id}`} className="border-charcoal-800 border-b">
      <td className="text-charcoal-500 px-2 py-1">{entry.id}</td>
      <td className="text-charcoal-300 px-2 py-1">
        {new Date(entry.timestampMs).toLocaleTimeString()}
      </td>
      <td className="text-charcoal-100 px-2 py-1">{entry.broker}</td>
      <td className="text-charcoal-100 px-2 py-1">{entry.action}</td>
      <td className="text-charcoal-300 truncate px-2 py-1" title={payloadPreview}>
        {payloadPreview}
      </td>
      <td className="text-charcoal-400 px-2 py-1">{entry.source}</td>
      <td className={cn("px-2 py-1", outcomeColor)}>{entry.outcome}</td>
    </tr>
  );
}

interface FilterSelectProps {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
  dataTestId?: string;
}

function FilterSelect({ label, value, options, onChange, dataTestId }: FilterSelectProps) {
  return (
    <label className="flex flex-col gap-0.5">
      <span className="text-charcoal-400 text-[10px] uppercase">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid={dataTestId}
        className="bg-charcoal-800 text-charcoal-100 h-7 rounded-md px-2 text-xs outline-none"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

interface DateRangeFilterProps {
  startMs: number | null;
  endMs: number | null;
  onChange: (startMs: number | null, endMs: number | null) => void;
}

function DateRangeFilter({ startMs, endMs, onChange }: DateRangeFilterProps) {
  return (
    <div className="flex items-end gap-1">
      <label className="flex flex-col gap-0.5">
        <span className="text-charcoal-400 text-[10px] uppercase">From</span>
        <input
          type="datetime-local"
          data-testid="audit-filter-start"
          value={startMs !== null ? toLocalInputValue(startMs) : ""}
          onChange={(e) => onChange(fromLocalInputValue(e.target.value), endMs)}
          className="bg-charcoal-800 text-charcoal-100 h-7 rounded-md px-2 text-[11px] outline-none"
        />
      </label>
      <label className="flex flex-col gap-0.5">
        <span className="text-charcoal-400 text-[10px] uppercase">To</span>
        <input
          type="datetime-local"
          data-testid="audit-filter-end"
          value={endMs !== null ? toLocalInputValue(endMs) : ""}
          onChange={(e) => onChange(startMs, fromLocalInputValue(e.target.value))}
          className="bg-charcoal-800 text-charcoal-100 h-7 rounded-md px-2 text-[11px] outline-none"
        />
      </label>
    </div>
  );
}

function toLocalInputValue(ms: number): string {
  const d = new Date(ms);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInputValue(value: string): number | null {
  if (value === "") {
    return null;
  }
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? null : ms;
}
