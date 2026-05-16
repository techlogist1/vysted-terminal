/**
 * Vysted Terminal — execution-safety wire contract.
 *
 * BLUEPRINT §6.5's eight safety non-negotiables are not just convention —
 * each one is enforced in code, at type-level where the language allows
 * and in the runtime where it does not. This file defines the wire shapes
 * of every safety surface so the frontend, sidecar, and broker adapters
 * speak the same vocabulary:
 *
 *   1. Paper mode default → `BrokerState.mode` defaults to `"paper"`
 *      (`types/broker.ts`); the sidecar adapter sets it in the constructor.
 *   2. Per-order confirmation → `BrokerOrderProposal` (`types/broker.ts`)
 *      is the ONLY object handed back from `propose_order`; placement
 *      requires a separate `confirm_and_place(proposal_id, human_confirmed)`
 *      call.
 *   3. Position limits → `PositionLimits` configurable per broker.
 *   4. Append-only audit log → `AuditLogEntry` with the SQLite trigger
 *      enforcement in `sidecar/services/audit_log.py`.
 *   5. Global kill switch → `KillSwitchEvent` broadcast through the
 *      `KillSwitchBus` (every broker adapter subscribes on construction).
 *   6. AI-order gate → orders with `source: "ai-agent" | "workflow"` open
 *      the confirmation dialog defaulted to declined; v0.5.0 ships NO
 *      auto-approve mode (tightening of BLUEPRINT §6.5 #6 — see plan).
 *   7. Read-only mode → `BrokerState.readOnly` honored at the adapter
 *      boundary (raises in `propose_order` regardless of any other flag).
 *   8. Layered disclaimers → `DisclaimerAcknowledgment` records first-launch
 *      TOS + per-broker first-connect + first-live-order-per-session acks.
 *
 * This file is foundation-tier. Every teammate consumes from here.
 */

import type { BrokerId, BrokerOrderProposal } from "./broker";

// ---------------------------------------------------------------------------
// Kill switch
// ---------------------------------------------------------------------------

/** Origin of a kill-switch fire — recorded in the audit log for forensics. */
export type KillSwitchFiredBy = "user-toolbar" | "user-keyboard" | "user-tray" | "user-command";

/**
 * One kill-switch fire event broadcast to every broker adapter. Adapters
 * cancel all open orders, set `readOnly = true`, and refuse new orders
 * until the user explicitly resets — `KillSwitchBus.reset()` requires a
 * re-acknowledgment and is exposed through a dedicated route, not an
 * everyday toggle.
 */
export interface KillSwitchEvent {
  /** Epoch milliseconds when the fire was initiated. */
  firedAt: number;
  /** Human-readable reason captured at fire time (free-form). */
  reason: string;
  firedBy: KillSwitchFiredBy;
}

/**
 * Per-subscriber acknowledgment timing, returned by `KillSwitchBus.fire`.
 * The dedicated safety-layer audit checkpoint asserts `maxAckMs < 2000`
 * (BLUEPRINT §6.5 #5 — instrumented benchmark, not approximated).
 */
export interface KillSwitchFireResult {
  event: KillSwitchEvent;
  /** One entry per subscriber that acked, keyed by subscriber name. */
  ackTimesMs: Record<string, number>;
  /** P50 / P95 / max ack time across all subscribers. */
  p50AckMs: number;
  p95AckMs: number;
  maxAckMs: number;
}

// ---------------------------------------------------------------------------
// Audit log
// ---------------------------------------------------------------------------

/**
 * What action an audit-log entry records. The schema is append-only at
 * the SQLite level (triggers in `sidecar/services/audit_log.py` raise on
 * UPDATE/DELETE), and the broker-adapter writer connection has no path
 * to bypass the triggers — verified by the dedicated safety audit suite.
 */
export type AuditLogAction =
  | "order-proposed"
  | "order-confirmed"
  | "order-declined"
  | "order-placed"
  | "order-cancelled"
  | "order-rejected"
  | "kill-switch-fired"
  | "kill-switch-reset"
  | "mode-changed"
  | "read-only-changed"
  | "connection"
  | "disclaimer-ack";

/** One row in the audit log. */
export interface AuditLogEntry {
  /** Monotonically increasing id assigned by SQLite. */
  id: number;
  /** Epoch milliseconds of the event. */
  timestampMs: number;
  /** Broker associated with the action; `"_meta"` for app-wide events. */
  broker: BrokerId | "_meta";
  /** Account id at the broker; `"_meta"` for app-wide events. */
  accountId: string;
  action: AuditLogAction;
  /** Action-specific payload — JSON-encoded in the DB, parsed at read time. */
  payload: Record<string, unknown>;
  /** Where the action originated; mirrors `BrokerOrderSource`. */
  source: "manual" | "ai-agent" | "workflow" | "system";
  /** Free-form outcome string (e.g. `"ok"`, `"rejected: insufficient margin"`). */
  outcome: string;
}

