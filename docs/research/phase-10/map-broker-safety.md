# Phase 10 Map — Broker Integration Layer, §6.5 Safety Boundary, Kite Connect, and the Connect-a-Provider Surface

Date: 2026-05-29
Scope: MAP only. No code changes proposed to any §6.5 LOCKED file
(`sidecar/services/broker_base.py`, `audit_log.py`, `kill_switch.py`,
`types/plugin.ts`, `tests/test_safety_end_to_end.py`). Every claim is cited to
`file:line` against the real source.

---

## 0. TL;DR

- **7 broker execution adapters exist** in `sidecar/services/brokers/` (dhan,
  angelone, kite, alpaca, ib, oanda, ccxt_exec), all inheriting the LOCKED
  `BrokerAdapter` ABC. These are **execution** adapters — they DO place orders
  via `_place_confirmed` — gated by §6.5, NOT read-only.
- **The "read-only / no-place / GET-only / supportsControlPlane=false" pattern
  in the task brief describes the Tradesa V2 wrapper plugin (v0.6.5), NOT the
  Phase 5 broker adapters.** The broker plugins are `supportsControlPlane=true`
  and the brokers router has POST routes. Do not conflate the two.
- **Kite has NO real OAuth `request_token → access_token` daily flow anywhere in
  the codebase.** `KiteAdapter._connect` accepts an already-resolved
  `access_token` and an `api_key` only (`kite.py:76-77`). There is no
  `generate_session`, no `login_url`, no `request_token` exchange, no use of
  `api_secret`. The UI collects `api_secret` (`BrokerConnectPanel.tsx:53`) but
  the sidecar never reads it. The user must obtain the daily access token
  externally and paste it. This is the single biggest gap to a real "connect
  your broker" hub.
- **Read-only endpoints (positions/holdings/P&L) exist only as one fused route:**
  `GET /brokers/{id}/account` returns `AccountSummary` (equity, cash,
  buyingPower, positions[] with unrealizedPnl). There is no separate
  `/positions`, `/holdings`, or `/margins` route in the brokers router.
- **There is no unified user-facing "Connect your broker" hub.** Broker
  connection lives in a dockview panel (`BrokerConnectPanel`), entirely separate
  from the Settings surface (`SettingsPanel.tsx`), which only has an "AI
  Providers (BYOK)" section. The 7 broker _plugins_ under `plugins/brokers/` are
  NOT bundled into the app (`plugin-bootstrap.ts:45-49`), so their slash
  commands / control-plane commands (`kite.connect`, `set-static-ip`, etc.) are
  dead code at runtime.

---

## 1. The §6.5 safety boundary (LOCKED — read-only understanding)

### 1.1 The ABC contract — `sidecar/services/broker_base.py` (LOCKED)

`BrokerAdapter(ABC)` (`broker_base.py:69`) is the single safety-layer-enforced
order entry point. Subclasses implement only four abstract methods
(`broker_base.py:461-480`):

- `_connect(credentials)` — open the session
- `_account_info()` — read account + positions (no mutation, no audit row;
  `broker_base.py:215-217`)
- `_place_confirmed(proposal)` — place an already-confirmed order
- `_cancel_order(broker_order_id)` — cancel

The non-overridable public surface enforces the eight §6.5 non-negotiables:

