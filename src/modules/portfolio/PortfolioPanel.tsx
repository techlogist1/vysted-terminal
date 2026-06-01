"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Briefcase, Pencil, Plus, Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatCompactMoney, formatMoney, formatPercent, formatSignedMoney } from "@/lib/format";
import { SidecarError } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { usePanelContextBus } from "@/store/panel-context";
import type { Position, PositionInput } from "../../../types/data";
import {
  createPosition,
  deletePosition,
  fetchPositionQuotes,
  fetchPositions,
  updatePosition,
} from "./api";
import { buildPortfolioSummary, type PortfolioSummary } from "./metrics";

interface FormState {
  symbol: string;
  quantity: string;
  costBasis: string;
  assetClass: "equity" | "crypto";
  note: string;
}

function toFormState(position?: Position): FormState {
  return {
    symbol: position?.symbol ?? "",
    quantity: position ? String(position.quantity) : "",
    costBasis: position ? String(position.cost_basis) : "",
    assetClass: position?.asset_class === "crypto" ? "crypto" : "equity",
    note: position?.note ?? "",
  };
}

/**
 * Portfolio panel — manual positions backed by the sidecar SQLite store, with
 * P&L, weight, and basic risk metrics computed client-side by joining each
 * position to a live quote. Add / edit / delete are all manual entry (broker
 * connection is Phase 5).
 */
