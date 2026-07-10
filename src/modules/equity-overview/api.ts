/**
 * Equity-overview sidecar access.
 *
 * One symbol selection fans out to the five fundamentals endpoints plus a live
 * quote. The calls are independent, so a failure in one (e.g. analyst ratings
 * unavailable) does not blank the whole panel — `loadEquityOverview` returns a
 * `null` for any section that failed and an `error` only if every call failed.
 */

import { KEYCHAIN_NAMESPACES, getSecret } from "@/lib/keychain";
import {
  extractSidecarDetail,
  getSidecarBaseUrl,
  SidecarError,
  sidecarApi,
  sidecarGet,
} from "@/lib/sidecar-client";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { modelForProvider } from "@/store/model-selection";
import type {
  AnalystRating,
  BalanceSheet,
  CashFlowStatement,
  CompanyNarrative,
  Fundamentals,
  IncomeStatement,
  Quote,
} from "../../../types/data";

/** One autocomplete candidate from the read-only `/resolve/autocomplete` route. */
export interface SymbolCandidate {
  symbol: string;
  name: string;
  exchange: string;
  region: string;
  asset_class: string;
  yahoo_symbol: string;
  confidence: number;
}

/**
 * On-keystroke symbol autocomplete — masters-only, network-free server-side, so
 * it stays fast enough to fire per keystroke. Empty/blank query short-circuits to
 * `[]` without a request; any failure degrades to `[]` (the search box still works).
 */
export async function autocompleteSymbols(query: string, limit = 8): Promise<SymbolCandidate[]> {
  if (!query.trim()) {
    return [];
  }
  try {
    const res = await sidecarGet<{ candidates: SymbolCandidate[] }>("/resolve/autocomplete", {
      q: query,
      limit: String(limit),
    });
    return res.candidates ?? [];
  } catch {
    return [];
  }
}

/** The assembled equity-overview payload for one symbol. */
export interface EquityOverview {
  symbol: string;
  quote: Quote | null;
  fundamentals: Fundamentals | null;
  /**
   * Why the fundamentals leg failed, when it did (R13) — a 404 (the sidecar no
   * longer serves an all-null shell) or any other rejection surfaces its real
   * reason here instead of `fundamentals` collapsing to a bare `null` the panel
   * can't explain. `null` when the leg succeeded, or failed with nothing more
   * specific to say.
   */
  fundamentalsError: string | null;
  income: IncomeStatement | null;
  balance: BalanceSheet | null;
  cashFlow: CashFlowStatement | null;
  ratings: AnalystRating | null;
  /** `true` when every section failed to load — the panel shows an error. */
  allFailed: boolean;
}

function settled<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}

/** The human reason a leg was rejected — the sidecar's own detail via
 *  `SidecarError`, an `Error#message`, or a generic fallback. `null` for a
 *  fulfilled leg. */
function rejectionReason(result: PromiseSettledResult<unknown>): string | null {
  if (result.status !== "rejected") {
    return null;
  }
  const reason: unknown = result.reason;
  if (reason instanceof SidecarError || reason instanceof Error) {
    return reason.message;
  }
  return "Failed to load fundamentals.";
}

/** Fetch every section for one symbol; partial failures degrade gracefully. */
export async function loadEquityOverview(symbol: string): Promise<EquityOverview> {
  const [quote, fundamentals, income, balance, cashFlow, ratings] = await Promise.allSettled([
    sidecarApi.quote(symbol),
    sidecarApi.fundamentals(symbol),
    sidecarApi.incomeStatement(symbol),
    sidecarApi.balanceSheet(symbol),
    sidecarApi.cashFlow(symbol),
    sidecarApi.analystRating(symbol),
  ]);

  const sections = [quote, fundamentals, income, balance, cashFlow, ratings];
  const allFailed = sections.every((section) => section.status === "rejected");

  return {
    symbol,
    quote: settled(quote),
    fundamentals: settled(fundamentals),
    fundamentalsError: rejectionReason(fundamentals),
    income: settled(income),
    balance: settled(balance),
    cashFlow: settled(cashFlow),
    ratings: settled(ratings),
    allFailed,
  };
}

// --- AI narrative ---------------------------------------------------------

/**
 * Fetch the LLM-written, numerically-verified company narrative for `symbol`.
 *
 * Resolves the active BYOK provider + model + key the SAME way the chat sidebar
 * does — the default provider from the LLM-providers store, its default model,
 * and the OS-keychain key for that provider — and passes them in HEADERS (the
 * established read-path BYOK convention; never the body, never logged). The
 * sidecar always answers 200: a missing key or empty model output comes back as
 * `summary === null` + a `reason`, so the panel shows a quiet unavailable state
 * rather than throwing. A transport/5xx failure throws `SidecarError`.
 */
export async function loadCompanyNarrative(symbol: string): Promise<CompanyNarrative> {
  // The default provider lives in the store (same source the chat sidebar uses).
  const provider = useLLMProvidersStore.getState().defaultProviderId;

  let apiKey: string | null = null;
  try {
    apiKey = await getSecret(KEYCHAIN_NAMESPACES.llmProvider(provider));
  } catch {
    // Outside the Tauri shell the keychain rejects — treat as no key. The
    // sidecar then returns the graceful "no key" narrative.
    apiKey = null;
  }

  const base = await getSidecarBaseUrl();
  const url = new URL(`/fundamentals/${encodeURIComponent(symbol)}/narrative`, base);
  const headers: Record<string, string> = {
    "X-LLM-Provider": provider,
    "X-LLM-Model": modelForProvider(provider),
  };
  // Only attach the key header when we actually have one — never an empty secret.
  // No key for a key-requiring provider → no header → the sidecar returns a
  // graceful null narrative with a "configure a key" reason.
  if (apiKey) {
    headers["X-LLM-Api-Key"] = apiKey;
  }

  const response = await fetch(url.toString(), { headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = extractSidecarDetail(await response.json(), response.statusText);
    } catch {
      // non-JSON body — keep the status text
    }
    throw new SidecarError(response.status, detail);
  }
  return (await response.json()) as CompanyNarrative;
}
