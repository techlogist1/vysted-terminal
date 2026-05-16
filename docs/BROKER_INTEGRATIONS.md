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