// ---------------------------------------------------------------------------
// Position limits
// ---------------------------------------------------------------------------

/**
 * Per-broker order limits. Configurable per-plugin (user can raise through
 * an explicit confirmation step); the defaults are conservative on purpose.
 *
 * Foundation enforces these in the `BrokerAdapter.propose_order` path —
 * exceeding any limit raises `BrokerError` before any broker API call is
 * made. The dedicated safety audit suite proves this for all seven adapters.
 */
export interface PositionLimits {
  /** Maximum order value (`quantity * limitPrice`) in account currency. */
  maxOrderValueAccountCurrency: number;
  /** Maximum percentage of account equity per single order. */
  maxPercentOfAccount: number;
  /** Maximum total position size per symbol (sum across open orders). */
  maxPositionSizePerSymbol: number;
  /**
   * Daily-loss circuit breaker — when realized + unrealized losses today
   * exceed this value, the adapter flips to read-only until reset.
   */
  dailyLossCircuitBreaker: number;
}

// ---------------------------------------------------------------------------
// Disclaimer flow
// ---------------------------------------------------------------------------

/**
 * Which disclaimer surface a user is acknowledging. v0.5.0 ships three:
 *
 *   - `first-launch-tos`: blocks all broker connections until accepted.
 *     Acked-state stored in keychain under `broker:_meta:first-launch-tos`.
 *   - `broker-first-connect`: per-broker terms reminder; blocks the
 *     connection until accepted. Stored under
 *     `broker:<broker-id>:_meta:first-connect-ack`.
 *   - `first-live-order-this-session`: shown the first time the user
 *     clicks Confirm on a live (not paper) order in a given session;
 *     resets on app restart. Session state in `useSafetyStore`.
 */
export type DisclaimerKind =
  | "first-launch-tos"
  | "broker-first-connect"
  | "first-live-order-this-session";

/** A user's acknowledgment of one disclaimer surface. */
export interface DisclaimerAcknowledgment {
  kind: DisclaimerKind;
  /** Specific broker the ack is for; `null` for `first-launch-tos`. */
  broker: BrokerId | null;
  /** Epoch milliseconds of the ack. */
  ackedAt: number;
}

// ---------------------------------------------------------------------------
// Static-IP detection
// ---------------------------------------------------------------------------

/**
 * Result of comparing the user's detected public IP to their configured
 * static IP. Used by the Kite plugin (and any future broker that sets
 * `BrokerCapabilities.requiresStaticIp = true`). The broker-connect UI
 * surfaces a banner when `matches === false`; the order placement path
 * itself does NOT pre-block (a user behind a VPN/VPS may have the right
 * static IP even when the detected default-route IP differs).
 */
export interface StaticIpStatus {
  /** Detected public IP via a one-shot HTTP call (e.g. `api.ipify.org`). */
  detectedIp: string | null;
  /** User-configured static IP from broker plugin settings. */
  configuredIp: string | null;
  /** `true` iff both are present and equal. */
  matches: boolean;
  /** Free-form message for the UI ("matched", "mismatch", "detection failed"). */
  message: string;
  /** Epoch milliseconds of the detection. */
  detectedAt: number;
}

// ---------------------------------------------------------------------------
// AI-order gate
// ---------------------------------------------------------------------------

/**
 * Specialisation of `BrokerOrderProposal` for AI-originated orders. The
 * confirmation dialog uses this to render the agent-named banner and to
 * keep the Confirm button disabled until the user actively confirms.
 * Identical wire shape to the base proposal — typing the source narrows
 * to `"ai-agent" | "workflow"` and forces `sourceDetails` to include the
 * originator's id + display name.
 */
export interface AiOrderGateProposal extends BrokerOrderProposal {
  source: "ai-agent" | "workflow";
  sourceDetails: {
    /** Agent id (for `source: "ai-agent"`) or workflow id (for `source: "workflow"`). */
    originatorId: string;
    /** Display name to show in the dialog banner. */
    originatorName: string;
    /** Workflow node id when applicable. */
    nodeId?: string;
    /** Free-form rationale captured at propose time (a short agent quote). */
    rationale?: string;
  };
}

// ---------------------------------------------------------------------------
// Aggregated safety store snapshot
// ---------------------------------------------------------------------------

/**
 * The frontend safety store's view, mirroring `useSafetyStore` shape.
 * Used by `KillSwitchToolbar`, `AuditLogViewer`, and `DisclaimerFlow`.
 */
export interface SafetyStoreSnapshot {
  killSwitchFired: boolean;
  killSwitchFiredAt: number | null;
  pendingProposals: BrokerOrderProposal[];
  recentAudit: AuditLogEntry[];
  /** ACKed disclaimers indexed by kind+broker. Session-acks are in-memory only. */
  disclaimerAcks: DisclaimerAcknowledgment[];
}