export function PortfolioPanel() {
  // `summary` is `null` until the first load resolves — that drives the loading
  // view without a synchronous setState inside the effect.
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(toFormState());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  // Ref for the Symbol input — used by the empty-state CTA to focus it.
  const symbolInputRef = useRef<HTMLInputElement | null>(null);
  // Pending auto-retry timer for the cold-boot bind race — cleared on unmount.
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Holds the current `load` so the retry timer can re-invoke it without `load`
  // referencing itself inside its own useCallback (rules-of-hooks immutability).
  const loadRef = useRef<(attempt?: number) => void>(() => {});

  const load = useCallback(async (attempt = 0) => {
    try {
      const stored = await fetchPositions();
      const quotes = await fetchPositionQuotes(stored);
      setSummary(buildPortfolioSummary(stored, quotes));
      setError(null);
    } catch (err) {
      // Auto-retry with backoff (1s, 2s, 4s, then capped at 5s for ~12 attempts
      // ≈ 50s) so a cold-boot sidecar bind (PyInstaller `_MEI` re-exec, ~30s)
      // self-heals instead of latching a permanent error block.
      if (attempt < 12) {
        retryTimer.current = setTimeout(
          () => loadRef.current(attempt + 1),
          Math.min(1000 * 2 ** attempt, 5000),
        );
        return;
      }
      const message = err instanceof SidecarError ? err.message : "Failed to load portfolio";
      setSummary(null);
      setError(message);
    }
  }, []);
  // Keep the retry-callback ref pointed at the latest `load` (assigned in an
  // effect, never during render).
  useEffect(() => {
    loadRef.current = load;
  }, [load]);

  // Clear a save/validation error as soon as the user edits any field — the
  // red bar should not persist after the input has been corrected.
  const formKey = `${form.symbol}|${form.quantity}|${form.costBasis}|${form.assetClass}|${form.note}`;
  useEffect(() => {
    // Only clear errors that belong to the save/validate path (summary !== null
    // means positions are loaded — the load-error path clears on its own via load()).
    if (error !== null && summary !== null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formKey]);

  useEffect(() => {
    // `load` only sets state after an awaited fetch resolves (never
    // synchronously), so the cascading-render concern does not apply.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    return () => {
      if (retryTimer.current) {
        clearTimeout(retryTimer.current);
        retryTimer.current = null;
      }
    };
  }, [load]);

  // --- panel-context bus: publish snapshot on positions change ------------
  const publishPanelContext = usePanelContextBus((s) => s.publish);
  const unregisterPanelContext = usePanelContextBus((s) => s.unregisterSource);

  // Depend on primitive snapshot fields, not the `summary` object itself —
  // a re-build of summary that yields the same count/value should NOT trigger
  // a publish (Phase-2 chart-sync infinite-loop avoidance).
  const positionCount = summary?.rows.length ?? 0;
  const totalValue = summary?.totalMarketValue ?? 0;

  useEffect(() => {
    publishPanelContext({
      source: "portfolio",
      kind: "snapshot",
      payload: {
        positionCount,
        totalValue,
      },
      emittedAt: Date.now(),
    });
  }, [publishPanelContext, positionCount, totalValue]);

  useEffect(() => {
    return () => {
      unregisterPanelContext("portfolio");
    };
  }, [unregisterPanelContext]);

  const resetForm = () => {
    setForm(toFormState());
    setEditingId(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const quantity = Number(form.quantity);
    const costBasis = Number(form.costBasis);
    if (form.symbol.trim() === "" || !Number.isFinite(quantity) || !Number.isFinite(costBasis)) {
      setError("Symbol, quantity, and cost basis are required");
      return;
    }
    if (quantity <= 0) {
      setError("Quantity must be greater than 0");
      return;
    }
    if (costBasis < 0) {
      setError("Cost basis cannot be negative");
      return;
    }
    const payload: PositionInput = {
      symbol: form.symbol.trim().toUpperCase(),
      quantity,
      cost_basis: costBasis,
      asset_class: form.assetClass,
      opened_at: null,
      note: form.note.trim() === "" ? null : form.note.trim(),
    };
    setBusy(true);
    try {
      if (editingId !== null) {
        await updatePosition(editingId, payload);
      } else {
        await createPosition(payload);
      }
      resetForm();
      await load();
    } catch (err) {
      const message = err instanceof SidecarError ? err.message : "Failed to save position";
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  const handleEdit = (position: Position) => {
    setForm(toFormState(position));
    setEditingId(position.id);
  };

  const handleDelete = async (id: number | null) => {
    if (id === null) {
      return;
    }
    setBusy(true);
    try {
      await deletePosition(id);
      if (editingId === id) {
        resetForm();
      }
      await load();
    } catch (err) {
      const message = err instanceof SidecarError ? err.message : "Failed to delete position";
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <form
        onSubmit={handleSubmit}
        className="border-charcoal-700 flex flex-wrap items-end gap-2 border-b p-3"
      >
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[0.6rem] uppercase">Symbol</span>
          <input
            ref={symbolInputRef}
            aria-label="Symbol"
            value={form.symbol}
            disabled={busy}
            onChange={(event) => setForm((prev) => ({ ...prev, symbol: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 h-8 w-24 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-50"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[0.6rem] uppercase">Quantity</span>
          <input
            aria-label="Quantity"
            inputMode="decimal"
            value={form.quantity}
            disabled={busy}
            onChange={(event) => setForm((prev) => ({ ...prev, quantity: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 h-8 w-24 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-50"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[0.6rem] uppercase">Cost basis</span>
          <input
            aria-label="Cost basis"
            inputMode="decimal"
            value={form.costBasis}
            disabled={busy}
            onChange={(event) => setForm((prev) => ({ ...prev, costBasis: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 h-8 w-24 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-50"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[0.6rem] uppercase">Class</span>
          <select
            aria-label="Asset class"
            value={form.assetClass}
            disabled={busy}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                assetClass: event.target.value === "crypto" ? "crypto" : "equity",
              }))
            }
            className="bg-charcoal-800 text-charcoal-200 h-8 rounded-md px-2 font-mono text-xs outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-50"
          >
            <option value="equity">Equity</option>
            <option value="crypto">Crypto</option>
          </select>
        </label>
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[0.6rem] uppercase">Note</span>
          <input
            aria-label="Note"
            value={form.note}
            disabled={busy}
            onChange={(event) => setForm((prev) => ({ ...prev, note: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 h-8 min-w-24 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-50"
          />
        </label>
        <Button type="submit" size="sm" variant="outline" disabled={busy}>
          <Plus />
          {editingId !== null ? "Save" : "Add"}
        </Button>
        {editingId !== null && (
          <Button
            type="button"
            size="icon-sm"
            variant="ghost"
            aria-label="Cancel edit"
            onClick={resetForm}
          >
            <X />
          </Button>
        )}
      </form>

      {error !== null && summary === null && (
        <div className="border-charcoal-700 flex items-center gap-3 border-b px-3 py-2">
          <p className="text-negative font-mono text-xs">{error}</p>
          <Button type="button" size="sm" variant="outline" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      )}
      {error !== null && summary !== null && (
        <div className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2">
          <p className="text-negative font-mono text-xs">{error}</p>
          <button
            type="button"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
            className="text-charcoal-400 hover:text-charcoal-200 ml-auto pl-3"
          >
            <X className="size-3" />
          </button>
        </div>
      )}

      {summary !== null && summary.rows.length > 0 && (
        <div className="border-charcoal-700 text-charcoal-200 flex flex-wrap gap-x-6 gap-y-1 border-b px-3 py-2 font-mono text-xs">
          <span>
            Market value:{" "}
            <span className="text-charcoal-100">
              {formatCompactMoney(summary.totalMarketValue)}
            </span>
          </span>
          <span>
            Total P&amp;L:{" "}
            <span
              className={
                summary.totalPnl > 0
                  ? "text-positive"
                  : summary.totalPnl < 0
                    ? "text-negative"
                    : "text-charcoal-200"
              }
            >
              {formatSignedMoney(summary.totalPnl, true)} ({formatPercent(summary.totalPnlPercent)})
            </span>
          </span>
          <span>
            Concentration:{" "}
            <span className="text-charcoal-100">{(summary.concentration * 100).toFixed(1)}%</span>
          </span>
          {summary.unresolvedCount > 0 && (
            <span className="text-charcoal-400">
              {summary.unresolvedCount} symbol(s) without a live quote
            </span>
          )}
        </div>
      )}

      <div className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto">
        {summary === null ? (
          <table className="w-full table-fixed border-collapse animate-pulse">
            <colgroup>
              <col style={{ width: "18%" }} />
              <col style={{ width: "8%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "22%" }} />
              <col style={{ width: "9%" }} />
              <col style={{ width: "7%" }} />
            </colgroup>
            <tbody>
              {Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-charcoal-800 border-b">
                  {[36, 20, 28, 28, 32, 52, 22, 16].map((w, j) => (
                    <td key={j} className="px-3 py-2">
                      <div
                        className={`bg-charcoal-800 h-3 rounded`}
                        style={{ width: `${w}%`, marginLeft: j > 0 ? "auto" : undefined }}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : summary.rows.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
            <Briefcase className="text-charcoal-600 size-8" />
            <p className="text-charcoal-300 font-mono text-sm">No positions tracked</p>
            <p className="text-charcoal-500 font-mono text-xs">
              Manually add a stock or crypto holding to see P&amp;L, weight, and risk metrics.
            </p>
            <button
              type="button"
              onClick={() => symbolInputRef.current?.focus()}
              className="border-charcoal-700 bg-charcoal-800 text-charcoal-300 rounded-md border px-3 py-1.5 font-mono text-xs transition-colors hover:border-amber-500 hover:text-amber-300"
            >
              Add your first position
            </button>
          </div>
        ) : (
          <table className="w-full table-fixed border-collapse">
            {/* Explicit column widths so the 8-column table holds at the
                enforced minimum panel width without cells colliding.
                Symbol gives way first (truncates); numeric columns hold.  */}
            <colgroup>
              <col style={{ width: "18%" }} />
              <col style={{ width: "8%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "22%" }} />
              <col style={{ width: "9%" }} />
              <col style={{ width: "7%" }} />
            </colgroup>
            <thead>
              <tr className="text-charcoal-400 border-charcoal-700 border-b text-left font-mono text-[0.65rem] uppercase">
                <th className="px-3 py-2 font-medium">Symbol</th>
                <th className="px-3 py-2 text-right font-medium">Qty</th>
                <th className="px-3 py-2 text-right font-medium">Cost</th>
                <th className="px-3 py-2 text-right font-medium">Price</th>
                <th className="px-3 py-2 text-right font-medium">Mkt val</th>
                <th className="px-3 py-2 text-right font-medium">P&amp;L</th>
                <th className="px-3 py-2 text-right font-medium">Wt</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {summary.rows.map(({ position, quote, marketValue, pnl, pnlPercent, weight }) => {
                const pnlColor =
                  pnl === null
                    ? "text-charcoal-400"
                    : pnl > 0
                      ? "text-positive"
                      : pnl < 0
                        ? "text-negative"
                        : "text-charcoal-200";
                return (
                  <tr
                    key={position.id ?? position.symbol}
                    className="border-charcoal-800 hover:bg-charcoal-800/50 border-b font-mono text-sm"
                  >
                    <td className="text-charcoal-100 overflow-hidden px-3 py-2">
                      <span className="block truncate">{position.symbol}</span>
                    </td>
                    <td className="text-charcoal-200 overflow-hidden px-3 py-2 text-right whitespace-nowrap tabular-nums">
                      <span className="block truncate">
                        {typeof position.quantity === "number"
                          ? position.quantity.toLocaleString("en-US", { maximumFractionDigits: 8 })
                          : position.quantity}
                      </span>
                    </td>
                    <td className="text-charcoal-200 overflow-hidden px-3 py-2 text-right whitespace-nowrap tabular-nums">
                      <span className="block truncate">{formatMoney(position.cost_basis)}</span>
                    </td>
                    <td className="text-charcoal-200 overflow-hidden px-3 py-2 text-right whitespace-nowrap tabular-nums">
                      <span className="block truncate">
                        {quote !== null ? formatMoney(quote.price) : "—"}
                      </span>
                    </td>
                    <td className="text-charcoal-200 overflow-hidden px-3 py-2 text-right whitespace-nowrap tabular-nums">
                      <span className="block truncate">
                        {marketValue !== null ? formatCompactMoney(marketValue) : "—"}
                      </span>
                    </td>
                    <td className={cn("max-w-0 overflow-hidden px-3 py-2 text-right", pnlColor)}>
                      <span className="block truncate whitespace-nowrap">
                        {pnl !== null
                          ? `${formatSignedMoney(pnl, true)} (${pnlPercent !== null ? formatPercent(pnlPercent) : "—"})`
                          : "—"}
                      </span>
                    </td>
                    <td className="text-charcoal-200 overflow-hidden px-3 py-2 text-right whitespace-nowrap tabular-nums">
                      <span className="block truncate">
                        {weight !== null ? `${(weight * 100).toFixed(1)}%` : "—"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        aria-label={`Edit ${position.symbol}`}
                        disabled={busy}
                        onClick={() => handleEdit(position)}
                      >
                        <Pencil />
                      </Button>
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        aria-label={`Delete ${position.symbol}`}
                        onClick={() => handleDelete(position.id)}
                        disabled={busy}
                      >
                        <Trash2 />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