| #   | Guarantee                              | Code location                                                                                                                                                                        |
| --- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Paper mode hard-coded default          | `broker_base.py:94` `self._mode = "paper"` in `__init__`; no constructor arg flips it                                                                                                |
| 2   | Every order confirmed; no bypass       | `_place_confirmed` only called from `confirm_and_place` (`broker_base.py:365`); `confirm_and_place` requires `human_confirmed=True` (`broker_base.py:325`)                           |
| 3   | Position limits before any broker call | `propose_order` checks `max_order_value_account_currency` (`broker_base.py:269`) + `max_position_size_per_symbol` (`broker_base.py:274`); `DEFAULT_LIMITS` at `broker_base.py:82-87` |
| 4   | Append-only audit log                  | every state-changing method calls `audit_log.append(...)`; DB-level triggers live in the LOCKED `models/audit_log.py`                                                                |
| 5   | Kill switch subscription forced        | `broker_base.py:103` `self._unsubscribe = kill_switch.get_bus().subscribe(...)` in `__init__` — cannot instantiate an adapter without subscribing                                    |
| 6   | AI-order gate                          | `propose_order(source="ai-agent"\|"workflow")` writes audit but never places (`broker_base.py:223-308`); no auto-approve path                                                        |
| 7   | Read-only mode                         | checked in `propose_order` (`broker_base.py:253`) AND re-checked in `confirm_and_place` (`broker_base.py:347`); kill-switch handler forces `_read_only=True` (`broker_base.py:441`)  |
| 8   | Layered disclaimers                    | mode/connect changes audited; session ack in `disclaimer_session.py`                                                                                                                 |

The two-step is: `propose_order` (sync, audit-logs `order-proposed`, returns
`BrokerOrderProposal`) → user confirms → `confirm_and_place(proposal,
human_confirmed=True)` (re-checks gates, calls `_place_confirmed`, audit-logs
`order-confirmed` then `order-placed`/`order-rejected`).

### 1.2 §6.5 reference status

`docs/SAFETY_ARCHITECTURE.md:3-7` records the audit suite passing 9/9 at v0.5.0
and that **live execution is ENABLED**. The per-guarantee `file:line` map is in
that doc (lines 20-29 table, 31-196 detail). `docs/BROKER_INTEGRATIONS.md:77-100`
restates the eight guarantees per broker.

---

## 2. The broker integration layer that EXISTS today

### 2.1 Sidecar adapters — `sidecar/services/brokers/`

All seven define `_place_confirmed` (i.e. they place real orders):

```
alpaca.py:158    _place_confirmed → self._client.submit_order  (alpaca.py:219)
angelone.py:120  _place_confirmed
dhan.py:152      _place_confirmed → self._client.place_order   (dhan.py:167)
ib.py:220        _place_confirmed
ccxt_exec.py:289 _place_confirmed
kite.py:208      _place_confirmed → self._client.place_order   (kite.py:238)
oanda.py:177     _place_confirmed
```

`BrokerId` literal type (`models/broker.py:24-35`): `dhan`, `angelone`, `kite`,
`alpaca`, `ib`, `oanda`, `ccxt-bybit`, `ccxt-binance`, `ccxt-kraken`,
`ccxt-coinbase`.

Registry (`services/brokers/registry.py`): module-singleton dict keyed by
`BrokerId`. `bootstrap_default_adapters()` (`registry.py:97-112`) instantiates
**only the three India adapters** (Dhan, Angel One, Kite) at startup;
Alpaca/IB/OANDA/ccxt are wired through their own bootstrap entrypoints (comment
`registry.py:13-14`). The router resolves via `registry.get()` so tests can
substitute fakes.

### 2.2 The brokers router — `sidecar/routers/brokers.py`

Routes (`brokers.py:140-309`):

| Method | Route                                        | Purpose                                             |
| ------ | -------------------------------------------- | --------------------------------------------------- |
| GET    | `/brokers`                                   | list all adapter `BrokerState`s                     |
| GET    | `/brokers/{id}/state`                        | one broker's state                                  |
| POST   | `/brokers/{id}/connect`                      | open session (credentials in **body**)              |
| GET    | `/brokers/{id}/account`                      | **the only read route — account + positions + P&L** |
| POST   | `/brokers/{id}/orders`                       | propose order                                       |
| POST   | `/brokers/{id}/orders/{proposal_id}/confirm` | confirm + place                                     |
| POST   | `/brokers/{id}/orders/cancel`                | cancel                                              |
| POST   | `/brokers/{id}/mode`                         | paper/live toggle                                   |
| POST   | `/brokers/{id}/read-only`                    | read-only toggle                                    |
| GET    | `/brokers/kite/static-ip`                    | get configured static IP                            |
| POST   | `/brokers/kite/static-ip`                    | set configured static IP                            |

