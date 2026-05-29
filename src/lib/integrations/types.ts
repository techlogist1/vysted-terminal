/**
 * Integrations registry — the declarative, host-side table of everything a user
 * can connect (brokers, data providers, AI providers, MCP servers). Modelled on
 * Fincept's ConnectorRegistry + OpenBB's per-provider credential-onboarding
 * blob, kept as host-side TypeScript (the locked `types/plugin.ts` can't carry
 * this, exactly like the `PLUGIN_COMPANIONS` host-glue precedent).
 *
 * The Phase-10 hub is read-only by design: brokers connect for positions/P&L +
 * AI analysis; order-execution mode toggles stay in the broker-connect panel.
 */

export type IntegrationCategory = "broker" | "data" | "ai-provider" | "mcp";

export type IntegrationFieldType = "text" | "password" | "url" | "number";

/** Strategy for obtaining a usable session.
 *  - `static-token`: paste a long-lived token (Dhan, Alpaca).
 *  - `loopback-oauth`: real OAuth login → request_token → access_token (Kite).
 *  - `interactive-session`: live credentials + TOTP mint a session (Angel One). */
export type IntegrationAuthFlow = "static-token" | "loopback-oauth" | "interactive-session";

export interface IntegrationFieldDef {
  /** Keychain field name, e.g. "api_key". */
  key: string;
  label: string;
  /** Drives input masking by type (not a brittle name-substring heuristic). */
  type: IntegrationFieldType;
  placeholder?: string;
  required: boolean;
  /** Inline per-field hint. */
  help?: string;
}

export interface IntegrationSpec {
  /** Matches the BrokerId for brokers, e.g. "kite". */
  id: string;
  category: IntegrationCategory;
  label: string;
  /** Lucide icon name. */
  icon: string;
  /** One-line subtitle. */
  blurb: string;
  /** Full connect-card body. */
  description: string;
  /** "Get your key here" link. */
  website?: string;
  /** Markdown how-to (OpenBB-style). */
  instructions?: string;
  authFlow: IntegrationAuthFlow;
  fields: IntegrationFieldDef[];
  /** Daily-expiry copy for tokens that die at a fixed boundary (Kite). */
  dailyExpiry?: { boundaryLabel: string; note: string };
  /** Read endpoint the "Test" affordance hits (brokers). */
  testEndpoint?: string;
}
