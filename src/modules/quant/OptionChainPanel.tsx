"use client";

/**
 * Option Chain: one expiry of a listed chain with exchange-published open
 * interest (R15-DATA-079). Strike rows, calls left and puts right, each side's
 * OI, change in OI and last price. India F&O underlyings come from the NSE F&O
 * bhavcopy, US listings from yfinance. EOD research data, labelled by `as_of`.
 * Hits `GET /quant/option/chain/{symbol}?expiry=`.
 */

import { useCallback, useState } from "react";
import { Layers } from "lucide-react";

import { DataTable, type DataColumn } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { sidecarApi } from "@/lib/sidecar-client";
import { useSettingsStore } from "@/store/settings";

import type { OptionChain, OptionContract } from "../../../types/data";

interface StrikeRow {
  strike: number;
  call?: OptionContract;
  put?: OptionContract;
}

const num = (v: number | null | undefined, digits = 0): string =>
  v == null
    ? "—"
    : v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

const signed = (v: number | null | undefined): string =>
  v == null ? "—" : `${v > 0 ? "+" : ""}${num(v)}`;

const COLUMNS: DataColumn<StrikeRow>[] = [
  { key: "call_oi", header: "Call OI", numeric: true, format: (r) => num(r.call?.open_interest) },
  { key: "call_chg", header: "Chg OI", numeric: true, format: (r) => signed(r.call?.change_in_oi) },
  { key: "call_ltp", header: "Last", numeric: true, format: (r) => num(r.call?.last_price, 2) },
  { key: "strike", header: "Strike", numeric: true, format: (r) => num(r.strike, 2) },
  { key: "put_ltp", header: "Last", numeric: true, format: (r) => num(r.put?.last_price, 2) },
  { key: "put_chg", header: "Chg OI", numeric: true, format: (r) => signed(r.put?.change_in_oi) },
  { key: "put_oi", header: "Put OI", numeric: true, format: (r) => num(r.put?.open_interest) },
];

function strikeRows(chain: OptionChain): StrikeRow[] {
  const byStrike = new Map<number, StrikeRow>();
  for (const c of chain.contracts) {
    const row = byStrike.get(c.strike) ?? { strike: c.strike };
    row[c.option_type] = c;
    byStrike.set(c.strike, row);
  }
  return [...byStrike.values()].sort((a, b) => a.strike - b.strike);
}

export function OptionChainPanel() {
  const region = useSettingsStore((s) => s.region);
  const [symbol, setSymbol] = useState(region === "IN" ? "NIFTY" : "SPY");
  const [chain, setChain] = useState<OptionChain | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (expiry?: string) => {
      const sym = symbol.trim();
      if (!sym) return;
      setLoading(true);
      setError(null);
      try {
        setChain(await sidecarApi.optionChain(sym, expiry));
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    },
    [symbol],
  );

  return (
    <div className="bg-charcoal-900 flex h-full min-h-0 w-full flex-col gap-4 p-6">
      <form
        className="flex items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-500 text-micro">Underlying</span>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            data-testid="option-chain-symbol"
            className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 w-40 border px-3 outline-none"
          />
        </label>
        {chain && (
          <label className="flex flex-col gap-1">
            <span className="text-charcoal-500 text-micro">Expiry</span>
            <select
              value={chain.expiry}
              onChange={(e) => void load(e.target.value)}
              disabled={loading}
              data-testid="option-chain-expiry"
              className="bg-charcoal-850 text-charcoal-100 border-charcoal-700 rounded-control text-body focus-visible:border-charcoal-500 h-8 border px-3 outline-none"
            >
              {chain.expiries.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
        )}
        <Button type="submit" disabled={loading || !symbol.trim()} data-testid="option-chain-load">
          <Layers />
          {loading ? "Loading…" : "Load chain"}
        </Button>
      </form>

      {error && (
        <p
          className="text-negative bg-negative/10 border-negative/30 text-caption rounded-none border px-3 py-2"
          role="alert"
          data-testid="option-chain-error"
        >
          {error}
        </p>
      )}

      {chain ? (
        <>
          <p className="text-charcoal-400 text-caption" data-testid="option-chain-meta">
            {chain.symbol} · spot {num(chain.underlying_price, 2)} {chain.currency} · end of day as
            of {chain.as_of}
            {chain.freshness === "stale" ? " (stale)" : ""} · {chain.provider}
          </p>
          <div className="min-h-0 flex-1 overflow-auto">
            <DataTable
              columns={COLUMNS}
              rows={strikeRows(chain)}
              rowKey={(r) => String(r.strike)}
              rowTestId={(r) => `option-chain-row-${r.strike}`}
              stickyHeader
            />
          </div>
        </>
      ) : (
        !loading &&
        !error && (
          <EmptyState
            icon={Layers}
            headline="No chain loaded"
            hint="Open interest by strike for an F&O underlying (NIFTY, RELIANCE) or a US listing."
            cta={{ label: "Load chain", onClick: () => void load(), primary: true }}
          />
        )
      )}
    </div>
  );
}