The router is intentionally thin (`brokers.py:1-23`): it parses the body,
resolves the adapter, awaits the method, translates `BrokerError → HTTP 400`.
The `_pending_proposals` in-memory dict (`brokers.py:119`) holds proposals
between propose and confirm; lost on sidecar restart by design.

> **Distinction from the read-only wrapper pattern.** The task brief's "no
> insert/place/submit, GET-only routers, supportsControlPlane=false" is the
> **Tradesa V2** read-only wrapper pattern (`plugins/tradesa-v2/index.ts:80`
> `supportsControlPlane: false`; `routers/tradesa_v2.py` is entirely
> `@router.get`). The Phase 5 broker adapters are the OPPOSITE: they have POST
> routes (`brokers.py:153,181,210,240,253,270,302`) and the broker plugins set
> `supportsControlPlane: true` (`plugins/brokers/kite/index.ts:53`,
> alpaca/oanda/angelone/ib/dhan all `true`). Only `ccxt-exec`
> (`plugins/brokers/ccxt-exec/index.ts:73`) is `false`.

### 2.3 Read-only endpoints (positions / holdings / P&L)

There is **one** read route: `GET /brokers/{id}/account` (`brokers.py:171-178`)
→ `adapter.account_info()` → `AccountSummary` (`models/broker.py:109-121`):
`equity`, `cash`, `buyingPower`, `positions: list[BrokerPosition]`,
`capturedAt`. Each `BrokerPosition` (`models/broker.py:97-106`) carries `symbol`,
`quantity`, `averageCost`, `marketValue`, `unrealizedPnl`.

Kite maps broker holdings into this shape: `_account_info` (`kite.py:170-202`)
returns synthetic paper data in paper mode (₹1,000,000 equity) and, in live
mode, calls `self._client.margins()` + `self._client.holdings()` and translates
via `_translate_kite_holdings` (`kite.py:298-315`). **There is no separate
`/positions`, `/holdings`, or `/margins` HTTP route** — the task brief implies
those might exist; they do not. All P&L flows through `/account`.

---

## 3. Kite Connect — what EXISTS vs. the OAuth gap

### 3.1 What the Kite adapter actually does (`sidecar/services/brokers/kite.py`)

`KiteAdapter._connect` (`kite.py:69-102`):

```
api_key      = credentials.get("api_key") or credentials.get("apiKey")
access_token = credentials.get("access_token") or credentials.get("accessToken")
if not api_key or not access_token: raise BrokerError(...)          # kite.py:78-81
configured_ip = credentials.get("static_ip") or credentials.get("staticIp")  # kite.py:85
client = KiteConnect(api_key=api_key)                                # kite.py:94
client.set_access_token(access_token)                                # kite.py:95
profile = client.profile()                                           # kite.py:97
self._account_id = profile["user_id"]                                # kite.py:102
```

**It consumes a pre-resolved `access_token`. It NEVER:**

- calls `kite.login_url()` to start OAuth,
- accepts a `request_token`,
- calls `kite.generate_session(request_token, api_secret)` to mint the daily
  access token,
- uses `api_secret` at all.

The adapter's own docstring admits this (`kite.py:13-17`): "the user logs in at
kite.zerodha.com and pastes the URL back into the plugin... **The adapter
expects the frontend to handle the token-refresh dance** — the credentials dict
at `_connect` time carries the resolved `api_key` + `access_token`."

**No frontend code does that dance.** Grep for `generate_session`,
`request_token`, `login_url`, `checksum` across `src/`, `plugins/`, `sidecar/`
returns ZERO hits for Kite. The only `generate_session` hit is **Angel One**
(`angelone.py:76` `client.generateSession(client_code, password, totp)`), which
does implement a real OAuth-style session exchange. Kite does not.

### 3.2 The contradiction in the UI credentials form

`BrokerConnectPanel.tsx:51-56` declares Kite fields:

