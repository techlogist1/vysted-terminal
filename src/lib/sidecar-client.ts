/**
 * Sidecar API client.
 *
 * Resolves the Python sidecar's localhost port from the Tauri core (cached after
 * the first call) and exposes typed accessors for the data-layer REST endpoints,
 * plus a WebSocket helper for crypto streams. Panels call these functions rather
 * than building URLs themselves.
 */

import { invoke } from "@tauri-apps/api/core";

import { buildSearchHeaders } from "@/lib/search-headers";
import { useSettingsStore } from "@/store/settings";
import type {
  AnalystRating,
  BalanceSheet,
  CashFlowStatement,
  Fundamentals,
  IncomeStatement,
  OHLCVSeries,
  OptionChain,
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
  const status = await invoke<SidecarBootStatus>("get_sidecar_port");
  if (status.state === "failed") {
    // A spawn failure or an exited engine is named at once (R15-LIFECYCLE-010).
    throw new SidecarError(0, status.reason ?? SIDECAR_UNREACHABLE);
  }
  return `http://127.0.0.1:${status.port}`;
}

/** The Rust core's `get_sidecar_port` answer. */
interface SidecarBootStatus {
  port: number;
  state: "starting" | "ready" | "failed";
  reason: string | null;
}

/**
 * Resolve (and cache) the sidecar base URL, gated on a real `/health` probe so
 * the first successful resolution implies the sidecar is actually listening.
 *
 * Rust announces the port *number* before the sidecar binds (a cold
 * PyInstaller boot takes tens of seconds to extract and import), and a
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
    reportReachability(false, error instanceof Error ? error.message : String(error));
    throw error;
  });
  return readyPromise;
}

async function resolveAndAwaitReady(): Promise<string> {
  const deadline = Date.now() + 120_000;
  let delay = 250;
  for (;;) {
    // Re-read each round: a spawn that fails while we probe stops the wait.
    const base = await resolvePortToBaseUrl();
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

/** C1: the message for a sidecar that did not answer at all (connection
 *  refused, the engine gone) — never WebKit's bare "Load failed". */
export const SIDECAR_UNREACHABLE =
  "The data engine is not responding — it may have stopped. Restart Vysted.";

/** The message for a sidecar that accepted the request but missed its deadline. */
export const SIDECAR_TIMED_OUT = "The data engine did not answer in time. Try again.";

/**
 * The deadline for a local list/CRUD call (custom agents, schedules, saved
 * workflows): the sidecar answers these from SQLite in milliseconds, so 30 s
 * means it hung. Streams and long compute (quant pricing, runs) pass none.
 */
export const SIDECAR_REQUEST_TIMEOUT_MS = 30_000;

/** True when `signal` fired because its `timeoutMs` deadline passed. */
function timedOut(signal: AbortSignal | null | undefined): boolean {
  return (signal?.reason as { name?: unknown } | undefined)?.name === "TimeoutError";
}

/** The caller's signal joined with an optional deadline. */
function withDeadline(signal?: AbortSignal, timeoutMs?: number): AbortSignal | undefined {
  if (!timeoutMs) {
    return signal;
  }
  const deadline = AbortSignal.timeout(timeoutMs);
  return signal ? AbortSignal.any([signal, deadline]) : deadline;
}

/**
 * `fetch` against the sidecar with its transport failure named: a rejection
 * becomes `SidecarError(0, SIDECAR_UNREACHABLE)` and drops the cached base URL
 * so the next call re-resolves it; a passed `timeoutMs` deadline becomes
 * `SidecarError(504, SIDECAR_TIMED_OUT)`. A caller's own abort passes through
 * as is. Every sidecar fetch (REST and the SSE stream) goes through here.
 */
export async function sidecarFetch(url: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (err) {
    if (init?.signal?.aborted) {
      throw timedOut(init.signal) ? new SidecarError(504, SIDECAR_TIMED_OUT) : err;
    }
    readyPromise = null;
    reportReachability(false, SIDECAR_UNREACHABLE);
    throw new SidecarError(0, SIDECAR_UNREACHABLE);
  }
  reportReachability(true);
  return response;
}

type ReachabilityListener = (reachable: boolean, reason?: string) => void;
const reachabilityListeners = new Set<ReachabilityListener>();

