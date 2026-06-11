"use client";

/**
 * BrokerReadsSection (FR-042 / SC-012) — the granular read display for a
 * connected broker.
 *
 * Renders the DISTINCT positions (net + day), settled holdings, and per-segment
 * margins the broker actually exposes — not one aliased account summary. Every
 * block carries the FR-041 provenance badge: a paper-mode / disconnected value
 * reads as `PAPER · synthetic` so it is never mistaken for a real position; a
 * live read reads as `LIVE · <provider>`. When the adapter has no granular read
 * the route falls back to the account summary and the block says so. Read-only:
 * there is no write/execution control anywhere in this surface (§6.5 untouched).
 */

import { useCallback, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

import type { BrokerId, AccountSummary } from "../../../types/broker";
import type {
  BrokerHoldingsResult,
  BrokerMarginsResult,
  BrokerPositionsResult,
} from "../../../types/broker-reads";

import { fetchHoldings, fetchMargins, fetchPositions, isGranular } from "./broker-reads";

interface Reads {
  positions?: BrokerPositionsResult | AccountSummary;
  holdings?: BrokerHoldingsResult | AccountSummary;
  margins?: BrokerMarginsResult | AccountSummary;
}

export function BrokerReadsSection({ broker }: { broker: BrokerId }) {
  const [open, setOpen] = useState(false);
  const [reads, setReads] = useState<Reads>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [positions, holdings, margins] = await Promise.all([
        fetchPositions(broker),
        fetchHoldings(broker),
        fetchMargins(broker),
      ]);
      setReads({ positions, holdings, margins });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read the account.");
    } finally {
      setLoading(false);
    }
  }, [broker]);

  // Toggle the section, fetching lazily the first time it is opened (an event
  // handler, not an effect — no synchronous setState-in-effect cascade).
  const handleToggle = useCallback(() => {
    const next = !open;
    setOpen(next);
    if (next && reads.positions === undefined && !loading) {
      void load();
    }
  }, [open, reads.positions, loading, load]);

  return (
    <div className="mt-2" data-testid={`broker-reads-${broker}`}>
      <button
        type="button"
        onClick={handleToggle}
        className="text-charcoal-400 hover:text-charcoal-100 text-micro flex items-center gap-1 uppercase"
        aria-expanded={open}
        data-testid={`broker-reads-toggle-${broker}`}
      >
        {open ? <ChevronDown size={11} aria-hidden /> : <ChevronRight size={11} aria-hidden />}
        Positions · Holdings · Margins
      </button>

      {open && (
        <div className="border-charcoal-800 mt-1 flex flex-col gap-2 border-l pl-2">
          {loading && reads.positions === undefined && (
            <p className="text-charcoal-500 text-micro">Reading account…</p>
          )}
          {error !== null && <p className="text-negative text-micro">{error}</p>}

          {reads.positions !== undefined && <PositionsBlock result={reads.positions} />}
          {reads.holdings !== undefined && <HoldingsBlock result={reads.holdings} />}
          {reads.margins !== undefined && <MarginsBlock result={reads.margins} />}

          {reads.positions !== undefined && (
            <button
              type="button"
              onClick={() => void load()}
              className="text-charcoal-500 text-micro hover:text-charcoal-100 self-start"
            >
              Refresh
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/** FR-041 provenance badge — synthetic/paper values are plainly labeled. */
function ProvenanceBadge({
  synthetic,
  mode,
  provider,
}: {
  synthetic: boolean;
  mode: string;
  provider: string;
}) {
  return (
    <span
      data-testid="broker-read-provenance"
      className={cn(
        "rounded-control text-micro px-1 py-0.5 uppercase",
        synthetic ? "bg-warning/20 text-warning" : "bg-positive/15 text-positive",
      )}
      title={synthetic ? "Paper-mode synthetic placeholder — not a real broker read" : provider}
    >
      {synthetic ? `${mode} · synthetic` : `${mode} · ${provider}`}
    </span>
  );
}

function BlockHeader({ label, right }: { label: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-charcoal-300 text-micro uppercase">{label}</span>
      {right}
    </div>
  );
}

function FallbackNote() {
  return (
    <p className="text-charcoal-500 text-micro">
      This broker exposes no granular read; falling back to the account summary.
    </p>
  );
}

function num(n: number): string {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function signed(n: number | undefined): string {
  if (n === undefined) return "—";
  return `${n >= 0 ? "+" : ""}${num(n)}`;
}

function PositionsBlock({ result }: { result: BrokerPositionsResult | AccountSummary }) {
  if (!isGranular<BrokerPositionsResult>(result)) {
    return (
      <div>
        <BlockHeader label="Positions" />
        <FallbackNote />
      </div>
    );
  }
  const legs = [...result.net, ...result.day];
  return (
    <div>
      <BlockHeader
        label={`Positions (${result.net.length} net · ${result.day.length} day)`}
        right={
          <ProvenanceBadge
            synthetic={result.synthetic}
            mode={result.mode}
            provider={result.provider}
          />
        }
      />
      {legs.length === 0 ? (
        <p className="text-charcoal-500 text-micro">No open positions.</p>
      ) : (
        <ul className="mt-0.5 flex flex-col gap-0.5">
          {legs.map((leg, i) => (
            <li
              key={`${leg.symbol}-${i}`}
              className="text-charcoal-200 text-micro flex items-center justify-between gap-2"
            >
              <span className="truncate">
                {leg.symbol} {leg.product ? `· ${leg.product}` : ""}
              </span>
              <span className="text-charcoal-400 shrink-0">
                {num(leg.quantity)} @ {num(leg.averageCost)}
                <span
                  className={cn(
                    "ml-1",
                    (leg.unrealizedPnl ?? 0) >= 0 ? "text-positive" : "text-negative",
                  )}
                >
                  {signed(leg.unrealizedPnl)}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function HoldingsBlock({ result }: { result: BrokerHoldingsResult | AccountSummary }) {
  if (!isGranular<BrokerHoldingsResult>(result)) {
    return (
      <div>
        <BlockHeader label="Holdings" />
        <FallbackNote />
      </div>
    );
  }
  return (
    <div>
      <BlockHeader
        label={`Holdings (${result.holdings.length})`}
        right={
          <ProvenanceBadge
            synthetic={result.synthetic}
            mode={result.mode}
            provider={result.provider}
          />
        }
      />
      {result.holdings.length === 0 ? (
        <p className="text-charcoal-500 text-micro">No settled holdings.</p>
      ) : (
        <ul className="mt-0.5 flex flex-col gap-0.5">
          {result.holdings.map((h, i) => (
            <li
              key={`${h.symbol}-${i}`}
              className="text-charcoal-200 text-micro flex items-center justify-between gap-2"
            >
              <span className="truncate">{h.symbol}</span>
              <span className="text-charcoal-400 shrink-0">
                {num(h.quantity)} · mv {num(h.marketValue)}
                <span
                  className={cn(
                    "ml-1",
                    (h.unrealizedPnl ?? 0) >= 0 ? "text-positive" : "text-negative",
                  )}
                >
                  {signed(h.unrealizedPnl)}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MarginsBlock({ result }: { result: BrokerMarginsResult | AccountSummary }) {
  if (!isGranular<BrokerMarginsResult>(result)) {
    return (
      <div>
        <BlockHeader label="Margins" />
        <FallbackNote />
      </div>
    );
  }
  return (
    <div>
      <BlockHeader
        label="Margins"
        right={
          <ProvenanceBadge
            synthetic={result.synthetic}
            mode={result.mode}
            provider={result.provider}
          />
        }
      />
      {result.segments.length === 0 ? (
        <p className="text-charcoal-500 text-micro">No margin segments reported.</p>
      ) : (
        <ul className="mt-0.5 flex flex-col gap-0.5">
          {result.segments.map((seg, i) => (
            <li
              key={`${seg.segment}-${i}`}
              className="text-charcoal-200 text-micro flex items-center justify-between gap-2"
            >
              <span className="truncate">
                {seg.segment} ({seg.currency})
              </span>
              <span className="text-charcoal-400 shrink-0">
                avail {num(seg.available)} · used {num(seg.used)} · net {num(seg.net)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
