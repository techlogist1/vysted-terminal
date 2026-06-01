/**
 * Sidecar API client.
 *
 * Resolves the Python sidecar's localhost port from the Tauri core (cached after
 * the first call) and exposes typed accessors for the data-layer REST endpoints,
 * plus a WebSocket helper for crypto streams. Panels call these functions rather
 * than building URLs themselves.
 */

import { invoke } from "@tauri-apps/api/core";

import { useSettingsStore } from "@/store/settings";
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

/** One entry of a FastAPI 422 validation-error `detail` array. */
interface FastApiValidationError {
  msg?: string;
  loc?: unknown[];
}

/**
 * Extract a human-readable message from a sidecar error response body. FastAPI
 * returns `detail` as a plain string for `HTTPException`, but as an ARRAY of
 * validation-error objects for 422 — which naively stringifies to
 * "[object Object]" (the bug News/Portfolio showed). Handle both shapes; fall
 * back to the provided default for anything unrecognised.
 */
export function extractSidecarDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim() !== "") {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const messages = detail
        .map((entry) => {
          const e = entry as FastApiValidationError;
          const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : undefined;
          const msg = typeof e.msg === "string" ? e.msg : undefined;
          if (msg && field !== undefined) {
            return `${String(field)}: ${msg}`;
          }
          return msg ?? String(entry);
        })
        .filter((m): m is string => Boolean(m));
      if (messages.length > 0) {
        return messages.join("; ");
      }
    }
  }
  return fallback;
}

let readyPromise: Promise<string> | null = null;

/**
 * Resolve the sidecar port to a base URL (no readiness probe).
 *
 * Inside the Tauri shell the port is read from the Rust core via
 * `invoke("get_sidecar_port")` — the canonical production path.
 *
 * **Dev-mode fallback** (added v0.7.0 F7): when running standalone in a
 * regular browser (e.g. chrome-devtools MCP pointed at `http://localhost:3000`
 * while `pnpm tauri dev` is running in parallel), Tauri's `invoke` is
 * unavailable. The fallback honours a `?sidecar-port=NN` query param and points
 * the frontend at `http://127.0.0.1:NN`. Gated on the absence of
 * `__TAURI_INTERNALS__`, so it never short-circuits inside the production Tauri
 * webview.
 */
async function resolvePortToBaseUrl(): Promise<string> {
  if (typeof window !== "undefined" && !("__TAURI_INTERNALS__" in window)) {
    const urlParam = new URLSearchParams(window.location.search).get("sidecar-port");
    if (urlParam && /^\d+$/.test(urlParam)) {
      return `http://127.0.0.1:${urlParam}`;
    }
  }
  const port = await invoke<number>("get_sidecar_port");
  return `http://127.0.0.1:${port}`;
}

/**
 * Resolve (and cache) the sidecar base URL, gated on a real `/health` probe so
 * the first successful resolution implies the sidecar is actually listening.
 *
 * Rust announces the port *number* before the sidecar binds (the main sidecar
 * spawns only after a tens-of-seconds MCP-supervisor join on cold boot), and a
 * bare-port URL with no probe makes single-shot panels (News, Portfolio) fire
 * into a dead socket and latch a permanent error. Cold boot can be tens of
 * seconds, so budget generously with exponential backoff. Shared promise:
 * concurrent panel mounts await the same probe instead of each firing a doomed
 * fetch. Re-armable — a failure nulls the promise so a later caller (or a
 * manual Retry) re-probes.
 */
export function getSidecarBaseUrl(): Promise<string> {
  if (readyPromise) {
    return readyPromise;
  }
  readyPromise = resolveAndAwaitReady().catch((error: unknown) => {
    readyPromise = null; // re-armable: a later caller / manual Retry re-probes
    throw error;
  });
  return readyPromise;
}

async function resolveAndAwaitReady(): Promise<string> {
  const base = await resolvePortToBaseUrl();
  const deadline = Date.now() + 120_000;
  let delay = 250;
  for (;;) {
    try {
      const response = await fetch(new URL("/health", base).toString());
      if (response.ok) {
        return base;
      }
    } catch {
      // Connection refused — sidecar has a port assigned but is not bound yet.
    }
    if (Date.now() > deadline) {
      throw new SidecarError(503, "The data engine did not become ready in time.");
    }
    await new Promise((resolve) => setTimeout(resolve, delay));
    delay = Math.min(delay * 1.6, 2_000);
  }
}

type QueryParams = Record<string, string | number | undefined>;

/**
 * Low-level typed GET against a sidecar endpoint. `headers` carries BYOK
 * credentials read from the OS keychain (the read-only-plugin pattern: secret
 * in a header, never the body/query) — e.g. the `X-Vysted-Newsapi-Key` the news
 * feed sends. Undefined header values are dropped so an absent key is a no-op.
 */
export async function sidecarGet<T>(
  path: string,
  params?: QueryParams,
  headers?: Record<string, string | undefined>,
): Promise<T> {
  const base = await getSidecarBaseUrl();
  const url = new URL(path, base);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  // The active region rides every sidecar request (Pass B B1 locale-native
  // contract): the sidecar reads `X-Vysted-Region` to pick region-first data
  // providers/feeds. Read at call time so a region change reflects immediately;
  // `getState()` is SSR/static-export safe (no window/navigator at module load).
  const requestHeaders: Record<string, string> = {
    "X-Vysted-Region": useSettingsStore.getState().region,
  };
  // A per-call header arg takes precedence if it ever sets the same key.
  if (headers) {
    for (const [key, value] of Object.entries(headers)) {
      if (value !== undefined) {
        requestHeaders[key] = value;
      }
    }
  }
  const response = await fetch(url.toString(), {
    headers: requestHeaders,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = extractSidecarDetail(await response.json(), response.statusText);
    } catch {
      // Response body was not JSON — keep the status text.
    }
    throw new SidecarError(response.status, detail);
  }
  try {
    return (await response.json()) as T;
  } catch (err) {
    // A 200 with a truncated / non-JSON body (sidecar crash mid-response,
    // proxy hiccup) would otherwise reject with a raw SyntaxError the callers
    // don't expect — normalize to a SidecarError so error handling is uniform
    // (Phase 9.5).
    const message = err instanceof Error ? err.message : "malformed response body";
    throw new SidecarError(502, `Malformed sidecar response: ${message}`);
  }
}

/**
 * Probe whether an LLM provider is actually usable right now — a valid key for
 * a cloud provider, or a reachable local daemon for a keyless one (Ollama's
 * `validate_key` returns true only when `client.list()` succeeds). Used to gate
 * the first agent call so a keyless local provider that isn't running surfaces a
 * clear onboarding message instead of a doomed call (the ratified "offer both,
 * never silently fail against an absent local model" rule). Never throws.
 */
export async function validateProvider(provider: string, apiKey?: string): Promise<boolean> {
  try {
    const base = await getSidecarBaseUrl();
    const url = new URL("/llm/keys/validate", base);
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, api_key: apiKey ?? null }),
    });
    if (!response.ok) {
      return false;
    }
    const body = (await response.json()) as { ok?: boolean };
    return body.ok === true;
  } catch {
    return false;
  }
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
