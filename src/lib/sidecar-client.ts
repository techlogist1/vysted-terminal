/**
 * Sidecar API client.
 *
 * Resolves the Python sidecar's localhost port from the Tauri core (cached after
 * the first call) and exposes typed accessors for the data-layer REST endpoints,
 * plus a WebSocket helper for crypto streams. Panels call these functions rather
 * than building URLs themselves.
 */

import { invoke } from "@tauri-apps/api/core";

import type {
  AnalystRating,
  BalanceSheet,
  CashFlowStatement,
  Fundamentals,
  IncomeStatement,
  OHLCVSeries,
  Quote,
} from "../../types/data";

/** Error thrown when a sidecar request returns a non-2xx response. */
export class SidecarError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "SidecarError";
  }
}

let cachedBaseUrl: string | null = null;

/** Resolve (and cache) the sidecar's HTTP base URL via the Tauri core. */
export async function getSidecarBaseUrl(): Promise<string> {
  if (cachedBaseUrl !== null) {
    return cachedBaseUrl;
  }
  const port = await invoke<number>("get_sidecar_port");
  cachedBaseUrl = `http://127.0.0.1:${port}`;
  return cachedBaseUrl;
}

type QueryParams = Record<string, string | number | undefined>;

/** Low-level typed GET against a sidecar endpoint. */
export async function sidecarGet<T>(path: string, params?: QueryParams): Promise<T> {
  const base = await getSidecarBaseUrl();
  const url = new URL(path, base);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  const response = await fetch(url.toString());
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // Response body was not JSON — keep the status text.
    }
    throw new SidecarError(response.status, detail);
  }
  return (await response.json()) as T;
}

/** Open a WebSocket to the crypto ticker stream. The caller owns the socket. */
export async function openCryptoStream(exchange: string, symbol: string): Promise<WebSocket> {
  const base = await getSidecarBaseUrl();
  const url = new URL("/crypto/stream", base.replace(/^http/, "ws"));
  url.searchParams.set("exchange", exchange);
  url.searchParams.set("symbol", symbol);
  return new WebSocket(url.toString());
}

/** Shape of the `/health` response. */
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  providers: Record<string, string>;
}

/** Typed accessors for the Phase 1.A sidecar data-layer endpoints. */
export const sidecarApi = {
  health: (): Promise<HealthResponse> => sidecarGet<HealthResponse>("/health"),

  quote: (symbol: string, assetClass = "equity"): Promise<Quote> =>
    sidecarGet<Quote>(`/quotes/${encodeURIComponent(symbol)}`, { asset_class: assetClass }),

  quotes: (symbols: string[], assetClass = "equity"): Promise<Quote[]> =>
    sidecarGet<Quote[]>("/quotes", { symbols: symbols.join(","), asset_class: assetClass }),

  history: (
    symbol: string,
    timeframe = "1d",
    range?: string,
    assetClass = "equity",
  ): Promise<OHLCVSeries> =>
    sidecarGet<OHLCVSeries>(`/history/${encodeURIComponent(symbol)}`, {
      timeframe,
      range,
      asset_class: assetClass,
    }),

  cryptoExchanges: (): Promise<{ exchanges: string[] }> =>
    sidecarGet<{ exchanges: string[] }>("/crypto/exchanges"),

  cryptoTicker: (exchange: string, symbol: string): Promise<Quote> =>
    sidecarGet<Quote>("/crypto/ticker", { exchange, symbol }),

  cryptoHistory: (exchange: string, symbol: string, timeframe = "1d"): Promise<OHLCVSeries> =>
    sidecarGet<OHLCVSeries>("/crypto/history", { exchange, symbol, timeframe }),

  fundamentals: (symbol: string): Promise<Fundamentals> =>
    sidecarGet<Fundamentals>(`/fundamentals/${encodeURIComponent(symbol)}`),

  incomeStatement: (symbol: string): Promise<IncomeStatement> =>
    sidecarGet<IncomeStatement>(`/fundamentals/${encodeURIComponent(symbol)}/income`),

  balanceSheet: (symbol: string): Promise<BalanceSheet> =>
    sidecarGet<BalanceSheet>(`/fundamentals/${encodeURIComponent(symbol)}/balance`),

  cashFlow: (symbol: string): Promise<CashFlowStatement> =>
    sidecarGet<CashFlowStatement>(`/fundamentals/${encodeURIComponent(symbol)}/cashflow`),

  analystRating: (symbol: string): Promise<AnalystRating> =>
    sidecarGet<AnalystRating>(`/fundamentals/${encodeURIComponent(symbol)}/ratings`),
};