```
api_key      → "API Key"
api_secret   → "API Secret"        # <-- collected, stored in keychain, NEVER used by sidecar
access_token → "Access Token"      # <-- user must paste the resolved daily token
static_ip    → "Static IP (SEBI rule)"
```

The dialog stores every field to the keychain
(`BrokerConnectPanel.tsx:292-294` `setSecret(broker(id, key), value)`) and POSTs
them all to `/brokers/kite/connect` (`brokers.ts:78-92`). The sidecar silently
ignores `api_secret`. So today's UX is: _the user is asked for an API secret
that does nothing, and must separately go to Zerodha, generate a request_token,
exchange it for a daily access_token by hand (or with an external script), and
paste that token back in — every single trading day._ That is the gap.

### 3.3 Order placement at Kite (`kite.py:208-261`)

Paper mode short-circuits to `_synthetic_paper_result` (imported from
`dhan.py`). Live mode builds Kite SDK params (`kite.py:225-235`,
`variety=regular`, `product=CNC`, exchange via `_kite_exchange` NSE/BSE,
order_type via `_kite_order_type`) and calls `self._client.place_order(**params)`
on a thread. Any SDK exception (including the SEBI static-IP 403) propagates as
`BrokerError("kite: place_order failed: ...")`, which the LOCKED
`confirm_and_place` catches and audit-logs as `order-rejected`.

### 3.4 The static-IP detector + banner (EXISTS, works, but mis-wired in UI)

- Detector: `services/static_ip_detector.py`. `detect_public_ip` (line 39)
  does a one-shot `httpx` GET to `https://api.ipify.org` (`DEFAULT_IP_ECHO_URL`,
  line 36); never raises. `static_ip_status(configured_ip)` (line 79) returns a
  `StaticIpStatus` with `detectedIp`, `configuredIp`, `matches`, `message`.
- Adapter override: `KiteAdapter.set_mode` (`kite.py:126-164`) defers to the
  LOCKED base `set_mode`, then on `"live"` runs the detector and writes a second
  `mode-changed` audit row with `outcome="ok"` or `"static-ip-mismatch"`
  (`kite.py:162`). Never pre-blocks placement (`kite.py:6-9` rationale: VPN/VPS).
- Configured-IP storage: `set_configured_static_ip` / `configured_static_ip`
  (`kite.py:108-124`), surfaced via `GET/POST /brokers/kite/static-ip`
  (`brokers.py:293-309`).
- Safety route: `GET /safety/static-ip-status?configured=<ip>`
  (`safety.py:186-193`) → `static_ip_detector.static_ip_status(configured)`.
- Banner component: `kite-static-ip-banner.tsx`. Polls the safety route every
  30 s (`kite-static-ip-banner.tsx:63,124`), renders loading/ok/mismatch/error
  variants.

**Mis-wire / bug (medium):** `BrokerConnectPanel.tsx:254` mounts the banner with
`configuredIp={null}` hardcoded, so the banner always asks the safety route with
no `configured=` param and always reports "No static IP configured". The
adapter does store the configured IP (the user can set it via the static-IP
route), but the panel never reads it back from `GET /brokers/kite/static-ip` to
feed the banner. The banner is also only mounted when `state.mode === "live"`
(`BrokerConnectPanel.tsx:252`), contradicting `BROKER_INTEGRATIONS.md:62-65`
which says "the banner still mounts in paper mode to surface the comparison
eagerly." Doc and code disagree; code wins.

---

## 4. The current "connect a provider" surface(s)

### 4.1 Settings panel — `src/components/SettingsPanel.tsx`

Four sections (`SettingsPanel.tsx:53-56`): **AI Providers (BYOK)**, Layouts,
Modules, About. The AI Providers section (`ProvidersSection`, line 68) is the
canonical "where do I put my key" surface — per-provider add/update/remove key
into the OS keychain via `KEYCHAIN_NAMESPACES.llmProvider(id)` + a
default-provider picker. **There is NO broker section here.** Brokers are not
discoverable from Settings at all.

### 4.2 Broker-connect module — `src/modules/broker-connect/`

