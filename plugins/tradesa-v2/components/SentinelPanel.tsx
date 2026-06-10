/**
 * Tradesa V2 wrapper — Sentinel panel.
 *
 * Renders the 12-18 sentinel gate decline tallies from
 * `sentinel_block_counts`. Sorted by today_count desc so the most-
 * blocking gate today rises to the top. Polls `/tradesa-v2/sentinel`
 * every 60 seconds.
 *
 * Columns: gate id, human label, today's block count, lifetime block
 * count, last blocked at (relative), fail-closed badge (red if true,
 * gray if false).
 */

"use client";

import { useMemo } from "react";

import { POLL_CADENCE_MS, arrayOrEmpty, useTradesaStore } from "../store";

import { PanelShell } from "./_PanelShell";
import { PanelFetchError } from "./PanelFetchError";
import { formatRelativeIso, useInterval } from "./_utils";

import type { TradesaSentinelBlock } from "../../../types/tradesa_v2";

function FailModeBadge({ failClosed }: { failClosed: boolean }) {
  const cls = failClosed
    ? "text-negative bg-negative/15 border-negative/40"
    : "bg-charcoal-800 text-charcoal-400 border-charcoal-700";
  return (
    <span
      data-testid={`tradesa-fail-${failClosed ? "closed" : "open"}`}
      className={`text-micro inline-flex rounded border px-1.5 py-0.5 font-semibold tracking-wide uppercase ${cls}`}
    >
      {failClosed ? "Fail-closed" : "Fail-open"}
    </span>
  );
}

function SentinelTable({ rows }: { rows: readonly TradesaSentinelBlock[] }) {
  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => b.today_count - a.today_count);
  }, [rows]);

  if (sorted.length === 0) {
    return (
      <div
        data-testid="tradesa-sentinel-empty"
        className="text-charcoal-500 flex flex-1 items-center justify-center p-6 text-sm"
      >
        No sentinel-gate data yet.
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-charcoal-925 sticky top-0 z-10">
            <tr className="border-charcoal-700 text-charcoal-500 border-b text-left text-[11px] font-medium tracking-wide uppercase">
              <th className="px-3 py-2">Gate</th>
              <th className="px-3 py-2">Label</th>
              <th className="px-3 py-2 text-right">Today</th>
              <th className="px-3 py-2 text-right">Total</th>
              <th className="px-3 py-2 text-right">Last blocked</th>
              <th className="px-3 py-2">Mode</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((gate) => (
              <tr
                key={gate.gate_id}
                data-testid="tradesa-sentinel-row"
                className="border-charcoal-800 hover:bg-charcoal-800/40 border-b transition-colors"
              >
                <td className="text-charcoal-400 px-3 py-2 font-mono text-[11px]">
                  {gate.gate_id}
                </td>
                <td className="text-charcoal-200 px-3 py-2 text-xs">{gate.gate_label}</td>
                <td className="px-3 py-2 text-right">
                  <span
                    className={`inline-flex rounded px-1.5 py-0.5 font-mono text-xs ${
                      gate.today_count > 0
                        ? "text-warning bg-warning/15"
                        : "bg-charcoal-800 text-charcoal-500"
                    }`}
                  >
                    {gate.today_count.toLocaleString()}
                  </span>
                </td>
                <td className="text-charcoal-400 px-3 py-2 text-right font-mono text-xs">
                  {gate.total_count.toLocaleString()}
                </td>
                <td className="text-charcoal-400 px-3 py-2 text-right text-xs">
                  {formatRelativeIso(gate.last_blocked_at)}
                </td>
                <td className="px-3 py-2">
                  <FailModeBadge failClosed={gate.fail_closed} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function SentinelPanel() {
  const sentinelState = useTradesaStore((s) => s.sentinelBlocks);
  const refreshSentinel = useTradesaStore((s) => s.refreshSentinel);

  useInterval(() => {
    void refreshSentinel();
  }, POLL_CADENCE_MS.sentinel);

  const rows = arrayOrEmpty(sentinelState.data);

  return (
    <PanelShell title="Sentinel Gates">
      <PanelFetchError error={sentinelState.error} onRetry={() => void refreshSentinel()} />
      <SentinelTable rows={rows} />
    </PanelShell>
  );
}

export default SentinelPanel;
