# Broker Integrations

Vysted Terminal v0.5.0 ships seven broker execution plugins. Each adapter
inherits the safety-layer-enforced `BrokerAdapter` ABC in
`sidecar/services/broker_base.py` and plugs into the locked `VystedPlugin`
contract in `types/plugin.ts`. Paper mode is the hard-coded default; live
mode requires explicit user opt-in through the broker-connect UI.

## India brokers (Teammate I)

| Broker     | SDK              | Asset coverage                | Static IP required |
| ---------- | ---------------- | ----------------------------- | ------------------ |
| Dhan       | `dhanhq` 2.x     | Equity + options + futures    | No                 |
| Angel One  | `smartapi-python`| Equity + options + futures    | No                 |
| Kite Connect | `kiteconnect`  | Equity + options + forex + futures | **Yes**       |

### Kite Connect — static-IP UX path

SEBI/NSE retail-algo compliance (in effect 2026-04-01) requires a static IP
registered with Kite for order placement API calls. Data, holdings, and
positions endpoints are unaffected. Kite Connect rejects orders from
unregistered IPs at the gateway.

#### Flow

1. The user obtains a static IP (VPS, dedicated home connection, or VPN
   with a static exit IP).
2. The user registers the static IP with Kite through the Kite developer
   console.
3. The user pastes the same static IP into the **Kite plugin → Settings →
   Static IP** field. The plugin's `set-static-ip` control-plane command
   posts to `POST /brokers/kite/static-ip`; the sidecar's `KiteAdapter`
   persists it in-memory for the active session.
4. When the user toggles Kite to live mode through **Broker Connect → Kite
   → Mode → Live**:
   - The route awaits `KiteAdapter.set_mode("live")`.
   - The base `BrokerAdapter.set_mode` writes a `mode-changed` audit row.
   - The Kite override calls `static_ip_detector.static_ip_status()` and
     writes a second `mode-changed` row carrying the detection result.
     The `outcome` field is `"ok"` when `matches=True` and
     `"static-ip-mismatch"` when not.
5. The `<KiteStaticIpBanner />` component (mounted inside Teammate S's
   `BrokerConnectPanel.tsx`) polls `GET /safety/static-ip-status?configured=<ip>`
   on a 30 s interval and re-renders whenever the comparison flips.

#### Graceful rejection UX

The order placement path itself does **not** pre-block on a detected IP
mismatch. A user behind a VPN/VPS with the registered IP may still have
the correct public IP for Kite, even when the local default-route IP
differs. When Kite rejects an order at the gateway (HTTP 403 / SDK
`NetworkException`), the adapter's `_place_confirmed` lets the exception
propagate as `BrokerError(f"kite: place_order failed: {exc}")`; the base
`confirm_and_place` catches it, writes an `order-rejected` audit row, and
re-raises. The order-confirmation dialog in the UI surfaces the error
message; the audit-log viewer shows the rejected proposal with the full
broker error string for forensics. No stack trace is shown to the user.

#### Paper mode

In paper mode the adapter returns synthetic filled order results without
touching the Kite SDK, so the static-IP requirement only matters when the
user has explicitly toggled to live mode. The banner still mounts in paper
mode to surface the comparison eagerly, so users have visibility into the
static-IP status before they commit to live.

## Global brokers (Teammate G)

Alpaca, Interactive Brokers (TWS / IB Gateway), and OANDA — see the
Teammate G section once their adapters are shipped.

## Crypto execution (Teammate X)

ccxt-based execution for Bybit, Binance, Kraken, and Coinbase — see the
Teammate X section once their adapters are shipped.

## Safety guarantees (all brokers)

Every broker adapter inherits the eight `BLUEPRINT.md` §6.5 safety
guarantees through `BrokerAdapter`:

1. Paper mode is the hard-coded default in `__init__`.
2. Every order routes through `propose_order → confirm_and_place` with
   `human_confirmed: bool` — there is no path from the AI layer to a
   placed order that skips the confirmation gate.
3. `PositionLimits` are enforced before any broker API call.
4. Every action is audit-logged to the append-only SQLite log; UPDATE and
   DELETE are refused by SQL triggers.
5. The global kill switch broadcasts to every adapter; subscribers must
   ack within 2 s (instrumented).
6. AI-proposed orders (`source="ai-agent" | "workflow"`) follow the same
   `propose → confirm` flow; v0.5.0 ships no auto-approve mode.
7. Read-only mode is honored at the adapter boundary and re-checked at
   confirm time.
8. Layered disclaimers (first-launch TOS, per-broker first-connect,
   first-live-order-per-session) are recorded as `disclaimer-ack` audit
   rows.

The dedicated safety-audit suite asserts each guarantee against the
integrated codebase before any v0.5.0 release.
