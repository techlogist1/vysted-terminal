"use client";

import { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SidecarError } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import type { Position, PositionInput } from "../../../types/data";
import {
  createPosition,
  deletePosition,
  fetchPositionQuotes,
  fetchPositions,
  updatePosition,
} from "./api";
import { buildPortfolioSummary, type PortfolioSummary } from "./metrics";

function formatMoney(value: number): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

function formatSignedMoney(value: number): string {
  return `${value > 0 ? "+" : ""}${formatMoney(value)}`;
}

function formatPercent(value: number): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

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

  const load = useCallback(async () => {
    try {
      const stored = await fetchPositions();
      const quotes = await fetchPositionQuotes(stored);
      setSummary(buildPortfolioSummary(stored, quotes));
      setError(null);
    } catch (err) {
      const message = err instanceof SidecarError ? err.message : "Failed to load portfolio";
      setSummary(buildPortfolioSummary([], new Map()));
      setError(message);
    }
  }, []);

  useEffect(() => {
    // `load` only sets state after an awaited fetch resolves (never
    // synchronously), so the cascading-render concern does not apply.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

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
            aria-label="Symbol"
            value={form.symbol}
            onChange={(event) => setForm((prev) => ({ ...prev, symbol: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 h-8 w-24 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[0.6rem] uppercase">Quantity</span>
          <input
            aria-label="Quantity"
            inputMode="decimal"
            value={form.quantity}
            onChange={(event) => setForm((prev) => ({ ...prev, quantity: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 h-8 w-24 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[0.6rem] uppercase">Cost basis</span>
          <input
            aria-label="Cost basis"
            inputMode="decimal"
            value={form.costBasis}
            onChange={(event) => setForm((prev) => ({ ...prev, costBasis: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 h-8 w-24 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[0.6rem] uppercase">Class</span>
          <select
            aria-label="Asset class"
            value={form.assetClass}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                assetClass: event.target.value === "crypto" ? "crypto" : "equity",
              }))
            }
            className="bg-charcoal-800 text-charcoal-200 h-8 rounded-md px-2 font-mono text-xs outline-none"
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
            onChange={(event) => setForm((prev) => ({ ...prev, note: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 h-8 min-w-24 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
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

      {error !== null && (
        <p className="text-negative border-charcoal-700 border-b px-3 py-2 font-mono text-xs">
          {error}
        </p>
      )}

      {summary !== null && summary.rows.length > 0 && (
        <div className="border-charcoal-700 text-charcoal-200 flex flex-wrap gap-x-6 gap-y-1 border-b px-3 py-2 font-mono text-xs">
          <span>
            Market value:{" "}
            <span className="text-charcoal-100">{formatMoney(summary.totalMarketValue)}</span>
          </span>
          <span>
            Total P&amp;L:{" "}
            <span className={summary.totalPnl >= 0 ? "text-positive" : "text-negative"}>
              {formatSignedMoney(summary.totalPnl)} ({formatPercent(summary.totalPnlPercent)})
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
          <p className="text-charcoal-400 p-4 font-mono text-xs">Loading portfolio…</p>
        ) : summary.rows.length === 0 ? (
          <p className="text-charcoal-400 p-4 font-mono text-xs">
            No positions yet — add one above.
          </p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-charcoal-400 border-charcoal-700 border-b text-left font-mono text-[0.65rem] uppercase">
                <th className="px-3 py-2 font-medium">Symbol</th>
                <th className="px-3 py-2 text-right font-medium">Qty</th>
                <th className="px-3 py-2 text-right font-medium">Cost</th>
                <th className="px-3 py-2 text-right font-medium">Price</th>
                <th className="px-3 py-2 text-right font-medium">Mkt value</th>
                <th className="px-3 py-2 text-right font-medium">P&amp;L</th>
                <th className="px-3 py-2 text-right font-medium">Weight</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {summary.rows.map(({ position, quote, marketValue, pnl, pnlPercent, weight }) => {
                const pnlPositive = (pnl ?? 0) >= 0;
                return (
                  <tr
                    key={position.id ?? position.symbol}
                    className="border-charcoal-800 hover:bg-charcoal-800/50 border-b font-mono text-sm"
                  >
                    <td className="text-charcoal-100 max-w-24 truncate px-3 py-2">
                      {position.symbol}
                    </td>
                    <td className="text-charcoal-200 px-3 py-2 text-right">{position.quantity}</td>
                    <td className="text-charcoal-200 px-3 py-2 text-right">
                      {formatMoney(position.cost_basis)}
                    </td>
                    <td className="text-charcoal-200 px-3 py-2 text-right">
                      {quote !== null ? formatMoney(quote.price) : "—"}
                    </td>
                    <td className="text-charcoal-200 px-3 py-2 text-right">
                      {marketValue !== null ? formatMoney(marketValue) : "—"}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 text-right",
                        pnl === null
                          ? "text-charcoal-400"
                          : pnlPositive
                            ? "text-positive"
                            : "text-negative",
                      )}
                    >
                      {pnl !== null && pnlPercent !== null
                        ? `${formatSignedMoney(pnl)} (${formatPercent(pnlPercent)})`
                        : "—"}
                    </td>
                    <td className="text-charcoal-200 px-3 py-2 text-right">
                      {weight !== null ? `${(weight * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        aria-label={`Edit ${position.symbol}`}
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
