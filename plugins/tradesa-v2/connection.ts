/**
 * Tradesa V2 wrapper — connection adapter.
 *
 * The generic interface a Vysted Terminal "trading-system wrapper" plugin
 * implements to talk to an external trading bot. This is the abstraction
 * future plugins (TauricResearch, Forge, etc.) mirror — the panel layer
 * never reaches past this seam, so swapping the underlying bot's REST /
 * Supabase / WebSocket transport changes ONE file.
 *
 * The Tradesa V2 implementation routes every read through the Vysted
 * sidecar (`/tradesa-v2/*` endpoints). Credentials travel as request
 * headers — the renderer reads the OS keychain via `keychain.ts`, the
 * sidecar never reads keychain directly (Tauri Rust owns that surface).
 *
 * v0.6.5 is READ-ONLY by operator decision: no writes flow toward the
 * bot. There is no `placeOrder` / `closePosition` / `fireKillSwitch`
 * method on this adapter — adding one is a Tier-4 contract change.
 */

import { KEYCHAIN_NAMESPACES, getSecret } from "@/lib/keychain";
import { getSidecarBaseUrl, SidecarError } from "@/lib/sidecar-client";

import type {
  TradesaBotSetting,
  TradesaConnectionState,
  TradesaCostRollup,
  TradesaDecision,
  TradesaDiscoveryHypothesis,
  TradesaKillSwitchEvent,
  TradesaMetaAgentRun,
  TradesaReflectionNote,
  TradesaSentinelBlock,
  TradesaSettingsDrift,
  TradesaTrade,
  TradesaTuningProposal,
} from "../../types/tradesa_v2";

// ---------------------------------------------------------------------------
// Credentials (read from OS keychain via Tauri)
// ---------------------------------------------------------------------------

/** Stable keychain account ids the plugin reads / writes. */
export const TRADESA_KEYCHAIN_ACCOUNTS = {
  supabaseUrl: KEYCHAIN_NAMESPACES.pluginSecret("tradesa-v2", "supabase-url"),
  supabaseServiceRoleKey: KEYCHAIN_NAMESPACES.pluginSecret(
    "tradesa-v2",
    "supabase-service-role-key",
  ),
} as const;

/** Returns the credentials pair if both keychain entries are present, else null. */
export async function readCredentials(): Promise<{ url: string; key: string } | null> {
  const url = await getSecret(TRADESA_KEYCHAIN_ACCOUNTS.supabaseUrl);
  const key = await getSecret(TRADESA_KEYCHAIN_ACCOUNTS.supabaseServiceRoleKey);
  if (!url || !key) return null;
  return { url, key };
}

// ---------------------------------------------------------------------------
// Generic adapter contract
// ---------------------------------------------------------------------------

/**
 * The set of read methods a trading-system wrapper plugin exposes to its
 * panel components. Each method maps 1:1 to a Vysted sidecar endpoint
 * for the bot in question. The interface is intentionally narrow — every
 * method is a read; future write methods land in a separate `WriteOps`
 * interface when v0.6.6+ ships write capability.
 *
 * TauricResearch and any future trading-system plugin implements the
 * same interface (or a near-identical one — the method names may shift
 * for non-crypto-perp domains, but the shape stays: status probe + per-
 * panel typed reads + graceful-degradation classification).
 */
export interface TradingBotReadAdapter {
  /** Connection probe — returns a typed state for graceful-degradation UX. */
  probeStatus(): Promise<TradesaConnectionState>;

  // Trade surface
  listOpenPositions(limit?: number): Promise<TradesaTrade[]>;
  listClosedTrades(limit?: number): Promise<TradesaTrade[]>;

  // Brain + LLM ledger
  listDecisions(limit?: number): Promise<TradesaDecision[]>;
  listMetaAgentRuns(opts?: { limit?: number; kind?: string }): Promise<TradesaMetaAgentRun[]>;
  getCostToday(): Promise<TradesaCostRollup>;

  // Health + kill-switch (display-only)
  getHealth(): Promise<{
    latest: TradesaBotHealthLike | null;
    recent_kill_switch_events: TradesaKillSwitchEvent[];
  }>;
  listKillSwitchEvents(limit?: number): Promise<TradesaKillSwitchEvent[]>;

  // Sentinel + settings + drift
  listSentinelBlocks(): Promise<TradesaSentinelBlock[]>;
  listSettings(): Promise<TradesaBotSetting[]>;
  getSettingsDrift(): Promise<TradesaSettingsDrift[]>;

  // Meta-agents (tuning / discovery / reflection)
  listTuningProposals(limit?: number): Promise<TradesaTuningProposal[]>;
  listDiscoveryHypotheses(limit?: number): Promise<TradesaDiscoveryHypothesis[]>;
  listReflectionNotes(limit?: number): Promise<TradesaReflectionNote[]>;
}

/**
 * Display-only `bot_health.latest` shape served by `/tradesa-v2/health`.
 * Kept loose (string-typed `recorded_at` etc.) because the panel parses
 * the date lazily.
 */
export interface TradesaBotHealthLike {
  recorded_at: string;
  service: string;
  status: string;
  detail: string | null;
  fd_count: number | null;
  thread_count: number | null;
  uptime_s: number | null;
}

// ---------------------------------------------------------------------------
// Tradesa V2 implementation
// ---------------------------------------------------------------------------

const HEADER_URL = "X-Tradesa-Supabase-Url";
const HEADER_KEY = "X-Tradesa-Supabase-Service-Key";

