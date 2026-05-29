/**
 * The integrations registry — the single declarative table the hub + Settings
 * section render from. One spec per integration; the ConnectCard renders any
 * spec dynamically (fields + authFlow drive everything, no per-broker UI).
 */

import type { IntegrationSpec } from "./types";

const KITE_REDIRECT = "http://127.0.0.1:43117/kite/callback";

export const INTEGRATIONS: IntegrationSpec[] = [
  {
    id: "kite",
    category: "broker",
    label: "Zerodha (Kite Connect)",
    icon: "trending-up",
    blurb: "India equities, F&O & currency — read-only positions, holdings & P&L.",
    description:
      "Connect your Zerodha account read-only via the official Kite Connect login. " +
      "Vysted reads your positions, holdings and P&L and lets the copilot analyse your real portfolio. Order execution is not enabled here.",
    website: "https://developers.kite.trade/",
    instructions:
      "1. Create an app at the Kite developer console (kite.trade).\n" +
      `2. Set the app's redirect URL to ${KITE_REDIRECT}.\n` +
      "3. Paste your API key + API secret below, then click Connect with Zerodha and log in.\n" +
      "Note: your API secret never leaves this machine and is used only to mint the daily session token.",
    authFlow: "loopback-oauth",
    fields: [
      {
        key: "api_key",
        label: "API key",
        type: "text",
        required: true,
        placeholder: "kite api_key",
      },
      {
        key: "api_secret",
        label: "API secret",
        type: "password",
        required: true,
        help: "Used only to mint the daily session token; never stored in the JS layer.",
      },
      {
        key: "static_ip",
        label: "Static IP (optional)",
        type: "text",
        required: false,
        help: "SEBI rule — needed only for order placement. Read-only positions work from any IP.",
      },
    ],
    dailyExpiry: {
      boundaryLabel: "6:00 AM IST",
      note: "Kite resets your session daily — reconnect each trading morning (one tap).",
    },
    testEndpoint: "/brokers/kite/account",
  },
  {
    id: "dhan",
    category: "broker",
    label: "Dhan",
    icon: "trending-up",
    blurb: "India equities & F&O — read-only positions & P&L.",
    description:
      "Connect Dhan read-only with a long-lived access token from the Dhan console. Re-enter the token if you rotate it.",
    website: "https://dhanhq.co/",
    instructions:
      "Generate an access token in the Dhan web console (My Profile → DhanHQ Trading API) and paste your client id + token below.",
    authFlow: "static-token",
    fields: [
      { key: "client_id", label: "Client ID", type: "text", required: true },
      { key: "access_token", label: "Access token", type: "password", required: true },
    ],
    testEndpoint: "/brokers/dhan/account",
  },
  {
    id: "angelone",
    category: "broker",
    label: "Angel One (SmartAPI)",
    icon: "trending-up",
    blurb: "India equities & F&O — read-only positions & P&L.",
    description:
      "Connect Angel One read-only. A live 6-digit TOTP mints a session; re-connect to refresh it.",
    website: "https://smartapi.angelbroking.com/",
    instructions:
      "Enter your SmartAPI key, client code, password (PIN) and the CURRENT 6-digit TOTP from your authenticator, then connect immediately (the code rotates every 30s).",
    authFlow: "interactive-session",
    fields: [
      { key: "api_key", label: "API key", type: "text", required: true },
      { key: "client_code", label: "Client code", type: "text", required: true },
      { key: "password", label: "Password / PIN", type: "password", required: true },
      {
        key: "totp",
        label: "TOTP (current 6-digit code)",
        type: "text",
        required: true,
        help: "The current code from your authenticator — enter it immediately before connecting.",
      },
    ],
    testEndpoint: "/brokers/angelone/account",
  },
];

/** The pinned loopback redirect the user registers once in the Kite console. */
export const KITE_REDIRECT_URL = KITE_REDIRECT;

export function getIntegration(id: string): IntegrationSpec | undefined {
  return INTEGRATIONS.find((spec) => spec.id === id);
}

export function integrationsByCategory(category: string): IntegrationSpec[] {
  return INTEGRATIONS.filter((spec) => spec.category === category);
}
