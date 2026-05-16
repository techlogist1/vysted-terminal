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
import { formatRelativeIso, useInterval } from "./_utils";

import type { TradesaSentinelBlock } from "../../../types/tradesa_v2";

function FailModeBadge({ failClosed }: { failClosed: boolean }) {
  const cls = failClosed
    ? "bg-red-950/60 text-red-300 border-red-800"
    : "bg-zinc-900 text-zinc-400 border-zinc-700";
  return (
    <span
      data-testid={`tradesa-fail-${failClosed ? "closed" : "open"}`}
      className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase ${cls}`}
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
        className="flex flex-1 items-center justify-center p-6 text-sm text-zinc-500"
      >
        No sentinel-gate data yet.
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-zinc-950">
            <tr className="border-b border-zinc-800 text-left text-[11px] font-medium tracking-wide text-zinc-500 uppercase">
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
                className="border-b border-zinc-900/50 transition-colors hover:bg-zinc-900/40"
              >
                <td className="px-3 py-2 font-mono text-[11px] text-zinc-400">{gate.gate_id}</td>
                <td className="px-3 py-2 text-xs text-zinc-200">{gate.gate_label}</td>
                <td className="px-3 py-2 text-right">
                  <span
                    className={`inline-flex rounded px-1.5 py-0.5 font-mono text-xs ${
                      gate.today_count > 0
                        ? "bg-amber-950/60 text-amber-300"
                        : "bg-zinc-900 text-zinc-500"
                    }`}
                  >
                    {gate.today_count.toLocaleString()}
                  </span>
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs text-zinc-400">
                  {gate.total_count.toLocaleString()}
                </td>
                <td className="px-3 py-2 text-right text-xs text-zinc-400">
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
      <SentinelTable rows={rows} />
    </PanelShell>
  );
}

export default SentinelPanel;
