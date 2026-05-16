/**
 * Tradesa V2 wrapper — Trade History panel.
 *
 * Renders closed trades from the bot's `trades` table (status ===
 * "closed" with realized_pnl populated). Polls every 5 minutes — closed
 * trades are append-only and don't need a tighter cadence.
 *
 * Layout: top summary card (today's P&L / week P&L / total closed
 * count / win-rate %) + sortable table of closed trades (default sort
 * is closed_at desc). Columns: instrument, side, qty, entry/exit,
 * realized P&L (color-coded), duration, closed-at relative.
 */

"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";

import { POLL_CADENCE_MS, arrayOrEmpty, useTradesaStore } from "../store";

import { PanelShell } from "./_PanelShell";
import {
  formatDuration,
  formatNumber,
  formatRelativeIso,
  formatUsd,
  useInterval,
} from "./_utils";

import type { TradesaTrade } from "../../../types/tradesa_v2";

type SortKey = "closed_at" | "realized_pnl";
type SortDir = "asc" | "desc";

function SideBadge({ side }: { side: TradesaTrade["side"] }) {
  const cls =
    side === "long"
      ? "bg-emerald-950/60 text-emerald-300 border-emerald-800"
      : "bg-red-950/60 text-red-300 border-red-800";
  return (
    <span className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}>
      {side}
    </span>
  );
}

function PnlCell({ value }: { value: number | null }) {
  if (value === null) return <span className="text-zinc-500">—</span>;
  const cls = value >= 0 ? "text-emerald-300" : "text-red-300";
  const sign = value > 0 ? "+" : "";
  return (
    <span className={`font-mono text-xs ${cls}`}>
      {sign}
      {formatUsd(value)}
    </span>
  );
}

interface SummaryStats {
  todayPnl: number;
  weekPnl: number;
  totalCount: number;
  winRate: number;
  winCount: number;
  lossCount: number;
}

function computeSummary(rows: readonly TradesaTrade[]): SummaryStats {
  const now = Date.now();
  const dayAgo = now - 24 * 3600 * 1000;
  const weekAgo = now - 7 * 24 * 3600 * 1000;

  let todayPnl = 0;
  let weekPnl = 0;
  let winCount = 0;
  let lossCount = 0;

  for (const trade of rows) {
    if (trade.realized_pnl === null) continue;
    if (trade.realized_pnl > 0) winCount += 1;
    else if (trade.realized_pnl < 0) lossCount += 1;

    if (trade.closed_at) {
      const ms = Date.parse(trade.closed_at);
      if (Number.isFinite(ms)) {
        if (ms >= dayAgo) todayPnl += trade.realized_pnl;
        if (ms >= weekAgo) weekPnl += trade.realized_pnl;
      }
    }
  }
  const totalDecided = winCount + lossCount;
  const winRate = totalDecided > 0 ? winCount / totalDecided : 0;
  return { todayPnl, weekPnl, totalCount: rows.length, winRate, winCount, lossCount };
}

function SummaryCard({ stats }: { stats: SummaryStats }) {
  const tile = "rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2";
  return (
    <div
      data-testid="tradesa-trade-summary"
      className="grid shrink-0 grid-cols-2 gap-2 border-b border-zinc-800 bg-zinc-950/60 p-3 text-xs sm:grid-cols-4"
    >
      <div className={tile}>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">Today P&amp;L</div>
        <div className={`mt-0.5 font-mono text-sm ${stats.todayPnl >= 0 ? "text-emerald-300" : "text-red-300"}`}>
          {stats.todayPnl >= 0 ? "+" : ""}
          {formatUsd(stats.todayPnl)}
        </div>
      </div>
      <div className={tile}>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">7d P&amp;L</div>
        <div className={`mt-0.5 font-mono text-sm ${stats.weekPnl >= 0 ? "text-emerald-300" : "text-red-300"}`}>
          {stats.weekPnl >= 0 ? "+" : ""}
          {formatUsd(stats.weekPnl)}
        </div>
      </div>
      <div className={tile}>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">Closed</div>
        <div className="mt-0.5 font-mono text-sm text-zinc-200">{stats.totalCount}</div>
      </div>
      <div className={tile}>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">Win-rate</div>
        <div className="mt-0.5 font-mono text-sm text-zinc-200">
          {(stats.winRate * 100).toFixed(0)}%
          <span className="ml-1 text-[10px] text-zinc-500">
            {stats.winCount}W / {stats.lossCount}L
          </span>
        </div>
      </div>
    </div>
  );
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="ml-1 inline-block size-3 opacity-30" aria-hidden />;
  return dir === "desc" ? (
    <ArrowDown className="ml-1 inline size-3" aria-hidden />
  ) : (
    <ArrowUp className="ml-1 inline size-3" aria-hidden />
  );
}

