/**
 * Portfolio sidecar access.
 *
 * Positions CRUD against the sidecar's `/portfolio/positions` endpoints (SQLite
 * persistence, owned by the portfolio router). Live quotes for P&L come from
 * the shared `sidecarApi`; the panel joins positions to quotes and computes
 * P&L, weight, and risk metrics client-side — no derived sidecar model.
 */

import { sidecarGet, sidecarApi } from "@/lib/sidecar-client";
import type { Position, PositionInput, Quote } from "../../../types/data";

/** Fetch every stored position. */
export function fetchPositions(): Promise<Position[]> {
  return sidecarGet<Position[]>("/portfolio/positions");
}

async function sidecarSend<T>(path: string, method: string, body?: unknown): Promise<T> {
  const { getSidecarBaseUrl, SidecarError } = await import("@/lib/sidecar-client");
  const base = await getSidecarBaseUrl();
  const response = await fetch(new URL(path, base).toString(), {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const parsed = (await response.json()) as { detail?: string };
      if (parsed.detail) {
        detail = parsed.detail;
      }
    } catch {
      // Response body was not JSON — keep the status text.
    }
    throw new SidecarError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Create a new manually entered position. */
export function createPosition(input: PositionInput): Promise<Position> {
  return sidecarSend<Position>("/portfolio/positions", "POST", input);
}

/** Overwrite an existing position. */
export function updatePosition(id: number, input: PositionInput): Promise<Position> {
  return sidecarSend<Position>(`/portfolio/positions/${id}`, "PUT", input);
}

/** Delete a position by id. */
export function deletePosition(id: number): Promise<void> {
  return sidecarSend<void>(`/portfolio/positions/${id}`, "DELETE");
}

/**
 * Fetch a live quote for one position symbol, mapping the asset class onto the
 * sidecar's quote endpoint. A symbol that fails to resolve comes back `null`.
 */
export async function fetchPositionQuote(
  symbol: string,
  assetClass: string,
): Promise<Quote | null> {
  try {
    return await sidecarApi.quote(symbol, assetClass);
  } catch {
    return null;
  }
}

/** Fetch live quotes for a set of positions, keyed by upper-cased symbol. */
export async function fetchPositionQuotes(positions: Position[]): Promise<Map<string, Quote>> {
  const quotes = new Map<string, Quote>();
  const results = await Promise.all(
    positions.map((position) => fetchPositionQuote(position.symbol, position.asset_class)),
  );
  positions.forEach((position, index) => {
    const quote = results[index];
    if (quote !== null) {
      quotes.set(position.symbol.toUpperCase(), quote);
    }
  });
  return quotes;
}
