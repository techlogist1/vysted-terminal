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
import { PanelFetchError } from "./PanelFetchError";
import { formatNumber, formatRelativeIso, useInterval } from "./_utils";

import type { TradesaTrade } from "../../../types/tradesa_v2";

function SideBadge({ side }: { side: TradesaTrade["side"] }) {
  const cls =
    side === "long"
      ? "text-positive bg-positive/15 border-positive/40"
      : "text-negative bg-negative/15 border-negative/40";
  return (
    <span
      data-testid={`tradesa-side-${side}`}
      className={`text-micro rounded-control inline-flex items-center gap-1 border px-1 py-0.5 font-semibold tracking-wide uppercase ${cls}`}
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
        className="text-charcoal-500 text-body flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center"
      >
        <p>No open positions.</p>
        <p className="text-charcoal-400 text-caption">
          The bot opens positions when the Director LLM signals OPEN_LONG / OPEN_SHORT.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="overflow-auto">
        <table className="text-body w-full">
          <thead className="bg-charcoal-925 sticky top-0 z-10">
            <tr className="border-charcoal-700 text-charcoal-500 text-micro border-b text-left font-medium tracking-wide uppercase">
              <th className="px-3 py-1">Instrument</th>
              <th className="px-3 py-1">Side</th>
              <th className="px-3 py-1 text-right">Qty</th>
              <th className="px-3 py-1 text-right">Entry</th>
              <th className="px-3 py-1 text-right">Stop-Loss</th>
              <th className="px-3 py-1 text-right">Leverage</th>
              <th className="px-3 py-1 text-right">Opened</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((trade) => (
              <tr
                key={trade.id}
                data-testid="tradesa-position-row"
                className="border-charcoal-800 hover:bg-charcoal-800/40 border-b transition-colors"
              >
                <td className="px-3 py-1">
                  <span className="bg-charcoal-800 text-charcoal-200 rounded-control text-caption inline-flex px-1 py-0.5 font-mono">
                    {trade.instrument}
                  </span>
                </td>
                <td className="px-3 py-1">
                  <SideBadge side={trade.side} />
                </td>
                <td className="text-charcoal-200 text-caption px-3 py-1 text-right font-mono">
                  {formatNumber(trade.qty, 4)}
                </td>
                <td className="text-charcoal-200 text-caption px-3 py-1 text-right font-mono">
                  {formatNumber(trade.entry_price, 2)}
                </td>
                <td className="text-warning text-caption px-3 py-1 text-right font-mono">
                  {formatNumber(trade.stop_loss_price, 2)}
                </td>
                <td className="px-3 py-1 text-right">
                  <span
                    className={`text-micro rounded-control inline-flex px-1 py-0.5 font-mono ${
                      trade.leverage > 4
                        ? "text-negative bg-negative/15"
                        : "bg-charcoal-800 text-charcoal-400"
                    }`}
                  >
                    {trade.leverage}x
                  </span>
                </td>
                <td className="text-charcoal-400 text-caption px-3 py-1 text-right">
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
      <PanelFetchError error={positionsState.error} onRetry={() => void refreshPositions()} />
      <PositionsTable rows={rows} />
    </PanelShell>
  );
}

export default PositionsPanel;
