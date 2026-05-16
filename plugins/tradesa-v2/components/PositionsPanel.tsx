/**
 * Tradesa V2 wrapper — Live Positions panel.
 *
 * Renders open trades from the bot's `trades` table (status === "open"
 * or "reduce_only"). Polls `/tradesa-v2/positions` every 10s — the
 * cadence picked because close-out is the most time-sensitive read in
 * the wrapper.
 *
 * Columns: instrument badge, side (long/short color-coded), qty,
 * entry price, stop-loss price, leverage (always ≤4 per Tradesa's
 * HARD_LEVERAGE_CAP), opened-at relative time. Empty state: "No open
 * positions."
 */

"use client";

import { POLL_CADENCE_MS, arrayOrEmpty, useTradesaStore } from "../store";

import { PanelShell } from "./_PanelShell";
import {
  formatNumber,
  formatRelativeIso,
  useInterval,
} from "./_utils";

import type { TradesaTrade } from "../../../types/tradesa_v2";

function SideBadge({ side }: { side: TradesaTrade["side"] }) {
  const cls =
    side === "long"
      ? "bg-emerald-950/60 text-emerald-300 border-emerald-800"
      : "bg-red-950/60 text-red-300 border-red-800";
  return (
    <span
      data-testid={`tradesa-side-${side}`}
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}
    >
      {side}
    </span>
  );
}

function PositionsTable({ rows }: { rows: readonly TradesaTrade[] }) {
  if (rows.length === 0) {
    return (
      <div
        data-testid="tradesa-positions-empty"
        className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-sm text-zinc-500"
      >
        <p>No open positions.</p>
        <p className="text-xs text-zinc-600">
          The bot opens positions when the Director LLM signals OPEN_LONG / OPEN_SHORT.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-zinc-950">
            <tr className="border-b border-zinc-800 text-left text-[11px] font-medium uppercase tracking-wide text-zinc-500">
              <th className="px-3 py-2">Instrument</th>
              <th className="px-3 py-2">Side</th>
              <th className="px-3 py-2 text-right">Qty</th>
              <th className="px-3 py-2 text-right">Entry</th>
              <th className="px-3 py-2 text-right">Stop-Loss</th>
              <th className="px-3 py-2 text-right">Leverage</th>
              <th className="px-3 py-2 text-right">Opened</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((trade) => (
              <tr
                key={trade.id}
                data-testid="tradesa-position-row"
                className="border-b border-zinc-900/50 transition-colors hover:bg-zinc-900/40"
              >
                <td className="px-3 py-2">
                  <span className="inline-flex rounded bg-zinc-800/80 px-1.5 py-0.5 font-mono text-xs text-zinc-200">
                    {trade.instrument}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <SideBadge side={trade.side} />
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs text-zinc-200">
                  {formatNumber(trade.qty, 4)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs text-zinc-200">
                  {formatNumber(trade.entry_price, 2)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs text-amber-300">
                  {formatNumber(trade.stop_loss_price, 2)}
                </td>
                <td className="px-3 py-2 text-right">
                  <span
                    className={`inline-flex rounded px-1.5 py-0.5 font-mono text-[10px] ${
                      trade.leverage > 4
                        ? "bg-red-950/60 text-red-300"
                        : "bg-zinc-900 text-zinc-400"
                    }`}
                  >
                    {trade.leverage}x
                  </span>
                </td>
                <td className="px-3 py-2 text-right text-xs text-zinc-400">
                  {formatRelativeIso(trade.opened_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function PositionsPanel() {
  const positionsState = useTradesaStore((s) => s.positions);
  const refreshPositions = useTradesaStore((s) => s.refreshPositions);

  useInterval(() => {
    void refreshPositions();
  }, POLL_CADENCE_MS.positions);

  const rows = arrayOrEmpty(positionsState.data);

  return (
    <PanelShell title="Live Positions">
      <PositionsTable rows={rows} />
    </PanelShell>
  );
}

export default PositionsPanel;
