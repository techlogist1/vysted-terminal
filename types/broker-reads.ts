/**
 * Vysted Terminal — granular broker read wire contract (FR-042 / SC-012).
 *
 * Mirrors `sidecar/models/broker_reads.py` by hand — keep the two in sync
 * (CLAUDE.md Gotchas: `types/data.ts` mirrors `sidecar/models/`).
 *
 * `types/broker.ts` is the LOCKED §6.5 surface, so the genuine granular reads
 * live here. `GET /brokers/{id}/positions`, `/holdings`, and `/margins`
 * previously aliased `account_info()` → one `AccountSummary`; these shapes back
 * the DISTINCT reads each broker SDK actually exposes (positions ≠ holdings ≠
 * margins).
 *
 * Every result carries the FR-041 provenance label — `synthetic` + `mode` +
 * `provider` — so a paper / disconnected value is plainly badged in the
 * broker-connect panel and never read as a real broker position.
 */

import type { BrokerId, BrokerMode } from "./broker";

/**
 * Provenance label shared by every granular read result. `synthetic` is `true`
 * whenever the figures are paper-mode placeholders rather than a real read.
 */
export interface BrokerReadProvenance {
  broker: BrokerId;
  accountId: string;
  /** True when the figures are paper-mode placeholders, not a real read. */
  synthetic: boolean;
  mode: BrokerMode;
  /** Which adapter / SDK produced these figures (e.g. "kite"). */
  provider: string;
  /** Epoch milliseconds when this snapshot was captured. */
  capturedAt: number;
}

/** One leg of a granular positions read (net or day). */
export interface BrokerLegPosition {
  symbol: string;
  quantity: number;
  averageCost: number;
  lastPrice: number;
  /** Unrealized (open) P&L; absent when the broker does not report it. */
  unrealizedPnl?: number;
  /** Realized (booked) P&L; absent when the broker does not report it. */
  realizedPnl?: number;
  /** Broker product code, e.g. NRML / MIS / CNC. */
  product?: string;
}

/**
 * Intraday / F&O positions — the broker's distinct `positions()` call. `net` is
 * the net open position per instrument; `day` is the intraday leg. NOT the
 * settled holdings (see `BrokerHoldingsResult`).
 */
export interface BrokerPositionsResult extends BrokerReadProvenance {
  net: BrokerLegPosition[];
  day: BrokerLegPosition[];
}

/** One settled long-term holding. */
export interface BrokerHolding {
  symbol: string;
  quantity: number;
  averageCost: number;
  lastPrice: number;
  marketValue: number;
  unrealizedPnl?: number;
}

/** Settled long-term holdings — the broker's distinct `holdings()` call. */
export interface BrokerHoldingsResult extends BrokerReadProvenance {
  holdings: BrokerHolding[];
}

/** Funds for one trading segment (e.g. equity, commodity). */
export interface BrokerSegmentMargin {
  segment: string;
  currency: string;
  available: number;
  used: number;
  net: number;
}

/** Per-segment funds — the broker's distinct `margins()` call. */
export interface BrokerMarginsResult extends BrokerReadProvenance {
  segments: BrokerSegmentMargin[];
}

/** Which granular read a route narrows to. */
export type GranularBrokerRead = "positions" | "holdings" | "margins";