/**
 * Hear every sidecar answer (`true`) and every connection-level failure
 * (`false` + the reason) — how the app store keeps `sidecarStatus` current
 * without this module importing the store. Returns the unsubscribe.
 */
export function onSidecarReachability(listener: ReachabilityListener): () => void {
  reachabilityListeners.add(listener);
  return () => {
    reachabilityListeners.delete(listener);
  };
}

function reportReachability(reachable: boolean, reason?: string): void {
  for (const listener of reachabilityListeners) {
    listener(reachable, reason);
  }
}

export type SidecarMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface SidecarRequestOptions {
  params?: QueryParams;
  /** JSON-encoded as the request body. */
  body?: unknown;
  /** Per-call headers (BYOK keys ride here); undefined values are dropped. */
  headers?: Record<string, string | undefined>;
  signal?: AbortSignal;
  /** Give up after this many ms with `SidecarError(504, SIDECAR_TIMED_OUT)`;
   *  omitted, the call waits as long as the sidecar takes. */
  timeoutMs?: number;
}

/**
 * The `RequestInit` every sidecar call carries: the session region, the search
 * headers, the per-call headers, a JSON body and the optional deadline.
 * {@link sidecarRequest} builds on it; a caller that must read the raw
 * `Response` (an SSE stream) passes it to {@link sidecarFetch}, so the
 * transport is decided here once.
 */
export async function sidecarRequestInit(
  method: SidecarMethod,
  opts: Omit<SidecarRequestOptions, "params"> = {},
): Promise<RequestInit> {
  // The active region rides every sidecar request (Pass B B1 locale-native
  // contract): the sidecar reads `X-Vysted-Region` to pick region-first data
  // providers/feeds. Read at call time so a region change reflects immediately;
  // `getState()` is SSR/static-export safe (no window/navigator at module load).
  const requestHeaders: Record<string, string> = {
    "X-Vysted-Region": useSettingsStore.getState().region,
  };
  // The three-tier web-search contract (FR-080/083/084): the active tier, the
  // BYOK Exa key (keychain), and the local SearXNG URL ride every request so the
  // sidecar dispatches search to the right backend. Undefined values are dropped
  // below (never an empty header). Merged FIRST so a per-call header arg still
  // wins if it ever sets the same key.
  const searchHeaders = await buildSearchHeaders();
  for (const [key, value] of Object.entries({ ...searchHeaders, ...opts.headers })) {
    if (value !== undefined) {
      requestHeaders[key] = value;
    }
  }
  const init: RequestInit = {
    method,
    headers: requestHeaders,
    signal: withDeadline(opts.signal, opts.timeoutMs),
  };
  if (opts.body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.body);
  }
  return init;
}

/**
 * Typed request against a sidecar endpoint — the one client verb. `headers`
 * carries BYOK credentials read from the OS keychain (the read-only-plugin
 * pattern: secret in a header, never the body/query) — e.g. the
 * `X-Vysted-Newsapi-Key` the news feed sends. A non-2xx throws
 * `SidecarError(status, <human detail>)`; a 204 resolves `undefined`.
 */
