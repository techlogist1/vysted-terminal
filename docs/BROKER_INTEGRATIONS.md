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
# Broker integrations — v0.5.0

Vysted Terminal ships seven broker execution plugins in v0.5.0. Each
plugin is a thin frontend shell over a sidecar `BrokerAdapter` that
inherits the safety-layer-enforced ABC in `sidecar/services/broker_base.py`.
BLUEPRINT §6.5's eight non-negotiables apply uniformly — paper-mode
default, propose → confirm two-step, append-only audit log, kill
switch, position limits, AI-order gate, read-only mode, layered
disclaimers.

This document covers the three **global** brokers (Alpaca, Interactive
Brokers, OANDA) shipped by Teammate G. The Indian brokers (Dhan, Angel
One, Kite) are documented separately by Teammate I; the ccxt crypto
plugin by Teammate X.

## Alpaca

- **Markets:** US equities, options, crypto.
- **SDK:** [`alpaca-py==0.42.0`](https://pypi.org/project/alpaca-py/)
  (the modern replacement for the deprecated `alpaca-trade-api`).
- **Auth:** API key + API secret, BYOK via the OS keychain
  (`broker:alpaca:api_key`, `broker:alpaca:api_secret`).
- **Paper mode:** Alpaca operates a separate "paper" environment with
  its own endpoint. The adapter constructs `TradingClient(paper=True)`
  by default — paper-mode is the v0.5.0 §6.5 #1 default and the SDK's
  own default. Paper trading is free; live trading requires a funded
  Alpaca brokerage account.

### Connecting from the cmd+K bar

```
/alpaca connect
```

Pulls `api_key` + `api_secret` from the keychain and calls the
sidecar's `POST /brokers/alpaca/connect`. The adapter validates the
credentials by hitting `GET /v2/account` once before the route
returns; an invalid key surfaces a clear `BrokerError`.

### Switching to live mode

```
/alpaca live
```

POSTs `mode: live` to `/brokers/alpaca/mode`. The host MUST surface
the live-mode disclaimer (`first-live-order-this-session` per
`types/safety.ts`) before the user confirms — this is enforced by the
broker-connect UI (Teammate S), not the adapter.

## Interactive Brokers (TWS / IB Gateway)

- **Markets:** US + global equities, options, futures, forex (crypto
  is live-only via Paxos and not surfaced — route via the `ccxt`
  plugin for paper-mode crypto).
- **SDK:** [`ib_async==2.1.0`](https://pypi.org/project/ib_async/)
  (the maintained fork of `ib_insync` from the
  [`ib-api-reloaded/ib_async`](https://github.com/ib-api-reloaded/ib_async)
  org; NOT `ib_insync`).
- **Auth:** No web API key. Auth is at the TWS / IB Gateway level
  (the user logs in once in the Java app).

### Hard dependency: TWS or IB Gateway must be running

Interactive Brokers does NOT expose a hosted REST API. The `ib_async`
library speaks IB's proprietary TWS API over a TCP socket to a
**locally-running Java application** — either Trader Workstation (TWS)
or IB Gateway. Vysted Terminal does NOT bundle TWS / IB Gateway; the
user installs and runs them separately.

Default endpoints (paper first per §6.5 #1):

| Application        | Paper port | Live port |
| ------------------ | ---------- | --------- |
| Trader Workstation | **7497**   | 7496      |
| IB Gateway         | 4002       | 4001      |

The adapter selects the paper port from the current mode unless the
user overrides via the connect-credentials `port` field. If TWS / IB
Gateway is NOT running, the sidecar surfaces:

```
ib: TWS or IB Gateway not detected on 127.0.0.1:7497 —
start TWS (or IB Gateway) and retry
```

…and the broker-connect UI renders that as a recovery hint instead of
a stack trace. The test environment expectation is that screenshots
captured without TWS will show this error; the UX shape is the
deliverable, not a live connection.

### Connecting from the cmd+K bar

```
/ib connect
```

Calls `POST /brokers/ib/connect`. The default host is `127.0.0.1` and
the default port is 7497 (TWS paper). To target IB Gateway instead,
the user passes `port: 4002` in the connect command's credentials
payload.

## OANDA v20

- **Markets:** Forex + CFDs.
- **SDK:** [`oandapyV20==0.7.2`](https://pypi.org/project/oandapyV20/)
  — **last released 2021-08**. The library is stable but
  low-maintenance; OANDA's v20 REST API is itself versioned and
  stable. **Users should monitor SDK security advisories
  independently.** A Vysted maintenance audit at each release tag
  will flag any reported CVEs.
- **Auth:** Access token (a long-lived bearer) + the v20 account id,
  BYOK via the OS keychain (`broker:oanda:access_token`,
  `broker:oanda:account_id`).
- **Paper mode:** OANDA provides a free "fxTrade Practice" demo
  environment alongside live fxTrade. The adapter constructs the API
  client with `environment="practice"` by default — that is the
  paper-mode default per §6.5 #1. The user can open a demo fxTrade
  account in seconds at <https://www.oanda.com/forex-trading/fxtrade-demo/>.

### Connecting from the cmd+K bar

```
/oanda connect
```

Calls `POST /brokers/oanda/connect`. The adapter validates the access
token by hitting the v20 `/accounts/{accountID}/summary` endpoint
once.

### Switching to live

```
/oanda live
```

POSTs `mode: live` to `/brokers/oanda/mode`. As with the other
brokers, the host MUST surface the live-mode disclaimer before the
user confirms — and the user must already hold a funded fxTrade live
account; demo access tokens will not authenticate to the live
environment.

## Common patterns across all three

- **Paper-mode default.** No constructor argument flips an adapter to
  live; the only path is through `set_mode("live")` after the
  live-mode disclaimer has been acknowledged in the UI.
- **BYOK keychain access.** The sidecar reads credentials from the
  Tauri-managed OS keychain via the namespaced keys
  `broker:<id>:<field>` (v0.5.0 commit `0ee1663`). The adapters NEVER
  cache credentials beyond the broker-client instance lifetime.
- **Kill switch.** Every adapter subscribes to the kill-switch bus
  in `BrokerAdapter.__init__`. A kill-switch fire forces the adapter
  into read-only mode within 2 s (`max_ack_ms` budget, verified by
  the dedicated safety audit suite owned by Teammate S).
- **Audit log.** Every connect, mode change, propose, confirm,
  decline, place, cancel writes to the append-only SQLite audit log
  (`audit_log.db`). The log is exportable to CSV from the UI.
- **Position limits.** The default `PositionLimits` ($10k max order
  value, $2k daily-loss circuit breaker, 1000 units per symbol) apply
  uniformly. Users raise the caps through explicit confirmation in
  the plugin settings panel.

## Troubleshooting

| Symptom                                              | Likely cause                                                 | Fix                                                                                                               |
| ---------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `alpaca: connect failed — 403`                       | Wrong key set used (live key with paper=true, or vice versa) | Generate paper keys at <https://app.alpaca.markets/paper/dashboard/overview> when running in paper mode.          |
| `ib: TWS or IB Gateway not detected`                 | The Java app isn't running, or it's on a non-default port    | Start TWS / IB Gateway; verify the port in API Settings; pass `port` override if needed.                          |
| `oanda: connect failed — Insufficient authorization` | Demo access token used with live environment (or vice versa) | Generate the token in the matching dashboard — demo tokens only auth to `practice`.                               |
| `kill switch fired — order placement halted`         | The kill switch is in the fired state                        | Re-acknowledge the kill switch in the toolbar; the dedicated reset route requires a second confirmation per §6.5. |
