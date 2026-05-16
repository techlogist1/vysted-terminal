"use client";

/**
 * BrokerOrderEntry — manual order entry surface.
 *
 * The user picks a connected broker, fills in the order shape (symbol, side,
 * type, quantity, limit/stop), and clicks Propose. The component POSTs
 * `/brokers/{id}/orders` (route owned by Teammate I — see
 * sidecar/routers/brokers.py), receives back a `BrokerOrderProposal`, pushes
 * it into `useOrdersStore`, and opens the `OrderConfirmationDialog`.
 */

import { useCallback, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useBrokersStore } from "@/store/brokers";
import { useOrdersStore } from "@/store/orders";

import type {
  BrokerId,
  BrokerOrderProposal,
  BrokerOrderSide,
  BrokerOrderType,
} from "../../../types/broker";

interface FormState {
  broker: BrokerId | null;
  symbol: string;
  side: BrokerOrderSide;
  type: BrokerOrderType;
  quantity: string;
  limitPrice: string;
  stopPrice: string;
}

const initialForm: FormState = {
  broker: null,
  symbol: "",
  side: "buy",
  type: "limit",
  quantity: "",
  limitPrice: "",
  stopPrice: "",
};

export function BrokerOrderEntry() {
  const byId = useBrokersStore((s) => s.byId);
  const addProposal = useOrdersStore((s) => s.addProposal);
  const openProposal = useOrdersStore((s) => s.openProposal);

  const [form, setForm] = useState<FormState>(initialForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connectedBrokers = useMemo(
    () =>
      Object.values(byId)
        .filter((b): b is NonNullable<typeof b> => b !== undefined)
        .filter((b) => b.status === "connected"),
    [byId],
  );

  const handleSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (form.broker === null) {
        setError("Select a broker");
        return;
      }
      const quantity = Number(form.quantity);
      if (!Number.isFinite(quantity) || quantity <= 0) {
        setError("Quantity must be positive");
        return;
      }
      const limitPrice =
        form.limitPrice.length > 0 ? Number(form.limitPrice) : undefined;
      const stopPrice = form.stopPrice.length > 0 ? Number(form.stopPrice) : undefined;
      setBusy(true);
      setError(null);
      try {
        const base = await getSidecarBaseUrl();
        const response = await fetch(
          new URL(`/brokers/${encodeURIComponent(form.broker)}/orders`, base).toString(),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              symbol: form.symbol,
              side: form.side,
              type: form.type,
              quantity,
              limitPrice,
              stopPrice,
              source: "manual",
            }),
          },
        );
        if (!response.ok) {
          let detail = response.statusText;
          try {
            const body = (await response.json()) as { detail?: string };
            if (body.detail !== undefined) {
              detail = body.detail;
            }
          } catch {
            // ignore
          }
          throw new Error(detail);
        }
        const proposal = (await response.json()) as BrokerOrderProposal;
        addProposal(proposal);
        openProposal(proposal.proposalId);
        setForm(initialForm);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Propose failed");
      } finally {
        setBusy(false);
      }
    },
    [addProposal, form, openProposal],
  );

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="broker-order-entry"
      className="flex flex-col gap-2 p-3 font-mono text-xs text-charcoal-100"
    >
      <label className="flex flex-col gap-1">
        <span className="text-charcoal-400 text-[10px] uppercase">Broker</span>
        <select
          value={form.broker ?? ""}
          onChange={(e) =>
            setForm((prev) => ({ ...prev, broker: (e.target.value || null) as BrokerId | null }))
          }
          className="bg-charcoal-800 text-charcoal-100 h-8 rounded-md px-2 text-xs outline-none"
        >
          <option value="">Choose a broker</option>
          {connectedBrokers.map((b) => (
            <option key={b.broker} value={b.broker}>
              {b.broker} ({b.mode}
              {b.readOnly ? " · read-only" : ""})
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-charcoal-400 text-[10px] uppercase">Symbol</span>
        <input
          value={form.symbol}
          onChange={(e) => setForm((prev) => ({ ...prev, symbol: e.target.value.toUpperCase() }))}
          className="bg-charcoal-800 text-charcoal-100 h-8 rounded-md px-2 text-sm outline-none focus:ring-1 focus:ring-amber-400"
        />
      </label>

      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-[10px] uppercase">Side</span>
          <select
            value={form.side}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, side: e.target.value as BrokerOrderSide }))
            }
            className="bg-charcoal-800 text-charcoal-100 h-8 rounded-md px-2 text-xs outline-none"
          >
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-[10px] uppercase">Type</span>
          <select
            value={form.type}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, type: e.target.value as BrokerOrderType }))
            }
            className="bg-charcoal-800 text-charcoal-100 h-8 rounded-md px-2 text-xs outline-none"
          >
            <option value="market">Market</option>
            <option value="limit">Limit</option>
            <option value="stop">Stop</option>
            <option value="stop-limit">Stop-Limit</option>
          </select>
        </label>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-[10px] uppercase">Quantity</span>
          <input
            value={form.quantity}
            onChange={(e) => setForm((prev) => ({ ...prev, quantity: e.target.value }))}
            type="number"
            inputMode="decimal"
            className="bg-charcoal-800 text-charcoal-100 h-8 rounded-md px-2 text-sm outline-none"
          />
        </label>
        {(form.type === "limit" || form.type === "stop-limit") && (
          <label className="flex flex-col gap-1">
            <span className="text-charcoal-400 text-[10px] uppercase">Limit</span>
            <input
              value={form.limitPrice}
              onChange={(e) => setForm((prev) => ({ ...prev, limitPrice: e.target.value }))}
              type="number"
              inputMode="decimal"
              className="bg-charcoal-800 text-charcoal-100 h-8 rounded-md px-2 text-sm outline-none"
            />
          </label>
        )}
        {(form.type === "stop" || form.type === "stop-limit") && (
          <label className="flex flex-col gap-1">
            <span className="text-charcoal-400 text-[10px] uppercase">Stop</span>
            <input
              value={form.stopPrice}
              onChange={(e) => setForm((prev) => ({ ...prev, stopPrice: e.target.value }))}
              type="number"
              inputMode="decimal"
              className="bg-charcoal-800 text-charcoal-100 h-8 rounded-md px-2 text-sm outline-none"
            />
          </label>
        )}
      </div>

      {error !== null && <p className="text-xs text-red-400">{error}</p>}

      <Button type="submit" variant="outline" disabled={busy} data-testid="propose-order">
        {busy ? "Proposing…" : "Propose order"}
      </Button>
    </form>
  );
}
