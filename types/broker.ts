/**
 * Vysted Terminal — broker integration wire contract.
 *
 * Phase 5 ships six broker execution plugins plus a ccxt crypto execution
 * extension on the locked `VystedPlugin` contract. Each broker adapter
 * inherits the safety-layer-enforced `BrokerAdapter` ABC in the sidecar
 * (`services/broker_base.py`), so every order — manual OR AI-proposed —
 * routes through the SAME order-confirmation envelope, audit log, and
 * kill-switch handler. There is no path from the AI layer to a broker's
 * `place_order` call that does not pass the human-confirmation gate.
 *
 * BLUEPRINT §6.5's eight non-negotiables are enforced at this contract
 * level + the runtime in `broker_base.py`:
 *
 *   1. Paper mode is the default (`BrokerMode = "paper"` on construction).
 *   2. Every order confirmed (the `BrokerOrderProposal → confirm → place`
 *      flow; `_place_confirmed` is private in the sidecar adapter).
 *   3. Position limits (`PositionLimits` in `types/safety.ts`).
 *   4. Append-only audit log (`AuditLogEntry` in `types/safety.ts`).
 *   5. Global kill switch (`KillSwitchEvent` in `types/safety.ts`).
 *   6. AI-order gate (`source: "ai-agent" | "workflow"` proposals open the
 *      confirmation dialog defaulted to declined and named the agent).
 *   7. Read-only mode (per-plugin flag, enforced at the adapter boundary).
 *   8. Layered disclaimers (`DisclaimerAcknowledgment` in `types/safety.ts`).
 *
 * `types/plugin.ts` stays Tier-1 locked. Brokers plug in through the
 * existing capabilities: `contributesData` (account read), `contributesPanels`
 * (broker-specific panels), `contributesCommands` (`/connect alpaca`, etc.),
 * `executeCommand` for the control plane (`"place-order"`, `"halt-trading"`,
 * `"set-read-only"`, `"set-mode"`).
 */

// ---------------------------------------------------------------------------
// Identity
// ---------------------------------------------------------------------------

/**
 * Stable broker identifier. The seven v0.5.0 brokers + per-exchange ccxt
 * adapters. Each ccxt exchange counts as a distinct id so the broker-connect
 * UI lists them independently.
 */
export type BrokerId =
  | "dhan"
  | "angelone"
  | "kite"
  | "alpaca"
  | "ib"
  | "oanda"
  | "ccxt-bybit"
  | "ccxt-binance"
  | "ccxt-kraken"
  | "ccxt-coinbase";

// ---------------------------------------------------------------------------
// Mode + status
// ---------------------------------------------------------------------------

/**
 * Trading mode. `"paper"` is the hard-coded default at every adapter; flipping
 * to `"live"` requires the first-live-order-per-session disclaimer
 * acknowledgment (`DisclaimerKind.firstLiveOrderThisSession` in
 * `types/safety.ts`).
 */
export type BrokerMode = "paper" | "live";

/** Connection lifecycle state for the broker-connect UI badge. */
export type BrokerConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

/** What the broker adapter can do, surfaced to the order-entry UI. */
export interface BrokerCapabilities {
  supportsEquity: boolean;
  supportsOptions: boolean;
  supportsCrypto: boolean;
  supportsForex: boolean;
  supportsFutures: boolean;
  /**
   * SEBI/NSE retail-algo compliance flag (2026-04-01 enforcement). Currently
   * set true for `kite`; the broker-connect UI surfaces a static-IP status
   * banner when this is true and the detected public IP differs from the
   * user's configured static IP.
   */
  requiresStaticIp: boolean;
}

// ---------------------------------------------------------------------------
// Orders
// ---------------------------------------------------------------------------

/** Order side. */
export type BrokerOrderSide = "buy" | "sell";

/** Order type. */
export type BrokerOrderType = "market" | "limit" | "stop" | "stop-limit";

/**
 * Where the order proposal originated. Determines which confirmation dialog
 * variant fires: `"manual"` opens a normal confirm; `"ai-agent" | "workflow"`
 * opens with Confirm disabled by default and the originating-agent banner
 * visible (BLUEPRINT §6.5 #6 — tightened in v0.5.0 to remove the auto-approve
 * mode mentioned in the BLUEPRINT; see plan §"Tier-2/3 autonomous decisions").
 */