The actual broker surface is a dockview module (`broker-connect/index.ts:12-55`)
with two panels:

- `broker-connect-panel` → `BrokerConnectPanel` (connection manager)
- `broker-order-entry` → `BrokerOrderEntry` (manual order proposal form)

Registered in `src/modules/index.ts:67` (`brokerConnectModule`). It reads
`GET /brokers` via `useBrokersStore` (`store/brokers.ts:53-66`) and renders one
row per adapter with status/mode/read-only badges, a Connect button (opens
`CredentialsDialog`), and per-broker first-connect disclaimer
(`BrokerConnectPanel.tsx:281-298`). Connect is gated on the first-launch TOS ack
(`BrokerConnectPanel.tsx:145-149,161`).

Credential flow (matches the documented BYOK pattern, `keychain.ts:14-15`):
renderer collects fields → `setSecret(broker(id, field), value)` to OS keychain
→ then passes the same plaintext values as `connect(broker, credentials)` →
`store/brokers.ts:78-92` POSTs `{ credentials }` in the **request body** to
`/brokers/{id}/connect`. (Note: broker-connect uses the BODY, not headers; the
headers-not-body pattern is specific to the Tradesa V2 read-only wrapper per
CLAUDE.md, not to broker execution connect.)

### 4.3 The broker PLUGINS are dead code at runtime

`plugins/brokers/{kite,alpaca,dhan,angelone,ib,oanda,ccxt-exec}/index.ts` each
define a full `VystedPlugin` with slash commands and control-plane commands (the
Kite plugin's `set-static-ip`, `connect`, `static-ip-status`, etc. —
`plugins/brokers/kite/index.ts:67-100,215-233`). **None are bundled.**
`BUNDLED_PLUGINS` (`plugin-bootstrap.ts:45-49`) imports only `example`,
`openbb-mcp`, `tradesa-v2`. So:

- The Kite plugin's `set-static-ip` control-plane command is unreachable.
- `BROKER_INTEGRATIONS.md:30-33` and `kite-static-ip-banner.tsx:14-18` both
  describe the user setting the static IP "through the Kite plugin → Settings"
  — but that plugin isn't loaded, so that path doesn't exist in the running app.
- The cmd+K `/alpaca connect`, `/oanda connect` flows in
  `BROKER_INTEGRATIONS.md:130-242` don't fire either.

The only live broker surface is the `broker-connect` **module** (sections 4.2),
which talks directly to the sidecar HTTP routes and bypasses the plugin layer
entirely.

---

## 5. Bugs / gaps found (verified against source)

### 5.1 `/brokers/{id}/disconnect` route does not exist (medium)

`store/brokers.ts:94-104` `disconnect()` POSTs to `/brokers/{id}/disconnect`,
but `routers/brokers.py` has no such route (grep: no `disconnect` in
`brokers.py`). A disconnect call would 404. Latent only because
`BrokerConnectPanel` never calls `disconnect` today (no UI button wired to it).

### 5.2 Kite `api_secret` collected but never used; no OAuth exchange (high — the core Phase 10 gap)

`BrokerConnectPanel.tsx:53` collects `api_secret`; `kite.py:_connect` never reads
it. No `generate_session`/`request_token`/`login_url` exists. Users must
hand-resolve the daily access token externally. This is the headline gap to a
real "connect your broker" hub. (Fix lives entirely OUTSIDE the §6.5 LOCKED
files — it is new OAuth plumbing in `kite.py` + a new sidecar route + UI; the
`BrokerAdapter` contract is untouched.)

### 5.3 Static-IP banner hardcodes `configuredIp={null}` (medium)

`BrokerConnectPanel.tsx:254`. Banner never receives the adapter's stored
configured IP, so it always reports "no static IP configured" even after the
user sets one. Panel should fetch `GET /brokers/kite/static-ip` and pass
`configuredIp`.

### 5.4 Banner mount condition contradicts docs (low)