export async function sidecarRequest<T>(
  method: SidecarMethod,
  path: string,
  opts: SidecarRequestOptions = {},
): Promise<T> {
  const base = await getSidecarBaseUrl();
  const url = new URL(path, base);
  if (opts.params) {
    for (const [key, value] of Object.entries(opts.params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  const init = await sidecarRequestInit(method, opts);
  const response = await sidecarFetch(url.toString(), init);
  if (!response.ok) {
    // A body with no `detail` (and a blank status text) still names the status.
    let detail = response.statusText || `HTTP ${response.status}`;
    try {
      detail = extractSidecarDetail(await response.json(), detail);
    } catch {
      // Response body was not JSON — keep the status text.
    }
    throw new SidecarError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  try {
    return (await response.json()) as T;
  } catch (err) {
    // The deadline can pass while the body streams in: that is a timeout.
    if (timedOut(init.signal)) {
      throw new SidecarError(504, SIDECAR_TIMED_OUT);
    }
    // A 200 with a truncated / non-JSON body (sidecar crash mid-response,
    // proxy hiccup) would otherwise reject with a raw SyntaxError the callers
    // don't expect — normalize to a SidecarError so error handling is uniform
    // (Phase 9.5).
    const message = err instanceof Error ? err.message : "malformed response body";
    throw new SidecarError(502, `Malformed sidecar response: ${message}`);
  }
}

/** Typed GET against a sidecar endpoint (see {@link sidecarRequest}). */
export function sidecarGet<T>(
  path: string,
  params?: QueryParams,
  headers?: Record<string, string | undefined>,
): Promise<T> {
  return sidecarRequest<T>("GET", path, { params, headers });
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

/**
 * A per-call region override (`X-Vysted-Region`) for one instrument's request.
 * A ticker string can name different companies in different markets (AMAL is
 * Amal Ltd on BSE and Amalgamated Financial on NASDAQ), so a caller that knows
 * which listing the user picked sends that listing's region instead of the
 * session default. `undefined` sends nothing extra (the session region stands).
 */
function regionHeader(region?: string): Record<string, string | undefined> {
  return { "X-Vysted-Region": region };
}

/** Typed accessors for the Phase 1.A sidecar data-layer endpoints. The
 *  per-instrument accessors take an optional `region` (see {@link regionHeader}). */
export const sidecarApi = {
  health: (): Promise<HealthResponse> => sidecarGet<HealthResponse>("/health"),

  quote: (symbol: string, assetClass = "equity", region?: string): Promise<Quote> =>
    sidecarGet<Quote>(
      `/quotes/${encodeURIComponent(symbol)}`,
      { asset_class: assetClass },
      regionHeader(region),
    ),

  quotes: (symbols: string[], assetClass = "equity"): Promise<Quote[]> =>
    sidecarGet<Quote[]>("/quotes", { symbols: symbols.join(","), asset_class: assetClass }),

  history: (
    symbol: string,
    timeframe = "1d",
    range?: string,
    assetClass = "equity",
    region?: string,
  ): Promise<OHLCVSeries> =>
    sidecarGet<OHLCVSeries>(
      `/history/${encodeURIComponent(symbol)}`,
      {
        timeframe,
        range,
        asset_class: assetClass,
      },
      regionHeader(region),
    ),

  cryptoExchanges: (): Promise<{ exchanges: string[] }> =>
    sidecarGet<{ exchanges: string[] }>("/crypto/exchanges"),

  cryptoTicker: (exchange: string, symbol: string): Promise<Quote> =>
    sidecarGet<Quote>("/crypto/ticker", { exchange, symbol }),

  cryptoHistory: (exchange: string, symbol: string, timeframe = "1d"): Promise<OHLCVSeries> =>
    sidecarGet<OHLCVSeries>("/crypto/history", { exchange, symbol, timeframe }),

  fundamentals: (symbol: string, region?: string): Promise<Fundamentals> =>
    sidecarGet<Fundamentals>(
      `/fundamentals/${encodeURIComponent(symbol)}`,
      undefined,
      regionHeader(region),
    ),

  incomeStatement: (symbol: string, region?: string): Promise<IncomeStatement> =>
    sidecarGet<IncomeStatement>(
      `/fundamentals/${encodeURIComponent(symbol)}/income`,
      undefined,
      regionHeader(region),
    ),

  balanceSheet: (symbol: string, region?: string): Promise<BalanceSheet> =>
    sidecarGet<BalanceSheet>(
      `/fundamentals/${encodeURIComponent(symbol)}/balance`,
      undefined,
      regionHeader(region),
    ),

  cashFlow: (symbol: string, region?: string): Promise<CashFlowStatement> =>
    sidecarGet<CashFlowStatement>(
      `/fundamentals/${encodeURIComponent(symbol)}/cashflow`,
      undefined,
      regionHeader(region),
    ),

  optionChain: (symbol: string, expiry?: string): Promise<OptionChain> =>
    sidecarGet<OptionChain>(`/quant/option/chain/${encodeURIComponent(symbol)}`, { expiry }),

  analystRating: (symbol: string, region?: string): Promise<AnalystRating> =>
    sidecarGet<AnalystRating>(
      `/fundamentals/${encodeURIComponent(symbol)}/ratings`,
      undefined,
      regionHeader(region),
    ),
};
