/**
 * Kite Connect OAuth login flow (frontend half).
 *
 * The real login dance — NOT a static pasted access token:
 *   1. open the Kite login URL in the system browser (api_key only),
 *   2. the user logs in → Kite redirects to the registered redirect URL with a
 *      one-time `request_token` in the query,
 *   3. the user pastes that redirect URL (or the bare token) back,
 *   4. the sidecar exchanges it for a daily `access_token` (SHA-256 checksum +
 *      /session/token, api_secret used server-side only),
 *   5. we store the access_token in the keychain and connect the adapter.
 *
 * (A Rust loopback listener that auto-captures the request_token is a deferred
 *  polish — the manual paste works on any machine and needs no extra crates.)
 */

import { KEYCHAIN_NAMESPACES, getSecret, setSecret } from "@/lib/keychain";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useBrokersStore } from "@/store/brokers";

/** Build the official Kite login URL (api_key only — never the secret). */
export function kiteLoginUrl(apiKey: string): string {
  return `https://kite.zerodha.com/connect/login?v=3&api_key=${encodeURIComponent(apiKey)}`;
}

/** Open the Kite login in the system browser via the Tauri shell plugin. */
export async function openKiteLogin(apiKey: string): Promise<void> {
  const { open } = await import("@tauri-apps/plugin-shell");
  await open(kiteLoginUrl(apiKey));
}

/** Accept either a pasted redirect URL (…?request_token=XXX&…) or a bare token. */
export function extractRequestToken(pasted: string): string | null {
  const trimmed = pasted.trim();
  if (!trimmed) {
    return null;
  }
  try {
    const url = new URL(trimmed);
    const token = url.searchParams.get("request_token");
    if (token) {
      return token;
    }
  } catch {
    // Not a URL — treat the whole string as the token.
  }
  // A bare request_token is a short alphanumeric string with no spaces/slashes.
  return /^[A-Za-z0-9]+$/.test(trimmed) ? trimmed : null;
}

interface KiteSessionResponse {
  accessToken: string;
  userId?: string | null;
  loginTime?: string | null;
}

/**
 * Exchange a request_token for a daily access_token, persist it, and connect the
 * Kite adapter read-only. `api_secret` is read from the keychain and sent to the
 * sidecar exchange endpoint only (never persisted there, never echoed).
 */
export async function exchangeAndConnectKite(requestToken: string): Promise<{ userId?: string }> {
  const apiKey = await getSecret(KEYCHAIN_NAMESPACES.broker("kite", "api_key"));
  const apiSecret = await getSecret(KEYCHAIN_NAMESPACES.broker("kite", "api_secret"));
  if (!apiKey || !apiSecret) {
    throw new Error("Enter your Kite API key and secret first.");
  }

  const base = await getSidecarBaseUrl();
  const response = await fetch(new URL("/brokers/kite/session", base).toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ apiKey, apiSecret, requestToken }),
  });
  if (!response.ok) {
    let detail = `Kite login failed (HTTP ${response.status}).`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // keep the generic message
    }
    throw new Error(detail);
  }
  const session = (await response.json()) as KiteSessionResponse;

  // Persist the daily token; connect the adapter read-only with key + token.
  await setSecret(KEYCHAIN_NAMESPACES.broker("kite", "access_token"), session.accessToken);
  const staticIp = await getSecret(KEYCHAIN_NAMESPACES.broker("kite", "static_ip"));
  const credentials: Record<string, string> = {
    api_key: apiKey,
    access_token: session.accessToken,
  };
  if (staticIp) {
    credentials.static_ip = staticIp;
  }
  await useBrokersStore.getState().connect("kite", credentials);
  return { userId: session.userId ?? undefined };
}