export type BrokerOrderSource = "manual" | "ai-agent" | "workflow";

/**
 * A proposed order — written to the audit log AS SOON as it is proposed
 * (`AuditLogAction.orderProposed`) and held in the orders inbox until the
 * user confirms or declines. The broker adapter NEVER places an order
 * directly off this object; the `confirm_and_place` path requires
 * `human_confirmed: bool` in the sidecar contract.
 */
export interface BrokerOrderProposal {
  /** Stable id assigned by the sidecar at propose time; used in audit + confirm. */
  proposalId: string;
  broker: BrokerId;
  /** Broker account id; relevant when the user has multiple accounts at one broker. */
  accountId: string;
  symbol: string;
  side: BrokerOrderSide;
  type: BrokerOrderType;
  /** Order quantity in shares / contracts / units; broker-specific. */
  quantity: number;
  /** Limit price if `type` is `"limit"` or `"stop-limit"`. */
  limitPrice?: number;
  /** Stop trigger price if `type` is `"stop"` or `"stop-limit"`. */
  stopPrice?: number;
  /** Account currency; broker-reported. */
  currency: string;
  /** Adapter's estimate of fill cost — `quantity * (limitPrice ?? last)`. */
  estimatedValue: number;
  source: BrokerOrderSource;
  /**
   * Free-form context about the originator. For `source: "ai-agent"`:
   * `{ "agentId": "<id>", "agentName": "<name>" }`. For
   * `source: "workflow"`: `{ "workflowId": "<id>", "nodeId": "<id>" }`.
   */
  sourceDetails: Record<string, unknown>;
  /** Epoch milliseconds when the proposal was created. */
  proposedAt: number;
}

/** Outcome of placing a confirmed order at the broker. */
export interface BrokerOrderResult {
  proposalId: string;
  broker: BrokerId;
  /** Broker-assigned order id; absent when the broker rejected synchronously. */
  brokerOrderId?: string;
  status: "filled" | "partial" | "open" | "cancelled" | "rejected";
  /** The full request payload sent to the broker, captured for the audit log. */
  requestPayload: Record<string, unknown>;
  /** The full response received from the broker (or the error envelope). */
  responsePayload: Record<string, unknown>;
  /** Adapter-side error message if `status` is `"rejected"`. */
  error?: string;
  /** Epoch milliseconds when the placement completed. */
  placedAt: number;
}

// ---------------------------------------------------------------------------
// Account read surface
// ---------------------------------------------------------------------------

/**
 * A single open position at a broker. Renamed `BrokerPosition` to avoid a
 * name collision with the local-portfolio `Position` in `types/data.ts`
 * (the local-portfolio shape mirrors `sidecar/models/portfolio.py` and
 * uses snake_case field names like `cost_basis`).
 */
export interface BrokerPosition {
  symbol: string;
  quantity: number;
  /** Average cost per unit in account currency. */
  averageCost: number;
  /** Mark-to-market value of the position at the time of the snapshot. */
  marketValue: number;
  /** Unrealized P&L; absent when the broker does not report it. */
  unrealizedPnl?: number;
}

/** Account summary returned by `GET /brokers/{id}/account`. */
export interface AccountSummary {
  broker: BrokerId;
  accountId: string;
  currency: string;
  /** Total account equity. */
  equity: number;
  /** Cash available for new orders. */
  cash: number;
  /** Buying power (cash + margin). */
  buyingPower: number;
  positions: BrokerPosition[];
  /** Epoch milliseconds when this snapshot was captured. */
  capturedAt: number;
}

// ---------------------------------------------------------------------------
// Connection state
// ---------------------------------------------------------------------------

/**
 * Per-broker connection state surfaced to the broker-connect UI + the orders
 * store. Read-only-mode is independent from connection state — a connected
 * broker can still be read-only by user choice or broker permission level.
 */
export interface BrokerState {
  broker: BrokerId;
  status: BrokerConnectionStatus;
  mode: BrokerMode;
  readOnly: boolean;
  capabilities: BrokerCapabilities;
  /** Adapter-reported error message if `status` is `"error"`. */
  error?: string;
  /** Last time the adapter heard from the broker (account fetch, ping, etc.). */
  lastSeenAt?: number;
}