/**
 * Build the credential headers a Tradesa V2 sidecar fetch needs. Returns
 * an empty header dict if no credentials are configured — the sidecar's
 * `/tradesa-v2/status` endpoint handles missing creds gracefully (200
 * with `status: "unauthenticated"`), so the no-creds path stays
 * non-throwing.
 */
async function buildAuthHeaders(): Promise<Record<string, string>> {
  const creds = await readCredentials();
  if (!creds) return {};
  return {
    [HEADER_URL]: creds.url,
    [HEADER_KEY]: creds.key,
  };
}

/** Internal: sidecar GET with the Tradesa V2 auth headers attached. */
async function tradesaGet<T>(path: string, query?: Record<string, string | number>): Promise<T> {
  const base = await getSidecarBaseUrl();
  const url = new URL(path, base);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      url.searchParams.set(k, String(v));
    }
  }
  const headers = await buildAuthHeaders();
  const response = await fetch(url.toString(), {
    method: "GET",
    headers,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail =
        typeof body?.detail === "string"
          ? body.detail
          : typeof body?.detail?.message === "string"
            ? body.detail.message
            : JSON.stringify(body);
    } catch {
      /* fall through */
    }
    throw new SidecarError(response.status, detail);
  }
  return (await response.json()) as T;
}

/**
 * The Tradesa V2 implementation of `TradingBotReadAdapter`. One instance
 * per plugin lifetime — the credentials live in the keychain and are
 * re-read on every request (cheap; the OS keychain calls finish in
 * sub-millisecond on modern systems).
 *
 * Read-only by design: every method is a sidecar GET. Adding a write
 * method here, in `connection.ts`, in `panels.ts`, or in any
 * component is a Tier-4 contract change.
 */
export class TradesaV2ConnectionAdapter implements TradingBotReadAdapter {
  async probeStatus(): Promise<TradesaConnectionState> {
    return tradesaGet<TradesaConnectionState>("/tradesa-v2/status");
  }

  async listOpenPositions(limit = 50): Promise<TradesaTrade[]> {
    return tradesaGet<TradesaTrade[]>("/tradesa-v2/positions", { limit });
  }

  async listClosedTrades(limit = 100): Promise<TradesaTrade[]> {
    return tradesaGet<TradesaTrade[]>("/tradesa-v2/trade-history", { limit });
  }

  async listDecisions(limit = 100): Promise<TradesaDecision[]> {
    return tradesaGet<TradesaDecision[]>("/tradesa-v2/decisions", { limit });
  }

  async listMetaAgentRuns(opts?: {
    limit?: number;
    kind?: string;
  }): Promise<TradesaMetaAgentRun[]> {
    const params: Record<string, string | number> = { limit: opts?.limit ?? 100 };
    if (opts?.kind) params.kind = opts.kind;
    return tradesaGet<TradesaMetaAgentRun[]>("/tradesa-v2/meta-agent-runs", params);
  }

  async getCostToday(): Promise<TradesaCostRollup> {
    return tradesaGet<TradesaCostRollup>("/tradesa-v2/cost-today");
  }

  async getHealth(): Promise<{
    latest: TradesaBotHealthLike | null;
    recent_kill_switch_events: TradesaKillSwitchEvent[];
  }> {
    return tradesaGet("/tradesa-v2/health");
  }

  async listKillSwitchEvents(limit = 50): Promise<TradesaKillSwitchEvent[]> {
    return tradesaGet<TradesaKillSwitchEvent[]>("/tradesa-v2/kill-switch-events", { limit });
  }

  async listSentinelBlocks(): Promise<TradesaSentinelBlock[]> {
    return tradesaGet<TradesaSentinelBlock[]>("/tradesa-v2/sentinel");
  }

  async listSettings(): Promise<TradesaBotSetting[]> {
    return tradesaGet<TradesaBotSetting[]>("/tradesa-v2/settings");
  }

  async getSettingsDrift(): Promise<TradesaSettingsDrift[]> {
    return tradesaGet<TradesaSettingsDrift[]>("/tradesa-v2/settings/drift");
  }

  async listTuningProposals(limit = 50): Promise<TradesaTuningProposal[]> {
    const body = await tradesaGet<{ items: TradesaTuningProposal[] }>(
      "/tradesa-v2/meta-agents/tuning",
      { limit },
    );
    return body.items;
  }

  async listDiscoveryHypotheses(limit = 50): Promise<TradesaDiscoveryHypothesis[]> {
    const body = await tradesaGet<{ items: TradesaDiscoveryHypothesis[] }>(
      "/tradesa-v2/meta-agents/discovery",
      { limit },
    );
    return body.items;
  }

  async listReflectionNotes(limit = 50): Promise<TradesaReflectionNote[]> {
    const body = await tradesaGet<{ items: TradesaReflectionNote[] }>(
      "/tradesa-v2/meta-agents/reflection",
      { limit },
    );
    return body.items;
  }
}

// ---------------------------------------------------------------------------
// Singleton accessor (per-plugin lifetime)
// ---------------------------------------------------------------------------

let _adapter: TradingBotReadAdapter | null = null;

/** Returns the process-lifetime adapter instance; constructs on first call. */
export function getTradesaAdapter(): TradingBotReadAdapter {
  if (_adapter === null) {
    _adapter = new TradesaV2ConnectionAdapter();
  }
  return _adapter;
}

/** Test hook: swap the adapter (Vitest tests use this to install a stub). */
export function _setAdapterForTests(adapter: TradingBotReadAdapter | null): void {
  _adapter = adapter;
}
