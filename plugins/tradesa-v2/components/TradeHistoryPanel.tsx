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
import { PanelFetchError } from "./PanelFetchError";
import { formatDuration, formatNumber, formatRelativeIso, formatUsd, useInterval } from "./_utils";

import type { TradesaTrade } from "../../../types/tradesa_v2";

type SortKey = "closed_at" | "realized_pnl";
type SortDir = "asc" | "desc";

function SideBadge({ side }: { side: TradesaTrade["side"] }) {
  const cls =
    side === "long"
      ? "text-positive bg-positive/15 border-positive/40"
      : "text-negative bg-negative/15 border-negative/40";
  return (
    <span
      className={`text-micro inline-flex rounded border px-1.5 py-0.5 font-semibold tracking-wide uppercase ${cls}`}
    >
      {side}
    </span>
  );
}

function PnlCell({ value }: { value: number | null }) {
  if (value === null) return <span className="text-charcoal-500">—</span>;
  const cls = value >= 0 ? "text-positive" : "text-negative";
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
  const tile = "border-charcoal-800 bg-charcoal-900/40 rounded-md border px-3 py-2";
  return (
    <div
      data-testid="tradesa-trade-summary"
      className="border-charcoal-800 bg-charcoal-925/60 grid shrink-0 grid-cols-2 gap-2 border-b p-3 text-xs sm:grid-cols-4"
    >
      <div className={tile}>
        <div className="text-charcoal-500 text-micro tracking-wide uppercase">Today P&amp;L</div>
        <div
          className={`mt-0.5 font-mono text-sm ${stats.todayPnl >= 0 ? "text-positive" : "text-negative"}`}
        >
          {stats.todayPnl >= 0 ? "+" : ""}
          {formatUsd(stats.todayPnl)}
        </div>
      </div>
      <div className={tile}>
        <div className="text-charcoal-500 text-micro tracking-wide uppercase">7d P&amp;L</div>
        <div
          className={`mt-0.5 font-mono text-sm ${stats.weekPnl >= 0 ? "text-positive" : "text-negative"}`}
        >
          {stats.weekPnl >= 0 ? "+" : ""}
          {formatUsd(stats.weekPnl)}
        </div>
      </div>
      <div className={tile}>
        <div className="text-charcoal-500 text-micro tracking-wide uppercase">Closed</div>
        <div className="text-charcoal-200 mt-0.5 font-mono text-sm">{stats.totalCount}</div>
      </div>
      <div className={tile}>
        <div className="text-charcoal-500 text-micro tracking-wide uppercase">Win-rate</div>
        <div className="text-charcoal-200 mt-0.5 font-mono text-sm">
          {(stats.winRate * 100).toFixed(0)}%
          <span className="text-charcoal-500 text-micro ml-1">
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
        className="text-charcoal-500 flex flex-1 items-center justify-center p-6 text-sm"
      >
        No closed trades yet.
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-charcoal-925 sticky top-0 z-10">
            <tr className="border-charcoal-700 text-charcoal-500 border-b text-left text-[11px] font-medium tracking-wide uppercase">
              <th className="px-3 py-2">Instrument</th>
              <th className="px-3 py-2">Side</th>
              <th className="px-3 py-2 text-right">Qty</th>
              <th className="px-3 py-2 text-right">Entry</th>
              <th className="px-3 py-2 text-right">Exit</th>
              <th className="px-3 py-2 text-right">
                <button
                  type="button"
                  className="text-charcoal-400 hover:text-charcoal-200 inline-flex items-center text-[11px] font-medium tracking-wide uppercase"
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
                  className="text-charcoal-400 hover:text-charcoal-200 inline-flex items-center text-[11px] font-medium tracking-wide uppercase"
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
                className="border-charcoal-800 hover:bg-charcoal-800/40 border-b transition-colors"
              >
                <td className="px-3 py-2">
                  <span className="bg-charcoal-800 text-charcoal-200 inline-flex rounded px-1.5 py-0.5 font-mono text-xs">
                    {trade.instrument}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <SideBadge side={trade.side} />
                </td>
                <td className="text-charcoal-300 px-3 py-2 text-right font-mono text-xs">
                  {formatNumber(trade.qty, 4)}
                </td>
                <td className="text-charcoal-400 px-3 py-2 text-right font-mono text-xs">
                  {formatNumber(trade.entry_price, 2)}
                </td>
                <td className="text-charcoal-400 px-3 py-2 text-right font-mono text-xs">
                  {formatNumber(trade.exit_price, 2)}
                </td>
                <td className="px-3 py-2 text-right">
                  <PnlCell value={trade.realized_pnl} />
                </td>
                <td className="text-charcoal-400 px-3 py-2 text-right text-xs">
                  {formatDuration(trade.opened_at, trade.closed_at)}
                </td>
                <td className="text-charcoal-400 px-3 py-2 text-right text-xs">
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
      <PanelFetchError error={tradeHistoryState.error} onRetry={() => void refreshTradeHistory()} />
      <SummaryCard stats={stats} />
      <TradesTable rows={rows} />
    </PanelShell>
  );
}

export default TradeHistoryPanel;
