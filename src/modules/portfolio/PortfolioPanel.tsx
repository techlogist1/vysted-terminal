"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Briefcase, Check, Download, FolderPlus, Pencil, Plus, Trash2, X } from "lucide-react";

import { DataTable, type DataColumn } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { buildCsv, downloadCsv } from "@/lib/csv";
import {
  formatCompactMoney,
  formatMoney,
  formatPercent,
  formatSignedMoney,
  formatUnit,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { usePanelContextBus } from "@/store/panel-context";
import {
  type AssetClass,
  type Holding,
  type HoldingInput,
  usePortfoliosStore,
} from "@/store/portfolios";
import type { Position, Quote } from "../../../types/data";
import { fetchPositionQuotes } from "./api";
import { buildPortfolioSummary, type PositionRow } from "./metrics";

/** A holdings-table row — the computed position metrics joined to its source
 *  {@link Holding} (for edit/delete) by order. */
interface PortfolioTableRow extends PositionRow {
  holding: Holding | undefined;
}

/** Format a holding quantity — a precise count that still reads with a unit at
 *  scale (so a 12,000,000-share lot isn't a bare integer), full precision below. */
function fmtQuantity(quantity: number): string {
  if (Math.abs(quantity) >= 1000) return formatUnit(quantity);
  return quantity.toLocaleString("en-US", { maximumFractionDigits: 8 });
}

interface FormState {
  symbol: string;
  quantity: string;
  costBasis: string;
  assetClass: AssetClass;
  note: string;
}

function emptyForm(): FormState {
  return { symbol: "", quantity: "", costBasis: "", assetClass: "equity", note: "" };
}

/**
 * Portfolio panel — manually tracked holdings across one or more NAMED
 * portfolios the user can create, rename, switch between, and delete. Holdings
 * are hand-entered (symbol / quantity / cost basis / asset class) and persist in
 * the workspace blob; there is no broker sync. P&L, weight, and concentration
 * are computed client-side by joining each holding to a live quote.
 */
export function PortfolioPanel() {
  const portfolios = usePortfoliosStore((s) => s.portfolios);
  const activeId = usePortfoliosStore((s) => s.activeId);
  const createPortfolio = usePortfoliosStore((s) => s.createPortfolio);
  const renamePortfolio = usePortfoliosStore((s) => s.renamePortfolio);
  const deletePortfolio = usePortfoliosStore((s) => s.deletePortfolio);
  const setActive = usePortfoliosStore((s) => s.setActive);
  const addHolding = usePortfoliosStore((s) => s.addHolding);
  const updateHolding = usePortfoliosStore((s) => s.updateHolding);
  const removeHolding = usePortfoliosStore((s) => s.removeHolding);

  const active = useMemo(
    () => portfolios.find((p) => p.id === activeId) ?? portfolios[0],
    [portfolios, activeId],
  );
  const holdings = useMemo(() => active?.holdings ?? [], [active]);

  const [form, setForm] = useState<FormState>(emptyForm());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [quotes, setQuotes] = useState<Map<string, Quote>>(new Map());
  // Distinct from the form-validation `error`: a failed live-quote fetch must not
  // silently leave every Price/Mkt-val/P&L cell at "—" forever (A6 — failure is
  // designed for). `quotesNonce` lets the banner's Retry re-run the fetch.
  const [quotesError, setQuotesError] = useState(false);
  const [quotesNonce, setQuotesNonce] = useState(0);
  const symbolInputRef = useRef<HTMLInputElement | null>(null);

  // Portfolio header inline-edit state (create / rename).
  const [pfAction, setPfAction] = useState<null | "create" | "rename">(null);
  const [pfName, setPfName] = useState("");
  const pfInputRef = useRef<HTMLInputElement | null>(null);

  // Adapt holdings -> the Position shape buildPortfolioSummary expects (keeps
  // metrics.ts + its tests untouched). Order is preserved, so summary.rows[i]
  // corresponds to holdings[i] for edit/delete.
  const positions = useMemo<Position[]>(
    () =>
      holdings.map((h, i) => ({
        id: i,
        symbol: h.symbol,
        quantity: h.quantity,
        cost_basis: h.costBasis,
        asset_class: h.assetClass,
        opened_at: null,
        note: h.note ?? null,
      })),
    [holdings],
  );

  // Live quotes — refetched whenever the holding SET changes (symbols/classes).
  // Holdings render synchronously from the store; only the price / market-value
  // / P&L columns wait on the quote (they show "—" until it resolves).
  const quotesKey = holdings.map((h) => `${h.symbol}:${h.assetClass}`).join(",");
  useEffect(() => {
    let cancelled = false;
    // fetchPositionQuotes([]) resolves to an empty map, so an emptied portfolio
    // clears its quotes via the async path — no synchronous setState in-effect.
    void fetchPositionQuotes(holdings.map((h) => ({ symbol: h.symbol, assetClass: h.assetClass })))
      .then((q) => {
        if (!cancelled) {
          setQuotes(q);
          setQuotesError(false);
        }
      })
      .catch(() => {
        // A rejected quote fetch must not vanish — badge it so the user knows the
        // values are stale/absent rather than reading "—" as "no data".
        if (!cancelled) {
          setQuotesError(true);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quotesKey, quotesNonce]);

  const summary = useMemo(() => buildPortfolioSummary(positions, quotes), [positions, quotes]);

  // Clear a save/validation error as soon as the user edits any field.
  const formKey = `${form.symbol}|${form.quantity}|${form.costBasis}|${form.assetClass}|${form.note}`;
  useEffect(() => {
    if (error !== null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formKey]);

  // Focus the inline portfolio name input when create/rename opens.
  useEffect(() => {
    if (pfAction !== null) {
      pfInputRef.current?.focus();
      pfInputRef.current?.select();
    }
  }, [pfAction]);

  // --- panel-context bus: publish the ACTIVE portfolio's snapshot ----------
  // Multi-portfolio truth (FR-110/111, SC-024): publish the ACTIVE portfolio's
  // full holdings — symbol/quantity/costBasis/assetClass, plus the computed
  // marketValue/pnl per row where a live quote resolved (null otherwise, so the
  // payload stays provenance-honest) — alongside the active id/name. The chat
  // context-provider extracts these so the agent's get_portfolio reads the real
  // store with zero divergence.
  const publishPanelContext = usePanelContextBus((s) => s.publish);
  const unregisterPanelContext = usePanelContextBus((s) => s.unregisterSource);
  const positionCount = summary.rows.length;
  const totalValue = summary.totalMarketValue;
  const activePortfolioId = active?.id ?? null;
  const activePortfolioName = active?.name ?? null;
  // Serialise the published holdings as a stable string so the publish effect
  // only fires when the holdings (or their resolved P&L) actually change.
  const publishedHoldings = useMemo(
    () =>
      summary.rows.map(({ position, marketValue, pnl }) => ({
        symbol: position.symbol,
        quantity: position.quantity,
        costBasis: position.cost_basis,
        assetClass: position.asset_class === "crypto" ? "crypto" : "equity",
        marketValue: marketValue ?? null,
        pnl: pnl ?? null,
      })),
    [summary.rows],
  );
  const holdingsKey = JSON.stringify(publishedHoldings);
  useEffect(() => {
    publishPanelContext({
      source: "portfolio",
      kind: "snapshot",
      payload: {
        positionCount,
        totalValue,
        activePortfolioId,
        activePortfolioName,
        holdings: publishedHoldings,
      },
      emittedAt: Date.now(),
    });
    // `publishedHoldings` is captured fresh whenever `holdingsKey` changes; the
    // key is the exhaustive dep so we don't re-publish on referential churn.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    publishPanelContext,
    positionCount,
    totalValue,
    activePortfolioId,
    activePortfolioName,
    holdingsKey,
  ]);
  useEffect(() => {
    return () => {
      unregisterPanelContext("portfolio");
    };
  }, [unregisterPanelContext]);

  const resetForm = () => {
    setForm(emptyForm());
    setEditingId(null);
  };

  const handleSubmit = (event: React.FormEvent) => {
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
    const input: HoldingInput = {
      symbol: form.symbol.trim().toUpperCase(),
      quantity,
      costBasis,
      assetClass: form.assetClass,
      note: form.note.trim() === "" ? undefined : form.note.trim(),
    };
    if (editingId !== null) {
      updateHolding(active.id, editingId, input);
    } else {
      addHolding(active.id, input);
    }
    setError(null);
    resetForm();
  };

  const handleEdit = (holding: Holding) => {
    setForm({
      symbol: holding.symbol,
      quantity: String(holding.quantity),
      costBasis: String(holding.costBasis),
      assetClass: holding.assetClass,
      note: holding.note ?? "",
    });
    setEditingId(holding.id);
  };

  const handleDelete = (id: string) => {
    if (editingId === id) {
      resetForm();
    }
    removeHolding(active.id, id);
  };

  // Join each computed metrics row to its source holding (by order) so the
  // action column can edit/delete; rebuilt only when the metrics or holdings move.
  const tableRows = useMemo<PortfolioTableRow[]>(
    () => summary.rows.map((row, i) => ({ ...row, holding: holdings[i] })),
    [summary.rows, holdings],
  );

  // The 8-column holdings table on the shared DataTable. The P&L column is the
  // one signed/coloured value (green/red, never the accent); the trailing column
  // is a DataTable action column (edit/delete, outside truncation). All money
  // runs through format.ts; the quantity reads with a unit at scale.
  const holdingColumns = useMemo<DataColumn<PortfolioTableRow>[]>(
    () => [
      {
        key: "symbol",
        header: "Symbol",
        truncate: true,
        width: "18%",
        format: (r) => r.position.symbol,
      },
      {
        key: "quantity",
        header: "Qty",
        numeric: true,
        tier: "secondary",
        width: "10%",
        format: (r) => fmtQuantity(r.position.quantity),
      },
      {
        key: "cost",
        header: "Cost",
        numeric: true,
        tier: "secondary",
        width: "12%",
        format: (r) => formatMoney(r.position.cost_basis),
      },
      {
        key: "price",
        header: "Price",
        numeric: true,
        tier: "secondary",
        width: "12%",
        format: (r) => (r.quote !== null ? formatMoney(r.quote.price) : null),
      },
      {
        key: "marketValue",
        header: "Mkt val",
        numeric: true,
        width: "13%",
        format: (r) => (r.marketValue !== null ? formatCompactMoney(r.marketValue) : null),
      },
      {
        key: "pnl",
        header: "P&L",
        numeric: true,
        width: "20%",
        cell: (r) =>
          r.pnl === null ? null : (
            <span
              className={
                r.pnl > 0 ? "text-positive" : r.pnl < 0 ? "text-negative" : "text-charcoal-200"
              }
            >
              {`${formatSignedMoney(r.pnl, true)} (${r.pnlPercent !== null ? formatPercent(r.pnlPercent) : "—"})`}
            </span>
          ),
      },
      {
        key: "weight",
        header: "Wt",
        numeric: true,
        tier: "secondary",
        width: "8%",
        format: (r) => (r.weight !== null ? `${(r.weight * 100).toFixed(1)}%` : null),
      },
      {
        key: "actions",
        action: true,
        width: "7%",
        cell: (r) => (
          <>
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              aria-label={`Edit ${r.position.symbol}`}
              onClick={() => r.holding && handleEdit(r.holding)}
            >
              <Pencil />
            </Button>
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              aria-label={`Delete ${r.position.symbol}`}
              onClick={() => r.holding && handleDelete(r.holding.id)}
            >
              <Trash2 />
            </Button>
          </>
        ),
      },
    ],
    // handleEdit/handleDelete are stable enough across renders; the table only
    // needs to rebuild when nothing data-bearing changes here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const submitPfName = () => {
    const name = pfName.trim();
    if (name === "") {
      setPfAction(null);
      setPfName("");
      return;
    }
    if (pfAction === "create") {
      createPortfolio(name);
    } else if (pfAction === "rename") {
      renamePortfolio(active.id, name);
    }
    setPfAction(null);
    setPfName("");
  };

  const cancelPf = () => {
    setPfAction(null);
    setPfName("");
  };

  // Export the active portfolio to CSV — the hand-entered fields plus the
  // live-quote-derived market value / P&L / weight (blank where no quote
  // resolved, so the export stays provenance-honest). No-op when empty.
  const handleExport = () => {
    if (summary.rows.length === 0) {
      return;
    }
    const csv = buildCsv(
      [
        "Symbol",
        "Quantity",
        "Cost basis",
        "Asset class",
        "Price",
        "Market value",
        "P&L",
        "P&L %",
        "Weight %",
        "Note",
      ],
      summary.rows.map(({ position, quote, marketValue, pnl, pnlPercent, weight }) => [
        position.symbol,
        position.quantity,
        position.cost_basis,
        position.asset_class,
        quote?.price ?? "",
        marketValue ?? "",
        pnl ?? "",
        pnlPercent ?? "",
        weight !== null ? (weight * 100).toFixed(2) : "",
        position.note ?? "",
      ]),
    );
    const safeName =
      active.name
        .trim()
        .replace(/[^a-z0-9]+/gi, "-")
        .toLowerCase() || "portfolio";
    downloadCsv(`vysted-portfolio-${safeName}.csv`, csv);
  };

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      {/* Portfolio switcher / create / rename / delete. */}
      <div className="border-charcoal-700 flex items-center gap-2 border-b px-3 py-2">
        {pfAction !== null ? (
          <>
            <input
              ref={pfInputRef}
              value={pfName}
              onChange={(event) => setPfName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  submitPfName();
                } else if (event.key === "Escape") {
                  event.preventDefault();
                  cancelPf();
                }
              }}
              placeholder={pfAction === "create" ? "New portfolio name" : "Rename portfolio"}
              aria-label={pfAction === "create" ? "New portfolio name" : "Rename portfolio"}
              className="bg-charcoal-800 text-charcoal-100 text-body h-9 min-w-0 flex-1 rounded-md px-3 outline-none focus:ring-1 focus:ring-amber-400"
            />
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              aria-label="Confirm"
              onClick={submitPfName}
            >
              <Check />
            </Button>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              aria-label="Cancel"
              onClick={cancelPf}
            >
              <X />
            </Button>
          </>
        ) : (
          <>
            <Briefcase className="text-charcoal-500 size-4 shrink-0" aria-hidden="true" />
            <select
              aria-label="Active portfolio"
              value={active.id}
              onChange={(event) => setActive(event.target.value)}
              className="bg-charcoal-800 text-charcoal-100 text-body h-9 min-w-0 flex-1 rounded-md px-3 outline-none focus:ring-1 focus:ring-amber-400"
            >
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {p.holdings.length > 0 ? ` · ${p.holdings.length}` : ""}
                </option>
              ))}
            </select>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              aria-label="New portfolio"
              title="New portfolio"
              onClick={() => {
                setPfAction("create");
                setPfName("");
              }}
            >
              <FolderPlus />
            </Button>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              aria-label="Rename portfolio"
              title="Rename portfolio"
              onClick={() => {
                setPfAction("rename");
                setPfName(active.name);
              }}
            >
              <Pencil />
            </Button>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              aria-label="Export portfolio to CSV"
              title="Export portfolio to CSV"
              onClick={handleExport}
              disabled={holdings.length === 0}
            >
              <Download />
            </Button>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              aria-label="Delete portfolio"
              title="Delete portfolio"
              onClick={() => deletePortfolio(active.id)}
            >
              <Trash2 />
            </Button>
          </>
        )}
      </div>

      {/* Add / edit a holding. */}
      <form
        onSubmit={handleSubmit}
        className="border-charcoal-700 flex flex-wrap items-end gap-2 border-b p-3"
      >
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-micro">Symbol</span>
          <input
            ref={symbolInputRef}
            aria-label="Symbol"
            value={form.symbol}
            onChange={(event) => setForm((prev) => ({ ...prev, symbol: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 text-body h-9 w-24 rounded-md px-3 outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-micro">Quantity</span>
          <input
            aria-label="Quantity"
            inputMode="decimal"
            value={form.quantity}
            onChange={(event) => setForm((prev) => ({ ...prev, quantity: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 text-body h-9 w-24 rounded-md px-3 outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-micro">Cost basis</span>
          <input
            aria-label="Cost basis"
            inputMode="decimal"
            value={form.costBasis}
            onChange={(event) => setForm((prev) => ({ ...prev, costBasis: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 text-body h-9 w-24 rounded-md px-3 outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-micro">Class</span>
          <select
            aria-label="Asset class"
            value={form.assetClass}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                assetClass: event.target.value === "crypto" ? "crypto" : "equity",
              }))
            }
            className="bg-charcoal-800 text-charcoal-200 text-caption h-9 rounded-md px-3 outline-none focus:ring-1 focus:ring-amber-400"
          >
            <option value="equity">Equity</option>
            <option value="crypto">Crypto</option>
          </select>
        </label>
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-charcoal-400 text-micro">Note</span>
          <input
            aria-label="Note"
            value={form.note}
            onChange={(event) => setForm((prev) => ({ ...prev, note: event.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 text-body h-9 min-w-24 rounded-md px-3 outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
        <Button type="submit" size="sm" variant="outline">
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
        <div className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2">
          <p className="text-negative text-caption">{error}</p>
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

      {summary.rows.length > 0 && (
        <div className="border-charcoal-700 text-charcoal-200 text-caption flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-3 py-2 tabular-nums">
          <span className="whitespace-nowrap">
            Market value:{" "}
            <span className="text-charcoal-100">
              {formatCompactMoney(summary.totalMarketValue)}
            </span>
          </span>
          <span aria-hidden="true" className="text-charcoal-600">
            ·
          </span>
          <span className="whitespace-nowrap">
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
          <span aria-hidden="true" className="text-charcoal-600">
            ·
          </span>
          <span className="whitespace-nowrap">
            Concentration:{" "}
            <span className="text-charcoal-100">{(summary.concentration * 100).toFixed(1)}%</span>
          </span>
          {summary.unresolvedCount > 0 && (
            <>
              <span aria-hidden="true" className="text-charcoal-600">
                ·
              </span>
              <span className="text-charcoal-400 whitespace-nowrap">
                {summary.unresolvedCount} without a live quote
              </span>
            </>
          )}
        </div>
      )}

      {quotesError && holdings.length > 0 && (
        <div className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2">
          <span className="text-warning text-caption">
            Couldn&apos;t refresh live quotes — values shown without market data.
          </span>
          <button
            type="button"
            onClick={() => setQuotesNonce((n) => n + 1)}
            className="text-caption text-amber-300 transition-colors hover:text-amber-200"
          >
            Retry
          </button>
        </div>
      )}

      <div className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto">
        {holdings.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            headline="This portfolio is empty"
            hint="Manually add a stock or crypto holding to track P&L, weight, and concentration — no broker connection required."
            cta={{
              label: "Add your first holding",
              primary: true,
              onClick: () => symbolInputRef.current?.focus(),
            }}
          />
        ) : (
          <DataTable
            columns={holdingColumns}
            rows={tableRows}
            rowKey={(row) => row.holding?.id ?? row.position.symbol}
            minWidth="min-w-[680px]"
            data-testid="portfolio-holdings-table"
          />
        )}
      </div>
    </div>
  );
}
