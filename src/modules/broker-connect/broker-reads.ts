/**
 * Granular broker-read fetchers (FR-042 / SC-012) — the frontend half.
 *
 * `GET /brokers/{id}/positions`, `/holdings`, and `/margins` return the DISTINCT
 * granular shapes (`BrokerPositionsResult` ≠ `BrokerHoldingsResult` ≠
 * `BrokerMarginsResult`) when the adapter implements the read, else they fall
 * back to the shared `AccountSummary`. These typed wrappers narrow that union
 * for the `BrokerReadsSection` so a real read is rendered granularly and a
 * fallback / paper value is plainly badged (FR-041). Read-only: no write path.
 *
 * The sidecar serializes its response models by alias (camelCase), so the
 * `types/broker-reads.ts` mirror matches the wire directly — no remapping.
 */

import { sidecarGet } from "@/lib/sidecar-client";

import type { BrokerId, AccountSummary } from "../../../types/broker";
import type {
  BrokerHoldingsResult,
  BrokerMarginsResult,
  BrokerPositionsResult,
} from "../../../types/broker-reads";

/** A granular result carries the FR-041 provenance label; the fallback does not. */
export function isGranular<T extends { synthetic?: unknown }>(
  result: T | AccountSummary,
): result is T {
  return typeof (result as { synthetic?: unknown }).synthetic === "boolean";
}

export function fetchPositions(broker: BrokerId): Promise<BrokerPositionsResult | AccountSummary> {
  return sidecarGet<BrokerPositionsResult | AccountSummary>(
    `/brokers/${encodeURIComponent(broker)}/positions`,
  );
}

export function fetchHoldings(broker: BrokerId): Promise<BrokerHoldingsResult | AccountSummary> {
  return sidecarGet<BrokerHoldingsResult | AccountSummary>(
    `/brokers/${encodeURIComponent(broker)}/holdings`,
  );
}

export function fetchMargins(broker: BrokerId): Promise<BrokerMarginsResult | AccountSummary> {
  return sidecarGet<BrokerMarginsResult | AccountSummary>(
    `/brokers/${encodeURIComponent(broker)}/margins`,
  );
}