function TradesTable({ rows }: { rows: readonly TradesaTrade[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("closed_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      let av: number;
      let bv: number;
      if (sortKey === "closed_at") {
        av = a.closed_at ? Date.parse(a.closed_at) : 0;
        bv = b.closed_at ? Date.parse(b.closed_at) : 0;
      } else {
        av = a.realized_pnl ?? 0;
        bv = b.realized_pnl ?? 0;
      }
      return sortDir === "desc" ? bv - av : av - bv;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  const onSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  if (sorted.length === 0) {
    return (
      <div
        data-testid="tradesa-trade-history-empty"
        className="flex flex-1 items-center justify-center p-6 text-sm text-zinc-500"
      >
        No closed trades yet.
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
              <th className="px-3 py-2 text-right">Exit</th>
              <th className="px-3 py-2 text-right">
                <button
                  type="button"
                  className="inline-flex items-center text-[11px] font-medium uppercase tracking-wide text-zinc-400 hover:text-zinc-200"
                  onClick={() => onSort("realized_pnl")}
                >
                  P&amp;L
                  <SortIcon active={sortKey === "realized_pnl"} dir={sortDir} />
                </button>
              </th>
              <th className="px-3 py-2 text-right">Duration</th>
              <th className="px-3 py-2 text-right">
                <button
                  type="button"
                  className="inline-flex items-center text-[11px] font-medium uppercase tracking-wide text-zinc-400 hover:text-zinc-200"
                  onClick={() => onSort("closed_at")}
                >
                  Closed
                  <SortIcon active={sortKey === "closed_at"} dir={sortDir} />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((trade) => (
              <tr
                key={trade.id}
                data-testid="tradesa-trade-row"
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
                <td className="px-3 py-2 text-right font-mono text-xs text-zinc-300">
                  {formatNumber(trade.qty, 4)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs text-zinc-400">
                  {formatNumber(trade.entry_price, 2)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs text-zinc-400">
                  {formatNumber(trade.exit_price, 2)}
                </td>
                <td className="px-3 py-2 text-right">
                  <PnlCell value={trade.realized_pnl} />
                </td>
                <td className="px-3 py-2 text-right text-xs text-zinc-400">
                  {formatDuration(trade.opened_at, trade.closed_at)}
                </td>
                <td className="px-3 py-2 text-right text-xs text-zinc-400">
                  {formatRelativeIso(trade.closed_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function TradeHistoryPanel() {
  const tradeHistoryState = useTradesaStore((s) => s.tradeHistory);
  const refreshTradeHistory = useTradesaStore((s) => s.refreshTradeHistory);

  useInterval(() => {
    void refreshTradeHistory();
  }, POLL_CADENCE_MS.tradeHistory);

  const rows = arrayOrEmpty(tradeHistoryState.data);
  const stats = useMemo(() => computeSummary(rows), [rows]);

  return (
    <PanelShell title="Trade History">
      <SummaryCard stats={stats} />
      <TradesTable rows={rows} />
    </PanelShell>
  );
}

export default TradeHistoryPanel;