`BrokerConnectPanel.tsx:252` only mounts the banner in live mode;
`BROKER_INTEGRATIONS.md:62-65` says it mounts in paper mode too.

### 5.5 Broker plugins unbundled → plugin commands dead (medium, product gap)

`plugin-bootstrap.ts:45-49`. The `plugins/brokers/*` slash/control-plane commands
documented in `BROKER_INTEGRATIONS.md` are not reachable; the only working
broker surface is the `broker-connect` module.

### 5.6 No broker section in Settings; no unified provider hub (medium, product gap)

`SettingsPanel.tsx:53-56` has AI Providers but no brokers. Broker connection is
discoverable only by opening the `broker-connect` dockview panel. A real
"connect your broker" hub would unify these.

---

## 6. Where Phase 10 work plugs in (without touching LOCKED files)

A real Kite OAuth + connect-hub feature is buildable entirely outside §6.5:

- **New sidecar OAuth plumbing in `kite.py` (NOT locked):** add a
  `kite.login_url()` passthrough and a `generate_session(request_token,
api_secret)` exchange that mints + returns the daily `access_token`. Surface
  via NEW routes in `routers/brokers.py` (e.g. `GET /brokers/kite/login-url`,
  `POST /brokers/kite/session`). The `BrokerAdapter` ABC stays untouched —
  `_connect` still receives the resolved `access_token`; you are only adding the
  step that produces it.
- **Tauri deep-link / redirect capture** for the Zerodha `redirect_url` carrying
  `request_token` (Rust side, no §6.5 impact).
- **Settings "Brokers" section** mirroring `ProvidersSection`
  (`SettingsPanel.tsx:68`), or promote `BrokerConnectPanel` into a
  Settings-embedded hub. Reuse `KEYCHAIN_NAMESPACES.broker(id, field)`
  (`keychain.ts:46`).
- **Fix 5.1, 5.3, 5.4, 5.5** as part of the hub polish.

None of the above edits `broker_base.py`, `audit_log.py`, `kill_switch.py`,
`types/plugin.ts`, or `test_safety_end_to_end.py`. The propose→confirm→place
gate and the read-only/account read path are reused as-is.

---

## 7. File:line index (quick reference)

- LOCKED ABC: `sidecar/services/broker_base.py` (paper default :94, propose
  :223, confirm :310, place call :365, kill-switch sub :103)
- Kite adapter: `sidecar/services/brokers/kite.py` (connect :69, no-secret
  :76-81, set_mode static-ip :126, place :208, holdings translate :298)
- Angel One real OAuth (contrast): `sidecar/services/brokers/angelone.py:76`
- Brokers router: `sidecar/routers/brokers.py` (account read :171, propose :181,
  confirm :210, kite static-ip :293/:302)
- Safety router: `sidecar/routers/safety.py` (static-ip-status :186)
- Static-IP detector: `sidecar/services/static_ip_detector.py` (detect :39,
  status :79, ipify url :36)
- Broker models: `sidecar/models/broker.py` (BrokerId :24, AccountSummary :109,
  BrokerPosition :97, ConnectRequest body :138)
- Registry: `sidecar/services/brokers/registry.py:97` bootstrap (India only)
- Frontend connect panel: `src/modules/broker-connect/BrokerConnectPanel.tsx`
  (kite fields :51, api_secret :53, banner mount :252, configuredIp null :254)
- Banner: `src/modules/broker-connect/kite-static-ip-banner.tsx` (poll :124)
- Brokers store: `src/store/brokers.ts` (connect body :78, missing disconnect
  :94)
- Keychain: `src/lib/keychain.ts` (broker namespace :46, body-not-storage :14)
- Settings (no broker section): `src/components/SettingsPanel.tsx:53-56`
- Plugin bundling (brokers absent): `src/lib/plugin-bootstrap.ts:45-49,81-83`
- Module registration: `src/modules/broker-connect/index.ts:12`,
  `src/modules/index.ts:67`
- Docs: `docs/BROKER_INTEGRATIONS.md`, `docs/SAFETY_ARCHITECTURE.md`
